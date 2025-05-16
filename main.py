from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import sys
from typing import Dict, Any, List
import os
from pydantic import BaseModel
import sys
import logging
from datetime import datetime
import json
import asyncio
from queue import Queue
import threading

# Configure logging
class WebSocketLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.websocket_connections: List[WebSocket] = []
        self.log_queue = Queue()
        self.worker_thread = threading.Thread(target=self._process_logs, daemon=True)
        self.worker_thread.start()

    def emit(self, record):
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': record.levelname,
                'message': self.format(record)
            }
            self.log_queue.put(log_entry)
        except Exception:
            self.handleError(record)

    def _process_logs(self):
        while True:
            log_entry = self.log_queue.get()
            asyncio.run(self._broadcast_log(log_entry))

    async def _broadcast_log(self, log_entry):
        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(log_entry)
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.websocket_connections.remove(websocket)

    def add_connection(self, websocket: WebSocket):
        self.websocket_connections.append(websocket)

    def remove_connection(self, websocket: WebSocket):
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)

# Create custom handler instance
websocket_handler = WebSocketLogHandler()
websocket_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        websocket_handler
    ]
)
logger = logging.getLogger(__name__)

print("PYTHON EXECUTABLE:", sys.executable)

app = FastAPI(title="Stock Analysis API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = datetime.now()
    logger.info(f"Request started: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        process_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Request completed: {request.method} {request.url} - Status: {response.status_code} - Time: {process_time:.2f}s")
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url} - Error: {str(e)}")
        raise

# WebSocket endpoint for live logs
@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_handler.add_connection(websocket)
    logger.info("New WebSocket connection established for logs")
    try:
        while True:
            # Keep the connection alive and wait for client messages
            data = await websocket.receive_text()
            # You can handle any client messages here if needed
    except WebSocketDisconnect:
        websocket_handler.remove_connection(websocket)
        logger.info("WebSocket connection closed")

class ChatRequest(BaseModel):
    query: str

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection)
            except Exception as e:
                logger.error(f"Error broadcasting message: {str(e)}")
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle any client messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def stream_process_output(process):
    """Stream process output in real-time"""
    while True:
        # Read stdout
        output = process.stdout.readline()
        if output:
            # Check if the output is a warning
            if "UserWarning" in output or "warn(" in output:
                await manager.broadcast({
                    "type": "warning",
                    "data": output.strip()
                })
            else:
                await manager.broadcast({
                    "type": "output",
                    "data": output.strip()
                })
        
        # Read stderr
        error = process.stderr.readline()
        if error:
            # Only broadcast as error if it's not a warning
            if "UserWarning" not in error and "warn(" not in error:
                await manager.broadcast({
                    "type": "error",
                    "data": error.strip()
                })
            else:
                await manager.broadcast({
                    "type": "warning",
                    "data": error.strip()
                })
        
        # Check if process has finished
        if process.poll() is not None:
            # Read any remaining output
            remaining_output = process.stdout.read()
            remaining_error = process.stderr.read()
            
            if remaining_output:
                await manager.broadcast({
                    "type": "output",
                    "data": remaining_output.strip()
                })
            if remaining_error:
                await manager.broadcast({
                    "type": "error",
                    "data": remaining_error.strip()
                })
            
            # Send completion message
            await manager.broadcast({
                "type": "process_complete",
                "data": f"Process completed with return code: {process.returncode}"
            })
            break
        
        # Small delay to prevent CPU overuse
        await asyncio.sleep(0.1)

def run_script(script_path: str) -> Dict[str, Any]:
    try:
        # Get the absolute path of the script
        abs_script_path = os.path.abspath(script_path)
        # Get the directory containing the script
        script_dir = os.path.dirname(abs_script_path)
        # Get the project root directory
        project_root = os.path.dirname(os.path.abspath(__file__))
        
        # Set up the environment with the correct Python path
        env = os.environ.copy()
        python_path = os.pathsep.join([
            project_root,  # Add project root
            script_dir,    # Add script directory
            os.path.join(project_root, 'config')  # Add config directory
        ])
        env["PYTHONPATH"] = python_path
        
        process = subprocess.Popen(
            [sys.executable, abs_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
            cwd=project_root  # Set working directory to project root
        )
        
        # Start a background task to stream the output
        asyncio.create_task(stream_process_output(process))
        
        return {
            "status": "success",
            "process": process
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e)
            }
        )

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Stock Analysis API is running"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Execute the stock analyzer with a query"""
    logger.info(f"Chat request received with query: {request.query}")
    try:
        # Import the analyze_stock_query function
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from YOUTUBE.stock_analyzer import analyze_stock_query
        
        # Execute the analysis and stream results
        result = analyze_stock_query(request.query)
        await manager.broadcast({
            "type": "chat_response",
            "data": result
        })
        return {"status": "processing"}
    except Exception as e:
        logger.error(f"Chat analysis failed: {str(e)}")
        await manager.broadcast({
            "type": "error",
            "data": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e)
            }
        )

@app.post("/execute/youtube-fetcher")
async def execute_youtube_fetcher():
    """Execute the YouTube fetcher tool"""
    result = run_script("YOUTUBE/Tools/youtube_fetcher_tool.py")
    if result["status"] == "success":
        await manager.broadcast({
            "type": "process_started",
            "data": "YouTube fetcher process started"
        })
        return {"status": "processing"}
    return result

@app.post("/execute/transcript-analyzer")
async def execute_transcript_analyzer():
    """Execute the transcript analyzer tool"""
    result = run_script("YOUTUBE/Tools/transcript_analyzer_tool.py")
    if result["status"] == "success":
        await manager.broadcast({
            "type": "process_started",
            "data": "Transcript analyzer process started"
        })
        return {"status": "processing"}
    return result

@app.post("/execute/yahoo-tool")
async def execute_yahoo_tool():
    """Execute the Yahoo finance tool"""
    result = run_script("YAHOO/Tools/yahoo_tool.py")
    if result["status"] == "success":
        await manager.broadcast({
            "type": "process_started",
            "data": "Yahoo finance tool process started"
        })
        return {"status": "processing"}
    return result

@app.post("/execute/process-analysis")
async def execute_process_analysis():
    """Execute the process analysis script"""
    result = run_script("YOUTUBE/process_analysis.py")
    if result["status"] == "success":
        await manager.broadcast({
            "type": "process_started",
            "data": "Process analysis started"
        })
        return {"status": "processing"}
    return result

if __name__ == "__main__":
    logger.info("Starting Stock Analysis API server")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info") 
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import subprocess
import sys
from typing import Dict, Any
import os
from pydantic import BaseModel
import logging
from datetime import datetime
from collections import deque

# Configure logging with a rotating buffer
class LogBuffer:
    def __init__(self, max_size=1000):
        self.buffer = deque(maxlen=max_size)

    def add_log(self, log_entry):
        self.buffer.append(log_entry)

    def get_recent_logs(self):
        return list(self.buffer)

    def clear(self):
        self.buffer.clear()

# Create log buffer instance
log_buffer = LogBuffer()

class LogHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': record.levelname,
                'message': self.format(record)
            }
            log_buffer.add_log(log_entry)
        except Exception:
            self.handleError(record)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        LogHandler()
    ]
)
logger = logging.getLogger(__name__)

print("PYTHON EXECUTABLE:", sys.executable)

app = FastAPI(title="Stock Analysis API")

# Add CORS middleware with specific origins if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You may want to restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str

@app.post("/chat", response_class=JSONResponse)
async def chat(request: ChatRequest):
    """Execute the stock analyzer with a query"""
    log_buffer.clear()  # Clear previous logs
    logger.info(f"Chat request received with query: {request.query}")
    try:
        # Import the analyze_stock_query function
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from YOUTUBE.stock_analyzer import analyze_stock_query
        
        # Execute the analysis
        result = analyze_stock_query(request.query)
        logger.info("Analysis completed successfully")
        return {
            "status": "success", 
            "result": result,
            "logs": log_buffer.get_recent_logs()
        }
    except Exception as e:
        logger.error(f"Chat analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "logs": log_buffer.get_recent_logs()
        }

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
        
        # Run the script and capture output
        process = subprocess.run(
            [sys.executable, abs_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=project_root  # Set working directory to project root
        )
        
        # Log the output
        if process.stdout:
            for line in process.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                    
                # Parse the log line to extract level and message
                try:
                    # Check if the line contains a log level
                    if " - INFO - " in line:
                        logger.info(line.split(" - INFO - ")[-1])
                    elif " - ERROR - " in line:
                        logger.error(line.split(" - ERROR - ")[-1])
                    elif " - WARNING - " in line:
                        logger.warning(line.split(" - WARNING - ")[-1])
                    else:
                        # If no level is found, log as info
                        logger.info(line)
                except Exception:
                    # If parsing fails, log the entire line as info
                    logger.info(line)
        
        if process.stderr:
            for line in process.stderr.splitlines():
                line = line.strip()
                if not line:
                    continue
                    
                # Parse the log line to extract level and message
                try:
                    # Check if the line contains a log level
                    if " - INFO - " in line:
                        logger.info(line.split(" - INFO - ")[-1])
                    elif " - ERROR - " in line:
                        logger.error(line.split(" - ERROR - ")[-1])
                    elif " - WARNING - " in line:
                        logger.warning(line.split(" - WARNING - ")[-1])
                    else:
                        # If no level is found, log as error
                        logger.error(line)
                except Exception:
                    # If parsing fails, log the entire line as error
                    logger.error(line)
        
        # Check if the process was successful
        if process.returncode == 0:
            return {
                "status": "success",
                "message": "Script executed successfully"
            }
        else:
            raise Exception(f"Script failed with return code: {process.returncode}")
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e)
            }
        )

@app.post("/execute/youtube-fetcher", response_class=JSONResponse)
async def execute_youtube_fetcher():
    """Execute the YouTube fetcher tool"""
    log_buffer.clear()  # Clear previous logs
    logger.info("Starting YouTube fetcher process")
    try:
        result = run_script("YOUTUBE/Tools/youtube_fetcher_tool.py")
        return {
            "status": result["status"],
            "message": result.get("message", ""),
            "logs": log_buffer.get_recent_logs()
        }
    except Exception as e:
        logger.error(f"YouTube fetcher failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "logs": log_buffer.get_recent_logs()
        }

@app.post("/execute/transcript-analyzer", response_class=JSONResponse)
async def execute_transcript_analyzer():
    """Execute the transcript analyzer tool"""
    log_buffer.clear()  # Clear previous logs
    logger.info("Starting transcript analyzer process")
    try:
        result = run_script("YOUTUBE/Tools/transcript_analyzer_tool.py")
        return {
            "status": result["status"],
            "message": result.get("message", ""),
            "logs": log_buffer.get_recent_logs()
        }
    except Exception as e:
        logger.error(f"Transcript analyzer failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "logs": log_buffer.get_recent_logs()
        }

@app.post("/execute/yahoo-tool", response_class=JSONResponse)
async def execute_yahoo_tool():
    """Execute the Yahoo finance tool"""
    log_buffer.clear()  # Clear previous logs
    logger.info("Starting Yahoo finance tool process")
    try:
        result = run_script("YAHOO/Tools/yahoo_tool.py")
        return {
            "status": result["status"],
            "message": result.get("message", ""),
            "logs": log_buffer.get_recent_logs()
        }
    except Exception as e:
        logger.error(f"Yahoo tool failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "logs": log_buffer.get_recent_logs()
        }

@app.post("/execute/process-analysis", response_class=JSONResponse)
async def execute_process_analysis():
    """Execute the process analysis script"""
    log_buffer.clear()  # Clear previous logs
    logger.info("Starting process analysis")
    try:
        result = run_script("YOUTUBE/process_analysis.py")
        return {
            "status": result["status"],
            "message": result.get("message", ""),
            "logs": log_buffer.get_recent_logs()
        }
    except Exception as e:
        logger.error(f"Process analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "logs": log_buffer.get_recent_logs()
        }

if __name__ == "__main__":
    logger.info("Starting Stock Analysis API server")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info") 
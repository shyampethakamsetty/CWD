from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import sys
from typing import Dict, Any
import os
from pydantic import BaseModel
import sys
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

class ChatRequest(BaseModel):
    query: str

def run_script(script_path: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True
        )
        return {
            "status": "success",
            "output": result.stdout,
            "error": result.stderr
        }
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "output": e.stdout,
                "error": e.stderr
            }
        )

@app.get("/")
async def root():
    return {"message": "Stock Analysis API is running"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Execute the stock analyzer with a query"""
    try:
        # Import the analyze_stock_query function
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from YOUTUBE.stock_analyzer import analyze_stock_query
        
        # Execute the analysis
        result = analyze_stock_query(request.query)
        return result
    except Exception as e:
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
    return run_script("YOUTUBE/Tools/youtube_fetcher_tool.py")

@app.post("/execute/transcript-analyzer")
async def execute_transcript_analyzer():
    """Execute the transcript analyzer tool"""
    return run_script("YOUTUBE/Tools/transcript_analyzer_tool.py")

@app.post("/execute/yahoo-tool")
async def execute_yahoo_tool():
    """Execute the Yahoo finance tool"""
    return run_script("YAHOO/Tools/yahoo_tool.py")

@app.post("/execute/process-analysis")
async def execute_process_analysis():
    """Execute the process analysis script"""
    return run_script("YOUTUBE/process_analysis.py")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
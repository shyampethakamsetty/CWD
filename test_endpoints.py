import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_root():
    print("\n=== Testing Root Endpoint ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def test_chat():
    print("\n=== Testing Chat Endpoint ===")
    payload = {
        "query": "What is the current trend for AAPL stock?"
    }
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def test_youtube_fetcher():
    print("\n=== Testing YouTube Fetcher ===")
    response = requests.post(f"{BASE_URL}/execute/youtube-fetcher")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def test_transcript_analyzer():
    print("\n=== Testing Transcript Analyzer ===")
    response = requests.post(f"{BASE_URL}/execute/transcript-analyzer")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def test_yahoo_tool():
    print("\n=== Testing Yahoo Tool ===")
    response = requests.post(f"{BASE_URL}/execute/yahoo-tool")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def test_process_analysis():
    print("\n=== Testing Process Analysis ===")
    response = requests.post(f"{BASE_URL}/execute/process-analysis")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def test_log_stream():
    print("\n=== Testing Log Stream ===")
    print("Connecting to log stream...")
    response = requests.get(f"{BASE_URL}/logs/stream", stream=True)
    print(f"Status Code: {response.status_code}")
    
    # Read a few log entries
    count = 0
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith('data: '):
                log_data = json.loads(decoded_line[6:])
                print(f"Log: {log_data}")
                count += 1
                if count >= 5:  # Read 5 log entries
                    break

def run_all_tests():
    print(f"Starting tests at {datetime.now()}")
    
    try:
        test_root()
        test_chat()
        test_youtube_fetcher()
        test_transcript_analyzer()
        test_yahoo_tool()
        test_process_analysis()
        test_log_stream()
        
        print("\n=== All tests completed ===")
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the server. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"\nError during testing: {str(e)}")

if __name__ == "__main__":
    run_all_tests() 
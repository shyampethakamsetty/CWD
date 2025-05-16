from dotenv import load_dotenv
load_dotenv()
import os
import sys
import json
import yaml
from datetime import datetime
from config.paths import PATHS

# Add the parent directory to sys.path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Tools.context_agent import ContextAgent

def load_config(config_path):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        print(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        return None

def test_context_agent():
    """Test the ContextAgent functionality with configuration from YAML."""
    print("Starting ContextAgent test...")
    
    # Load configuration from YAML file
    config_path = PATHS['YAHOO']['CONFIG'] / 'agent_config.yaml'
    config = load_config(config_path)
    
    if not config:
        print("Failed to load configuration. Exiting test.")
        return {'status': 'error', 'message': 'Configuration loading failed'}
    
    # Initialize the agent with loaded configuration
    agent = ContextAgent(config=config)
    
    # Create a test context with symbols from config
    test_context = {
        'symbols': config.get('SYMBOLS')
    }
    
    # Execute the task
    print("Fetching stock data...")
    result = agent.execute_task("Fetch latest stock prices", test_context)
    
    # Print the result
    print(f"Task execution status: {result['status']}")
    print(f"Message: {result['message']}")
    
    # Check if data was saved correctly
    date_now = datetime.now().strftime('%Y-%m-%d')
    output_file = PATHS['YAHOO']['OUTPUTS'] / f'{date_now}_stock_last_close.json'
    
    if os.path.exists(output_file):
        print(f"Output file created successfully: {output_file}")
        
        # Read and display the data
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        print("\nFetched stock prices:")
        for symbol, price in data.items():
            print(f"{symbol}: ${price}")
        
        print(f"\nTotal symbols processed: {len(data)}")
    else:
        print(f"Error: Output file not found at {output_file}")
    
    return result

if __name__ == "__main__":
    test_result = test_context_agent()
    print("\nTest completed.")
import os
import sys
# Add the project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

import json
import glob
from datetime import datetime
import weaviate
from dotenv import load_dotenv
from config.paths import PATHS

# Load environment variables
load_dotenv()

# Weaviate client configuration
weaviate_url = os.getenv("WEAVIATE_URL")
weaviate_api_key = os.getenv("WEAVIATE_API_KEY")

if not weaviate_url or not weaviate_api_key:
    print("Error: WEAVIATE_URL and WEAVIATE_API_KEY must be set in your .env file")
    print("Please add these variables to your .env file:")
    print("WEAVIATE_URL=your_weaviate_url")
    print("WEAVIATE_API_KEY=your_weaviate_api_key")
    sys.exit(1)

if not weaviate_url.startswith("https://"):
    weaviate_url = f"https://{weaviate_url}"

client = weaviate.Client(
    url=weaviate_url,
    auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key),
    additional_headers={
        "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")
    }
)

def setup_schema():
    """Set up the Weaviate schema for both vector and graph storage"""
    
    # Define the Stock class schema
    stock_class = {
        "class": "Stock",
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {
                "model": "text-embedding-3-small",
                "type": "text"
            }
        },
        "properties": [
            {
                "name": "symbol",
                "dataType": ["string"],
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            },
            {
                "name": "lastClose",
                "dataType": ["number"],
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            },
            {
                "name": "direction",
                "dataType": ["string"],
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            },
            {
                "name": "sentiment",
                "dataType": ["string"],
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            },
            {
                "name": "summary",
                "dataType": ["text"],
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": False
                    }
                }
            }
        ]
    }

    # Define the Analysis class schema
    analysis_class = {
        "class": "Analysis",
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {
                "model": "text-embedding-3-small",
                "type": "text"
            }
        },
        "properties": [
            {
                "name": "analysisId",
                "dataType": ["string"],
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            },
            {
                "name": "timestamp",
                "dataType": ["date"],
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            },
            {
                "name": "sourceType",
                "dataType": ["string"],
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            },
            {
                "name": "model",
                "dataType": ["string"],
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            },
            {
                "name": "hasStock",
                "dataType": ["Stock[]"],
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": True
                    }
                }
            }
        ]
    }

    # Create the schema if it doesn't exist
    try:
        # Check if classes exist
        schema = client.schema.get()
        existing_classes = [c["class"] for c in schema["classes"]]
        
        if "Stock" not in existing_classes:
            client.schema.create_class(stock_class)
            print("Stock class created successfully")
        else:
            print("Stock class already exists")
            
        if "Analysis" not in existing_classes:
            client.schema.create_class(analysis_class)
            print("Analysis class created successfully")
        else:
            print("Analysis class already exists")
            
    except Exception as e:
        print(f"Error creating schema: {str(e)}")

def process_analysis_file(file_path):
    """Process a single analysis file and store data in Weaviate"""
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Process each stock in the analysis
    stock_uuids = []  # Store all stock UUIDs for this analysis
    
    for stock_data in data['stocks']:
        # Create stock object
        stock_object = {
            "symbol": stock_data['symbol'],
            "lastClose": stock_data['last_close'],
            "direction": stock_data['direction'],
            "sentiment": stock_data['sentiment'],
            "summary": stock_data['summary']
        }
        
        # Add stock to Weaviate
        stock_uuid = client.data_object.create(
            stock_object,
            "Stock"
        )
        stock_uuids.append(stock_uuid)
    
    # Convert timestamp to RFC3339 format
    timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
    rfc3339_timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    
    # Create analysis object with array of stock references
    analysis_object = {
        "analysisId": data['analysis_id'],
        "timestamp": rfc3339_timestamp,
        "sourceType": data['source']['type'],
        "model": data['source']['model'],
        "hasStock": [{"beacon": f"weaviate://localhost/Stock/{uuid}"} for uuid in stock_uuids]
    }
    
    # Add analysis to Weaviate
    client.data_object.create(
        analysis_object,
        "Analysis"
    )

def main():
    # Set up schema
    setup_schema()
    
    # Find the latest analysis directory
    output_dirs = sorted(PATHS['YOUTUBE']['OUTPUTS'].glob('*'))
    if not output_dirs:
        print("No output directories found")
        return
        
    latest_dir = output_dirs[-1]
    analysis_dir = latest_dir / "analysis"
    
    # Process all analysis files
    for file_path in analysis_dir.glob("*_analysis.json"):
        print(f"Processing {file_path}")
        process_analysis_file(file_path)

if __name__ == "__main__":
    main() 
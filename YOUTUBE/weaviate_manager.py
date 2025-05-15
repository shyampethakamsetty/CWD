import os
import weaviate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Weaviate client configuration
weaviate_url = os.getenv("WEAVIATE_URL")
if not weaviate_url.startswith("https://"):
    weaviate_url = f"https://{weaviate_url}"

client = weaviate.Client(
    url=weaviate_url,
    auth_client_secret=weaviate.AuthApiKey(api_key=os.getenv("WEAVIATE_API_KEY")),
    additional_headers={
        "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")
    }
)

def clear_vector_data():
    """
    Clear all vector data from the Stock class.
    This will remove all stock objects and their vector embeddings.
    """
    try:
        # Delete all objects from Stock class
        result = client.batch.delete_objects(
            class_name="Stock",
            where={
                "operator": "Like",
                "path": ["symbol"],
                "valueString": "*"  # Match any symbol
            }
        )
        print(f"Cleared vector data: {result}")
    except Exception as e:
        print(f"Error clearing vector data: {str(e)}")

def clear_graph_data():
    """
    Clear all graph data from the Analysis class.
    This will remove all analysis objects and their relationships.
    """
    try:
        # Delete all objects from Analysis class
        result = client.batch.delete_objects(
            class_name="Analysis",
            where={
                "operator": "Like",
                "path": ["analysisId"],
                "valueString": "*"  # Match any analysis ID
            }
        )
        print(f"Cleared graph data: {result}")
    except Exception as e:
        print(f"Error clearing graph data: {str(e)}")

def clear_all_data():
    """
    Clear all data from both Stock and Analysis classes.
    """
    clear_vector_data()
    clear_graph_data()

if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage Weaviate collections')
    parser.add_argument('--clear', choices=['vector', 'graph', 'all'], 
                      help='Clear vector data, graph data, or all data')
    
    args = parser.parse_args()
    
    if args.clear == 'vector':
        clear_vector_data()
    elif args.clear == 'graph':
        clear_graph_data()
    elif args.clear == 'all':
        clear_all_data() 
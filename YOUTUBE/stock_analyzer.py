import os
import weaviate
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
import openai
import json

# Load environment variables
load_dotenv()

# Get environment variables
weaviate_url = os.getenv("WEAVIATE_URL")
openai_api_key = os.getenv("OPENAI_API_KEY")
weaviate_api_key = os.getenv("WEAVIATE_API_KEY")

# Debug API keys (masked for security)
print("\nDebug - API Keys Configuration:")
print(f"WEAVIATE_URL: {weaviate_url}")
print(f"WEAVIATE_API_KEY: {weaviate_api_key[:10] if weaviate_api_key else 'Not set'}...")
print(f"OPENAI_API_KEY: {openai_api_key[:10] if openai_api_key else 'Not set'}...")

# Validate environment variables
if not weaviate_url:
    raise ValueError("WEAVIATE_URL environment variable is not set")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
if not weaviate_api_key:
    raise ValueError("WEAVIATE_API_KEY environment variable is not set")

# Configure OpenAI for Azure
openai.api_type = "azure"
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")

deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
if not deployment_name:
    raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME environment variable is not set")

# Configure Weaviate URL
if not weaviate_url.startswith("https://"):
    weaviate_url = f"https://{weaviate_url}"

# Initialize Weaviate client
client = weaviate.Client(
    url=weaviate_url,
    auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key),
    additional_headers={
        "X-OpenAI-Api-Key": openai_api_key
    }
)

# Test Weaviate connection
try:
    print("\nDebug - Testing Weaviate Connection...")
    client.is_ready()
    print("Weaviate connection successful!")
except Exception as e:
    print(f"Weaviate connection failed: {str(e)}")
    raise

# Stock symbol mapping
STOCK_SYMBOLS = {
    'AAPL': ['apple', 'aapl'],
    'MSFT': ['microsoft', 'msft'],
    'GOOGL': ['google', 'googl', 'alphabet'],
    'AMZN': ['amazon', 'amzn'],
    'TSLA': ['tesla', 'tsla'],
    'META': ['meta', 'facebook', 'fb'],
    'NVDA': ['nvidia', 'nvda'],
    'PYPL': ['paypal', 'pypl'],
    'INTC': ['intel', 'intc'],
    'CMCSA': ['comcast', 'cmcsa'],
    'NFLX': ['netflix', 'nflx'],
    'ADBE': ['adobe', 'adbe'],
    'PEP': ['pepsi', 'pep'],
    'CSCO': ['cisco', 'csco'],
    'AVGO': ['broadcom', 'avgo'],
    'TXN': ['texas instruments', 'txn'],
    'COST': ['costco', 'cost'],
    'TMUS': ['t-mobile', 'tmus'],
    'AMGN': ['amgen', 'amgn'],
    'SBUX': ['starbucks', 'sbux'],
    'QCOM': ['qualcomm', 'qcom'],
    'GILD': ['gilead', 'gild'],
    'MDLZ': ['mondelez', 'mdlz'],
    'INTU': ['intuit', 'intu'],
    'ISRG': ['intuitive surgical', 'isrg'],
    'VRTX': ['vertex', 'vrtx'],
    'REGN': ['regeneron', 'regn'],
    'ILMN': ['illumina', 'ilmn'],
    'ADI': ['analog devices', 'adi'],
    'CSX': ['csx', 'csx corporation'],
    'MU': ['micron', 'mu'],
    'BKNG': ['booking', 'bkng'],
    'AMAT': ['applied materials', 'amat'],
    'ADP': ['automatic data processing', 'adp'],
    'MNST': ['monster', 'mnst'],
    'MELI': ['mercado libre', 'meli'],
    'ADSK': ['autodesk', 'adsk'],
    'JD': ['jd.com', 'jd'],
    'LRCX': ['lam research', 'lrcx'],
    'EBAY': ['ebay', 'ebay'],
    'KHC': ['kraft heinz', 'khc'],
    'BIIB': ['biogen', 'biib'],
    'LULU': ['lululemon', 'lulu'],
    'EA': ['electronic arts', 'ea'],
    'WDAY': ['workday', 'wday'],
    'PCAR': ['paccar', 'pcar'],
    'DXCM': ['dexcom', 'dxcm'],
    'CTSH': ['cognizant', 'ctsh'],
    'MRVL': ['marvell', 'mrvl'],
    'CRM': ['salesforce', 'crm']
}

def detect_symbol(query: str) -> Optional[str]:
    """
    Detect stock symbol from user query
    """
    query = query.lower()
    for symbol, keywords in STOCK_SYMBOLS.items():
        if any(keyword in query for keyword in keywords):
            return symbol
    return None

def semantic_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Perform semantic search on stock summaries using hybrid search
    """
    try:
        # First try exact match
        result = (
            client.query
            .get("Stock", ["symbol", "summary", "sentiment", "direction", "lastClose"])
            .with_where({
                "path": ["symbol"],
                "operator": "Equal",
                "valueString": query.upper()
            })
            .with_limit(limit)
            .do()
        )
        
        if result["data"]["Get"]["Stock"]:
            return result["data"]["Get"]["Stock"]
            
        # If no exact match, try keyword search
        result = (
            client.query
            .get("Stock", ["symbol", "summary", "sentiment", "direction", "lastClose"])
            .with_bm25(
                query=query
            )
            .with_limit(limit)
            .do()
        )
        
        print(f"\nDebug - Weaviate Response: {json.dumps(result, indent=2)}")
        
        if "data" in result and "Get" in result["data"] and "Stock" in result["data"]["Get"]:
            return result["data"]["Get"]["Stock"] or []
        return []
    except Exception as e:
        print(f"\nDebug - Semantic Search Error: {str(e)}")
        return []

def graph_search(symbol: str) -> List[Dict[str, Any]]:
    """
    Search for analysis data related to a specific stock
    """
    try:
        result = (
            client.query
            .get("Analysis", ["analysisId", "timestamp", "sourceType", "model"])
            .with_where({
                "path": ["hasStock", "Stock", "symbol"],
                "operator": "Equal",
                "valueString": symbol
            })
            .with_additional(["classification"])
            .do()
        )
        
        if "data" in result and "Get" in result["data"] and "Analysis" in result["data"]["Get"]:
            return result["data"]["Get"]["Analysis"]
        return []
    except Exception as e:
        raise Exception(f"Error in graph search: {str(e)}")

def refine_response_with_llm(query: str, analysis_result: Dict[str, Any]) -> str:
    """
    Use Azure OpenAI to generate a user-friendly response based on the analysis results
    
    Args:
        query (str): The original user query
        analysis_result (Dict[str, Any]): The analysis results from analyze_stock_query
        
    Returns:
        str: A refined, user-friendly response
    """
    try:
        prompt = f"""
You are a helpful financial assistant. Based on the user's query and the analysis results below, generate a response that is clear, concise, and directly answers the query using only the most relevant information.

User Query: {query}

Analysis Results:
{json.dumps(analysis_result, indent=2)}

Instructions:
- Only include information directly related to the user's query.
- Use plain, non-technical language.
- Prioritize key insights and include specific data points (e.g., price levels, trends).
- If multiple stocks are mentioned, only refer to those relevant to the query.
- Keep the response short and focused.
- If data is missing or unclear, explain that briefly.
"""

        response = openai.chat.completions.create(
    model=deployment_name,
    messages=[
        {"role": "system", "content": "You are a helpful financial assistant that provides clear, concise, and accurate information about stocks."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.3,
    max_tokens=500,
    top_p=0.95
)

        return response.choices[0].message.content.strip()

        
    except Exception as e:
        return f"Error generating refined response: {str(e)}"

def analyze_stock_query(query: str) -> Dict[str, Any]:
    """
    Main function to analyze a stock-related query and return structured results
    """
    try:
        # Detect stock symbol from query
        symbol = detect_symbol(query)
        print(f"\nDebug - Detected Symbol: {symbol}")
        
        # Perform semantic search
        semantic_results = semantic_search(query)
        print(f"\nDebug - Semantic Results: {json.dumps(semantic_results, indent=2)}")
        
        if not semantic_results:
            return {
                "status": "error",
                "error": "No stock data found",
                "refined_response": "No stock data was found for your query. Please check if the stock symbol is correct or try a different query."
            }
        
        # Perform graph search if symbol is found
        graph_results = graph_search(symbol) if symbol else []
        print(f"\nDebug - Graph Results: {json.dumps(graph_results, indent=2)}")
        
        # Find the most relevant stock based on the query
        query_lower = query.lower()
        most_relevant_stock = None
        
        for stock in semantic_results:
            if stock["symbol"].lower() in query_lower or any(keyword in query_lower for keyword in STOCK_SYMBOLS.get(stock["symbol"], [])):
                most_relevant_stock = stock
                break
        
        if not most_relevant_stock and semantic_results:
            most_relevant_stock = semantic_results[0]  # Use first result if no exact match
            
        print(f"\nDebug - Most Relevant Stock: {json.dumps(most_relevant_stock, indent=2)}")
        
        # Prepare the response
        response = {
            "status": "success",
            "data": {
                "query": query,
                "detected_symbol": symbol,
                "stock_analysis": most_relevant_stock,
                "historical_analysis": graph_results[:3] if graph_results else []
            }
        }
        
        # Only generate refined response if status is success
        refined_response = refine_response_with_llm(query, response)
        response["refined_response"] = refined_response
        
        return response
        
    except Exception as e:
        print(f"\nDebug - Main Error: {str(e)}")
        error_response = {
            "status": "error",
            "error": str(e),
            "refined_response": f"Error retrieving information: {str(e)}"
        }
        return error_response

def test_weaviate_connection():
    """
    Test function to verify Weaviate connection and API key
    """
    try:
        print("\nTesting Weaviate Connection and API Key...")
        
        # Test 1: Basic connection
        print("\nTest 1: Basic Connection")
        is_ready = client.is_ready()
        print(f"Connection status: {'Success' if is_ready else 'Failed'}")
        
        # Test 2: Schema check
        print("\nTest 2: Schema Check")
        schema = client.schema.get()
        print("Available classes:", [class_obj["class"] for class_obj in schema["classes"]])
        
        # Test 3: Simple query
        print("\nTest 3: Simple Query")
        result = (
            client.query
            .get("Stock", ["symbol"])
            .with_limit(1)
            .do()
        )
        print("Query result:", json.dumps(result, indent=2))
        
        return True
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        return False

if __name__ == "__main__":
    # Test Weaviate connection first
    if test_weaviate_connection():
        print("\nAll tests passed! Weaviate connection and API key are working correctly.")
    else:
        print("\nTests failed. Please check your configuration and API keys.")
        exit(1)
    
    # Continue with the main query if tests pass
    query = "AAPL"
    result = analyze_stock_query(query)
    print("\nComplete Raw Response:")
    print(json.dumps(result, indent=2))
    print("\nRefined Response:")
    print(result["refined_response"])
import os
import weaviate
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# Load environment variables
load_dotenv()

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
    Perform semantic search on stock summaries
    """
    try:
        result = (
            client.query
            .get("Stock", ["symbol", "summary", "sentiment", "direction", "lastClose"])
            .with_near_text({"concepts": [query]})
            .with_limit(limit)
            .do()
        )
        if "data" in result and "Get" in result["data"] and "Stock" in result["data"]["Get"]:
            return result["data"]["Get"]["Stock"]
        return []
    except Exception as e:
        raise Exception(f"Error in semantic search: {str(e)}")

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

def analyze_stock_query(query: str) -> Dict[str, Any]:
    """
    Main function to analyze a stock-related query and return structured results
    
    Args:
        query (str): The user's query about a stock
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - status: "success" or "error"
            - data: The analysis results if successful
            - error: Error message if unsuccessful
    """
    try:
        # Detect stock symbol from query
        symbol = detect_symbol(query)
        
        # Perform semantic search
        semantic_results = semantic_search(query)
        
        # Perform graph search if symbol is found
        graph_results = graph_search(symbol) if symbol else []
        
        # Find the most relevant stock based on the query
        query_lower = query.lower()
        most_relevant_stock = None
        
        for stock in semantic_results:
            if stock["symbol"].lower() in query_lower or any(keyword in query_lower for keyword in STOCK_SYMBOLS.get(stock["symbol"], [])):
                most_relevant_stock = stock
                break
        
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
        
        return response
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Example usage:
if __name__ == "__main__":
    # Example query
    query = input()
    result = analyze_stock_query(query)
    print(result) 
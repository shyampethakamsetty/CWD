import os
import weaviate
from dotenv import load_dotenv
import json
from datetime import datetime
import streamlit as st
from typing import List, Dict, Any

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

def detect_symbol(query: str) -> str:
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
        else:
            st.warning(f"No stock data found for query: {query}")
            return []
    except Exception as e:
        st.error(f"Error in semantic search: {str(e)}")
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
        else:
            st.warning(f"No graph data found for symbol: {symbol}")
            return []
    except Exception as e:
        st.error(f"Error in graph search: {str(e)}")
        return []

def hybrid_search(query: str, symbol: str = None) -> Dict[str, Any]:
    """
    Combine semantic and graph search results
    """
    results = {
        "semantic_results": semantic_search(query),
        "graph_results": []
    }
    
    if symbol:
        results["graph_results"] = graph_search(symbol)
    
    return results

def format_response(results: Dict[str, Any], query: str) -> str:
    """
    Format search results into a readable response that's specific to the user's query
    """
    response = []
    
    # Format semantic search results
    if results["semantic_results"]:
        # Find the most relevant stock based on the query
        query_lower = query.lower()
        most_relevant_stock = None
        
        for stock in results["semantic_results"]:
            if stock["symbol"].lower() in query_lower or any(keyword in query_lower for keyword in STOCK_SYMBOLS.get(stock["symbol"], [])):
                most_relevant_stock = stock
                break
        
        if most_relevant_stock:
            # Format the response based on the query type
            if "sentiment" in query_lower:
                response.append(f"📊 Sentiment Analysis for {most_relevant_stock['symbol']}:")
                response.append(f"\n🔹 Current Sentiment: {most_relevant_stock['sentiment']}")
                response.append(f"🔹 Price Direction: {most_relevant_stock['direction']}")
                response.append(f"🔹 Last Close: ${most_relevant_stock['lastClose']}")
                response.append(f"\n📝 Summary: {most_relevant_stock['summary']}")
            elif "price" in query_lower or "trading" in query_lower:
                response.append(f"💰 Price Information for {most_relevant_stock['symbol']}:")
                response.append(f"\n🔹 Last Close: ${most_relevant_stock['lastClose']}")
                response.append(f"🔹 Direction: {most_relevant_stock['direction']}")
                response.append(f"\n📝 Analysis: {most_relevant_stock['summary']}")
            else:
                response.append(f"📊 Analysis for {most_relevant_stock['symbol']}:")
                response.append(f"\n🔹 Sentiment: {most_relevant_stock['sentiment']}")
                response.append(f"🔹 Direction: {most_relevant_stock['direction']}")
                response.append(f"🔹 Last Close: ${most_relevant_stock['lastClose']}")
                response.append(f"\n📝 Summary: {most_relevant_stock['summary']}")
    
    # Format graph search results if available
    if results["graph_results"]:
        response.append("\n📈 Historical Analysis:")
        for analysis in results["graph_results"][:3]:  # Limit to 3 most recent analyses
            timestamp = datetime.fromisoformat(analysis["timestamp"].replace('Z', '+00:00'))
            response.append(f"\n🔸 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}:")
            response.append(f"   Source: {analysis['sourceType']}")
            response.append(f"   Model: {analysis['model']}")
    
    return "\n".join(response) if response else "No results found."

def main():
    st.title("Stock Analysis Chat")
    st.write("Ask questions about stock analysis and sentiment")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process the query
        with st.chat_message("assistant"):
            with st.spinner("Searching..."):
                # Detect stock symbol from query
                symbol = detect_symbol(prompt)
                
                # Perform hybrid search
                results = hybrid_search(prompt, symbol)
                response = format_response(results, prompt)
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main() 
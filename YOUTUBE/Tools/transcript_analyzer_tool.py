import os
import sys
# Add the project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_dir)

from openai import AzureOpenAI
import os
import json
import logging
from dotenv import load_dotenv
import glob
from datetime import datetime
import pandas as pd
from typing import Dict, List, Any
from config.paths import PATHS

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PATHS['YOUTUBE']['LOGS'] / 'transcript_analysis.log')
    ]
)

# Load environment variables
load_dotenv()

# Configure Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
if not deployment_name:
    raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME environment variable is not set")

# Define the list of symbols to track
TRACKED_SYMBOLS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'PYPL', 'INTC', 'CMCSA',
    'NFLX', 'ADBE', 'PEP', 'CSCO', 'AVGO', 'TXN', 'COST', 'TMUS', 'AMGN', 'SBUX',
    'QCOM', 'GILD', 'MDLZ', 'INTU', 'ISRG', 'VRTX', 'REGN', 'ILMN', 'ADI', 'CSX',
    'MU', 'BKNG', 'AMAT', 'ADP', 'MNST', 'MELI', 'ADSK', 'JD', 'LRCX', 'EBAY',
    'KHC', 'BIIB', 'LULU', 'EA', 'WDAY', 'PCAR', 'DXCM', 'CTSH', 'MRVL', 'CRM'
]

class YouTubeTranscriptAnalyzer:
    def __init__(self):
        self.description = "Analyzes YouTube video transcripts for stock market insights"
        self.last_close_prices = self._load_last_close_prices()
        
    def _load_last_close_prices(self):
        """Load the latest close prices from historical data"""
        try:
            # Read the CSV file
            df = pd.read_csv(PATHS['YAHOO']['OUTPUTS'] / 'historical_stock_prices.csv')
            
            # Get the latest date (last column)
            latest_date = df.columns[-1]
            
            # Create a dictionary of symbol to last close price
            return dict(zip(df['SYMBOLS'], df[latest_date]))
        except Exception as e:
            logging.error(f"Error loading last close prices: {str(e)}")
            return {}
        
    def _create_graph_nodes_and_relationships(self, stock_data: Dict) -> tuple[List[Dict], List[Dict]]:
        """Create graph nodes and relationships from stock data"""
        nodes = []
        relationships = []
        
        # Create stock node
        stock_node = {
            "id": f"{stock_data['symbol']}_{datetime.now().strftime('%Y-%m-%d')}",
            "type": "stock",
            "properties": {
                "symbol": stock_data["symbol"],
                "last_close": stock_data["last_close"],
                "direction": stock_data["direction"],
                "timestamp": datetime.now().isoformat()
            }
        }
        nodes.append(stock_node)
        
        # Create support level nodes and relationships
        for support in stock_data.get("support_levels", []):
            support_node = {
                "id": f"{stock_data['symbol']}_support_{support['price']}",
                "type": "support_level",
                "properties": {
                    "price": support["price"],
                    "description": support["description"],
                    "level_type": support.get("level_type", "pivot")  # pivot or major
                }
            }
            nodes.append(support_node)
            
            relationships.append({
                "source": stock_node["id"],
                "target": support_node["id"],
                "type": "HAS_SUPPORT_LEVEL",
                "properties": {
                    "timestamp": datetime.now().isoformat()
                }
            })
        
        # Create resistance level nodes and relationships
        for resistance in stock_data.get("resistance_levels", []):
            resistance_node = {
                "id": f"{stock_data['symbol']}_resistance_{resistance['price']}",
                "type": "resistance_level",
                "properties": {
                    "price": resistance["price"],
                    "description": resistance["description"],
                    "level_type": resistance.get("level_type", "pivot")  # pivot or major
                }
            }
            nodes.append(resistance_node)
            
            relationships.append({
                "source": stock_node["id"],
                "target": resistance_node["id"],
                "type": "HAS_RESISTANCE_LEVEL",
                "properties": {
                    "timestamp": datetime.now().isoformat()
                }
            })
        
        return nodes, relationships

    def _create_vector_content(self, stock_data: Dict) -> Dict:
        """Create vector content from stock data"""
        return {
            "summary": f"Analysis of {stock_data['symbol']} stock showing {stock_data['direction']} momentum with key support and resistance levels identified.",
            "detailed_analysis": [{
                "symbol": stock_data["symbol"],
                "last_close": stock_data["last_close"],
                "technical_indicators": {
                    "moving_averages": {
                        "20_day": stock_data.get("20_day_ma", None),
                        "50_day": stock_data.get("50_day_ma", None),
                        "200_day": stock_data.get("200_day_ma", None)
                    },
                    "momentum": {
                        "macd": stock_data.get("macd", None),
                        "rsi": stock_data.get("rsi", None)
                    },
                    "volatility": stock_data.get("volatility", None)
                },
                "key_insights": stock_data.get("key_insights", []),
                "risk_factors": stock_data.get("risk_factors", [])
            }]
        }

    def analyze_transcript(self, transcript_text: str) -> Dict:
        """Analyze a single transcript and return structured analysis"""
        try:
            # Create a string of symbols with their last close prices
            symbols_with_prices = "\n".join([
                f"{symbol}: ${self.last_close_prices.get(symbol, 'N/A')}"
                for symbol in TRACKED_SYMBOLS
            ])
            
            prompt = f"""
            Analyze the following transcript for insights about these specific stocks ONLY:
            {symbols_with_prices}

            For each of these symbols that is explicitly mentioned in the transcript:
            1. Extract ONLY the key points that are explicitly stated
            2. If support/resistance levels are mentioned, include them
            3. If technical indicators are discussed, list them
            4. If a clear direction or sentiment is stated, include it
            5. Create a brief summary of what was actually said about the stock

            Validation Rules:
            - Use the last close prices to validate extracted information:
              * Support levels must be below the last close price
              * Resistance levels must be above the last close price
              * If a mentioned level doesn't make sense relative to last close, exclude it
            - For technical indicators:
              * RSI values should be between 0 and 100
              * MACD values should be reasonable relative to the stock price
              * Moving averages should be in correct order (e.g., 20-day < 50-day < 200-day)
            - For sentiment and direction:
              * Should be consistent with mentioned price movements
              * Should align with technical indicators if mentioned

            Rules:
            - ONLY include stocks from the provided list that are explicitly mentioned
            - Use EXACT symbol names (e.g., 'GOOGL' not 'Google')
            - DO NOT make up or infer any information
            - If a stock is mentioned but no specific insights are given, still include it
            - Keep the summary concise and factual
            - Format response as JSON with this exact structure for each mentioned symbol:
            {{
                "stocks": [
                    {{
                        "symbol": "SYMBOL",
                        "last_close": PRICE,  # Include the last close price for reference
                        "direction": "bullish/bearish/neutral" or null if not mentioned,
                        "resistance_levels": [PRICE] or [] if not mentioned,
                        "support_levels": [PRICE] or [] if not mentioned,
                        "indicators": ["INDICATOR1", "INDICATOR2"] or [] if not mentioned,
                        "sentiment": "bullish/bearish/neutral" or null if not mentioned,
                        "summary": "Brief summary of what was actually said about the stock"
                    }}
                ]
            }}
            
            Transcript:
            {transcript_text}
            """
            
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a financial analyst expert who extracts ONLY explicitly stated information from transcripts. Your response must be a valid JSON object. DO NOT make up or infer any information. Only include stocks that are explicitly mentioned. Use exact symbol names. Validate all extracted information against the last close prices to ensure accuracy."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000,
                top_p=0.95,
                response_format={"type": "json_object"}
            )
            
            raw_analysis = json.loads(response.choices[0].message.content)
            
            # Validate the response structure
            if not isinstance(raw_analysis, dict) or 'stocks' not in raw_analysis:
                logging.warning(f"Invalid response structure: {raw_analysis}")
                return {
                    "analysis_id": f"{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.now().isoformat(),
                    "source": {
                        "type": "youtube_transcript",
                        "model": deployment_name,
                        "version": "1.0"
                    },
                    "stocks": []
                }
            
            # Create the final analysis structure
            analysis = {
                "analysis_id": f"{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "source": {
                    "type": "youtube_transcript",
                    "model": deployment_name,
                    "version": "1.0"
                },
                "stocks": raw_analysis.get("stocks", [])
            }
            
            return analysis
            
        except Exception as e:
            logging.error(f"Error analyzing transcript: {str(e)}")
            return {
                "analysis_id": f"{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "source": {
                    "type": "youtube_transcript",
                    "model": deployment_name,
                    "version": "1.0"
                },
                "stocks": []
            }

    def process_transcripts(self):
        """Process all transcripts in the latest output folder"""
        try:
            # Find latest output folder
            output_folders = glob.glob("YOUTUBE\\OUTPUTS\\*")
            if not output_folders:
                raise FileNotFoundError("No output folders found in OUTPUTS directory")
            latest_folder = max(output_folders, key=os.path.getmtime)
            
            # Process transcripts
            transcripts_path = os.path.join(latest_folder, "transcripts")
            if not os.path.exists(transcripts_path):
                raise FileNotFoundError(f"No transcripts folder found in {latest_folder}")
            
            transcript_files = glob.glob(os.path.join(transcripts_path, "*.json"))
            
            for transcript_file in transcript_files:
                try:
                    # Read transcript
                    with open(transcript_file, 'r') as f:
                        transcript_data = json.load(f)
                    
                    # Analyze transcript
                    analysis = self.analyze_transcript(transcript_data['transcript'])
                    
                    # Save individual analysis
                    analysis_filename = os.path.basename(transcript_file).replace('.json', '_analysis.json')
                    analysis_path = os.path.join(latest_folder, "analysis", analysis_filename)
                    os.makedirs(os.path.dirname(analysis_path), exist_ok=True)
                    
                    with open(analysis_path, 'w') as f:
                        json.dump(analysis, f, indent=2)
                    
                    logging.info(f"Processed {os.path.basename(transcript_file)} successfully")
                    
                except Exception as e:
                    logging.error(f"Error processing {transcript_file}: {str(e)}")
                    
        except Exception as e:
            logging.error(f"Error in process_transcripts: {str(e)}")

def main():
    logging.info("Starting transcript analysis")
    analyzer = YouTubeTranscriptAnalyzer()
    analyzer.process_transcripts()
    logging.info("Transcript analysis completed")

if __name__ == "__main__":
    main()
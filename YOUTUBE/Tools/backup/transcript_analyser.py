from openai import AzureOpenAI
import os
import json
import logging
from dotenv import load_dotenv
import glob
from datetime import datetime
import pandas as pd

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('transcript_analysis.log')
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
            df = pd.read_csv('YAHOO/Outputs/historical_stock_prices.csv')
            
            # Get the latest date (last column)
            latest_date = df.columns[-1]
            
            # Create a dictionary of symbol to last close price
            return dict(zip(df['SYMBOLS'], df[latest_date]))
        except Exception as e:
            logging.error(f"Error loading last close prices: {str(e)}")
            return {}
        
    def analyze_transcript(self, transcript_text):
        """Analyze a single transcript and return structured analysis"""
        try:
            # Create a string of symbols with their last close prices
            symbols_with_prices = "\n".join([
                f"{symbol}: ${self.last_close_prices.get(symbol, 'N/A')}"
                for symbol in TRACKED_SYMBOLS
            ])
            
            prompt = f"""
            Analyze the following transcript for insights about these specific stocks ONLY.
            Here are the symbols and their last close prices:
            {symbols_with_prices}

            For each of these symbols that is explicitly mentioned in the transcript, extract:
            1. Support levels (ONLY if exact price points are mentioned)
            2. Resistance levels (ONLY if exact price points are mentioned)
            3. Direction (bullish/bearish/neutral) based on explicit statements
            4. Key insights from the discussion (only factual statements from transcript)
            5. Risk factors mentioned (only if explicitly stated)
            6. Price targets (ONLY if exact price points are mentioned)
            
            Rules:
            - ONLY include stocks from the provided list that are explicitly mentioned
            - Use EXACT symbol names (e.g., 'GOOGL' not 'Google')
            - DO NOT make up or infer price levels - only include if explicitly stated
            - If a stock from the list is not mentioned, do not include it in the output
            - For direction, only use if there's a clear statement (e.g., "dropped 7.5%" = bearish)
            - When mentioning price levels, ensure they make sense relative to the last close price
            - Format response as JSON with this exact structure for each mentioned symbol:
            {{
                "symbol": "SYMBOL",
                "last_close": PRICE,
                "support_levels": [
                    {{"price": PRICE, "description": "DESCRIPTION"}}
                ],
                "resistance_levels": [
                    {{"price": PRICE, "description": "DESCRIPTION"}}
                ],
                "direction": "bullish/bearish/neutral",
                "key_insights": ["INSIGHT1", "INSIGHT2"],
                "risk_factors": ["RISK1", "RISK2"],
                "price_targets": [
                    {{"price": PRICE, "description": "DESCRIPTION"}}
                ]
            }}
            
            Transcript:
            {transcript_text}
            """
            
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a financial analyst expert who extracts ONLY explicitly stated information from transcripts. Your response must be a valid JSON object. DO NOT make up or infer price levels. Only include stocks that are explicitly mentioned. Use exact symbol names and ensure any price levels mentioned make sense relative to the last close price."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Reduced temperature for more consistent output
                max_tokens=2000,
                top_p=0.95,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            # Add metadata for vector/graph storage
            analysis["metadata"] = {
                "analysis_date": datetime.now().isoformat(),
                "source": "youtube_transcript",
                "model": deployment_name,
                "version": "1.0"
            }
            
            return analysis
            
        except Exception as e:
            logging.error(f"Error analyzing transcript: {str(e)}")
            return {"error": str(e)}

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
                    
                    # Save analysis
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
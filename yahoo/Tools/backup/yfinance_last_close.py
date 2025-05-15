import yfinance as yf
import json
import logging
import os
from datetime import datetime
import time
from tqdm import tqdm
from typing import Dict, Optional, List
import sys

def setup_directories():
    """Create necessary directories for logs and outputs."""
    date_now = datetime.now().strftime('%Y-%m-%d')
    
    # Create directories if they don't exist
    log_dir = os.path.join('Yahoo', 'Logs')
    output_dir = os.path.join('Yahoo', 'Outputs')
    
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    return {
        'LOG_FILE': os.path.join(log_dir, f'{date_now}_stock_price_fetcher.log'),
        'OUTPUT_DIR': output_dir,
        'DATE': date_now
    }

# Get directory setup and current date
dir_config = setup_directories()

# Configuration
CONFIG = {
    'RETRY_ATTEMPTS': 3,
    'RETRY_DELAY': 5,
    'RATE_LIMIT_DELAY': 1,  # Delay between API calls in seconds
    'LOG_FILE': dir_config['LOG_FILE'],
    'OUTPUT_DIR': dir_config['OUTPUT_DIR'],
    'CURRENT_DATE': dir_config['DATE'],
    'BATCH_SIZE': 50  # Number of symbols to process in one batch
}

# Configure logging
logging.basicConfig(
    filename=CONFIG['LOG_FILE'],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add console handler to see logs in terminal
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

# List of stock symbols
symbols = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "PYPL", "INTC", "CMCSA",
           "NFLX", "ADBE", "PEP", "CSCO", "AVGO", "TXN", "COST", "TMUS", "AMGN", "SBUX",
           "QCOM", "GILD", "MDLZ", "INTU", "ISRG", "VRTX", "REGN", "ILMN", "ADI",
           "CSX", "MU", "BKNG", "AMAT", "ADP", "MNST", "MELI", "ADSK", "JD", "LRCX",
           "EBAY", "KHC", "BIIB", "LULU", "EA", "WDAY", "PCAR", "DXCM", "CTSH", "MRVL",
           "CRM"]

def validate_price(price: float) -> bool:
    """Validate if the price is reasonable."""
    return isinstance(price, (int, float)) and price > 0

def fetch_last_close(symbol: str) -> Optional[float]:
    """
    Fetch last close price for a given symbol with retries.
    
    Args:
        symbol (str): Stock symbol to fetch
        
    Returns:
        Optional[float]: Last closing price if successful, None otherwise
    """
    for attempt in range(CONFIG['RETRY_ATTEMPTS']):
        try:
            stock = yf.Ticker(symbol)
            history = stock.history(period="1d")
            
            if history.empty:
                logging.warning(f"No data available for {symbol}")
                return None
                
            last_close = history['Close'].iloc[-1]
            
            if not validate_price(last_close):
                logging.warning(f"Invalid price for {symbol}: {last_close}")
                return None
                
            logging.info(f"Successfully fetched {symbol} Last Close: {last_close}")
            return last_close
            
        except Exception as e:
            logging.error(f"Error fetching {symbol} (Attempt {attempt+1}/{CONFIG['RETRY_ATTEMPTS']}): {str(e)}")
            time.sleep(CONFIG['RETRY_DELAY'])
    
    return None

def process_batch(symbols_batch: List[str]) -> Dict[str, float]:
    """Process a batch of symbols with rate limiting."""
    batch_data = {}
    for symbol in tqdm(symbols_batch, desc="Processing batch", unit="stock"):
        last_close = fetch_last_close(symbol)
        if last_close is not None:
            batch_data[symbol] = round(last_close, 2)
        time.sleep(CONFIG['RATE_LIMIT_DELAY'])  # Rate limiting
    return batch_data

def save_data(data: Dict[str, float], date: str) -> bool:
    """
    Save data to JSON file with error handling.
    
    Args:
        data (Dict[str, float]): Stock price data to save
        date (str): Current date string
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        filename = os.path.join(CONFIG['OUTPUT_DIR'], f'{date}_stock_last_close.json')
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        logging.info(f"Successfully saved data to {filename}")
        return True
    except Exception as e:
        logging.error(f"Error saving data: {str(e)}")
        return False
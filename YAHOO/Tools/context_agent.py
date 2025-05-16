from crewai import Agent
from typing import Dict, Optional, List, Any, ClassVar
from pydantic import Field
import logging
from datetime import datetime
import os
import sys
import yfinance as yf
import json
from tqdm import tqdm
import time
import yaml
import pandas as pd
import random
from config.paths import PATHS

# Configure logging with more detailed formatting
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Setup logging directory and file
log_dir = PATHS['YAHOO']['LOGS']
log_file = log_dir / f'{datetime.now().strftime("%Y-%m-%d")}_context_agent.log'
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class ConfigurationManager:
    """Configuration management for the ContextAgent"""
    
    @staticmethod
    def setup_directories() -> Dict[str, str]:
        """Create and validate necessary directories."""
        date_now = datetime.now().strftime('%Y-%m-%d')
        log_dir = PATHS['YAHOO']['LOGS']
        output_dir = PATHS['YAHOO']['OUTPUTS']
        
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Log directory validated: {log_dir}")
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory validated: {output_dir}")
            
            return {
                'LOG_FILE': str(log_dir / f'{date_now}_stock_price_fetcher.log'),
                'OUTPUT_DIR': str(output_dir),
                'DATE': date_now
            }
        except Exception as e:
            logger.error(f"Error setting up directories: {str(e)}")
            raise
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate configuration parameters."""
        required_fields = {
            'RETRY_ATTEMPTS': (int, lambda x: x > 0),
            'RETRY_DELAY': ((int, float), lambda x: x >= 0),
            'RATE_LIMIT_DELAY': ((int, float), lambda x: x >= 0),
            'BATCH_SIZE': (int, lambda x: x > 0)
        }
        
        try:
            for field, (expected_type, validator) in required_fields.items():
                if field not in config:
                    logger.error(f"Missing required configuration field: {field}")
                    return False
                    
                if not isinstance(config[field], expected_type):
                    logger.error(f"Invalid type for {field}. Expected {expected_type}, got {type(config[field])}")
                    return False
                    
                if not validator(config[field]):
                    logger.error(f"Invalid value for {field}: {config[field]}")
                    return False
            
            logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Error during configuration validation: {str(e)}")
            return False
    
    @staticmethod
    def validate_symbols(symbols: List[str]) -> bool:
        """Validate stock symbols list."""
        try:
            if not symbols:
                logger.error("Symbols list cannot be empty")
                return False
                
            if not all(isinstance(symbol, str) for symbol in symbols):
                logger.error("All symbols must be strings")
                return False
                
            if not all(symbol.strip() for symbol in symbols):
                logger.error("Symbols cannot be empty strings")
                return False
                
            if len(symbols) != len(set(symbols)):
                logger.error("Duplicate symbols found in the list")
                return False
            
            logger.info(f"Symbol list validation successful. Total symbols: {len(symbols)}")
            return True
            
        except Exception as e:
            logger.error(f"Error during symbols validation: {str(e)}")
            return False

class StockDataFetcher:
    """Handles stock data fetching operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        logger.info("StockDataFetcher initialized with configuration")
    
    def validate_price(self, price: float) -> bool:
        """Validate if the price is reasonable."""
        return isinstance(price, (int, float)) and price > 0

    def fetch_last_close(self, symbol: str) -> Optional[float]:
        """Fetch last close price for a given symbol with retries."""
        for attempt in range(self.config['RETRY_ATTEMPTS']):
            try:
                # Add exponential backoff delay
                if attempt > 0:
                    delay = self.config['RETRY_DELAY'] * (2 ** attempt)
                    logger.info(f"Retry attempt {attempt + 1}, waiting {delay} seconds...")
                    time.sleep(delay)
                
                stock = yf.Ticker(symbol)
                history = stock.history(period="1d")
                
                if history.empty:
                    logger.warning(f"No data available for {symbol}")
                    return None
                    
                last_close = history['Close'].iloc[-1]
                
                if not self.validate_price(last_close):
                    logger.warning(f"Invalid price for {symbol}: {last_close}")
                    return None
                    
                logger.debug(f"Successfully fetched {symbol} Last Close: {last_close}")
                return last_close
                
            except Exception as e:
                logger.error(f"Error fetching {symbol} (Attempt {attempt+1}/{self.config['RETRY_ATTEMPTS']}): {str(e)}")
                if attempt < self.config['RETRY_ATTEMPTS'] - 1:
                    time.sleep(self.config['RETRY_DELAY'])
        
        return None

    def process_batch(self, symbols_batch: List[str]) -> Dict[str, float]:
        """Process a batch of symbols with rate limiting."""
        batch_data = {}
        for symbol in tqdm(symbols_batch, desc="Processing batch", unit="stock"):
            # Add random delay between requests
            delay = random.uniform(2, 5)
            time.sleep(delay)
            
            last_close = self.fetch_last_close(symbol)
            if last_close is not None:
                batch_data[symbol] = round(last_close, 2)
        return batch_data

    def save_data(self, data: Dict[str, float], date: str) -> bool:
        """Save data to JSON file with error handling."""
        try:
            filename = PATHS['YAHOO']['OUTPUTS'] / f'{date}_stock_last_close.json'
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Successfully saved data to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")
            return False

    def update_historical_csv(self, prices: dict, date: str, csv_path: Optional[str] = None) -> bool:
        """Update or create a historical CSV with last close prices for each symbol and date."""
        try:
            if csv_path is None:
                csv_path = PATHS['YAHOO']['OUTPUTS'] / 'historical_stock_prices.csv'
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path, index_col=0)
            else:
                df = pd.DataFrame(index=prices.keys())
            # Add today's prices
            df[date] = pd.Series(prices)
            df = df.sort_index()
            df.to_csv(csv_path)
            logger.info(f"Successfully updated historical CSV at {csv_path}")
            return True
        except Exception as e:
            logger.error(f"Error updating historical CSV: {str(e)}")
            return False

class ContextAgent(Agent):
    """Agent for fetching and maintaining stock price context"""
    
    # Default configuration - will be overridden by YAML when available
    DEFAULT_CONFIG: ClassVar[Dict[str, Any]] = {
        'RETRY_ATTEMPTS': 3,
        'RETRY_DELAY': 5,
        'RATE_LIMIT_DELAY': 1,
        'BATCH_SIZE': 50,
        'SYMBOLS': [],  # Empty default list, will be loaded from YAML
        'HISTORICAL_CSV_PATH': None  # Optional CSV path
    }
    
    # Field declarations
    data_fetcher: Any = Field(default=None, description="The stock data fetcher instance")
    config: Dict[str, Any] = Field(default_factory=lambda: ContextAgent.DEFAULT_CONFIG.copy())

    def __init__(self, config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None, **kwargs):
        """Initialize the ContextAgent.
        
        Args:
            config: Optional dictionary with configuration values
            config_path: Optional path to a YAML configuration file
            **kwargs: Additional arguments for the Agent base class
        """
        print("="*80)
        print("INITIALIZING CONTEXT AGENT")
        print("="*80)
        logger.info("Initializing ContextAgent")
        
        # First create base Agent fields
        base_kwargs = {
            "role": 'Stock Price Context Generator',
            "goal": 'Generate accurate last closing price data for stocks to provide market context',
            "backstory": """I am a specialized agent that fetches and maintains up-to-date stock price data 
            for market analysis and decision making. I ensure data quality through validation and error handling.""",
            "allow_delegation": False,
            "verbose": True
        }
        base_kwargs.update(kwargs)
        super().__init__(**base_kwargs)
        
        # Setup configuration after super init
        if config:
            self.config.update(config)
            print(f"Configuration dictionary provided with {len(config)} parameters")
        
        # Load configuration from YAML if path provided
        if config_path:
            print(f"Loading configuration from: {config_path}")
            yaml_config = self.load_config_from_yaml(config_path)
            if yaml_config is None:
                error_msg = f"Failed to load configuration from {config_path}"
                print(f"ERROR: {error_msg}")
                raise ValueError(error_msg)
            else:
                print(f"Successfully loaded configuration with {len(yaml_config)} parameters")
                if 'SYMBOLS' in yaml_config:
                    print(f"Loaded {len(yaml_config['SYMBOLS'])} symbols from configuration")
        
        # Validate final configuration
        print("Validating configuration...")
        if not ConfigurationManager.validate_config(self.config):
            error_msg = "Invalid configuration provided"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        print("Configuration validation successful")
            
        # Initialize data fetcher after config
        print("Initializing data fetcher...")
        self.data_fetcher = StockDataFetcher(self.config)
        logger.info("ContextAgent initialized successfully")
        print("ContextAgent initialized successfully")
        print("="*80)

    def execute_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a task based on the given instruction and context."""
        logger.info(f"Executing task: {task}")
        
        # Ensure context is a dictionary
        if context is None:
            context = {}
        elif isinstance(context, str):
            # Handle case where context is passed as a string
            logger.warning(f"Context was passed as a string: '{context}'. Converting to dictionary.")
            context = {"instruction": context}
        
        try:
            # Setup directories
            dirs = ConfigurationManager.setup_directories()
            self.config.update(dirs)
            
            # Process symbols in batches - use symbols from config if not provided in context
            symbols = context.get('symbols', self.config.get('SYMBOLS', []))
            if not ConfigurationManager.validate_symbols(symbols):
                raise ValueError("Invalid symbols list")
            
            all_data = {}
            for i in range(0, len(symbols), self.config['BATCH_SIZE']):
                batch = symbols[i:i + self.config['BATCH_SIZE']]
                batch_data = self.data_fetcher.process_batch(batch)
                all_data.update(batch_data)
            
            # Save the results
            if all_data:
                self.data_fetcher.save_data(all_data, self.config['DATE'])
                # Update or create the historical CSV
                csv_path = self.config.get('HISTORICAL_CSV_PATH', os.path.join(self.config['OUTPUT_DIR'], 'historical_stock_prices.csv'))
                self.data_fetcher.update_historical_csv(all_data, self.config['DATE'], csv_path=csv_path)
                return {
                    'status': 'success',
                    'data': all_data,
                    'message': f"Successfully processed {len(all_data)} symbols"
                }
            else:
                return {
                    'status': 'error',
                    'data': {},
                    'message': "No valid data was collected"
                }
                
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            return {
                'status': 'error',
                'data': {},
                'message': f"Task execution failed: {str(e)}"
            }
    
    def get_task_context(self) -> Dict[str, Any]:
        """Get the current context for task execution."""
        return {
            'config': self.config,
            'symbols': self.SYMBOLS,
            'date': datetime.now().strftime('%Y-%m-%d')
        }

    def load_config_from_yaml(self, config_path):
        """Load configuration from a YAML file.
        
        Args:
            config_path: Path to the YAML configuration file
            
        Returns:
            Dict containing the configuration or None if loading failed
        """
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            logger.info(f"Configuration loaded from {config_path}")
            
            # Update the agent's config with the loaded values
            if config:
                self.config.update(config)
                
            # Validate the updated configuration
            if not ConfigurationManager.validate_config(self.config):
                logger.error("Invalid configuration in YAML file")
                return None
                
            return config
        except Exception as e:
            logger.error(f"Error loading configuration from YAML: {str(e)}")
            return None

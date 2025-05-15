from typing import Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

class ConfigurationValidator:
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        Validates the configuration dictionary for required fields and correct types.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary to validate
            
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        required_fields = {
            'RETRY_ATTEMPTS': int,
            'RETRY_DELAY': (int, float),
            'RATE_LIMIT_DELAY': (int, float),
            'LOG_FILE': str,
            'OUTPUT_DIR': str,
            'CURRENT_DATE': str,
            'BATCH_SIZE': int
        }
        
        try:
            # Check for required fields and their types
            for field, expected_type in required_fields.items():
                if field not in config:
                    logger.error(f"Missing required configuration field: {field}")
                    return False
                
                if not isinstance(config[field], expected_type):
                    logger.error(f"Invalid type for {field}. Expected {expected_type}, got {type(config[field])}")
                    return False
            
            # Validate specific field values
            if config['RETRY_ATTEMPTS'] <= 0:
                logger.error("RETRY_ATTEMPTS must be greater than 0")
                return False
                
            if config['RETRY_DELAY'] < 0:
                logger.error("RETRY_DELAY cannot be negative")
                return False
                
            if config['RATE_LIMIT_DELAY'] < 0:
                logger.error("RATE_LIMIT_DELAY cannot be negative")
                return False
                
            if config['BATCH_SIZE'] <= 0:
                logger.error("BATCH_SIZE must be greater than 0")
                return False
            
            # Validate directories exist or can be created
            try:
                os.makedirs(os.path.dirname(config['LOG_FILE']), exist_ok=True)
                os.makedirs(config['OUTPUT_DIR'], exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating directories: {str(e)}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error during configuration validation: {str(e)}")
            return False
            
    @staticmethod
    def validate_symbols(symbols: list) -> bool:
        """
        Validates the stock symbols list.
        
        Args:
            symbols (list): List of stock symbols to validate
            
        Returns:
            bool: True if symbols list is valid, False otherwise
        """
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
                
            return True
            
        except Exception as e:
            logger.error(f"Error during symbols validation: {str(e)}")
            return False

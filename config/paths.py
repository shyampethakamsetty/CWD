import os
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Define all paths relative to project root
PATHS = {
    # Yahoo paths
    'YAHOO': {
        'ROOT': PROJECT_ROOT / 'YAHOO',
        'LOGS': PROJECT_ROOT / 'YAHOO' / 'Logs',
        'OUTPUTS': PROJECT_ROOT / 'YAHOO' / 'Outputs',
        'CONFIG': PROJECT_ROOT / 'YAHOO' / 'Config',
    },
    
    # YouTube paths
    'YOUTUBE': {
        'ROOT': PROJECT_ROOT / 'YOUTUBE',
        'LOGS': PROJECT_ROOT / 'YOUTUBE' / 'Logs',
        'OUTPUTS': PROJECT_ROOT / 'YOUTUBE' / 'Outputs',
        'CONFIG': PROJECT_ROOT / 'YOUTUBE' / 'Config',
        'CACHE': PROJECT_ROOT / 'YOUTUBE' / '.cache',
    },
    
    # Common paths
    'COMMON': {
        'LOGS': PROJECT_ROOT / 'Logs',
        'CONFIG': PROJECT_ROOT / 'Config',
    }
}

# Create all directories if they don't exist
def ensure_directories():
    """Create all necessary directories if they don't exist"""
    for category in PATHS.values():
        for path in category.values():
            path.mkdir(parents=True, exist_ok=True)

# Initialize directories
ensure_directories() 
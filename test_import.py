import os
import sys

print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

try:
    from config.paths import PATHS
    print("Successfully imported PATHS")
    print(PATHS)
except ImportError as e:
    print(f"Import error: {e}") 
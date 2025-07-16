import os
from dotenv import load_dotenv
from pathlib import Path

# Try multiple ways to load .env
print(f"Current directory: {os.getcwd()}")
print(f".env exists: {os.path.exists('.env')}")

# Load with explicit path
env_path = Path('.') / '.env'
load_dotenv(env_path)

# Also try without path
load_dotenv()

# Check what we got
api_key = os.getenv('API_KEY')
print(f"API_KEY from env: {api_key}")
print(f"API_KEY type: {type(api_key)}")
print(f"API_KEY length: {len(api_key) if api_key else 'None'}")

# Also check with default
api_key_with_default = os.getenv('API_KEY', 'default-not-found')
print(f"API_KEY with default: {api_key_with_default}")
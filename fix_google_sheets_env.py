#!/usr/bin/env python3
"""
Quick fix for missing GOOGLE_SHEETS_CREDENTIALS_FILE environment variable.
This script will help you set it up properly.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv, set_key

# Load existing environment variables
load_dotenv()

print("🔧 GOOGLE SHEETS CREDENTIALS SETUP\n")

# Check for common credential file locations
possible_locations = [
    "credentials.json",
    "google-credentials.json",
    "sheets-credentials.json",
    "service-account-key.json",
    "config/credentials.json",
    "src/config/credentials.json",
    ".credentials/google-sheets.json"
]

found_files = []
for location in possible_locations:
    if Path(location).exists():
        found_files.append(location)
        print(f"✅ Found: {location}")

if found_files:
    print(f"\nFound {len(found_files)} potential credential file(s).")
    
    if len(found_files) == 1:
        cred_file = found_files[0]
        print(f"\nUsing: {cred_file}")
    else:
        print("\nMultiple credential files found. Please select one:")
        for i, f in enumerate(found_files, 1):
            print(f"{i}. {f}")
        
        choice = input("\nEnter number (or press Enter to skip): ").strip()
        if choice and choice.isdigit() and 1 <= int(choice) <= len(found_files):
            cred_file = found_files[int(choice) - 1]
        else:
            cred_file = None
    
    if cred_file:
        # Update .env file
        env_file = Path(".env")
        if env_file.exists():
            set_key(".env", "GOOGLE_SHEETS_CREDENTIALS_FILE", cred_file)
            print(f"\n✅ Updated .env file with GOOGLE_SHEETS_CREDENTIALS_FILE={cred_file}")
        else:
            print(f"\n⚠️  No .env file found. Add this line manually:")
            print(f"GOOGLE_SHEETS_CREDENTIALS_FILE={cred_file}")
        
        # Set for current session
        os.environ["GOOGLE_SHEETS_CREDENTIALS_FILE"] = cred_file
        print(f"✅ Set environment variable for current session")
else:
    print("\n❌ No credential files found in common locations.")
    print("\nTo fix this:")
    print("1. Download your Google Sheets service account credentials")
    print("2. Save it as 'credentials.json' in the project root")
    print("3. Run this script again")
    print("\nAlternatively, add this line to your .env file:")
    print("GOOGLE_SHEETS_CREDENTIALS_FILE=path/to/your/credentials.json")

# Test if it's set now
if os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE"):
    print("\n✅ GOOGLE_SHEETS_CREDENTIALS_FILE is now set!")
    
    # Try to validate the file
    cred_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
    if Path(cred_path).exists():
        try:
            with open(cred_path) as f:
                creds = json.load(f)
                if "type" in creds and creds["type"] == "service_account":
                    print("✅ Valid service account credentials file")
                else:
                    print("⚠️  File exists but may not be valid service account credentials")
        except:
            print("⚠️  Could not validate credentials file format")
    else:
        print("❌ Credentials file path is set but file doesn't exist")
else:
    print("\n❌ GOOGLE_SHEETS_CREDENTIALS_FILE is still not set")

print("\nYou can now run the intake tests!")
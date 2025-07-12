import requests
import json

# Your API details
API_URL = "http://localhost:8000/api/assessment"
API_KEY = "your-api-key-from-env-file"

# Sample data
test_data = {
    "uuid": "test-123",
    "timestamp": "2024-01-15T10:00:00Z",
    "name": "John Smith",
    "email": "john@example.com",
    "industry": "Professional Services",
    "years_in_business": "10-20 years",
    "age_range": "55-64",
    "exit_timeline": "1-2 years",
    "location": "Pacific/Western US",
    "responses": {
        "q1": "I handle all client meetings and final approvals",
        "q2": "Less than 3 days",
        "q3": "Consulting 60%, Training 40%",
        "q4": "20-40%",
        "q5": "7",
        "q6": "Improved slightly",
        "q7": "Client relationships and technical knowledge",
        "q8": "4",
        "q9": "Long-term client relationships",
        "q10": "8"
    }
}

# Make the request
headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

response = requests.post(API_URL, json=test_data, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
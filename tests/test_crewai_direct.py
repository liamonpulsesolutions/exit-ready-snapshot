from src.crew import ExitReadySnapshotCrew
import json

# Use the actual data from your Tally test
test_data = {
    "uuid": "test-direct-123",
    "timestamp": "2025-07-12T12:00:00Z",
    "name": "Form Test 01",
    "email": "test@forms.com",
    "industry": "Advertising & Marketing",
    "years_in_business": "10-20 years",
    "age_range": "55-64",
    "exit_timeline": "2-3 years",
    "location": "Pacific/Western US",
    "responses": {
        "q1": "Final client presentation approvals and major campaign strategy decisions",
        "q2": "Less than 3 days",
        "q3": "1) Monthly retainer clients for ongoing digital marketing services - about 65% of revenue",
        "q4": "60-80%",
        "q5": "6",
        "q6": "Declined slightly",
        "q7": "1) Client relationship management and day-to-day project coordination",
        "q8": "4",
        "q9": "1) Exclusive partnerships with three major industry software platforms",
        "q10": "7"
    }
}

print("Testing CrewAI directly...")
print("This will take 1-2 minutes as agents process...\n")

# Initialize and run
crew = ExitReadySnapshotCrew(locale='us')
result = crew.kickoff(inputs=test_data)

print("\nCrewAI Result:")
print(json.dumps(result, indent=2))
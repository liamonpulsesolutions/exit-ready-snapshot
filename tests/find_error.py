import json
with open('output_test_enhanced_qa_20250715_225951.json') as f:
    data = json.load(f)
    print("Failed assertions:")
    for a in data['assertions']:
        if not a['passed']:
            print(f"- {a['description']}")
            print(f"  Details: {a.get('details', {})}")
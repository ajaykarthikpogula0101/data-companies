from education_ontology import classify_education

# Test the specific failing case
text = " Studium der Informatik"
print(f"Testing: {repr(text)}")

result = classify_education(text)
print(f"Result:")
print(f"  education_type: value='{result['education_type'].value}'")
print(f"  education_stream: value='{result['education_stream'].value}'")
print(f"  education_qualification: value='{result['education_qualification'].value}'")

# Let's also test what we expect
expected_stream = "Computer Science / IT"
print(f"\nExpected stream: {expected_stream}")
print(f"Actual stream: '{result['education_stream'].value}'")
print(f"Match: {result['education_stream'].value == expected_stream}")
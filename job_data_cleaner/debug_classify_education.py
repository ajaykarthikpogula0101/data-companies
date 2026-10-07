from education_ontology import classify_education, classify_type, classify_stream

text = " Studium der Informatik"
print(f"Text: {repr(text)}")

# Check classify_type
edu_type = classify_type(text)
print(f"classify_type result: value='{edu_type.value}', confidence='{edu_type.confidence}'")

# Check classify_stream directly
stream = classify_stream(text)
print(f"classify_stream result: value='{stream.value}', confidence='{stream.confidence}'")

# Check the full classification
result = classify_education(text)
print(f"\nFull classify_education result:")
print(f"  education_type: value='{result['education_type'].value}', confidence='{result['education_type'].confidence}'")
print(f"  education_stream: value='{result['education_stream'].value}', confidence='{result['education_stream'].confidence}'")
print(f"  education_qualification: value='{result['education_qualification'].value}', confidence='{result['education_qualification'].confidence}'")
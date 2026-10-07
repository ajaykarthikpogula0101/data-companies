from education_ontology import classify_education, classify_type, WEAK_LEVELS, first_match_in_list_order

# Debug the two failing cases
test_cases = [
    ' abgeschlossene Fachschulausbildung',
    ' Ausbildung im Maschinenbau'
]

for text in test_cases:
    print(f"\n=== Debugging: '{text}' ===")

    # Check classify_type
    edu_type = classify_type(text)
    print(f"classify_type result: value='{edu_type.value}', confidence='{edu_type.confidence}'")

    # Check WEAK_LEVELS matches in order
    print("WEAK_LEVELS matches in order:")
    for i, (value, pattern) in enumerate(WEAK_LEVELS):
        import re
        match = re.search(pattern, text, re.I)
        if match:
            print(f"  {i}: {value} - MATCH: '{match.group()}'")
        else:
            print(f"  {i}: {value} - no match")

    # Check first_match_in_list_order
    match_result = first_match_in_list_order(text, WEAK_LEVELS)
    if match_result:
        print(f"first_match_in_list_order: {match_result[1]} at position {match_result[0]}")
    else:
        print("first_match_in_list_order: None")

    # Full classification
    result = classify_education(text)
    print(f"classify_education result:")
    print(f"  education_type: value='{result['education_type'].value}', confidence='{result['education_type'].confidence}'")
    print(f"  education_stream: value='{result['education_stream'].value}', confidence='{result['education_stream'].confidence}'")
    print(f"  education_qualification: value='{result['education_qualification'].value}', confidence='{result['education_qualification'].confidence}'")
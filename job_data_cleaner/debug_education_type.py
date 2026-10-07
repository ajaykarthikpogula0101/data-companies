from education_ontology import classify_education, classify_type, STRONG_LEVELS, WEAK_LEVELS, cue_windows, earliest

def debug_education_detection(text):
    print(f"\n=== Debugging education detection for: '{text}' ===")

    # First check what classify_type returns
    edu_type_result = classify_type(text)
    print(f"classify_type result: value='{edu_type_result.value}', confidence='{edu_type_result.confidence}'")

    # Check STRONG_LEVELS
    hit = earliest(text, STRONG_LEVELS)
    if hit:
        print(f"Strong level match: {hit[1]} at position {hit[0]}")
    else:
        print("No strong level match")

    # Check WEAK_LEVELS in cue windows
    print("\nChecking WEAK_LEVELS in cue windows:")
    windows = cue_windows(text)
    print(f"Number of cue windows: {len(windows)}")

    candidates = []
    for offset, window in windows:
        hit = earliest(window, WEAK_LEVELS)
        if hit:
            candidates.append((offset + hit[0], hit[1], hit[2], window))
            print(f"  Window offset {offset}: '{window[:50]}{'...' if len(window) > 50 else ''}' -> {hit[1]} at position {hit[0]} in window")

    if candidates:
        _, value, match, window = min(candidates, key=lambda item: item[0])
        print(f"Best WEAK_LEVELS candidate in window: {value} at position {_}")

    # Check WEAK_LEVELS on whole text as fallback
    hit = earliest(text, WEAK_LEVELS)
    if hit:
        print(f"WEAK_LEVELS match on whole text: {hit[1]} at position {hit[0]}")
    else:
        print("No WEAK_LEVELS match on whole text")

    # Now the full classification
    result = classify_education(text)
    print(f"\nFinal result:")
    print(f"  education_type: value='{result['education_type'].value}', confidence='{result['education_type'].confidence}'")
    print(f"  education_stream: value='{result['education_stream'].value}', confidence='{result['education_stream'].confidence}'")
    print(f"  education_qualification: value='{result['education_qualification'].value}', confidence='{result['education_qualification'].confidence}'")

# Test the failing cases
test_cases = [
    " Studium der Informatik",
    " Ausbildung im Maschinenbau",
    " Studium der Elektrotechnik",
    " Architektur Studium",
    " Betriebswirtschaftslehre Studium"
]

for case in test_cases:
    debug_education_detection(case)
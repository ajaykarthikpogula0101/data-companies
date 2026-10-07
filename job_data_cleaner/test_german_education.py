#!/usr/bin/env python3
"""Test script to validate German education enhancements"""

from education_ontology import classify_education

def test_german_education_terms():
    """Test German-specific education terms"""

    # Test cases for German education terms
    # Format: (text, expected_education_type, expected_education_stream, expected_qualification)
    test_cases = [
        # Traditional German degrees
        ("Wir suchen einen Diplom-Ingenieur", "Master's Equivalent", "", ""),
        ("abgeschlossenes Studium als Magister", "Master's Equivalent", "", ""),
        ("Staatsexamen in Rechtswissenschaften", "State Examination", "", ""),
        ("Meister im Handwerk", "Master Craftsman", "", ""),
        ("staatlich geprüfter Techniker", "Technician", "", ""),

        # German vocational terms
        (" abgeschlossene Ausbildung als Facharbeiter", "Vocational Certificate", "", ""),
        ("Gesellenbrief im Schreinerhandwerk", "Vocational Certificate", "", ""),
        (" abgeschlossene Fachschulausbildung", "Technical School", "", ""),
        (" Fachhochschulabschluss Maschinenbau", "College of Applied Sciences", "", ""),
        (" duales Studium BWL", "Cooperative Education", "", ""),

        # German academic streams (these should detect stream but not necessarily type)
        (" Studium der Informatik", "", "Computer Science / IT", ""),
        (" Ausbildung im Maschinenbau", "Apprenticeship", "Engineering (German)", ""),
        (" Studium der Elektrotechnik", "", "Engineering (German)", ""),
        (" Architektur Studium", "", "Architecture", ""),
        (" Betriebswirtschaftslehre Studium", "", "Business Administration", ""),
    ]

    print("Testing German education enhancements...")
    passed = 0
    total = len(test_cases)

    for text, expected_type, expected_stream, expected_qualification in test_cases:
        result = classify_education(text)
        actual_type = result["education_type"].value
        actual_stream = result["education_stream"].value
        actual_qualification = result["education_qualification"].value

        # Check education type
        type_match = actual_type == expected_type
        # Check education stream
        stream_match = actual_stream == expected_stream
        # Check qualification
        qualification_match = actual_qualification == expected_qualification

        if type_match and stream_match and qualification_match:
            print(f"PASS: '{text}' -> type: {actual_type or '(empty)'}, stream: {actual_stream or '(empty)'}, qualification: {actual_qualification or '(empty)'}")
            passed += 1
        else:
            print(f"FAIL: '{text}'")
            if not type_match:
                print(f"  Type - Expected: {expected_type or '(empty)'}, Got: {actual_type or '(empty)'}")
            if not stream_match:
                print(f"  Stream - Expected: {expected_stream or '(empty)'}, Got: {actual_stream or '(empty)'}")
            if not qualification_match:
                print(f"  Qualification - Expected: {expected_qualification or '(empty)'}, Got: {actual_qualification or '(empty)'}")

    print(f"\nResults: {passed}/{total} tests passed")
    return passed == total

if __name__ == "__main__":
    success = test_german_education_terms()
    exit(0 if success else 1)
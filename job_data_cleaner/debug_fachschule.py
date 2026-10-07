import re
from education_ontology import WEAK_LEVELS, first_match_in_list_order

text = " abgeschlossene Fachschulausbildung"
print(f"Text: {repr(text)}")

# Check the Technical School pattern
pattern = r'\b(?:technikerschule|fachschulreife)\b'
print(f"Technical School pattern: {pattern}")
match = re.search(pattern, text, re.I)
print(f"Match: {match}")
if match:
    print(f"Matched: {match.group()}")

# Check all WEAK_LEVELS patterns in order
print("\nChecking WEAK_LEVELS in order:")
for i, (value, pat) in enumerate(WEAK_LEVELS):
    match = re.search(pat, text, re.I)
    if match:
        print(f"{i}: {value} - MATCH: {match.group()}")
    else:
        print(f"{i}: {value} - no match")

# Test first_match_in_list_order
result = first_match_in_list_order(text, WEAK_LEVELS)
if result:
    print(f"\nFirst match in list order: {result[1]} at position {result[0]}")
else:
    print(f"\nFirst match in list order: None")

# Test regular earliest function
from education_ontology import earliest
result2 = earliest(text, WEAK_LEVELS)
if result2:
    print(f"Earliest match (position order): {result2[1]} at position {result2[0]}")
else:
    print(f"Earliest match (position order): None")
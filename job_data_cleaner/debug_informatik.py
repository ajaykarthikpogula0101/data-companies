import re
from education_ontology import STREAMS, CUE, first_match_in_list_order, cue_windows

text = " Studium der Informatik"
print(f"Text: {repr(text)}")

# Check if we find any cues
cues = list(CUE.finditer(text))
print(f"Cues found: {[m.group() for m in cues]}")

# Check the Computer Science / IT pattern
pattern = r'\b(?:computer science|software engineering|information technology|informatics|computer engineering|informatik|informationstechnologie|anwendungsentwicklung|systemintegration)\b'
print(f"Computer Science / IT pattern: {pattern}")
match = re.search(pattern, text, re.I)
print(f"Match: {match}")
if match:
    print(f"Matched: {match.group()}")

# Check all STREAMS patterns in order
print("\nChecking STREAMS in order:")
for i, (value, pat) in enumerate(STREAMS):
    match = re.search(pat, text, re.I)
    if match:
        print(f"{i}: {value} - MATCH: {match.group()}")
    else:
        print(f"{i}: {value} - no match")

# Test first_match_in_list_order
result = first_match_in_list_order(text, STREAMS)
if result:
    print(f"\nFirst match in list order: {result[1]} at position {result[0]}")
else:
    print(f"\nFirst match in list order: None")

# Check cue_windows
windows = cue_windows(text)
print(f"\nNumber of windows: {len(windows)}")
for i, (offset, window) in enumerate(windows):
    print(f"Window {i}: offset={offset}, text='{window}'")
    hit = first_match_in_list_order(window, STREAMS)
    if hit:
        print(f"  -> Stream match: {hit[1]} at position {hit[0]} in window")
    else:
        print(f"  -> No STREAMS match in this window")
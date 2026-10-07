import re
from education_ontology import WEAK_LEVELS, CUE, QUALIFICATION, earliest

# Let's test the pattern for Facharbeiter
pattern = r'\b(?:facharbeiter|gesellenbrief|ibb)\b'
text = " abgeschlossene Ausbildung als Facharbeiter"
print(f"Text: {repr(text)}")
print(f"Pattern: {pattern}")
match = re.search(pattern, text, re.I)
print(f"Match: {match}")
if match:
    print(f"Matched: {match.group()}")

# Now let's see what earliest returns for WEAK_LEVELS
print("\nTesting earliest with WEAK_LEVELS:")
for value, pat in WEAK_LEVELS:
    if re.search(pat, text, re.I):
        print(f"Matched {value} with pattern {pat}")

# Now let's test the cue_windows and see if the cue word is found
print("\nTesting cue_windows:")
cues = list(CUE.finditer(text))
print(f"Cues found: {cues}")
for m in cues:
    print(f"Cue: {m.group()} at {m.start()}-{m.end()}")

# Now let's test the whole classify_education function step by step
from education_ontology import classify_education
result = classify_education(text)
print(f"\nResult: {result}")
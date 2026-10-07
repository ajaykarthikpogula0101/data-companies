import re

# Test the business administration pattern
pattern = r"\b(?:business administration|business studies|mba|betriebswirtschaft|lwu|lw|wae|wirtschaftsingenieurwesen|handelswirtschaft)\b"
text = "Betriebswissenschaftslehre Studium"
print(f"Text: {text}")
print(f"Pattern: {pattern}")

match = re.search(pattern, text, re.IGNORECASE)
print(f"Match: {match}")

# Let's see what substrings we have
text_lower = text.lower()
print(f"Lowercase text: {text_lower}")
print(f"Contains 'betriebswirtschaft': {'betriebswirtschaft' in text_lower}")

# Check if there's a word boundary issue
# Let's try without word boundaries
pattern_no_bound = r"(?:business administration|business studies|mba|betriebswirtschaft|lwu|lw|wae|wirtschaftsingenieurwesen|handelswirtschaft)"
match_no_bound = re.search(pattern_no_bound, text, re.IGNORECASE)
print(f"Match without boundaries: {match_no_bound}")
if match_no_bound:
    print(f"Matched text: '{match_no_bound.group()}'")
    print(f"Position: {match_no_bound.start()}-{match_no_bound.end()}")
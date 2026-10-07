import sys
sys.path.insert(0, '/d/data_companies')
from job_data_cleaner.mojibake_fix import clean_with_mojibake_fix

s = "We are looking for an engineer with knowledge of Ändern and Übertragung. Also we need someone who can work with Müller und Schmitt."
print("Input:", repr(s))
print("Output:", repr(clean_with_mojibake_fix(s)))
print("Output (pretty):", clean_with_mojibake_fix(s))
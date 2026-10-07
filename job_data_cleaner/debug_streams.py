import re
from education_ontology import STREAMS, CUE, earliest, cue_windows

def debug_stream_detection(text):
    print(f"\n=== Debugging stream detection for: '{text}' ===")

    # Check if we find any cues
    cues = list(CUE.finditer(text))
    print(f"Cues found: {[m.group() for m in cues]}")

    if not cues:
        print("No cues found - trying direct STREAMS match on text")
        hit = earliest(text, STREAMS)
        if hit:
            print(f"Direct match: {hit[1]} at position {hit[0]}")
        else:
            print("No direct STREAMS match found")
        return

    # Check each cue window
    windows = cue_windows(text)
    print(f"Number of windows: {len(windows)}")

    for i, (offset, window) in enumerate(windows):
        print(f"\nWindow {i}: offset={offset}, text='{window[:100]}{'...' if len(window) > 100 else ''}'")
        hit = earliest(window, STREAMS)
        if hit:
            print(f"  -> Stream match: {hit[1]} at position {hit[0]} in window")
            print(f"     Absolute position: {offset + hit[0]}")
        else:
            print(f"  -> No STREAMS match in this window")

    # Check what earliest on whole text gives us
    hit = earliest(text, STREAMS)
    if hit:
        print(f"\nDirect STREAMS match on whole text: {hit[1]} at position {hit[0]}")
    else:
        print(f"\nNo direct STREAMS match on whole text")

# Test the failing cases
test_cases = [
    " Studium der Informatik",
    " Ausbildung im Maschinenbau",
    " Studium der Elektrotechnik",
    " Architektur Studium",
    " Betriebswirtschaftslehre Studium"
]

for case in test_cases:
    debug_stream_detection(case)
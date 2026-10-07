import re

# Test the current pattern
current_pattern = re.compile(r"(?:boards|careers)\.greenhouse\.io/([a-zA-Z0-9\-_.]+)")
test_url = "https://boards.eu.greenhouse.io/embed/job_board/js?for=b2c2"

print(f"Testing URL: {test_url}")
print(f"Current pattern: {current_pattern.pattern}")

match = current_pattern.search(test_url)
if match:
    print(f"Match: {match.group()}")
    print(f"Group 1: '{match.group(1)}'")
else:
    print("No match with current pattern")

print("\n" + "="*50)

# Test a pattern that looks for greenhouse.io and then tries to extract from path or query
pattern2 = re.compile(r"(?:boards|careers)\.greenhouse\.io/(?:[^/?#]+/)*(?:[^/?#]*[?&]for=)?([a-zA-Z0-9\-_.]+)")
print(f"Pattern 2: {pattern2.pattern}")

match2 = pattern2.search(test_url)
if match2:
    print(f"Match 2: {match2.group()}")
    print(f"Group 1: '{match2.group(1)}'")
else:
    print("No match with pattern 2")

print("\n" + "="*50)

# Test a simpler approach: check for greenhouse.io domain, then look for for parameter
import urllib.parse

def detect_greenhouse_with_query(url):
    """Special handling for greenhouse URLs with company in query parameter"""
    parsed = urllib.parse.urlparse(url.lower())
    if 'greenhouse.io' in parsed.netloc:
        # Check if it's a boards or careers subdomain
        if any(subdomain in parsed.netloc for subdomain in ['boards', 'careers']):
            # Look for 'for' parameter in query string
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'for' in query_params and query_params['for']:
                return 'greenhouse', query_params['for'][0]
    return None, None

print("Testing custom greenhouse detection:")
ats, captured = detect_greenhouse_with_query(test_url)
print(f"ATS: {ats}, Captured: '{captured}'")

# Test with a standard greenhouse URL
std_url = "https://boards.greenhouse.io/acmecorp"
print(f"\nTesting standard URL: {std_url}")
ats2, captured2 = detect_greenhouse_with_query(std_url)
print(f"ATS: {ats2}, Captured: '{captured2}'")

# Test with greenhouse URL that has company in path
path_url = "https://boards.eu.greenhouse.io/acmecorp/jobs"
print(f"\nTesting path-based URL: {path_url}")
ats3, captured3 = detect_greenhouse_with_query(path_url)
print(f"ATS: {ats3}, Captured: '{captured3}'")

print("\n" + "="*50)
print("Combined approach:")

def detect_greenhouse_combined(url):
    """Combined detection for greenhouse URLs"""
    # First try the standard pattern
    std_pattern = re.compile(r"(?:boards|careers)\.greenhouse\.io/([a-zA-Z0-9\-_.]+)")
    match = std_pattern.search(url)
    if match:
        return 'greenhouse', match.group(1)

    # If that fails, try to extract from query parameters
    parsed = urllib.parse.urlparse(url.lower())
    if 'greenhouse.io' in parsed.netloc:
        # Check if it's a boards or careers subdomain
        if any(subdomain in parsed.netloc for subdomain in ['boards', 'careers']):
            # Look for 'for' parameter in query string
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'for' in query_params and query_params['for']:
                return 'greenhouse', query_params['for'][0]

    return None, None

print(f"Testing combined approach with: {test_url}")
ats4, captured4 = detect_greenhouse_combined(test_url)
print(f"ATS: {ats4}, Captured: '{captured4}'")

print(f"\nTesting combined approach with: {std_url}")
ats5, captured5 = detect_greenhouse_combined(std_url)
print(f"ATS: {ats5}, Captured: '{captured5}'")

print(f"\nTesting combined approach with: {path_url}")
ats6, captured6 = detect_greenhouse_combined(path_url)
print(f"ATS: {ats6}, Captured: '{captured6}'")
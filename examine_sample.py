import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Examine the saved HTML sample
sample_file = r"D:\data_companies\b2c2_careers_sample.html"

print(f"Examining HTML sample from: {sample_file}")
print("=" * 60)

try:
    with open(sample_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    print(f"Sample length: {len(html_content)} characters")
    print("\nFirst 2000 characters:")
    print(html_content[:2000])
    print("\n" + "=" * 60)

    # Look for the "Current job openings" heading and surrounding content
    if "Current job openings" in html_content:
        print("Found 'Current job openings' in the sample!")
        # Find the position
        pos = html_content.find("Current job openings")
        # Show surrounding content
        start = max(0, pos - 200)
        end = min(len(html_content), pos + 500)
        print(f"\nContext around 'Current job openings':")
        print(html_content[start:end])
    else:
        print("'Current job openings' not found in the sample")

    # Look for common job listing HTML patterns
    print("\n" + "=" * 60)
    print("Checking for common job listing HTML structures...")

    # Look for lists (ul/ol) that might contain jobs
    if "<ul" in html_content or "<ol" in html_content:
        print("Found list elements (ul/ol)")
        # Show some list content
        list_start = html_content.find("<ul")
        if list_start == -1:
            list_start = html_content.find("<ol")
        if list_start != -1:
            list_end = html_content.find("</ul>", list_start)
            if list_end == -1:
                list_end = html_content.find("</ol>", list_start)
            if list_end != -1:
                list_content = html_content[list_start:list_end+5]
                print(f"List content sample: {list_content[:500]}...")

    # Look for tables that might contain jobs
    if "<table" in html_content:
        print("Found table elements")
        table_start = html_content.find("<table")
        table_end = html_content.find("</table>", table_start)
        if table_end != -1:
            table_content = html_content[table_start:table_end+8]
            print(f"Table content sample: {table_content[:500]}...")

    # Look for divs with repetitive structure that might be job cards
    print("\n" + "=" * 60)
    print("Looking for repetitive div structures that might be job cards...")

    # Count occurrences of common div patterns
    div_patterns = [
        '<div class="',
        '<div id="',
        '</div>'
    ]

    for pattern in div_patterns:
        count = html_content.count(pattern)
        print(f"Pattern '{pattern}' appears {count} times")

except FileNotFoundError:
    print(f"Sample file not found: {sample_file}")
except Exception as e:
    print(f"Error reading sample file: {e}")

print("=" * 60)
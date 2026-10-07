import re
pattern = re.compile(r'(?P<min>\d{1,3}(?:[.]\d{3})*(?:[,]\d+)?)\s*(?:-|–|—|to)\s*(?P<max>\d{1,3}(?:[.]\d{3})*(?:[,]\d+)?)\s*(?:€|eur|euro)', re.I)
test = "Jahresbruttogehalt von 60.000-112.000€"
print("Pattern:", pattern)
print("Test:", test)
match = pattern.search(test)
if match:
    print("Match:", match.group())
    print("Groups:", match.groups())
    print("Group dict:", match.groupdict())
else:
    print("No match")
    # maybe the dash is a different unicode? Let's check
    for ch in test:
        print(f"{ch}: {ord(ch)}")
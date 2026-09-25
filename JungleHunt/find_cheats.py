import re

with open('junglehunt_A00_to_1eff_and_6000_to_7fff (annoté).txt', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("--- Usages of $42 / $43 ---")
for i, line in enumerate(lines, 1):
    if re.search(r'\$(42|43)\b', line):
        print(f"{i}: {line.strip()}")

print("\n--- Search for oxygen / diving / level 2 ---")
for i, line in enumerate(lines, 1):
    if any(k in line.lower() for k in ['oxyg', 'plong', 'croco', 'air', 'nage']):
        print(f"{i}: {line.strip()}")

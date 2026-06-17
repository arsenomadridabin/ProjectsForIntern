import json
import re

# Read the markdown file
with open("output/2005-SLB/2005-SLB.md", "r") as f:
    lines = f.readlines()

# Find table lines
table_lines = [l.strip() for l in lines if l.startswith("|") and "Feldspar" in l or
               l.startswith("|") and "Olivine" in l or
               l.startswith("|") and "Wadsleyite" in l or
               l.startswith("|") and "Ringwoodite" in l or
               l.startswith("|") and "Orthopyroxene" in l or
               l.startswith("|") and "Clinopyroxene" in l or
               l.startswith("|") and "Perovskite" in l or
               l.startswith("|") and "Spinel" in l or
               l.startswith("|") and "Garnet" in l or
               l.startswith("|") and "Stishovite" in l or
               l.startswith("|") and "Akimotoite" in l or
               l.startswith("|") and "Magnesiow" in l or
               l.startswith("|") and "HP-clino" in l or
               l.startswith("|") and "Ca-perovskite" in l]

def clean(val):
    # Remove uncertainty in parentheses e.g. "128 (2)" -> 128.0
    val = val.strip()
    val = re.sub(r'\s*\(.*?\)', '', val)
    try:
        return float(val)
    except:
        return val

results = []
for line in table_lines:
    cols = [c.strip() for c in line.split("|")[1:-1]]
    if len(cols) < 11:
        continue
    entry = {
        "phase":    cols[0],
        "species":  cols[1],
        "formula":  cols[2],
        "V0":       clean(cols[3]),
        "K0":       clean(cols[4]),
        "K0_prime": clean(cols[5]),
        "theta0":   clean(cols[6]),
        "gamma0":   clean(cols[7]),
        "q":        clean(cols[8]),
        "G0":       clean(cols[9]),
        "G0_prime": clean(cols[10]),
        "eta_s0":   clean(cols[11]) if len(cols) > 11 else None
    }
    results.append(entry)

with open("output.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"Extracted {len(results)} mineral species to output.json")

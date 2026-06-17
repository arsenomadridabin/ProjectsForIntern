import json

def extract_mantle_parameters(md_file, json_file):

    results = []

    with open(md_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:

        if not line.startswith("|"):
            continue

        # Skip headers
        if (
            "Properties of mantle species" in line
            or "Phase" in line
            or "---" in line
        ):
            continue

        cols = [c.strip() for c in line.split("|")[1:-1]]

        # Data rows should have at least 13 columns
        if len(cols) < 13:
            continue

        try:
            entry = {
                "phase": cols[0],
                "species": cols[1],
                "formula": cols[2],

                "V0": cols[3],
                "K0": cols[4],
                "K0_prime": cols[5],
                "theta0": cols[6],
                "gamma0": cols[7],
                "q": cols[8],
                "G0": cols[9],
                "G0_prime": cols[10],
                "etaS0": cols[11]
            }

            results.append(entry)

        except IndexError:
            continue

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Extracted {len(results)} species")
    print(f"Saved to {json_file}")


if __name__ == "__main__":

    extract_mantle_parameters(
        "/jet/home/dwilson1/papers/output/2005-SLB/2005-SLB/2005-SLB.md",
        "mantle_parameters.json"
    )

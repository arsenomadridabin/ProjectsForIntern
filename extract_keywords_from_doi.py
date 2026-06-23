import csv
import time
import requests

BASE_URL = "https://api.crossref.org/works"
KEYWORDS = [
    "minerals crystallographic thermodynamics",
]
# Try and see what happends when you permute these keywords. For example : See what happens when you have keywords as: KEYWORDS = [ "thermodynamics minerals crystallographic" ]. Check what combination of keyword would help us get literatures on EOS of lower mantle minerals.
def get_year(item):
    for key in ["published-print", "published-online", "published"]:
        if key in item:
            parts = item[key].get("date-parts", [])
            if parts and parts[0]:
                return parts[0][0]
    return ""


def fetch_crossref_pages(query, start, end, mailto, rows=100, max_pages=20):
    headers = {
        "User-Agent": "columbia-mineral-search/1.0 (mailto:ashakya@ldeo.columbia.edu)"
    }

    cursor = "*"
    all_items = []

    for page in range(max_pages):
        print(f"Fetching page {page + 1}/{max_pages} for query: '{query}'")

        params = {
            "query": query,
            "rows": rows,
            "cursor": cursor,
            "filter": f"type:journal-article,from-pub-date:{start},until-pub-date:{end}",
            "select": "DOI,title,published-print,published-online,published",
            "mailto": mailto,
        }

        r = None
        for attempt in range(3):
            try: # See what is going on here.
                r = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
                if r.status_code == 200:
                    break
                print(f"HTTP {r.status_code}, retrying...")
            except requests.RequestException as e:
                print(f"Request error: {e}")

            time.sleep(2 * (attempt + 1))

        if r is None or r.status_code != 200:
            print(f"Failed query: {query}")
            break

        msg = r.json()["message"]
        items = msg.get("items", [])

        if not items:
            break

        all_items.extend(items)

        cursor = msg.get("next-cursor") # what is it doing ?
        if not cursor:
            break

        time.sleep(1) # Why do we need it here?

    return all_items


def harvest_dois(output_file, start, end, mailto):
    seen = set()
    records = []

    for query in KEYWORDS:
        print(f"\nSearching: {query}")

        items = fetch_crossref_pages(
            query=query,
            start=start,
            end=end,
            mailto=mailto,
            rows=100,
            max_pages=30, # See what happens when you change this parameter....increase it to 100, 200,....
        )

        for item in items:
            doi = item.get("DOI", "").strip().lower()
            if not doi or doi in seen:
                continue

            title = item.get("title", [""])[0]
            year = get_year(item)

            seen.add(doi)
            records.append({
                "doi": doi,
                "title": title,
                "year": year,
                "matched_query": query,
            })

        print(f"Unique DOIs so far: {len(seen)}")
        time.sleep(1)

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["doi", "title", "year", "matched_query"]
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"\nDone. Saved {len(records)} unique DOIs to {output_file}")


if __name__ == "__main__":
    harvest_dois(
        output_file="minerals_dois_1995_2025.csv",
        start="1995-01-01", # Change these parameters and see what happens
        end="2025-12-31",
        mailto="ashakya@ldeo.columbia.edu",
    )

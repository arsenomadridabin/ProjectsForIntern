from pathlib import Path
import json
import os
from openai import OpenAI

INPUT_FILE = "paper1.md"
OUTPUT_FILE = "paper1_parameters.json"

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

text = Path(INPUT_FILE).read_text(encoding="utf-8", errors="ignore")

# Keep only likely useful parts so we do not send the whole paper
keywords = ["V0", "K0", "theta", "gamma", "q0", "G0", "eta", "parameter", "species", "formula"]
chunks = text.split("\n\n")
useful_text = "\n\n".join(
    chunk for chunk in chunks
    if any(word.lower() in chunk.lower() for word in keywords)
)

prompt = f"""
Extract the 9 thermodynamic parameters from this Markdown.

Parameters:
V0, K0, K0_prime, theta0, gamma0, q0, G0, G0_prime, etaS0

Return ONLY valid JSON.

Use this format:
{{
  "species": [
    {{
      "phase": "",
      "species_name": "",
      "formula": "",
      "parameters": {{
        "V0": null,
        "K0": null,
        "K0_prime": null,
        "theta0": null,
        "gamma0": null,
        "q0": null,
        "G0": null,
        "G0_prime": null,
        "etaS0": null
      }}
    }}
  ]
}}

Markdown:
{useful_text}
"""

response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[{"role": "user", "content": prompt}],
    temperature=0
)

json_text = response.choices[0].message.content

# Save raw JSON response
Path(OUTPUT_FILE).write_text(json_text, encoding="utf-8")

print(f"Saved output to {OUTPUT_FILE}")

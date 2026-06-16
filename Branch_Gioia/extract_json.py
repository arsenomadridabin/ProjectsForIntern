from pathlib import Path
import json
import os
from openai import OpenAI

INPUT_FILE = "paper1.md"
OUTPUT_FILE = "paper1_parameters.json"

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

text = Path(INPUT_FILE).read_text(encoding="utf-8", errors="ignore")

prompt = """
You are extracting a table from a scientific paper.

Extract EVERY row/species from the thermodynamic parameter table.

Return ONLY valid JSON in this exact structure:
{
  "species": [
    {
      "phase": "",
      "species_name": "",
      "formula": "",
      "parameters": {
        "V0": null,
        "K0": null,
        "K0_prime": null,
        "theta0": null,
        "gamma0": null,
        "q0": null,
        "G0": null,
        "G0_prime": null,
        "etaS0": null
      }
    }
  ]
}

Rules:
- Do not stop after one row.
- Extract all rows from the table.
- If a value has uncertainty like 128 (2), keep it as the string "128 (2)".
- If a value is missing, use null.
- Do not include explanations.
"""

full_prompt = prompt + "\n\nPaper text:\n" + text

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": full_prompt}],
    temperature=0,
)

output_text = response.choices[0].message.content.strip()

if output_text.startswith("```"):
    output_text = output_text.replace("```json", "").replace("```", "").strip()

print(output_text)

data = json.loads(output_text)

Path(OUTPUT_FILE).write_text(
    json.dumps(data, indent=2),
    encoding="utf-8",
)

print(f"Saved extracted parameters to {OUTPUT_FILE}")

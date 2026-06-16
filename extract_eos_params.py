"""
extract_eos_params.py
=====================
Extracts the nine ambient-condition equation-of-state parameters
(V0, K0, K0', theta0, gamma0, q0, G0, G0', etaS0) for mantle mineral
species from Marker-converted Markdown files of mineralogy / geophysics
papers, using the DeepSeek API (OpenAI-compatible chat completions endpoint).

Pipeline (adapted from Paudel et al. 2026 polymer database paper):
  1. Load Markdown
  2. Strip irrelevant sections (references, acknowledgements, appendices
     that contain only citations — but KEEP appendices with tables)
  3. Identify sections likely to contain EOS parameter data
  4. Schema-guided LLM extraction → structured JSON per species
  5. Validate and write output

Usage
-----
Single file:
    python extract_eos_params.py --input paper.md --output results.json

Batch (folder of .md files):
    python extract_eos_params.py --input ./markdown_papers/ --output ./results/

Requirements
------------
    pip install openai tiktoken

Environment variable:
    DS_API_KEY=sk-...
"""

import os
import re
import json
import argparse
import logging
from pathlib import Path
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("Run: pip install openai")

try:
    import tiktoken
except ImportError:
    raise ImportError("Run: pip install tiktoken")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MAX_CONTEXT_TOKENS = 55_000    # DeepSeek-chat context is 64k; leave headroom for prompt+response
ENCODING_NAME = "cl100k_base"  # close approximation; DeepSeek has no public tiktoken encoding

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

PARAMETER_SCHEMA = {
    "species": "string — mineral species name as given in the paper (e.g. 'Forsterite', 'Mg-perovskite')",
    "phase":   "string — phase or mineral group (e.g. 'Olivine', 'Perovskite', 'Garnet')",
    "formula": "string — chemical formula (e.g. 'Mg2SiO4')",
    "V0":      "float  — molar volume at ambient conditions (cm³/mol)",
    "K0":      "float  — isothermal bulk modulus at ambient conditions (GPa)",
    "K0_prime":"float  — pressure derivative of K0 (dimensionless)",
    "theta0":  "float  — Debye temperature at ambient conditions (K)",
    "gamma0":  "float  — Grüneisen parameter at ambient conditions (dimensionless)",
    "q0":      "float  — logarithmic volume derivative of gamma (dimensionless)",
    "G0":      "float  — shear modulus at ambient conditions (GPa)",
    "G0_prime":"float  — pressure derivative of G0 (dimensionless)",
    "etaS0":   "float  — shear strain derivative of the Grüneisen parameter (dimensionless)",
    "uncertainty_V0":      "float or null — reported uncertainty on V0",
    "uncertainty_K0":      "float or null — reported uncertainty on K0",
    "uncertainty_K0_prime":"float or null — reported uncertainty on K0'",
    "uncertainty_theta0":  "float or null — reported uncertainty on theta0",
    "uncertainty_gamma0":  "float or null — reported uncertainty on gamma0",
    "uncertainty_q0":      "float or null — reported uncertainty on q0",
    "uncertainty_G0":      "float or null — reported uncertainty on G0",
    "uncertainty_G0_prime":"float or null — reported uncertainty on G0'",
    "uncertainty_etaS0":   "float or null — reported uncertainty on etaS0",
    "conditions":  "string — brief note on P-T conditions (should be ambient: P≈0 GPa, T≈298 K)",
    "source_table":"string or null — table number/label where values were found, if identifiable",
    "notes":       "string or null — any caveats e.g. 'estimated from systematics', 'from first principles'",
}

SCHEMA_JSON = json.dumps(PARAMETER_SCHEMA, indent=2)

# ---------------------------------------------------------------------------
# Sections to REMOVE before sending to LLM (noise reduction)
# These sections cannot contain EOS parameter tables.
# ---------------------------------------------------------------------------

STRIP_PATTERNS = [
    # References / bibliography sections
    r"(?im)^#{1,3}\s*(references?|bibliography)\s*\n.*?(?=\n#{1,3}\s|\Z)",
    # Acknowledgements
    r"(?im)^#{1,3}\s*(acknowledgements?|acknowledgments?|funding)\s*\n.*?(?=\n#{1,3}\s|\Z)",
    # Competing interests / author contributions
    r"(?im)^#{1,3}\s*(competing interests?|author contributions?|conflict of interest)\s*\n.*?(?=\n#{1,3}\s|\Z)",
    # Plain reference lists: lines starting with [N] Author et al.
    r"(?m)^\[\d+\].*\n",
    # DOI / URL lines that are just citations
    r"(?m)^https?://doi\.org/\S+\s*\n",
]

# Sections KNOWN to contain EOS data — used to prioritise chunks
PRIORITY_KEYWORDS = [
    "equation of state", "eos", "bulk modulus", "shear modulus",
    "grüneisen", "gruneisen", "debye", "molar volume", "v0", "k0",
    "theta_0", "gamma_0", "eta_s", "table a", "appendix", "parameter",
    "ambient", "ambient condition", "zero pressure",
]

# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding(ENCODING_NAME)
    return len(enc.encode(text))


def strip_noise(text: str) -> str:
    """Remove sections that definitely do not contain EOS parameters."""
    for pattern in STRIP_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.DOTALL)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def score_chunk(chunk: str) -> int:
    """Return a priority score for a text chunk based on keyword density."""
    lower = chunk.lower()
    return sum(lower.count(kw) for kw in PRIORITY_KEYWORDS)


def split_into_chunks(text: str, max_tokens: int = MAX_CONTEXT_TOKENS) -> list[str]:
    """
    Split text into chunks that fit within max_tokens.
    Tries to split on section boundaries (## headings) first.
    If the entire document fits, returns it as a single chunk.
    """
    if count_tokens(text) <= max_tokens:
        return [text]

    # Split on markdown headings
    sections = re.split(r"(?m)^(#{1,3} )", text)
    chunks, current = [], ""
    for part in sections:
        candidate = current + part
        if count_tokens(candidate) > max_tokens:
            if current:
                chunks.append(current)
            current = part
        else:
            current = candidate
    if current:
        chunks.append(current)

    # Sort chunks: highest-priority first so the most data-rich content
    # is always within the first API call
    chunks.sort(key=score_chunk, reverse=True)
    return chunks


# ---------------------------------------------------------------------------
# System and user prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert geophysicist and data extraction specialist.
Your task is to extract equation-of-state (EOS) parameters for mantle mineral species
from scientific paper text.

TARGET PARAMETERS (nine, following Stixrude & Lithgow-Bertelloni notation):
  V0       — molar volume at ambient conditions (cm³/mol)
  K0       — isothermal bulk modulus (GPa)
  K0'      — dK/dP pressure derivative (dimensionless)
  theta0   — Debye temperature (K)
  gamma0   — Grüneisen parameter (dimensionless)
  q0       — volume logarithmic derivative of gamma (dimensionless)
  G0       — shear modulus (GPa)
  G0'      — dG/dP pressure derivative (dimensionless)
  etaS0    — shear strain derivative of gamma (dimensionless)

CRITICAL RULES:
1. Extract ONLY ambient-condition values (P ≈ 0 GPa, T ≈ 298 K).
   If a paper reports values at multiple pressures, take only the zero-pressure entry.
2. Each mineral species gets its own JSON object.
   Different end-members of the same phase (e.g. Mg-forsterite vs Fe-fayalite) are separate entries.
3. If a parameter is not reported for a species, set it to null — never guess or interpolate.
4. Record uncertainties exactly as printed (e.g. parenthetical notation like 128(2) means value=128, uncertainty=2).
5. Note when values are flagged as estimated from systematics or first-principles rather than experiment.
6. Do NOT extract experimental data measured at high P or high T — only ambient reference values.
7. Parameters often appear in large summary tables (e.g. "Table A1", "Table 1") — prioritise these.
8. Return ONLY valid JSON. No markdown fences, no preamble, no explanation.

OUTPUT FORMAT — a JSON array, one object per species:
[
  {
    "species": "Forsterite",
    "phase": "Olivine",
    "formula": "Mg2SiO4",
    "V0": 43.60,
    "K0": 128.0,
    "K0_prime": 4.2,
    "theta0": 809.0,
    "gamma0": 0.99,
    "q0": 2.1,
    "G0": 82.0,
    "G0_prime": 1.4,
    "etaS0": 2.4,
    "uncertainty_V0": null,
    "uncertainty_K0": 2.0,
    "uncertainty_K0_prime": 0.2,
    "uncertainty_theta0": 1.0,
    "uncertainty_gamma0": 0.03,
    "uncertainty_q0": 0.2,
    "uncertainty_G0": 2.0,
    "uncertainty_G0_prime": 0.1,
    "uncertainty_etaS0": 0.1,
    "conditions": "ambient (P=0, T=298 K)",
    "source_table": "Table A1",
    "notes": null
  }
]

If no EOS parameters are found in the provided text, return an empty array: []
"""


def build_user_prompt(chunk: str, paper_filename: str) -> str:
    return f"""Extract all ambient-condition EOS parameters from the following text.
Source file: {paper_filename}

=== PAPER TEXT ===
{chunk}
=== END TEXT ===

Return a JSON array of species objects as described. Return [] if no parameters found."""


# ---------------------------------------------------------------------------
# OpenAI extraction
# ---------------------------------------------------------------------------

def call_llm(client: OpenAI, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.0,       # deterministic
        max_tokens=4096,
        # Note: DeepSeek's API does not support response_format={"type": "json_object"}
        # the way OpenAI's does. JSON-only output is enforced via the system prompt
        # instead, and parse_llm_response() below strips markdown fences defensively.
    )
    return response.choices[0].message.content


def parse_llm_response(raw: str) -> list[dict]:
    """
    Parse the LLM JSON response.
    Unlike OpenAI's json_object mode, DeepSeek may occasionally wrap its
    output in markdown code fences (```json ... ```) despite instructions
    not to. Strip those defensively before parsing.
    """
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    # If the model wrapped the array: {"species": [...]} or {"results": [...]}
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
        return []
    if isinstance(data, list):
        return data
    return []


def merge_species(existing: list[dict], new_entries: list[dict]) -> list[dict]:
    """
    Merge new_entries into existing list, deduplicating by (species, formula).
    For duplicate species, fill in null fields from the new entry.
    """
    index = {(e["species"], e.get("formula", "")): i for i, e in enumerate(existing)}
    for entry in new_entries:
        key = (entry["species"], entry.get("formula", ""))
        if key in index:
            # Fill nulls in existing entry with values from new entry
            idx = index[key]
            for k, v in entry.items():
                if existing[idx].get(k) is None and v is not None:
                    existing[idx][k] = v
        else:
            existing.append(entry)
            index[key] = len(existing) - 1
    return existing


# ---------------------------------------------------------------------------
# Per-file extraction pipeline
# ---------------------------------------------------------------------------

def extract_from_markdown(
    md_path: Path,
    client: OpenAI,
    output_dir: Optional[Path] = None,
) -> list[dict]:
    """
    Full pipeline for a single Markdown file.
    Returns list of extracted species dicts.
    """
    log.info(f"Processing: {md_path.name}")

    # 1. Load
    text = md_path.read_text(encoding="utf-8", errors="replace")
    log.info(f"  Loaded {len(text):,} chars / {count_tokens(text):,} tokens")

    # 2. Strip noise
    text = strip_noise(text)
    log.info(f"  After stripping noise: {count_tokens(text):,} tokens")

    # 3. Chunk (most papers fit in one call; large review papers may need 2-3)
    chunks = split_into_chunks(text)
    log.info(f"  Split into {len(chunks)} chunk(s)")

    # 4. Extract from each chunk, merge results
    all_species: list[dict] = []
    for i, chunk in enumerate(chunks):
        log.info(f"  Chunk {i+1}/{len(chunks)} — {count_tokens(chunk):,} tokens")
        user_prompt = build_user_prompt(chunk, md_path.name)
        try:
            raw = call_llm(client, SYSTEM_PROMPT, user_prompt)
            entries = parse_llm_response(raw)
            log.info(f"    → {len(entries)} species extracted from this chunk")
            all_species = merge_species(all_species, entries)
        except Exception as e:
            log.error(f"    API error on chunk {i+1}: {e}")

    log.info(f"  Total unique species: {len(all_species)}")

    # 5. Attach provenance
    for s in all_species:
        s["source_file"] = md_path.name

    # 6. Write per-file output
    if output_dir:
        out_path = output_dir / (md_path.stem + "_eos.json")
        out_path.write_text(json.dumps(all_species, indent=2), encoding="utf-8")
        log.info(f"  Saved → {out_path}")

    return all_species


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract mantle mineral EOS parameters from Markdown papers using DeepSeek."
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to a single .md file OR a directory of .md files."
    )
    parser.add_argument(
        "--output", "-o", required=True,
        help="Output .json file (single) or output directory (batch)."
    )
    parser.add_argument(
        "--api-key", default=None,
        help="DeepSeek API key. Falls back to DS_API_KEY env var."
    )
    parser.add_argument(
        "--model", default=MODEL,
        help=f"DeepSeek model to use (default: {MODEL})."
    )
    args = parser.parse_args()

    # API key
    api_key = args.api_key or os.environ.get("DS_API_KEY")
    if not api_key:
        raise ValueError(
            "No DeepSeek API key found. Set DS_API_KEY or pass --api-key."
        )
    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    input_path = Path(args.input)
    output_path = Path(args.output)

    # ---- Single file -------------------------------------------------------
    if input_path.is_file():
        if not input_path.suffix == ".md":
            raise ValueError("Input file must be a .md file.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        species = extract_from_markdown(input_path, client, output_dir=None)
        output_path.write_text(json.dumps(species, indent=2), encoding="utf-8")
        log.info(f"Done. {len(species)} species written to {output_path}")

    # ---- Batch (directory) -------------------------------------------------
    elif input_path.is_dir():
        md_files = sorted(input_path.glob("*.md"))
        if not md_files:
            raise FileNotFoundError(f"No .md files found in {input_path}")
        output_path.mkdir(parents=True, exist_ok=True)

        all_results: list[dict] = []
        failed: list[str] = []

        for md_file in md_files:
            try:
                species = extract_from_markdown(md_file, client, output_dir=output_path)
                all_results.extend(species)
            except Exception as e:
                log.error(f"Failed on {md_file.name}: {e}")
                failed.append(md_file.name)

        # Write consolidated output
        combined_path = output_path / "_all_species.json"
        combined_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
        log.info(
            f"\nBatch complete. {len(all_results)} total species across "
            f"{len(md_files) - len(failed)} files."
        )
        log.info(f"Combined output → {combined_path}")
        if failed:
            log.warning(f"Failed files: {failed}")

    else:
        raise FileNotFoundError(f"Input path not found: {input_path}")


if __name__ == "__main__":
    main()

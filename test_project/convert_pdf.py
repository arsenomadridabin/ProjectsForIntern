import pymupdf4llm

pdf_path = "2005-SLB.pdf"
output_path = "output.md"

# Convert PDF to Markdown
markdown_text = pymupdf4llm.to_markdown(pdf_path)

# Save Markdown to file
with open(output_path, "w", encoding="utf-8") as f:
    f.write(markdown_text)

print(f"Markdown saved to {output_path}")

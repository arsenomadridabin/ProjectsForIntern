import sys
import os
import pymupdf4llm

def convert_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"[ERROR] File not found: {pdf_path}")
        return
    print(f"Converting: {pdf_path}")
    md_text = pymupdf4llm.to_markdown(pdf_path, show_progress=False)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(os.getcwd(), base_name + ".md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"Saved: {out_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_markdown.py <file.pdf or folder/>")
        sys.exit(1)
    target = sys.argv[1]
    if os.path.isdir(target):
        pdfs = [os.path.join(target, f) for f in os.listdir(target) if f.lower().endswith(".pdf")]
        print(f"Found {len(pdfs)} PDF(s)\n")
        for pdf in sorted(pdfs):
            convert_pdf(pdf)
    else:
        convert_pdf(target)
    print("\nDone.")

if __name__ == "__main__":
    main()

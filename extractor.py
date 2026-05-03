# ============================================================
#   extractor.py
#   Job : Extract clean text from a PDF resume using pdfplumber
#   Used by : app.py (passes the extracted text to screener.py)
# ============================================================

import pdfplumber
import re


def extract_text_from_pdf(pdf_file) -> str:
    """
    Accepts a file-like object (from Streamlit uploader)
    Returns clean extracted text as a single string.
    """
    full_text = []

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)

    raw = "\n".join(full_text)
    return clean_text(raw)


def clean_text(text: str) -> str:
    """
    Cleans up common PDF extraction artifacts:
    - Removes extra whitespace / blank lines
    - Removes non-printable characters
    """
    # Remove non-printable characters
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    # Collapse more than 2 newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_sections(text: str) -> dict:
    """
    Attempts to split resume text into common sections.
    Returns a dict like:
    { "skills": "...", "experience": "...", "education": "..." }
    Useful for ATS keyword matching by section.
    """
    sections = {}
    section_headers = {
        "skills":     r"(skills|technical skills|core competencies)",
        "experience": r"(experience|work experience|internship|employment)",
        "education":  r"(education|academic|qualification)",
        "projects":   r"(projects|personal projects|academic projects)",
        "certifications": r"(certifications|certificates|courses)",
    }

    text_lower = text.lower()

    for section, pattern in section_headers.items():
        match = re.search(pattern, text_lower)
        if match:
            start = match.start()
            # Find the next section header after this one
            next_starts = []
            for other_section, other_pattern in section_headers.items():
                if other_section == section:
                    continue
                other_match = re.search(other_pattern, text_lower[start + 1:])
                if other_match:
                    next_starts.append(start + 1 + other_match.start())

            end = min(next_starts) if next_starts else len(text)
            sections[section] = text[start:end].strip()

    return sections


# ─── Quick test (run this file directly to test) ────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "rb") as f:
            text = extract_text_from_pdf(f)
            print("── Extracted Text ──")
            print(text[:1000])
            print("\n── Sections Found ──")
            sections = extract_sections(text)
            for k, v in sections.items():
                print(f"\n[{k.upper()}]\n{v[:200]}")
    else:
        print("Usage: python extractor.py resume.pdf")

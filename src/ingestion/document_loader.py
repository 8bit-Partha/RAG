"""
Document loaders for SecuRAG.

Every loader in this module outputs a list of dicts in a common shape:

    {
        "text": str,            # raw section/page text
        "source": str,          # filename or source identifier
        "section": str,         # section/page label, used later for citations
        "doc_type": str,        # "policy" | "pdf" | "structured"
    }

Keeping this shape consistent is what lets downstream chunking and
embedding code stay agnostic to where a document actually came from.
"""

import json
import re
from pathlib import Path
from typing import List, Dict


def load_markdown(filepath: str) -> List[Dict]:
    """
    Parse a markdown file into section-level records, splitting on '##'
    headers. This preserves the document's own structure instead of
    chunking blindly, which matters a lot for policy documents where a
    section heading (e.g. "Section 3: Authentication Requirements") carries
    meaning that should stay attached to its body text.
    """
    path = Path(filepath)
    raw = path.read_text(encoding="utf-8")

    # Split on level-2 headers ("## Section ...") while keeping the header
    # text attached to the section that follows it.
    parts = re.split(r"(?=^## )", raw, flags=re.MULTILINE)

    records = []
    for part in parts:
        part = part.strip()
        if not part or part.startswith("# "):
            # Skip the top-level title-only fragment (before the first "##")
            if part and not part.startswith("## "):
                continue
        header_match = re.match(r"^##\s*(.+)$", part, flags=re.MULTILINE)
        section = header_match.group(1).strip() if header_match else "Introduction"

        if part.strip():
            records.append({
                "text": part.strip(),
                "source": path.name,
                "section": section,
                "doc_type": "policy",
            })
    return records


def load_pdf(filepath: str) -> List[Dict]:
    """
    Extract text from a PDF, page by page.

    Real-world PDFs (NIST SP 800-series, OWASP guides, etc.) often need
    more careful handling than this -- multi-column layouts, tables, and
    footnotes can get jumbled by naive extraction. pypdf is a reasonable
    starting point; if extraction quality is poor on your real documents,
    swap this out for the `unstructured` library, which handles layout
    detection much better at the cost of extra dependencies.
    """
    from pypdf import PdfReader

    path = Path(filepath)
    reader = PdfReader(str(path))

    records = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            records.append({
                "text": text,
                "source": path.name,
                "section": f"page {i + 1}",
                "doc_type": "pdf",
            })
    return records


def load_structured_json(filepath: str, text_fields=("tactic", "description")) -> List[Dict]:
    """
    Load structured data (e.g. threat tactic definitions, control catalogs)
    that already comes as clean JSON records rather than free text.

    Structured sources like this are a good complement to PDFs/policies:
    they don't need chunking (each record IS a chunk), and they let the
    retrieval system return precise, ID-addressable facts (e.g. "TA0006")
    instead of only fuzzy passages.
    """
    path = Path(filepath)
    data = json.loads(path.read_text(encoding="utf-8"))

    records = []
    for item in data:
        text = " - ".join(str(item[f]) for f in text_fields if f in item)
        records.append({
            "text": text,
            "source": path.name,
            "section": item.get("id", item.get("tactic", "unknown")),
            "doc_type": "structured",
        })
    return records


# Structured JSON sources use different field names depending on the
# taxonomy they represent. Rather than forcing every JSON source into one
# schema, we map filename -> which fields to concatenate into chunk text.
# Add an entry here whenever you drop a new structured source into
# data/raw/ with its own field names.
STRUCTURED_FIELD_MAP = {
    "threat_tactics.json": ("tactic", "description"),
    "nist_800_53_families.json": ("family", "description"),
    "owasp_top10_2021.json": ("category", "description"),
}
DEFAULT_STRUCTURED_FIELDS = ("tactic", "description")


def load_directory(raw_dir: str) -> List[Dict]:
    """
    Convenience entry point: walk a directory and dispatch each file to
    the right loader based on extension.
    """
    raw_path = Path(raw_dir)
    all_records = []

    for filepath in sorted(raw_path.glob("*")):
        if filepath.suffix == ".md":
            all_records.extend(load_markdown(str(filepath)))
        elif filepath.suffix == ".pdf":
            all_records.extend(load_pdf(str(filepath)))
        elif filepath.suffix == ".json":
            fields = STRUCTURED_FIELD_MAP.get(filepath.name, DEFAULT_STRUCTURED_FIELDS)
            all_records.extend(load_structured_json(str(filepath), text_fields=fields))
        else:
            print(f"Skipping unsupported file type: {filepath.name}")

    return all_records


if __name__ == "__main__":
    records = load_directory("data/raw")
    print(f"Loaded {len(records)} records from data/raw")
    for r in records[:3]:
        print(f"  [{r['doc_type']}] {r['source']} / {r['section']} -> {r['text'][:80]}...")

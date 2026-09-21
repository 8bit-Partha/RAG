import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.document_loader import load_markdown, load_structured_json, load_directory


def test_load_markdown_splits_on_sections(tmp_path):
    md_file = tmp_path / "sample.md"
    md_file.write_text(
        "# Title\n\n## Section 1: Alpha\nAlpha body text.\n\n## Section 2: Beta\nBeta body text.\n"
    )

    records = load_markdown(str(md_file))

    assert len(records) == 2
    assert records[0]["section"] == "Section 1: Alpha"
    assert "Alpha body text" in records[0]["text"]
    assert records[1]["section"] == "Section 2: Beta"
    assert all(r["doc_type"] == "policy" for r in records)


def test_load_markdown_preserves_source_filename(tmp_path):
    md_file = tmp_path / "policy_x.md"
    md_file.write_text("## Only Section\nSome text.\n")

    records = load_markdown(str(md_file))

    assert records[0]["source"] == "policy_x.md"


def test_load_structured_json_uses_id_as_section(tmp_path):
    json_file = tmp_path / "data.json"
    json_file.write_text(
        '[{"id": "X01", "tactic": "Example Tactic", "description": "An example."}]'
    )

    records = load_structured_json(str(json_file), text_fields=("tactic", "description"))

    assert len(records) == 1
    assert records[0]["section"] == "X01"
    assert records[0]["doc_type"] == "structured"
    assert "Example Tactic" in records[0]["text"]
    assert "An example." in records[0]["text"]


def test_load_directory_covers_all_sample_sources():
    """Smoke test against the actual sample corpus shipped in the repo."""
    records = load_directory("data/raw")
    doc_types = {r["doc_type"] for r in records}

    assert "policy" in doc_types
    assert "structured" in doc_types
    assert len(records) > 0

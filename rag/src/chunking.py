import sys
import subprocess

import pdfplumber
import re
from pypdf import PdfReader
import json
from typing import List, Dict, Any

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption

pdf_path = "../../data/knowledge_base/raw/DLprojectExample.pdf"

PDF_PATH=Path(pdf_path)
OUTPUT_PATH=Path("../../data/knowledge_base/processed/output.json")

MAX_CHUNK_CHARS = 3500

# Matches numbered headings: "1. Introduction", "8.1 Condition-Based…", "13.2 …"
HEADING_RE = re.compile(
    r"^(#{1,3}\s*)?(?P<num>\d+(?:\.\d+)*)\.\s+(?P<title>[A-Z][^.\n]{5,80})$",
    re.MULTILINE
)




def extract_with_docling(pdf_path: Path) -> str:
    """
    Run Docling and convert the document into a clean Markdown-like string
    that still preserves tables and section structure.
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False          # this PDF is already text
    pipeline_options.do_table_structure = True

    # Wrap the pipeline options in PdfFormatOption for Docling v2
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    result = converter.convert(pdf_path)
    doc = result.document

    # Export to Markdown
    markdown = doc.export_to_markdown()

    # Light cleaning
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


"""
Even with Docling’s excellent Markdown, we still re-group by the
document’s own numbered sections. This is the key step that turns
fine-grained parsing into RAG-ready chunks.
"""

def split_into_sections(text: str) -> List[Dict[str, Any]]:
    matches = list(HEADING_RE.finditer(text))

    if not matches:
        print("WARNING: No headings matched – falling back to whole document")
        return [{"section_id": "0", "title": "Full Document", "content": text}]

    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append({
            "section_id": m.group("num"),
            "title": m.group("title").strip(),
            "content": text[start:end].strip()
        })
    return sections


def recursive_split(text: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    if len(text) <= max_chars:
        return [text]

    separators = ["\n\n", "\n", ". ", " "]
    for sep in separators:
        if sep not in text:
            continue

        parts = text.split(sep)
        chunks, current = [], ""

        for part in parts:
            candidate = current + (sep if current else "") + part
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())
                current = part
        if current:
            chunks.append(current.strip())

        # Recurse on any still-too-big pieces
        final = []
        for c in chunks:
            final.extend(recursive_split(c, max_chars) if len(c) > max_chars else [c])
        return final

    # Absolute fallback
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]



def finalize_chunks(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chunks = []
    for sec in sections:
        content = sec["content"]

        if len(content) <= MAX_CHUNK_CHARS:
            chunks.append({
                "chunk_id": f"sec-{sec['section_id']}",
                "section_id": sec["section_id"],
                "title": sec["title"],
                "text": content,
                "char_count": len(content),
                "approx_tokens": len(content) // 4
            })
        else:
            for idx, sub in enumerate(recursive_split(content)):
                chunks.append({
                    "chunk_id": f"sec-{sec['section_id']}-{idx + 1}",
                    "section_id": sec["section_id"],
                    "title": f"{sec['title']} (part {idx + 1})",
                    "text": sub,
                    "char_count": len(sub),
                    "approx_tokens": len(sub) // 4
                })
    return chunks



print("1. Running Docling …")
full_text = extract_with_docling(PDF_PATH)
print(f"   → {len(full_text):,} characters of Markdown extracted")

print("2. Splitting into hierarchical sections …")
sections = split_into_sections(full_text)
print(f"   → {len(sections)} sections found")

print("3. Creating final RAG chunks …")
chunks = finalize_chunks(sections)
print(f"   → {len(chunks)} chunks created")

sizes = [c["approx_tokens"] for c in chunks]
print(f"\nApprox token stats: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)//len(sizes)}")

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(chunks, f, indent=2, ensure_ascii=False)

print(f"\nSaved → {OUTPUT_PATH}")




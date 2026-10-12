"""
rag/documents.py
----------------
Document loading and chunking for the RAG knowledge base.

Strategy: Fixed-size chunking with overlap.
  - Chunk size : 500 characters
  - Overlap    : 100 characters
  - Splitter   : RecursiveCharacterTextSplitter (paragraph → sentence → word)

Justification:
  Policy documents are short, structured paragraphs. Each paragraph
  typically contains one complete rule. Fixed-size chunking with a
  100-character overlap prevents a rule from being split across two
  chunks while keeping each chunk focused on a single policy point.
"""

from pathlib import Path
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter


# ============================================================
# CONFIGURATION
# ============================================================

KNOWLEDGE_BASE_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "knowledge_base"
)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Separators tried in order: paragraph → sentence → word → character.
# This preserves logical rule boundaries when possible.
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


# ============================================================
# DOCUMENT CHUNK
# ============================================================

class DocumentChunk:
    """
    A single chunk of text from a policy document.

    Attributes
    ----------
    text     : The chunk text.
    source   : The filename the chunk came from (e.g. 'return_policy.txt').
    doc_type : Human-readable document type label.
    chunk_id : Sequential index within the source document.
    """

    def __init__(
        self,
        text: str,
        source: str,
        doc_type: str,
        chunk_id: int,
    ):
        self.text = text
        self.source = source
        self.doc_type = doc_type
        self.chunk_id = chunk_id

    def __repr__(self) -> str:
        return (
            f"DocumentChunk(source={self.source!r}, "
            f"chunk_id={self.chunk_id}, "
            f"chars={len(self.text)})"
        )


# ============================================================
# DOCUMENT TYPE LABELS
# ============================================================

DOC_TYPE_MAP: dict[str, str] = {
    "return_policy.txt":   "Return Policy",
    "refund_policy.txt":   "Refund Policy",
    "warranty_policy.txt": "Warranty Policy",
}


# ============================================================
# LOADER
# ============================================================

def load_documents(
    knowledge_base_dir: Optional[Path] = None,
) -> list[DocumentChunk]:
    """
    Load all .txt policy files from the knowledge base directory
    and split them into chunks.

    Parameters
    ----------
    knowledge_base_dir : Path to the directory containing policy .txt files.
                         Defaults to data/knowledge_base/.

    Returns
    -------
    List of DocumentChunk objects ready for embedding.
    """

    kb_dir = knowledge_base_dir or KNOWLEDGE_BASE_DIR

    if not kb_dir.exists():
        raise FileNotFoundError(
            f"Knowledge base directory not found: {kb_dir}"
        )

    txt_files = sorted(kb_dir.glob("*.txt"))

    if not txt_files:
        raise ValueError(
            f"No .txt files found in knowledge base: {kb_dir}"
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
        length_function=len,
    )

    all_chunks: list[DocumentChunk] = []

    for txt_file in txt_files:

        raw_text = txt_file.read_text(encoding="utf-8")

        doc_type = DOC_TYPE_MAP.get(txt_file.name, txt_file.stem)

        raw_chunks = splitter.split_text(raw_text)

        for idx, chunk_text in enumerate(raw_chunks):

            chunk_text = chunk_text.strip()

            if not chunk_text:
                continue

            all_chunks.append(
                DocumentChunk(
                    text=chunk_text,
                    source=txt_file.name,
                    doc_type=doc_type,
                    chunk_id=idx,
                )
            )

        print(
            f"[Documents] Loaded {len(raw_chunks)} chunks "
            f"from {txt_file.name}"
        )

    print(
        f"[Documents] Total chunks loaded: {len(all_chunks)}"
    )

    return all_chunks


# ============================================================
# ALTERNATIVE CHUNKING — for evaluation comparison
# ============================================================

def load_documents_large_chunks(
    knowledge_base_dir: Optional[Path] = None,
) -> list[DocumentChunk]:
    """
    Alternative chunking strategy: larger chunks (1000 chars, 200 overlap).

    Used to compare retrieval quality against the default 500/100 strategy.
    Larger chunks capture more context but may introduce noise in retrieval.
    """

    kb_dir = knowledge_base_dir or KNOWLEDGE_BASE_DIR

    if not kb_dir.exists():
        raise FileNotFoundError(
            f"Knowledge base directory not found: {kb_dir}"
        )

    txt_files = sorted(kb_dir.glob("*.txt"))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=SEPARATORS,
        length_function=len,
    )

    all_chunks: list[DocumentChunk] = []

    for txt_file in txt_files:

        raw_text = txt_file.read_text(encoding="utf-8")
        doc_type = DOC_TYPE_MAP.get(txt_file.name, txt_file.stem)
        raw_chunks = splitter.split_text(raw_text)

        for idx, chunk_text in enumerate(raw_chunks):

            chunk_text = chunk_text.strip()

            if not chunk_text:
                continue

            all_chunks.append(
                DocumentChunk(
                    text=chunk_text,
                    source=txt_file.name,
                    doc_type=doc_type,
                    chunk_id=idx,
                )
            )

    print(
        f"[Documents-Large] Total chunks: {len(all_chunks)}"
    )

    return all_chunks

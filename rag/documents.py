from pathlib import Path
from pypdf import PdfReader

PROJECT_DIR = Path(__file__).resolve().parent.parent
POLICY_DIR = PROJECT_DIR / "data" / "policies"


def split_text(text, chunk_size=900, overlap=150):
    """Découpe un texte en passages avec un chevauchement."""
    text = " ".join(text.split())

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def load_documents(directory=POLICY_DIR):
    """Charge les PDF, TXT et MD du dossier des politiques."""
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(
            f"Le dossier des politiques est introuvable : {directory}"
        )

    records = []

    supported_extensions = {".pdf", ".txt", ".md"}

    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in supported_extensions:
            continue

        pages = []

        if path.suffix.lower() == ".pdf":
            reader = PdfReader(str(path))

            for page_number, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""

                if text.strip():
                    pages.append((page_number, text))

        else:
            text = path.read_text(encoding="utf-8-sig")
            pages.append((None, text))

        for page_number, text in pages:
            chunks = split_text(text)

            for chunk_number, chunk in enumerate(chunks, start=1):
                page_label = page_number or 0

                records.append({
                    "id": (
                        f"{path.name}:page{page_label}:"
                        f"chunk{chunk_number}"
                    ),
                    "text": chunk,
                    "metadata": {
                        "source": path.name,
                        "page": page_label,
                    },
                })

    if not records:
        raise ValueError(
            f"Aucun texte exploitable trouvé dans {directory}. "
            "Ajoute des fichiers PDF, TXT ou MD contenant du texte."
        )

    return records
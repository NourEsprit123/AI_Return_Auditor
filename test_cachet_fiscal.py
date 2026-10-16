"""
Validation de cachet fiscal sur devis.

Fonctionnalité isolée — SAV e-commerce.
Branche : feature/detection-cachet-fiscal

Stack : google.genai (Gemini) + PIL + PyMuPDF + pydantic + streamlit
Aucun import depuis les autres modules du projet.
"""

import io
import json
import os
import time
from pathlib import Path
from typing import Optional

import pymupdf as fitz              # PDF → PIL Image (page 0), PyMuPDF ≥ 1.24
from dotenv import load_dotenv
from google import genai
from PIL import Image
from pydantic import BaseModel, Field


# ============================================================
# ENVIRONNEMENT
# ============================================================

load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")

MODEL_NAME: str = os.getenv(
    "GEMINI_VISION_MODEL",
    "gemini-2.0-flash",
)

# Seuil de confiance au-delà duquel le cachet est considéré présent.
# 0.75 : tolérant aux cachets partiellement lisibles ou légèrement flous.
CONFIDENCE_THRESHOLD: float = 0.75

# Nombre de tentatives en cas d'erreur temporaire (503 / 429)
MAX_RETRIES: int = 2

RETRY_DELAY_SECONDS: int = 3


# ============================================================
# PROMPT MÉTIER (inline — autonome, pas de fichier externe)
# ============================================================

STAMP_DETECTION_PROMPT = """
You are a Fiscal Audit Agent. You are analyzing a digital PDF invoice converted into an image.

Look closely at the bottom-right corner of the document:

- If you see a colored rectangular box containing the text "STATE TAX AUTHORITY - OFFICIAL FISCAL STAMP", you MUST detect this as a valid fiscal stamp and return that the stamp is PRESENT.

- If that specific coordinate area is blank, return that the stamp is ABSENT.

Additional context for ambiguous documents:
- The stamp box may also contain a reference number (e.g. "Ref. FISC-2026-XXXXXX") and a validation date.
- The box border color is typically dark blue.
- Do NOT confuse a printed header, logo, or watermark anywhere else on the page with the fiscal stamp.
- Only the bottom-right rectangular box qualifies as the official fiscal stamp for this audit system.

Respond ONLY with a valid JSON object (no markdown, no text before or after), following this exact schema:
{
  "stamp_detected": true | false,
  "confidence": <float between 0.0 and 1.0>,
  "visual_evidence": "<precise description of what you observe in the bottom-right area>",
  "uncertainty": "<any ambiguity or limitation of the analysis>"
}
"""


# ============================================================
# SCHÉMA DE RÉSULTAT
# ============================================================

class StampAnalysis(BaseModel):
    """Résultat structuré de l'analyse du cachet fiscal."""

    stamp_detected: bool = Field(
        description="True si un cachet fiscal officiel est détecté sur le devis."
    )

    confidence: float = Field(
        description="Niveau de confiance de la détection, entre 0.0 et 1.0.",
        ge=0.0,
        le=1.0,
    )

    visual_evidence: str = Field(
        description="Description de ce qui est observé visuellement dans l'image."
    )

    uncertainty: str = Field(
        description="Ambiguïté ou limite éventuelle de l'analyse."
    )


# ============================================================
# UTILITAIRES INTERNES
# ============================================================

def _is_temporary_error(error: Exception) -> bool:
    """Détecte les erreurs réseau temporaires pour déclencher un retry."""
    error_text = str(error).lower()
    temporary_indicators = [
        "503",
        "unavailable",
        "high demand",
        "temporarily",
        "overloaded",
        "resource exhausted",
        "429",
        "rate limit",
    ]
    return any(indicator in error_text for indicator in temporary_indicators)


def _parse_stamp_analysis(raw_text: str) -> StampAnalysis:
    """
    Parse la réponse texte du modèle en StampAnalysis.
    Nettoie les éventuels blocs markdown avant de parser le JSON.
    """
    text = raw_text.strip()

    # Nettoyer les blocs ```json ... ``` si le modèle en produit malgré la consigne
    if text.startswith("```"):
        lines = text.splitlines()
        # Supprimer la première et la dernière ligne si ce sont des délimiteurs
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    data = json.loads(text)
    return StampAnalysis(**data)


# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def validate_invoice_stamp(image: Image.Image) -> bool:
    """
    Détecte la présence d'un cachet fiscal sur un devis.

    Parameters
    ----------
    image : PIL.Image.Image
        Image de la page du devis, déjà convertie en mémoire
        (typiquement la page 0 d'un PDF via pdf_page_to_image()).

    Returns
    -------
    bool
        True  → cachet fiscal détecté, document VALIDE.
        False → cachet absent ou non reconnu, document INVALIDE.

    Raises
    ------
    ValueError
        Si la clé API Gemini n'est pas configurée.
    RuntimeError
        Si l'analyse échoue après tous les retries.
    """
    if not API_KEY:
        raise ValueError(
            "La variable d'environnement GEMINI_API_KEY n'est pas configurée."
        )

    client = genai.Client(api_key=API_KEY)

    last_error: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[STAMP_DETECTION_PROMPT, image],
            )

            raw_text = response.text
            result: StampAnalysis = _parse_stamp_analysis(raw_text)

            # Décision : cachet présent ET confiance suffisante
            return result.stamp_detected and result.confidence >= CONFIDENCE_THRESHOLD

        except Exception as exc:
            last_error = exc

            if _is_temporary_error(exc) and attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
                continue

            # Erreur non temporaire ou dernière tentative : on remonte
            raise RuntimeError(
                f"Analyse du cachet fiscal échouée (tentative {attempt}/{MAX_RETRIES}) : {exc}"
            ) from exc

    raise RuntimeError(
        f"Analyse du cachet fiscal échouée après {MAX_RETRIES} tentatives. "
        f"Dernière erreur : {last_error}"
    )


# ============================================================
# INTERFACE STREAMLIT AUTONOME
# ============================================================

if __name__ == "__main__":

    import streamlit as st

    st.set_page_config(
        page_title="Validation Cachet Fiscal",
        page_icon="🔍",
        layout="wide",
    )

    st.title("🔍 Validation Cachet Fiscal")
    st.caption("Outil de vérification de devis — SAV e-commerce")

    st.markdown(
        "Chargez un devis **PDF** pour détecter automatiquement la présence "
        "d'un **cachet fiscal officiel**. La première page est analysée."
    )

    st.divider()

    uploaded_file = st.file_uploader(
        "Charger un devis (PDF)",
        type=["pdf"],
        help="Format accepté : PDF numérique (page 0 analysée, DPI 150).",
    )

    if uploaded_file is not None:

        # ── PDF → PIL Image (page 0 en mémoire, sans fichier tmp) ────────
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()

        # Aperçu de la page convertie
        st.image(
            img,
            caption=f"Page 1 — {uploaded_file.name}",
            use_container_width=True,
        )

        st.divider()

        if st.button("🔎 Analyser le cachet fiscal", type="primary"):

            try:
                with st.spinner("Analyse en cours via Gemini Vision..."):
                    is_valid = validate_invoice_stamp(img)

                if is_valid:
                    st.success(
                        "Cachet fiscal détecté — Devis **VALIDE**",
                        icon="✅",
                    )
                    st.balloons()
                else:
                    st.error(
                        "Aucun cachet fiscal détecté — Devis **INVALIDE**",
                        icon="❌",
                    )

            except ValueError as e:
                st.error(f"Erreur de configuration : {e}")

            except RuntimeError as e:
                st.error(f"Erreur d'analyse : {e}")

    else:
        st.info(
            "Chargez un devis ci-dessus pour commencer l'analyse.",
            icon="⬆️",
        )

    st.divider()
    st.caption(
        f"Modèle : {MODEL_NAME} · "
        f"Seuil de confiance : {int(CONFIDENCE_THRESHOLD * 100)} %"
    )

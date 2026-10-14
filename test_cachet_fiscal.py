"""
Validation de cachet fiscal sur devis.

Fonctionnalité isolée — SAV e-commerce.
Branche : feature/detection-cachet-fiscal

Stack : google.genai (Gemini) + PIL + pydantic + streamlit
Aucun import depuis les autres modules du projet.
"""

import io
import json
import os
import time
from pathlib import Path
from typing import Optional

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
Tu es un expert en validation de documents fiscaux pour un service après-vente.

Analyse cette image de devis et détermine si un cachet fiscal officiel est présent.

Un cachet fiscal valide présente AU MOINS deux des caractéristiques suivantes :
- Forme : rond, ovale ou rectangulaire
- Couleur d'encre : bleue, rouge, noire ou violette
- Contenu visible : numéro de registre du commerce, numéro fiscal, adresse de l'entreprise, logo ou nom officiel
- Aspect physique : bords nets ou légèrement baveux (tampon encreur), éventuellement incliné

Ne confonds pas avec :
- Une signature manuscrite seule
- Un en-tête imprimé ou logo numérique
- Un filigrane ou une watermark

Réponds UNIQUEMENT avec un objet JSON valide (pas de markdown, pas de texte avant ou après), respectant ce schéma :
{
  "stamp_detected": true | false,
  "confidence": <float entre 0.0 et 1.0>,
  "visual_evidence": "<description précise de ce que tu observes dans l'image>",
  "uncertainty": "<ambiguïté ou limite éventuelle de l'analyse>"
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

def validate_invoice_stamp(image_path: str) -> bool:
    """
    Détecte la présence d'un cachet fiscal sur un devis.

    Parameters
    ----------
    image_path : str
        Chemin vers l'image du devis (JPG, JPEG ou PNG).

    Returns
    -------
    bool
        True  → cachet fiscal détecté, document VALIDE.
        False → cachet absent ou non reconnu, document INVALIDE.

    Raises
    ------
    ValueError
        Si la clé API Gemini n'est pas configurée.
    FileNotFoundError
        Si le fichier image est introuvable.
    RuntimeError
        Si l'analyse échoue après tous les retries.
    """
    if not API_KEY:
        raise ValueError(
            "La variable d'environnement GEMINI_API_KEY n'est pas configurée."
        )

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image introuvable : {image_path}")

    image = Image.open(path)

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
        layout="centered",
    )

    st.title("🔍 Validation Cachet Fiscal")
    st.caption("Outil de vérification de devis — SAV e-commerce")

    st.markdown(
        "Chargez un devis pour détecter automatiquement la présence "
        "d'un **cachet fiscal officiel**."
    )

    st.divider()

    uploaded_file = st.file_uploader(
        "Charger un devis",
        type=["jpg", "jpeg", "png"],
        help="Formats acceptés : JPG, JPEG, PNG",
    )

    if uploaded_file is not None:

        # Aperçu de l'image chargée
        image_preview = Image.open(uploaded_file)
        st.image(
            image_preview,
            caption=f"Devis chargé : {uploaded_file.name}",
            use_container_width=True,
        )

        st.divider()

        if st.button("🔎 Analyser le cachet fiscal", type="primary"):

            # Sauvegarder temporairement le fichier pour validate_invoice_stamp
            tmp_path = Path(f"_tmp_{uploaded_file.name}")

            try:
                tmp_path.write_bytes(uploaded_file.getvalue())

                with st.spinner("Analyse en cours via Gemini Vision..."):
                    is_valid = validate_invoice_stamp(str(tmp_path))

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

            except FileNotFoundError as e:
                st.error(f"Fichier introuvable : {e}")

            except ValueError as e:
                st.error(f"Erreur de configuration : {e}")

            except RuntimeError as e:
                st.error(f"Erreur d'analyse : {e}")

            finally:
                # Nettoyage du fichier temporaire
                if tmp_path.exists():
                    tmp_path.unlink()

    else:
        st.info(
            "⬆️ Chargez un devis ci-dessus pour commencer l'analyse.",
            icon="ℹ️",
        )

    st.divider()
    st.caption(
        f"Modèle : {MODEL_NAME} · "
        f"Seuil de confiance : {int(CONFIDENCE_THRESHOLD * 100)} %"
    )

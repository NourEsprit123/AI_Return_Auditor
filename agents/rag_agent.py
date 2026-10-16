
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from rag.retriever import HybridRetriever


PROJECT_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = PROJECT_DIR / "prompts" / "rag_agent_v1.txt"

load_dotenv(PROJECT_DIR / ".env")


class RAGAgent:
    """Agent RAG hybride pour l'analyse des politiques de retour."""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY est absente du fichier .env."
            )

        self.client = genai.Client(api_key=api_key)

        self.model_name = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash",
        )

        self.retriever = HybridRetriever()

    def run(self, claim):
        """Récupère les politiques pertinentes et produit une analyse sourcée."""

        if not isinstance(claim, dict):
            raise TypeError("claim doit être un dictionnaire Python.")

        vision = claim.get("vision", {})

        if not isinstance(vision, dict):
            vision = {}

        # Certains résultats de vision peuvent être enveloppés dans "result".
        if isinstance(vision.get("result"), dict):
            vision = vision["result"]

        # --------------------------------------------------
        # 1. Construire la requête de recherche
        # --------------------------------------------------
        query_parts = [
            "Return refund policy",
            f"Product: {claim.get('product_name', '')}",
            f"Category: {claim.get('product_category', '')}",
            f"Customer description: {claim.get('description', '')}",
            f"Delivery date: {claim.get('delivery_date', '')}",
            f"Damage type: {vision.get('damage_type', '')}",
            f"Damage location: {vision.get('damage_location', '')}",
            f"Damage severity: {vision.get('damage_severity', '')}",
        ]

        query = "\n".join(
            part
            for part in query_parts
            if part.split(":", 1)[-1].strip()
        )

        # --------------------------------------------------
        # 2. Recherche hybride : sémantique + BM25
        # --------------------------------------------------
        passages = self.retriever.retrieve(
            query=query,
            top_k=5,
            candidate_k=10,
        )

        # Aucune politique trouvée : ne pas inventer de décision.
        if not passages:
            return {
                "summary": "Aucune politique pertinente retrouvée.",
                "policy_findings": [],
                "recommendation": "HUMAN_REVIEW",
                "confidence": 0.0,
                "citations": [],
                "missing_information": [
                    "Aucune source pertinente n'a été retrouvée."
                ],
                "needs_human_review": True,
                "sources": [],
                "model": self.model_name,
                "prompt_version": "rag_agent_v1",
            }

        # --------------------------------------------------
        # 3. Préparer les sources et leurs identifiants
        # --------------------------------------------------
        source_blocks = []
        sources = []

        for index, passage in enumerate(passages, start=1):
            source_id = f"S{index}"

            source = {
                "id": source_id,
                "source": passage.get(
                    "source", "Source inconnue"
                ),
                "page": passage.get("page", 0),
                "text": passage.get("text", ""),
                "semantic_score": round(
                    float(passage.get("semantic_score", 0.0)), 4
                ),
                "bm25_score": round(
                    float(passage.get("bm25_score", 0.0)), 4
                ),
            }

            sources.append(source)

            source_blocks.append(
                f"[{source_id}] "
                f"File: {source['source']}; "
                f"Page: {source['page']}\n"
                f"{source['text']}"
            )

        # --------------------------------------------------
        # 4. Charger le prompt de l'agent RAG
        # --------------------------------------------------
        if not PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Prompt introuvable : {PROMPT_PATH}"
            )

        instructions = PROMPT_PATH.read_text(
            encoding="utf-8"
        ).strip()

        formatted_sources = "\n\n".join(source_blocks)

        claim_json = json.dumps(
            claim,
            ensure_ascii=False,
            default=str,
            indent=2,
        )

        request_text = f"""
{instructions}

CLAIM INFORMATION:
{claim_json}

RETRIEVED POLICY PASSAGES:
{formatted_sources}
"""

        # --------------------------------------------------
        # 5. Appeler Gemini avec reprise sur erreur temporaire
        # --------------------------------------------------
        response = None
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=request_text,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                    ),
                )
                break

            except Exception as exc:
                error_text = str(exc).upper()

                retryable_markers = (
                    "503",
                    "UNAVAILABLE",
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "500",
                    "502",
                    "504",
                    "INTERNAL",
                )

                retryable = any(
                    marker in error_text
                    for marker in retryable_markers
                )

                # Les erreurs non temporaires doivent rester visibles.
                if not retryable:
                    raise

                if attempt < max_attempts - 1:
                    wait_seconds = 2 ** (attempt + 1)

                    print(
                        f"Gemini temporairement indisponible. "
                        f"Tentative {attempt + 1}/{max_attempts}. "
                        f"Nouvel essai dans {wait_seconds} secondes."
                    )

                    time.sleep(wait_seconds)

                else:
                    # Échec final : aucune décision automatique.
                    return {
                        "summary": (
                            "L'analyse automatique n'a pas pu aboutir, "
                            "car le service Gemini est indisponible."
                        ),
                        "policy_findings": [],
                        "recommendation": "HUMAN_REVIEW",
                        "confidence": 0.0,
                        "citations": [],
                        "missing_information": [
                            "L'analyse par le modèle n'a pas pu être terminée.",
                            "Une vérification humaine est nécessaire.",
                        ],
                        "needs_human_review": True,
                        "sources": sources,
                        "model": self.model_name,
                        "prompt_version": "rag_agent_v1",
                        "error": "GEMINI_TEMPORARILY_UNAVAILABLE",
                    }

        if response is None:
            raise RuntimeError(
                "Gemini n'a retourné aucune réponse."
            )

        # --------------------------------------------------
        # 6. Vérifier et convertir la réponse JSON
        # --------------------------------------------------
        if not response.text:
            raise RuntimeError(
                "Gemini n'a retourné aucune réponse exploitable."
            )

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "La réponse de Gemini n'est pas un JSON valide."
            ) from exc

        if not isinstance(result, dict):
            raise RuntimeError(
                "La réponse JSON de Gemini doit être un objet."
            )

        # --------------------------------------------------
        # 7. Vérifier les citations retournées
        # --------------------------------------------------
        valid_ids = {source["id"] for source in sources}
        citations = result.get("citations", [])

        if not isinstance(citations, list):
            citations = []

        result["citations"] = list(
            dict.fromkeys(
                citation
                for citation in citations
                if isinstance(citation, str)
                and citation in valid_ids
            )
        )

        # --------------------------------------------------
        # 8. Appliquer les garde-fous
        # --------------------------------------------------
        allowed_recommendations = {
            "ELIGIBLE",
            "NOT_ELIGIBLE",
            "HUMAN_REVIEW",
        }

        recommendation = result.get(
            "recommendation",
            "HUMAN_REVIEW",
        )

        if recommendation not in allowed_recommendations:
            recommendation = "HUMAN_REVIEW"

        result["recommendation"] = recommendation

        if not result["citations"]:
            result["needs_human_review"] = True
            result["recommendation"] = "HUMAN_REVIEW"

        if result.get("needs_human_review") is True:
            result["recommendation"] = "HUMAN_REVIEW"

        if not isinstance(result.get("policy_findings"), list):
            result["policy_findings"] = []

        if not isinstance(result.get("missing_information"), list):
            result["missing_information"] = []

        result["sources"] = sources
        result["model"] = self.model_name
        result["prompt_version"] = "rag_agent_v1"

        return result

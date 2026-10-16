
class DecisionAgent:

    def evaluate(self, claim, rag_result):
        citations = rag_result.get("citations", [])
        sources = rag_result.get("sources", [])

        recommendation = rag_result.get(
            "recommendation", "HUMAN_REVIEW"
        )

        needs_review = rag_result.get(
            "needs_human_review", True
        )

        # Vérifier les identifiants des sources récupérées.
        source_ids = {
            str(source["id"])
            for source in sources
            if isinstance(source, dict) and source.get("id") is not None
        }

        valid_citations = []

        for citation in citations:
            if isinstance(citation, dict):
                citation_id = (
                    citation.get("source_id")
                    or citation.get("id")
                )
            elif isinstance(citation, str):
                citation_id = citation
            else:
                citation_id = None

            if (
                citation_id is not None
                and str(citation_id) in source_ids
            ):
                valid_citations.append(citation)

        # Par défaut, aucune décision automatique.
        status = "HUMAN_REVIEW"

        if sources and valid_citations and not needs_review:
            if recommendation == "ELIGIBLE":
                status = "POLICY_SUPPORTS_RETURN"

            elif recommendation == "NOT_ELIGIBLE":
                status = "POLICY_DOES_NOT_SUPPORT_RETURN"

        return {
            "status": status,
            "summary": rag_result.get(
                "summary",
                "Aucune justification disponible."
            ),
            "policy_findings": rag_result.get(
                "policy_findings", []
            ),
            "citations": valid_citations,
            "sources": sources,
            "missing_information": rag_result.get(
                "missing_information", []
            ),
            "needs_human_review": status == "HUMAN_REVIEW",
            "model_confidence": rag_result.get("confidence"),
            "rag_result": rag_result,
        }

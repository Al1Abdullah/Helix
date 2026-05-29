"""
helix/utils/mesh.py

Resolves condition strings to authoritative NLM MeSH descriptor labels.
MeSH (Medical Subject Headings) is the controlled vocabulary PubMed uses
internally — resolving to MeSH terms before querying dramatically improves
search recall. Zero new dependencies: uses httpx already in the stack.
Falls back to the original string silently if the API is unavailable.
"""
import httpx
from helix.logger import get_logger

_log = get_logger(__name__)
_ENDPOINT = "https://id.nlm.nih.gov/mesh/lookup/descriptor"


async def resolveMeSH(condition: str) -> str:
    """
    Return the canonical NLM MeSH descriptor label for a condition string.
    Falls back to the original string if no match found or API unreachable.

    Examples:
        resolveMeSH("Type 2 Diabetes")  → "Diabetes Mellitus, Type 2"
        resolveMeSH("Lung Cancer")      → "Lung Neoplasms"
        resolveMeSH("unknown xyz")      → "unknown xyz"  (passthrough)
    """
    if not condition or not condition.strip():
        return condition
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                _ENDPOINT,
                params={"label": condition.strip(), "match": "startsWith", "limit": 1},
            )
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list):
                    label = data[0].get("label", "").strip()
                    if label:
                        _log.debug(
                            "mesh_resolved",
                            extra={"from": condition, "to": label},
                        )
                        return label
    except Exception as error:
        _log.debug("mesh_unavailable", extra={"condition": condition, "error": str(error)})
    return condition

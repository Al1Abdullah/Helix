"""
Shared pytest fixtures for Helix unit tests.
All fixtures are pure Python — no network calls, no external dependencies.
"""
import pytest


@pytest.fixture
def sample_trials_response():
    """Minimal valid ClinicalTrials.gov API response with 2 studies."""
    def _make_study(nct_id, title, min_age, max_age, phases, status="RECRUITING"):
        return {
            "protocolSection": {
                "identificationModule": {"nctId": nct_id, "briefTitle": title},
                "statusModule": {"overallStatus": status},
                "descriptionModule": {"briefSummary": f"A trial about {title.lower()}"},
                "eligibilityModule": {
                    "minimumAge": min_age,
                    "maximumAge": max_age,
                    "sex": "ALL",
                },
                "designModule": {"phases": phases},
                "contactsLocationsModule": {},
            }
        }

    return {
        "studies": [
            _make_study("NCT00000001", "Diabetes Semaglutide Trial", "18 Years", "65 Years", ["PHASE3"]),
            _make_study("NCT00000002", "Type 2 Diabetes Insulin Study", "40 Years", "70 Years", ["PHASE2"]),
        ]
    }


@pytest.fixture
def sample_pubmed_summaries():
    """Minimal valid PubMed esummary response."""
    return {
        "result": {
            "uids": ["12345678", "87654321"],
            "12345678": {
                "title": "Metformin for Type 2 Diabetes: A systematic review",
                "authors": [{"name": "Smith J"}, {"name": "Jones A"}],
                "source": "New England Journal of Medicine",
                "pubdate": "2023 Jan",
            },
            "87654321": {
                "title": "Insulin resistance mechanisms in diabetes",
                "authors": [{"name": "Brown K"}],
                "source": "Lancet",
                "pubdate": "2022 Mar",
            },
        }
    }


@pytest.fixture
def sample_fda_response():
    """Minimal valid openFDA drug label response."""
    return {
        "results": [
            {
                "openfda": {
                    "brand_name": ["GLUCOPHAGE"],
                    "generic_name": ["METFORMIN HYDROCHLORIDE"],
                    "manufacturer_name": ["Bristol-Myers Squibb"],
                    "route": ["ORAL"],
                },
                "indications_and_usage": ["For treatment of type 2 diabetes mellitus."],
                "warnings": ["Lactic acidosis risk. Renal impairment contraindication."],
            }
        ]
    }

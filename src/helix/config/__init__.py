import os
from dotenv import load_dotenv

load_dotenv()


class TrialsConfig:
    base_url: str = "https://clinicaltrials.gov/api/v2"
    default_limit: int = 10
    max_limit: int = 50


class PubMedConfig:
    base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    email: str = os.getenv("PUBMED_EMAIL", "helix@example.com")
    api_key: str = os.getenv("PUBMED_API_KEY", "")
    default_limit: int = 10


class FdaConfig:
    base_url: str = "https://api.fda.gov/drug"
    default_limit: int = 10


class ServerConfig:
    name: str = "Helix"
    version: str = "0.1.0"


trials = TrialsConfig()
pubmed = PubMedConfig()
fda = FdaConfig()
server = ServerConfig()

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from importlib.metadata import version as _pkg_version
    _VERSION = _pkg_version("helix")
except Exception:
    _VERSION = "1.3.0"


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


class CacheConfig:
    synthesis_ttl: int = 300   # 5 min
    trials_ttl: int = 180      # 3 min
    papers_ttl: int = 600      # 10 min
    drugs_ttl: int = 3600      # 1 hr


class ServerConfig:
    name: str = "Helix"
    version: str = _VERSION


trials = TrialsConfig()
pubmed = PubMedConfig()
fda = FdaConfig()
cache = CacheConfig()
server = ServerConfig()

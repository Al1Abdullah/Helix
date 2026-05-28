import os
from dotenv import load_dotenv

load_dotenv()

class TrialsConfig:
    baseUrl = "https://clinicaltrials.gov/api/v2"
    defaultLimit = 10
    maxLimit = 50

class PubMedConfig:
    baseUrl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    email = os.getenv("PUBMED_EMAIL", "helix@example.com")
    apiKey = os.getenv("PUBMED_API_KEY", "")
    defaultLimit = 10

class FdaConfig:
    baseUrl = "https://api.fda.gov/drug"
    defaultLimit = 10

class ServerConfig:
    name = "Helix"
    version = "0.1.0"

trials = TrialsConfig()
pubmed = PubMedConfig()
fda = FdaConfig()
server = ServerConfig()

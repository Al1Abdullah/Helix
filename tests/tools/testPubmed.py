import asyncio
from helix.tools.pubmed import searchPapers


async def main():
    print("Searching PubMed for Alzheimer's research...\n")
    results = await searchPapers("Alzheimer's disease", yearFrom=2023, limit=3)

    for paper in (results or []):
        print(f"ID      : {paper.get('id', 'N/A')}")
        print(f"Title   : {paper.get('title', 'N/A')}")
        print(f"Authors : {', '.join(paper.get('authors', []))}")
        print(f"Journal : {paper.get('journal', 'N/A')}")
        print(f"Year    : {paper.get('year', 'N/A')}")
        print(f"URL     : {paper.get('url', '')}")
        print("---")


asyncio.run(main())

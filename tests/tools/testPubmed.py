import asyncio
from helix.tools.pubmed import searchPapers

async def main():
    print("Searching PubMed for Alzheimer's research...\n")
    results = await searchPapers("Alzheimer's disease", yearFrom=2023, limit=3)

    for paper in results:
        print(f"ID      : {paper['id']}")
        print(f"Title   : {paper['title']}")
        print(f"Authors : {', '.join(paper['authors'])}")
        print(f"Journal : {paper['journal']}")
        print(f"Year    : {paper['year']}")
        print(f"URL     : {paper['url']}")
        print("---")

asyncio.run(main())

class Formatter:
    def shapeTrialResults(self, rawResponse: dict) -> list[dict]:
        studies = rawResponse.get("studies", [])
        results = []

        for study in studies:
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})
            description = protocol.get("descriptionModule", {})
            eligibility = protocol.get("eligibilityModule", {})
            contacts = protocol.get("contactsLocationsModule", {})
            centralContacts = contacts.get("centralContacts", [])
            contactInfo = centralContacts[0] if centralContacts else {}

            results.append({
                "id": identification.get("nctId", ""),
                "title": identification.get("briefTitle", ""),
                "status": status.get("overallStatus", ""),
                "phase": protocol.get("designModule", {}).get("phases", []),
                "summary": description.get("briefSummary", "")[:500],
                "minimumAge": eligibility.get("minimumAge", ""),
                "maximumAge": eligibility.get("maximumAge", ""),
                "sex": eligibility.get("sex", "ALL"),
                "contactName": contactInfo.get("name", ""),
                "contactEmail": contactInfo.get("email", ""),
                "url": f"https://clinicaltrials.gov/study/{identification.get('nctId', '')}",
            })

        return results

    def shapePaperResults(self, ids: list, summaries: dict) -> list[dict]:
        results = []
        uids = summaries.get("result", {}).get("uids", [])

        for uid in uids:
            paper = summaries.get("result", {}).get(uid, {})
            authors = paper.get("authors", [])
            authorNames = [a.get("name", "") for a in authors[:3]]

            results.append({
                "id": uid,
                "title": paper.get("title", ""),
                "authors": authorNames,
                "journal": paper.get("source", ""),
                "year": paper.get("pubdate", "")[:4] if paper.get("pubdate") else "",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
            })

        return results

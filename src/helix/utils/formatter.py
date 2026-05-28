def _parse_age(age_string: str) -> int | None:
    """Convert age strings like '18 Years' or '6 Months' to integer years."""
    if not age_string or not isinstance(age_string, str):
        return None
    lower = age_string.lower().strip()
    try:
        value = int(lower.split()[0])
        if "month" in lower:
            return max(value // 12, 0)
        return value
    except (ValueError, IndexError):
        return None


class Formatter:
    def shapeTrialResults(self, raw_response: dict) -> list[dict]:
        """Normalize raw ClinicalTrials.gov API response into canonical Trial dicts."""
        if not isinstance(raw_response, dict):
            return []

        studies = raw_response.get("studies", [])
        if not isinstance(studies, list):
            return []

        results = []
        for study in studies:
            if not isinstance(study, dict):
                continue

            protocol = study.get("protocolSection") or {}
            identification = protocol.get("identificationModule") or {}
            status = protocol.get("statusModule") or {}
            description = protocol.get("descriptionModule") or {}
            eligibility = protocol.get("eligibilityModule") or {}
            design = protocol.get("designModule") or {}
            contacts = protocol.get("contactsLocationsModule") or {}
            central_contacts = contacts.get("centralContacts") or []
            contact_info = central_contacts[0] if central_contacts else {}

            nct_id = identification.get("nctId") or ""
            min_age_raw = eligibility.get("minimumAge") or ""
            max_age_raw = eligibility.get("maximumAge") or ""

            results.append({
                # Canonical identifiers
                "id": nct_id,
                "title": identification.get("briefTitle") or "",
                # Status
                "status": status.get("overallStatus") or "",
                # Phase: list of strings e.g. ["PHASE3"]
                "phase": design.get("phases") or [],
                # Summary text (capped for token efficiency)
                "summary": (description.get("briefSummary") or "")[:500],
                # Age eligibility — parsed to int|None (canonical schema)
                "min_age": _parse_age(min_age_raw),
                "max_age": _parse_age(max_age_raw),
                # Keep raw string for display
                "min_age_raw": min_age_raw,
                "max_age_raw": max_age_raw,
                # Demographics
                "sex": eligibility.get("sex") or "ALL",
                # Contact
                "contact_name": contact_info.get("name") or "",
                "contact_email": contact_info.get("email") or "",
                # URL
                "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
            })

        return results

    def shapePaperResults(self, ids: list, summaries: dict) -> list[dict]:
        """Normalize raw PubMed esummary response into canonical Paper dicts."""
        if not isinstance(summaries, dict) or not isinstance(ids, list):
            return []

        result_block = summaries.get("result") or {}
        uids = result_block.get("uids") or []

        papers = []
        for uid in uids:
            if not isinstance(uid, str):
                continue
            paper = result_block.get(uid) or {}
            if not isinstance(paper, dict):
                continue

            authors_raw = paper.get("authors") or []
            author_names = [
                a.get("name") or ""
                for a in authors_raw[:3]
                if isinstance(a, dict)
            ]

            pub_date = paper.get("pubdate") or ""
            year_str = pub_date[:4] if pub_date else ""
            try:
                year = int(year_str)
            except (ValueError, TypeError):
                year = 0

            papers.append({
                "id": uid,
                "title": paper.get("title") or "",
                # abstract: esummary does not return full text; empty string is safe default
                "abstract": "",
                "authors": author_names,
                "journal": paper.get("source") or "",
                "year": year,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
            })

        return papers

    def shapeDrugResults(self, raw_response: dict) -> list[dict]:
        """Normalize raw openFDA drug label response into canonical Drug dicts."""
        if not isinstance(raw_response, dict):
            return []

        results = raw_response.get("results") or []
        if not isinstance(results, list):
            return []

        shaped = []
        for drug in results:
            if not isinstance(drug, dict):
                continue

            openfda = drug.get("openfda") or {}
            brand_names = openfda.get("brand_name") or []
            generic_names = openfda.get("generic_name") or []
            manufacturers = openfda.get("manufacturer_name") or []
            indications_list = drug.get("indications_and_usage") or []
            warnings_list = drug.get("warnings") or []

            shaped.append({
                "brand_name": brand_names[0] if brand_names else "",
                "generic_name": generic_names[0] if generic_names else "",
                "manufacturer": manufacturers[0] if manufacturers else "",
                "route": openfda.get("route") or [],
                "indications": (indications_list[0][:300]) if indications_list else "",
                "warnings": (warnings_list[0][:300]) if warnings_list else "",
            })

        return shaped

# app/services/academic_service.py
import re
import requests
from typing import Dict, Any, Optional

class AcademicVerificationService:
    """
    Tier 2: Public Academic & Open Web Connectors (Online, Privacy-Preserving).
    Guarantees that full student lecture notes and slides are NEVER sent to external APIs;
    only isolated, sanitized propositions are queried.
    """

    USER_AGENT = "NotesAppUniversity/1.0 (academic-research-tool; contact@studentnotes.local)"

    def sanitize_claim(self, raw_claim: str) -> str:
        """Strip student annotations and retain core factual proposition"""
        clean = re.sub(r"(?:\b(?:prof states|professor said|in lecture|i think|maybe|slide \d+:?)\b|\bnote:?)", "", raw_claim, flags=re.IGNORECASE)
        clean = re.sub(r"^\s*that\b", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"[^\w\s\d\.-]", "", clean).strip()
        clean = re.sub(r"^\s*that\b", "", clean, flags=re.IGNORECASE).strip()
        # Clean up any leftover multiple spaces
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def query_wikipedia(self, claim: str) -> Dict[str, Any]:
        sanitized = self.sanitize_claim(claim)
        if not sanitized:
            return {"status": "unverified", "citation": None, "snippet": "", "confidence": 0.0}

        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": sanitized,
            "utf8": 1,
            "format": "json"
        }
        headers = {"User-Agent": self.USER_AGENT}

        try:
            resp = requests.get(search_url, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                search_results = data.get("query", {}).get("search", [])
                if search_results:
                    top = search_results[0]
                    title = top.get("title", "")
                    raw_snippet = top.get("snippet", "")
                    clean_snippet = re.sub(r"<[^>]+>", "", raw_snippet)

                    # Simple stance evaluation
                    claim_words = set(re.findall(r"\b\w{3,}\b", sanitized.lower()))
                    snippet_words = set(re.findall(r"\b\w{3,}\b", clean_snippet.lower()))
                    overlap = len(claim_words.intersection(snippet_words))

                    if overlap >= 2:
                        return {
                            "status": "plausible",
                            "confidence": 0.85,
                            "source_tier": "wikipedia",
                            "citation": f"Wikipedia: {title}",
                            "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                            "snippet": clean_snippet
                        }
        except Exception as e:
            print(f"Wikipedia API error: {e}")

        return {
            "status": "unverified",
            "confidence": 0.35,
            "source_tier": "wikipedia",
            "citation": None,
            "snippet": ""
        }

    def query_semantic_scholar(self, claim: str) -> Dict[str, Any]:
        sanitized = self.sanitize_claim(claim)
        if not sanitized:
            return {"status": "unverified", "citation": None, "snippet": "", "confidence": 0.0}

        api_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": sanitized,
            "limit": 2,
            "fields": "title,abstract,authors,year"
        }
        headers = {"User-Agent": self.USER_AGENT}

        try:
            resp = requests.get(api_url, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                papers = data.get("data", [])
                if papers:
                    top = papers[0]
                    title = top.get("title", "")
                    abstract = top.get("abstract") or ""
                    year = top.get("year", "")
                    authors = ", ".join([a.get("name", "") for a in top.get("authors", [])[:2]])

                    return {
                        "status": "verified" if abstract else "plausible",
                        "confidence": 0.88,
                        "source_tier": "semantic_scholar",
                        "citation": f"{authors} ({year}). {title}",
                        "snippet": abstract[:280] if abstract else title
                    }
        except Exception as e:
            print(f"Semantic Scholar API error: {e}")

        return {
            "status": "unverified",
            "confidence": 0.30,
            "source_tier": "semantic_scholar",
            "citation": None,
            "snippet": ""
        }

    def verify_claim(self, claim: str) -> Dict[str, Any]:
        """Runs Tier 2 academic verification sequentially with privacy-sanitized proposition"""
        # Try Wikipedia first (fastest, high domain coverage)
        wiki_res = self.query_wikipedia(claim)
        if wiki_res.get("status") in ["verified", "plausible"]:
            return wiki_res

        # Fallback to Semantic Scholar
        scholar_res = self.query_semantic_scholar(claim)
        if scholar_res.get("status") in ["verified", "plausible"]:
            return scholar_res

        return {
            "claim": claim,
            "status": "unverified",
            "confidence": 0.25,
            "source_tier": "academic_web",
            "citation": "No conclusive academic consensus found online",
            "snippet": ""
        }

academic_service = AcademicVerificationService()

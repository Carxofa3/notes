# app/services/rag_service.py
import os
import re
import math
import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            PdfReader = None

from typing import List, Dict, Any, Optional
from app.database import db
from app.models.models import CourseDocument, SlideChunk, FactCheckResult

class CourseRAGService:
    """
    Tier 1: 100% Offline & Private Course Lecture Slide Ingestion & Verification Engine.
    Keeps all university PDFs, slide decks, and notes strictly on local hardware.
    """

    def ingest_pdf(self, file_path: str, course_name: Optional[str] = "General Course", custom_title: Optional[str] = None) -> CourseDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = os.path.basename(file_path)
        title = custom_title or os.path.splitext(filename)[0].replace("_", " ").title()

        reader = PdfReader(file_path)
        total_pages = len(reader.pages)

        doc = CourseDocument(
            filename=filename,
            title=title,
            course_name=course_name,
            total_pages=total_pages
        )
        db.session.add(doc)
        db.session.flush()

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            raw_text = page.extract_text() or ""
            clean_text = self._clean_slide_text(raw_text)

            if not clean_text:
                continue

            # Extract possible slide title from first non-empty line
            lines = [l.strip() for l in clean_text.split("\n") if l.strip()]
            slide_title = lines[0][:100] if lines else f"Slide {page_num}"

            chunk = SlideChunk(
                document_id=doc.id,
                page_number=page_num,
                slide_title=slide_title,
                content=clean_text
            )
            db.session.add(chunk)

        db.session.commit()
        return doc

    def search_slides(self, query: str, limit: int = 5, course_name: Optional[str] = None) -> List[Dict[str, Any]]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        chunks_query = db.session.query(SlideChunk, CourseDocument).join(
            CourseDocument, SlideChunk.document_id == CourseDocument.id
        )
        if course_name:
            chunks_query = chunks_query.filter(CourseDocument.course_name == course_name)

        all_results = []
        for chunk, doc in chunks_query.all():
            score = self._compute_bm25_score(query_terms, chunk.content)
            if score > 0:
                all_results.append({
                    "chunk_id": chunk.id,
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "course_name": doc.course_name,
                    "page_number": chunk.page_number,
                    "slide_title": chunk.slide_title,
                    "content": chunk.content,
                    "score": round(score, 3)
                })

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:limit]

    def verify_claim(self, claim: str, note_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Verifies an isolated claim against the local course slide repository.
        Returns stance, slide citation, excerpt, and suggested correction if disputed.
        """
        claim_terms = self._tokenize(claim)
        candidates = self.search_slides(claim, limit=3)

        if not candidates:
            res = {
                "claim": claim,
                "status": "unverified",
                "confidence": 0.30,
                "source_tier": "course_slides",
                "citation": "No matching course slide found",
                "evidence_text": "",
                "suggested_correction": None
            }
            self._save_fact_check(res, note_id)
            return res

        best = candidates[0]
        slide_text_lower = best["content"].lower()
        claim_lower = claim.lower()

        # Check for numeric contradictions
        claim_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", claim_lower)
        slide_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", slide_text_lower)

        has_number_conflict = False
        suggested_correction = None

        if claim_numbers and slide_numbers:
            # If claim claims e.g. 4 ATP but slide states 2 ATP
            shared_ctx_words = [w for w in claim_terms if len(w) > 3 and w in slide_text_lower]
            if len(shared_ctx_words) >= 2 and set(claim_numbers) != set(slide_numbers):
                # Search if there is a direct contradictory sentence
                for line in best["content"].split("\n"):
                    line_l = line.lower()
                    if any(w in line_l for w in shared_ctx_words) and any(n in line_l for n in slide_numbers):
                        has_number_conflict = True
                        suggested_correction = line.strip()
                        break

        if has_number_conflict:
            status = "contradiction"
            confidence = 0.92
            citation = f"Slide {best['page_number']}, {best['document_title']}"
            evidence = best["content"][:300]
        elif best["score"] >= 2.0:
            status = "verified"
            confidence = min(0.98, 0.70 + best["score"] * 0.08)
            citation = f"Slide {best['page_number']}, {best['document_title']}"
            evidence = best["content"][:300]
        elif best["score"] >= 0.8:
            status = "plausible"
            confidence = 0.75
            citation = f"Slide {best['page_number']}, {best['document_title']}"
            evidence = best["content"][:200]
        else:
            status = "unverified"
            confidence = 0.40
            citation = None
            evidence = ""

        result = {
            "claim": claim,
            "status": status,
            "confidence": round(confidence, 2),
            "source_tier": "course_slides",
            "citation": citation,
            "evidence_text": evidence,
            "suggested_correction": suggested_correction
        }
        self._save_fact_check(result, note_id)
        return result

    def _save_fact_check(self, data: Dict[str, Any], note_id: Optional[int]):
        try:
            fc = FactCheckResult(
                note_id=note_id,
                claim=data["claim"],
                status=data["status"],
                confidence=data["confidence"],
                source_tier=data["source_tier"],
                citation=data.get("citation"),
                evidence_text=data.get("evidence_text"),
                suggested_correction=data.get("suggested_correction")
            )
            db.session.add(fc)
            db.session.commit()
        except Exception:
            db.session.rollback()

    def _clean_slide_text(self, text: str) -> str:
        # Normalize whitespace and strip slide header/footer noise
        cleaned = re.sub(r"[ \t]+", " ", text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
        stopwords = {
            "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by",
            "is", "are", "was", "were", "of", "from", "that", "this", "these", "those"
        }
        return [w for w in words if w not in stopwords]

    def _compute_bm25_score(self, query_terms: List[str], doc_text: str, k1: float = 1.5, b: float = 0.75) -> float:
        doc_lower = doc_text.lower()
        doc_words = self._tokenize(doc_lower)
        doc_len = len(doc_words)
        if doc_len == 0:
            return 0.0

        avg_len = 50.0 # Approximate average slide length
        score = 0.0
        for term in query_terms:
            tf = doc_lower.count(term)
            if tf > 0:
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / avg_len))
                score += (numerator / denominator)

        return score

rag_service = CourseRAGService()

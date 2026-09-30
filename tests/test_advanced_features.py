# tests/test_advanced_features.py
import pytest
import json
import base64
import os
import io
import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    try:
        from pypdf import PdfWriter
    except ImportError:
        from PyPDF2 import PdfWriter

from app import create_app, db
from app.models.models import CourseDocument, SlideChunk, Note, Lesson, Unit
from app.services.decide_service import jev_engine
from app.services.rag_service import rag_service
from app.services.academic_service import academic_service
from app.services.sync_service import sync_service
from app.services.llm_escalation import llm_escalation

@pytest.fixture
def app():
    app = create_app(config_name='testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

# --- Jev / GLiNER2.5-Decide Engine Tests ---

def test_v1_decide_endpoint(client):
    """Test Jev-compatible /v1/decide endpoint"""
    payload = {
        "context": "Mitochondria produce 36 to 38 ATP per glucose molecule through aerobic respiration.",
        "schema": {
            "classification": ["Biology", "Chemistry", "Physics"],
            "fact_status": ["verified", "plausible", "suspect", "unverified"],
            "entities": ["organelle", "molecule", "biological_process"]
        }
    }
    response = client.post('/v1/decide', json=payload)
    assert response.status_code == 200
    data = response.json
    assert data["classification"] == "Biology"
    assert data["fact_status"] == "verified"
    assert data["confidence"] > 0.8
    entity_texts = [e["text"].lower() for e in data["entities"]]
    assert any("mitochondria" in t for t in entity_texts)
    assert any("atp" in t for t in entity_texts)
    assert any("glucose" in t for t in entity_texts)

def test_decide_engine_empty_input():
    """Test decide engine gracefully handles empty strings"""
    res = jev_engine.evaluate("")
    assert res["classification"] == "General"
    assert res["entities"] == []
    assert res["confidence"] == 0.0

def test_decide_engine_auto_format_triggers():
    """Test detection of unrendered LaTeX math formulas and lists"""
    context = "The formula has alpha and beta coefficients. \n- Item 1\n- Item 2"
    res = jev_engine.evaluate(context)
    trigger_types = [t["type"] for t in res["format_triggers"]]
    assert "unrendered_latex" in trigger_types
    assert "list_detected" in trigger_types

# --- Local-First Offline Note Creation Regression Test ---

def test_note_creation_and_update_without_api_keys(client, app):
    """Verify that creating and updating notes with content never crashes when cloud keys are unset."""
    with app.app_context():
        lesson = Lesson(name="Biology 101")
        db.session.add(lesson)
        db.session.flush()
        unit = Unit(name="Cellular Respiration", lesson_id=lesson.id)
        db.session.add(unit)
        db.session.commit()
        unit_id = unit.id

    # Create note with content via REST API
    post_res = client.post(f'/api/notes/by-unit/{unit_id}', json={
        "title": "Krebs Cycle",
        "content": "Acetyl-CoA enters the citric acid cycle producing NADH and FADH2."
    })
    assert post_res.status_code == 201
    note_id = post_res.json["id"]
    assert post_res.json["title"] == "Krebs Cycle"

    # Update note via REST API
    put_res = client.put(f'/api/notes/{note_id}', json={
        "title": "Krebs Cycle Updated",
        "content": "Updated content with additional details on oxaloacetate."
    })
    assert put_res.status_code == 200
    assert put_res.json["title"] == "Krebs Cycle Updated"

# --- Heavy LLM Escalation Endpoints ---

def test_heavy_llm_escalate_contradiction_endpoint(client):
    """Test Stage 2 contradiction resolution escalation endpoint"""
    payload = {
        "claim": "Glycolysis yields 4 ATP net per glucose",
        "slide_excerpt": "Slide 8: Glycolysis generates 4 ATP total, but consumes 2 ATP, resulting in a net yield of 2 ATP.",
        "web_evidence": "Biochemistry 9th ed."
    }
    res = client.post('/api/ai/escalate-contradiction', json=payload)
    assert res.status_code == 200
    data = res.json
    assert data["claim"] == payload["claim"]
    assert "resolution" in data
    assert data["suggested_action"] == "apply_diff_correction"

def test_heavy_llm_synthesize_lecture_endpoint(client):
    """Test Stage 2 structured study guide synthesis endpoint"""
    payload = {
        "content": "Photosynthesis occurs in chloroplasts. Light reactions split water and produce ATP and NADPH. Calvin cycle fixes CO2 into sugar."
    }
    res = client.post('/api/ai/synthesize-lecture', json=payload)
    assert res.status_code == 200
    assert "synthesized_content" in res.json
    assert len(res.json["synthesized_content"]) > 10

# --- Course Slide RAG Tests ---

def test_rag_verify_claim_support(app):
    """Test RAG verification when lecture slides support a factual claim"""
    with app.app_context():
        doc = CourseDocument(filename="bio_lec4.pdf", title="Biology Lecture 4: Respiration", course_name="Bio 101", total_pages=20)
        db.session.add(doc)
        db.session.flush()

        chunk = SlideChunk(
            document_id=doc.id,
            page_number=18,
            slide_title="ATP Yield per Glucose",
            content="Cellular respiration yields approximately 36 to 38 ATP molecules per glucose molecule under aerobic conditions."
        )
        db.session.add(chunk)
        db.session.commit()

        claim = "Aerobic cellular respiration yields 36 to 38 ATP per glucose molecule."
        result = rag_service.verify_claim(claim)
        assert result["status"] == "verified"
        assert "Slide 18" in result["citation"]
        assert result["confidence"] > 0.7

def test_rag_verify_claim_contradiction(app):
    """Test RAG verification detects contradiction when claim has disputed values"""
    with app.app_context():
        doc = CourseDocument(filename="bio_lec4.pdf", title="Cellular Respiration", course_name="Bio 101", total_pages=15)
        db.session.add(doc)
        db.session.flush()

        chunk = SlideChunk(
            document_id=doc.id,
            page_number=8,
            slide_title="Glycolysis Net Yield",
            content="Glycolysis net yield produces 2 ATP and 2 NADH molecules per glucose."
        )
        db.session.add(chunk)
        db.session.commit()

        claim = "Glycolysis net yield produces 4 ATP molecules per glucose."
        result = rag_service.verify_claim(claim)
        assert result["status"] == "contradiction"
        assert result["suggested_correction"] is not None
        assert "2 ATP" in result["suggested_correction"]

def test_rag_pdf_ingestion_and_search_endpoints(client, tmp_path):
    """Test complete upload, ingestion, listing, search, and verification endpoints for slides"""
    # Create a small valid test PDF with readable text
    raw_pdf = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 85 >> stream
BT
/F1 12 Tf
50 250 Td
(Cellular respiration produces 36 to 38 ATP per glucose molecule.) Tj
ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000380 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
459
%%EOF"""

    pdf_file = tmp_path / "bio_slides.pdf"
    pdf_file.write_bytes(raw_pdf)

    with open(pdf_file, 'rb') as f:
        data = {
            'file': (f, 'bio_slides.pdf'),
            'course_name': 'Bio 101',
            'title': 'Cellular Respiration Lecture'
        }
        upload_resp = client.post('/api/rag/upload', data=data, content_type='multipart/form-data')

    assert upload_resp.status_code == 201
    assert upload_resp.json["chunks_indexed"] >= 1
    doc_id = upload_resp.json["document_id"]

    # 1. Test listing documents
    docs_resp = client.get('/api/rag/documents')
    assert docs_resp.status_code == 200
    assert any(d["id"] == doc_id for d in docs_resp.json)

    # 2. Test searching slides
    search_resp = client.get('/api/rag/search?q=respiration')
    assert search_resp.status_code == 200
    assert len(search_resp.json) >= 1
    assert "respiration" in search_resp.json[0]["content"].lower()

    # 3. Test verifying claim via HTTP
    verify_resp = client.post('/api/rag/verify-claim', json={
        "claim": "Cellular respiration produces 36 to 38 ATP."
    })
    assert verify_resp.status_code == 200
    assert verify_resp.json["status"] in ["verified", "plausible"]

def test_rag_upload_scanned_pdf_warning(client, tmp_path):
    """Test uploading scanned image-only PDF surfaces graceful warning and chunks_indexed=0"""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    scanned_file = tmp_path / "scanned_deck.pdf"
    with open(scanned_file, "wb") as f:
        writer.write(f)

    with open(scanned_file, 'rb') as f:
        data = {
            'file': (f, 'scanned_deck.pdf'),
            'course_name': 'History 101',
            'title': 'Scanned Primary Sources'
        }
        upload_resp = client.post('/api/rag/upload', data=data, content_type='multipart/form-data')

    assert upload_resp.status_code == 201
    assert upload_resp.json["chunks_indexed"] == 0
    assert "warning" in upload_resp.json
    assert "OCR" in upload_resp.json["warning"]

# --- Academic Proposition Sanitization & Verification ---

def test_academic_sanitize_claim_extended():
    """Test student notes annotations are stripped across diverse edge cases"""
    cases = [
        ("Prof states that mitochondria generate ATP", "mitochondria generate ATP"),
        ("Professor said in lecture that DNA is double-stranded", "DNA is double-stranded"),
        ("Note: glucose is stored as glycogen in liver", "glucose is stored as glycogen in liver"),
        ("Slide 12: ATP synthase rotates like a turbine", "ATP synthase rotates like a turbine")
    ]
    for raw, expected in cases:
        sanitized = academic_service.sanitize_claim(raw)
        assert sanitized.lower() == expected.lower()

def test_academic_verify_endpoint(client):
    """Test HTTP API endpoint for Tier 2 academic verification"""
    res = client.post('/api/academic/verify', json={
        "claim": "Water molecule consists of two hydrogen atoms and one oxygen atom"
    })
    assert res.status_code == 200
    assert res.json["status"] in ["verified", "plausible", "unverified"]

# --- Tailscale Peer-to-Peer Sync API Tests ---

def test_sync_pair_info(client):
    """Test fetching local device Tailscale pairing info and QR code payload"""
    response = client.get('/api/sync/pair-info')
    assert response.status_code == 200
    data = response.json
    assert "magic_dns" in data
    assert "fingerprint" in data
    assert data["port"] == 58855
    assert "pairing_payload" in data

def test_sync_register_peer_and_crdt_delta(client, app):
    """Test peer registration and CRDT binary delta exchange"""
    peer_data = {
        "device_name": "Carle Galaxy Tab S9",
        "magic_dns": "carle-tab.tailnet.ts.net",
        "ip": "100.64.0.42",
        "port": 58855,
        "fingerprint": "ed25519:test-fingerprint-mobile"
    }
    reg_resp = client.post('/api/sync/peers', json=peer_data)
    assert reg_resp.status_code == 201

    peers_resp = client.get('/api/sync/peers')
    assert peers_resp.status_code == 200
    assert len(peers_resp.json) >= 1
    assert any(p["device_name"] == "Carle Galaxy Tab S9" for p in peers_resp.json)

    with app.app_context():
        lesson = Lesson(name="Math 101")
        db.session.add(lesson)
        db.session.flush()
        unit = Unit(name="Calculus", lesson_id=lesson.id)
        db.session.add(unit)
        db.session.flush()
        note = Note(title="Limits", content="Limit definitions", unit_id=unit.id)
        db.session.add(note)
        db.session.commit()
        note_id = note.id

    dummy_crdt_delta = b"\x01\x02\x03\x04YRS_BINARY_DELTA_V1"
    b64_delta = base64.b64encode(dummy_crdt_delta).decode('utf-8')

    delta_post = client.post('/api/sync/delta', json={
        "note_id": note_id,
        "delta_base64": b64_delta
    })
    assert delta_post.status_code == 200

    delta_get = client.get(f'/api/sync/delta/{note_id}')
    assert delta_get.status_code == 200
    assert delta_get.json["delta_base64"] == b64_delta

def test_serve_frontend_index(client):
    """Test that the Flask root endpoint serves the modern Svelte SPA"""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Ultimate University Notes" in response.data or b"My Notes" in response.data

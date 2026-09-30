/**
 * API Client for University Notes Ecosystem
 */

const BASE = ''; // Proxied via Vite or served from Flask root

export async function fetchLessons() {
  const res = await fetch(`${BASE}/api/lessons/`);
  return res.ok ? await res.json() : [];
}

export async function createLesson(name) {
  const res = await fetch(`${BASE}/api/lessons/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  });
  return res.ok ? await res.json() : null;
}

export async function fetchUnits(lessonId) {
  const res = await fetch(`${BASE}/api/units/by-lesson/${lessonId}`);
  return res.ok ? await res.json() : [];
}

export async function createUnit(lessonId, name) {
  const res = await fetch(`${BASE}/api/units/by-lesson/${lessonId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, lesson_id: lessonId })
  });
  return res.ok ? await res.json() : null;
}

export async function fetchNotes(unitId) {
  const res = await fetch(`${BASE}/api/notes/by-unit/${unitId}`);
  return res.ok ? await res.json() : [];
}

export async function fetchNote(noteId) {
  const res = await fetch(`${BASE}/api/notes/${noteId}`);
  return res.ok ? await res.json() : null;
}

export async function createNote(unitId, { title, content }) {
  const res = await fetch(`${BASE}/api/notes/by-unit/${unitId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ unit_id: unitId, title, content })
  });
  return res.ok ? await res.json() : null;
}

export async function updateNote(noteId, { title, content }) {
  const res = await fetch(`${BASE}/api/notes/${noteId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, content })
  });
  return res.ok ? await res.json() : null;
}

export async function deleteNote(noteId) {
  const res = await fetch(`${BASE}/api/notes/${noteId}`, { method: 'DELETE' });
  return res.status === 204;
}

// --- GLiNER2.5-Decide / Jev System 1 Decision Engine ---
export async function evaluateDecide(context, schema = {}) {
  const res = await fetch(`${BASE}/v1/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ context, schema })
  });
  return res.ok ? await res.json() : null;
}

// --- Course Slide RAG & Local Verification ---
export async function fetchSlideDocuments() {
  const res = await fetch(`${BASE}/api/rag/documents`);
  return res.ok ? await res.json() : [];
}

export async function uploadSlideDeck(formData) {
  const res = await fetch(`${BASE}/api/rag/upload`, {
    method: 'POST',
    body: formData
  });
  return res.ok ? await res.json() : null;
}

export async function searchSlides(query, course = '') {
  const params = new URLSearchParams({ q: query });
  if (course) params.append('course', course);
  const res = await fetch(`${BASE}/api/rag/search?${params}`);
  return res.ok ? await res.json() : [];
}

export async function verifyClaimAgainstSlides(claim, noteId = null) {
  const res = await fetch(`${BASE}/api/rag/verify-claim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim, note_id: noteId })
  });
  return res.ok ? await res.json() : null;
}

// --- Academic Web Connectors (Tier 2) ---
export async function verifyClaimAcademic(claim) {
  const res = await fetch(`${BASE}/api/academic/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim })
  });
  return res.ok ? await res.json() : null;
}

// --- Stage 2 Heavy LLM Escalation (Tailscale Ollama / Cloud) ---
export async function escalateContradiction(claim, slideExcerpt, webEvidence = '') {
  const res = await fetch(`${BASE}/api/ai/escalate-contradiction`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim, slide_excerpt: slideExcerpt, web_evidence: webEvidence })
  });
  return res.ok ? await res.json() : null;
}

export async function synthesizeLectureNotes(content) {
  const res = await fetch(`${BASE}/api/ai/synthesize-lecture`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  });
  return res.ok ? await res.json() : null;
}

// --- Tailscale Peer-to-Peer Sync ---
export async function fetchPairInfo() {
  const res = await fetch(`${BASE}/api/sync/pair-info`);
  return res.ok ? await res.json() : null;
}

export async function fetchPeers() {
  const res = await fetch(`${BASE}/api/sync/peers`);
  return res.ok ? await res.json() : [];
}

export async function registerPeer(peerData) {
  const res = await fetch(`${BASE}/api/sync/peers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(peerData)
  });
  return res.ok ? await res.json() : null;
}

export async function fetchSettings() {
  const res = await fetch(`${BASE}/api/settings/`);
  return res.ok ? await res.json() : {};
}

export async function updateSetting(key, value) {
  const res = await fetch(`${BASE}/api/settings/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, value })
  });
  return res.ok ? await res.json() : null;
}

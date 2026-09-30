/**
 * Hybrid API Client with Offline-First Local Storage Fallback
 * Works 100% offline on Android phones, desktop, and tablets.
 * Seamlessly connects to backend or Tailscale llama.cpp server when available.
 */

import {
  getServerUrl,
  setServerUrl,
  getLocalLessons,
  saveLocalLesson,
  getLocalUnits,
  saveLocalUnit,
  getLocalNotes,
  getLocalNote,
  saveLocalNote,
  updateLocalNote,
  deleteLocalNote
} from './storage.js';

export { getServerUrl, setServerUrl };

function isStandaloneMobile() {
  if (typeof window === 'undefined') return false;
  // If user configured a custom server URL, we are not standalone
  if (getServerUrl()) return false;
  // Detect Tauri app environment
  if (window.__TAURI_INTERNALS__ || window.__TAURI__) return true;
  // Detect tauri localhost origins
  if (window.location.origin.includes('tauri.localhost') || window.location.protocol === 'tauri:') return true;
  return false;
}

function getBase() {
  const custom = getServerUrl();
  if (custom) return custom;
  // If running in standalone Tauri mobile without configured server, bypass network fetches immediately
  if (isStandaloneMobile()) {
    return null;
  }
  // If running in browser or desktop electron/pywebview on same origin
  if (typeof window !== 'undefined' && window.location.origin.startsWith('http')) {
    if (!window.location.origin.includes('tauri.localhost') && !window.location.origin.includes('localhost:5173')) {
      return '';
    }
  }
  return '';
}

async function safeFetch(url, options = {}, timeoutMs = 1500) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(id);
    return res;
  } catch (e) {
    clearTimeout(id);
    return null;
  }
}

// --- Lessons ---
export async function fetchLessons() {
  const base = getBase();
  if (base !== null) {
    const res = await safeFetch(`${base}/api/lessons/`);
    if (res && res.ok) {
      try {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) return data;
      } catch (_) {}
    }
  }
  return getLocalLessons();
}

export async function createLesson(name) {
  const base = getBase();
  if (base !== null) {
    const res = await safeFetch(`${base}/api/lessons/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    if (res && res.ok) {
      try { return await res.json(); } catch (_) {}
    }
  }
  return saveLocalLesson(name);
}

// --- Units ---
export async function fetchUnits(lessonId) {
  const base = getBase();
  if (base !== null) {
    const res = await safeFetch(`${base}/api/units/by-lesson/${lessonId}`);
    if (res && res.ok) {
      try {
        const data = await res.json();
        if (Array.isArray(data)) return data;
      } catch (_) {}
    }
  }
  return getLocalUnits(lessonId);
}

export async function createUnit(lessonId, name) {
  const base = getBase();
  if (base !== null) {
    const res = await safeFetch(`${base}/api/units/by-lesson/${lessonId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, lesson_id: lessonId })
    });
    if (res && res.ok) {
      try { return await res.json(); } catch (_) {}
    }
  }
  return saveLocalUnit(lessonId, name);
}

// --- Notes ---
export async function fetchNotes(unitId) {
  const base = getBase();
  if (base !== null) {
    const res = await safeFetch(`${base}/api/notes/by-unit/${unitId}`);
    if (res && res.ok) {
      try {
        const data = await res.json();
        if (Array.isArray(data)) return data;
      } catch (_) {}
    }
  }
  return getLocalNotes(unitId);
}

export async function fetchNote(noteId) {
  const base = getBase();
  if (base !== null) {
    const res = await safeFetch(`${base}/api/notes/${noteId}`);
    if (res && res.ok) {
      try { return await res.json(); } catch (_) {}
    }
  }
  return getLocalNote(noteId);
}

export async function createNote(unitId, { title, content }) {
  const base = getBase();
  if (base !== null) {
    const res = await safeFetch(`${base}/api/notes/by-unit/${unitId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ unit_id: unitId, title, content })
    });
    if (res && res.ok) {
      try { return await res.json(); } catch (_) {}
    }
  }
  return saveLocalNote(unitId, { title, content });
}

export async function updateNote(noteId, { title, content }) {
  const base = getBase();
  if (base !== null) {
    const res = await safeFetch(`${base}/api/notes/${noteId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content })
    });
    if (res && res.ok) {
      try { return await res.json(); } catch (_) {}
    }
  }
  return updateLocalNote(noteId, { title, content });
}

export async function deleteNote(noteId) {
  const base = getBase();
  if (base !== null) {
    const res = await safeFetch(`${base}/api/notes/${noteId}`, { method: 'DELETE' });
    if (res && res.status === 204) return true;
  }
  return deleteLocalNote(noteId);
}

// --- Health Check / Server Ping ---
export async function pingServer(serverUrl) {
  const target = (serverUrl || getBase()).replace(/\/+$/, '');
  if (!target) return { ok: false, error: 'No server URL configured' };
  const start = Date.now();
  const res = await safeFetch(`${target}/api/lessons/`, {}, 3000);
  const latency = Date.now() - start;
  if (res && (res.ok || res.status === 404)) {
    return { ok: true, latency };
  }
  return { ok: false, error: 'Cannot reach server' };
}

// --- GLiNER2.5-Decide / Jev System 1 Decision Engine ---
export async function evaluateDecide(context, schema = {}) {
  const base = getBase();
  const res = await safeFetch(`${base}/v1/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ context, schema })
  });
  return res && res.ok ? await res.json() : null;
}

// --- Course Slide RAG & Local Verification ---
export async function fetchSlideDocuments() {
  const base = getBase();
  const res = await safeFetch(`${base}/api/rag/documents`);
  return res && res.ok ? await res.json() : [];
}

export async function uploadSlideDeck(formData) {
  const base = getBase();
  const res = await safeFetch(`${base}/api/rag/upload`, {
    method: 'POST',
    body: formData
  });
  return res && res.ok ? await res.json() : null;
}

export async function searchSlides(query, course = '') {
  const base = getBase();
  const params = new URLSearchParams({ q: query });
  if (course) params.append('course', course);
  const res = await safeFetch(`${base}/api/rag/search?${params}`);
  return res && res.ok ? await res.json() : [];
}

export async function verifyClaimAgainstSlides(claim, noteId = null) {
  const base = getBase();
  const res = await safeFetch(`${base}/api/rag/verify-claim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim, note_id: noteId })
  });
  return res && res.ok ? await res.json() : null;
}

// --- Academic Web Connectors (Tier 2) ---
export async function verifyClaimAcademic(claim) {
  const base = getBase();
  const res = await safeFetch(`${base}/api/academic/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim })
  });
  return res && res.ok ? await res.json() : null;
}

// --- Stage 2 Heavy LLM Escalation (llama.cpp / Tailscale) ---
export async function escalateContradiction(claim, slideExcerpt, webEvidence = '') {
  const base = getBase();
  const res = await safeFetch(`${base}/api/ai/escalate-contradiction`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim, slide_excerpt: slideExcerpt, web_evidence: webEvidence })
  });
  return res && res.ok ? await res.json() : null;
}

export async function synthesizeLectureNotes(content) {
  const base = getBase();
  const res = await safeFetch(`${base}/api/ai/synthesize-lecture`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  });
  return res && res.ok ? await res.json() : null;
}

// --- Tailscale Peer-to-Peer Sync ---
export async function fetchPairInfo() {
  const base = getBase();
  const res = await safeFetch(`${base}/api/sync/pair-info`);
  return res && res.ok ? await res.json() : null;
}

export async function fetchPeers() {
  const base = getBase();
  const res = await safeFetch(`${base}/api/sync/peers`);
  return res && res.ok ? await res.json() : [];
}

export async function registerPeer(peerData) {
  const base = getBase();
  const res = await safeFetch(`${base}/api/sync/peers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(peerData)
  });
  return res && res.ok ? await res.json() : null;
}

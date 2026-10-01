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
  updateLocalLesson,
  deleteLocalLesson,
  getLocalUnits,
  getAllLocalUnits,
  saveLocalUnit,
  updateLocalUnit,
  deleteLocalUnit,
  getLocalNotes,
  getAllLocalNotes,
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

// --- Lessons (Courses) ---
export async function fetchLessons() {
  const base = getBase();
  if (base !== null) {
    const res = await safeFetch(`${base}/api/lessons/`);
    if (res && res.ok) {
      try {
        const data = await res.json();
        if (Array.isArray(data)) return data;
      } catch (_) {}
    }
  }
  return getLocalLessons();
}

export async function createLesson(name, icon = '📚', color = '#3b82f6') {
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
  return saveLocalLesson(name, icon, color);
}

export async function updateLesson(lessonId, data) {
  return updateLocalLesson(lessonId, data);
}

export async function deleteLesson(lessonId) {
  const base = getBase();
  if (base !== null) {
    await safeFetch(`${base}/api/lessons/${lessonId}`, { method: 'DELETE' });
  }
  return deleteLocalLesson(lessonId);
}

// --- Units (Folders / Chapters) ---
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

export async function fetchAllUnits() {
  return getAllLocalUnits();
}

export async function createUnit(lessonId, name, icon = '📁', color = '#10b981') {
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
  return saveLocalUnit(lessonId, name, icon, color);
}

export async function updateUnit(unitId, data) {
  return updateLocalUnit(unitId, data);
}

export async function deleteUnit(unitId) {
  return deleteLocalUnit(unitId);
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

export async function fetchAllNotes() {
  return getAllLocalNotes();
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

export async function createNote(unitId, { title, content, icon = '📝', color = '#3b82f6' }) {
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
  return saveLocalNote(unitId, { title, content, icon, color });
}

export async function updateNote(noteId, { title, content, icon, color, unit_id }) {
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
  return updateLocalNote(noteId, { title, content, icon, color, unit_id });
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

// --- Cluster & Nodes Management ---
export async function fetchClusterOverview() {
  const base = getBase();
  const res = await safeFetch(`${base}/api/nodes/cluster`);
  return res && res.ok ? await res.json() : null;
}

export async function updateSelfConfig(data) {
  const base = getBase();
  const res = await safeFetch(`${base}/api/nodes/self/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res && res.ok ? await res.json() : null;
}

export async function checkLocalLlamaCppHealth() {
  const base = getBase();
  const res = await safeFetch(`${base}/api/nodes/self/llamacpp-health`);
  return res && res.ok ? await res.json() : null;
}

export async function renamePeerNode(peerId, alias) {
  const base = getBase();
  const res = await safeFetch(`${base}/api/nodes/peers/${encodeURIComponent(peerId)}/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alias })
  });
  return res && res.ok ? await res.json() : null;
}

export async function triggerRemoteGliner(peerId, peerUrl) {
  const base = getBase();
  const res = await safeFetch(`${base}/api/nodes/peers/${encodeURIComponent(peerId)}/trigger-gliner`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ peer_url: peerUrl })
  });
  return res && res.ok ? await res.json() : null;
}

export async function selectActiveLlm(endpoint) {
  const base = getBase();
  const res = await safeFetch(`${base}/api/nodes/select-llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ endpoint })
  });
  return res && res.ok ? await res.json() : null;
}

// --- GLiNER Model Hub ---
export async function fetchGlinerStatus() {
  const base = getBase();
  const res = await safeFetch(`${base}/api/gliner/status`);
  return res && res.ok ? await res.json() : null;
}

export async function triggerGlinerDownload() {
  const base = getBase();
  const res = await safeFetch(`${base}/api/gliner/download`, { method: 'POST' });
  return res && res.ok ? await res.json() : null;
}

// --- Auto-Updater ---
export async function checkAppUpdates(platform = '') {
  const base = getBase();
  const query = platform ? `?platform=${encodeURIComponent(platform)}` : '';
  const res = await safeFetch(`${base}/api/updater/check${query}`, {}, 5000);
  return res && res.ok ? await res.json() : null;
}

export async function fetchAppVersion() {
  const base = getBase();
  const res = await safeFetch(`${base}/api/updater/version`);
  return res && res.ok ? await res.json() : null;
}

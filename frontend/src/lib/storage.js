/**
 * Offline-First Local Storage Engine for Notes Workstation
 * Provides instant, zero-latency local persistence on mobile & desktop.
 * Seamlessly stores Lessons, Units, and Notes in localStorage.
 */

const STORAGE_KEYS = {
  LESSONS: 'notes_offline_lessons',
  UNITS: 'notes_offline_units',
  NOTES: 'notes_offline_notes',
  SERVER_URL: 'notes_server_url',
  PAIRED_CONNECTION: 'notes_paired_connection',
  DEVICE_ID: 'notes_device_id'
};

// Clean slate: Zero sample or mock data
const DEFAULT_LESSONS = [];
const DEFAULT_UNITS = [];
const DEFAULT_NOTES = [];

// Automatically purge any previous sample courses, folders, and notes from localStorage
function purgeLegacySamples() {
  try {
    const sampleLessonIds = ['les-default-1', 'les-default-2'];
    const sampleUnitIds = ['unit-default-1', 'unit-default-2', 'unit-default-3'];
    const sampleNoteIds = ['note-default-1'];

    let lessons = JSON.parse(localStorage.getItem(STORAGE_KEYS.LESSONS) || '[]');
    let units = JSON.parse(localStorage.getItem(STORAGE_KEYS.UNITS) || '[]');
    let notes = JSON.parse(localStorage.getItem(STORAGE_KEYS.NOTES) || '[]');

    const hasSamples = lessons.some(l => sampleLessonIds.includes(l.id) || l.name === 'Biology 101' || l.name === 'Physics & Calculus' || l.name === 'General Studies') ||
      units.some(u => sampleUnitIds.includes(u.id) || u.name === 'Cellular Respiration' || u.name === 'Genetics & DNA' || u.name === 'Classical Mechanics') ||
      notes.some(n => sampleNoteIds.includes(n.id) || n.title === 'Cellular Respiration & ATP Synthesis');

    if (hasSamples) {
      lessons = lessons.filter(l => !sampleLessonIds.includes(l.id) && l.name !== 'Biology 101' && l.name !== 'Physics & Calculus' && l.name !== 'General Studies');
      units = units.filter(u => !sampleUnitIds.includes(u.id) && u.name !== 'Cellular Respiration' && u.name !== 'Genetics & DNA' && u.name !== 'Classical Mechanics');
      notes = notes.filter(n => !sampleNoteIds.includes(n.id) && n.title !== 'Cellular Respiration & ATP Synthesis');
      localStorage.setItem(STORAGE_KEYS.LESSONS, JSON.stringify(lessons));
      localStorage.setItem(STORAGE_KEYS.UNITS, JSON.stringify(units));
      localStorage.setItem(STORAGE_KEYS.NOTES, JSON.stringify(notes));
    }
  } catch (e) {
    console.warn('[Storage] purgeLegacySamples error:', e);
  }
}

// Purge on module load
purgeLegacySamples();

function getStored(key, defaultVal = []) {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) {
      localStorage.setItem(key, JSON.stringify(defaultVal));
      return defaultVal;
    }
    return JSON.parse(raw);
  } catch (e) {
    console.warn(`[Storage] Error reading ${key}:`, e);
    return defaultVal;
  }
}

function setStored(key, val) {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch (e) {
    console.error(`[Storage] Error writing ${key}:`, e);
  }
}

export function getServerUrl() {
  return localStorage.getItem(STORAGE_KEYS.SERVER_URL) || '';
}

export function setServerUrl(url) {
  const clean = (url || '').trim().replace(/\/+$/, '');
  localStorage.setItem(STORAGE_KEYS.SERVER_URL, clean);
  return clean;
}

export function getPairedConnection() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEYS.PAIRED_CONNECTION) || 'null'); }
  catch (_) { return null; }
}

export function getDeviceId() {
  let deviceId = localStorage.getItem(STORAGE_KEYS.DEVICE_ID);
  if (deviceId) return deviceId;

  const bytes = new Uint8Array(16);
  if (globalThis.crypto?.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256);
    }
  }
  deviceId = `device-${Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('')}`;
  localStorage.setItem(STORAGE_KEYS.DEVICE_ID, deviceId);
  return deviceId;
}

export function setPairedConnection(payload, activeUrl) {
  const endpoints = [payload?.lan_url, payload?.tailscale_url]
    .filter(url => typeof url === 'string' && /^https?:\/\//i.test(url))
    .map(url => url.replace(/\/+$/, ''));
  const connection = {
    name: payload?.name || payload?.device_name || 'Notes Workstation',
    endpoints: [...new Set(endpoints)],
    activeUrl: (activeUrl || endpoints[0] || '').replace(/\/+$/, ''),
    accessToken: payload?.access_token || ''
  };
  localStorage.setItem(STORAGE_KEYS.PAIRED_CONNECTION, JSON.stringify(connection));
  if (connection.activeUrl) setServerUrl(connection.activeUrl);
  return connection;
}

export function setActivePairedEndpoint(url) {
  const connection = getPairedConnection();
  if (!connection) return;
  connection.activeUrl = (url || '').replace(/\/+$/, '');
  localStorage.setItem(STORAGE_KEYS.PAIRED_CONNECTION, JSON.stringify(connection));
  setServerUrl(connection.activeUrl);
}

export function clearPairedConnection() {
  localStorage.removeItem(STORAGE_KEYS.PAIRED_CONNECTION);
  setServerUrl('');
}

// Lessons
// Lessons
export function getLocalLessons() {
  return getStored(STORAGE_KEYS.LESSONS, DEFAULT_LESSONS);
}

export function saveLocalLesson(name, icon = '📚', color = '#3b82f6') {
  const lessons = getLocalLessons();
  const newLesson = {
    id: `les-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    name: name.trim(),
    icon: icon || '📚',
    color: color || '#3b82f6'
  };
  lessons.push(newLesson);
  setStored(STORAGE_KEYS.LESSONS, lessons);
  return newLesson;
}

export function updateLocalLesson(lessonId, { name, icon, color }) {
  const lessons = getLocalLessons();
  const idx = lessons.findIndex(l => String(l.id) === String(lessonId));
  if (idx === -1) return null;
  lessons[idx] = {
    ...lessons[idx],
    name: name !== undefined ? name.trim() : lessons[idx].name,
    icon: icon !== undefined ? icon : lessons[idx].icon,
    color: color !== undefined ? color : lessons[idx].color
  };
  setStored(STORAGE_KEYS.LESSONS, lessons);
  return lessons[idx];
}

export function deleteLocalLesson(lessonId) {
  let lessons = getLocalLessons();
  lessons = lessons.filter(l => String(l.id) !== String(lessonId));
  setStored(STORAGE_KEYS.LESSONS, lessons);

  // Also cascade delete units in this lesson
  let units = getStored(STORAGE_KEYS.UNITS, DEFAULT_UNITS);
  const unitsToDelete = units.filter(u => String(u.lesson_id) === String(lessonId)).map(u => String(u.id));
  units = units.filter(u => String(u.lesson_id) !== String(lessonId));
  setStored(STORAGE_KEYS.UNITS, units);

  // Also cascade delete notes in those units
  let notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  notes = notes.filter(n => !unitsToDelete.includes(String(n.unit_id)));
  setStored(STORAGE_KEYS.NOTES, notes);
  return true;
}

// Units (Folders)
export function getLocalUnits(lessonId) {
  const units = getStored(STORAGE_KEYS.UNITS, DEFAULT_UNITS);
  if (!lessonId) return units;
  return units.filter(u => String(u.lesson_id) === String(lessonId));
}

export function getAllLocalUnits() {
  return getStored(STORAGE_KEYS.UNITS, DEFAULT_UNITS);
}

export function saveLocalUnit(lessonId, name, icon = '📁', color = '#10b981') {
  const units = getStored(STORAGE_KEYS.UNITS, DEFAULT_UNITS);
  const newUnit = {
    id: `unit-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    lesson_id: lessonId,
    name: name.trim(),
    icon: icon || '📁',
    color: color || '#10b981'
  };
  units.push(newUnit);
  setStored(STORAGE_KEYS.UNITS, units);
  return newUnit;
}

export function updateLocalUnit(unitId, { name, icon, color, lesson_id }) {
  const units = getStored(STORAGE_KEYS.UNITS, DEFAULT_UNITS);
  const idx = units.findIndex(u => String(u.id) === String(unitId));
  if (idx === -1) return null;
  units[idx] = {
    ...units[idx],
    name: name !== undefined ? name.trim() : units[idx].name,
    icon: icon !== undefined ? icon : units[idx].icon,
    color: color !== undefined ? color : units[idx].color,
    lesson_id: lesson_id !== undefined ? lesson_id : units[idx].lesson_id
  };
  setStored(STORAGE_KEYS.UNITS, units);
  return units[idx];
}

export function deleteLocalUnit(unitId) {
  let units = getStored(STORAGE_KEYS.UNITS, DEFAULT_UNITS);
  units = units.filter(u => String(u.id) !== String(unitId));
  setStored(STORAGE_KEYS.UNITS, units);

  // Cascade delete notes inside this unit
  let notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  notes = notes.filter(n => String(n.unit_id) !== String(unitId));
  setStored(STORAGE_KEYS.NOTES, notes);
  return true;
}

// Notes
export function getLocalNotes(unitId) {
  const notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  if (!unitId) return notes;
  return notes.filter(n => String(n.unit_id) === String(unitId));
}

export function getAllLocalNotes() {
  return getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
}

export function getLocalNote(noteId) {
  const notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  return notes.find(n => String(n.id) === String(noteId)) || null;
}

export function saveLocalNote(unitId, { title, content, icon = '📝', color = '#3b82f6' }) {
  const notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  const newNote = {
    id: `note-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    unit_id: unitId,
    title: (title || 'New Lecture Note').trim(),
    content: content || '# New Lecture Note\n\n',
    icon: icon || '📝',
    color: color || '#3b82f6',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
  notes.unshift(newNote);
  setStored(STORAGE_KEYS.NOTES, notes);
  return newNote;
}

export function updateLocalNote(noteId, { title, content, icon, color, unit_id }) {
  const notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  const idx = notes.findIndex(n => String(n.id) === String(noteId));
  if (idx === -1) return null;
  notes[idx] = {
    ...notes[idx],
    title: title !== undefined ? title : notes[idx].title,
    content: content !== undefined ? content : notes[idx].content,
    icon: icon !== undefined ? icon : notes[idx].icon,
    color: color !== undefined ? color : notes[idx].color,
    unit_id: unit_id !== undefined ? unit_id : notes[idx].unit_id,
    updated_at: new Date().toISOString()
  };
  setStored(STORAGE_KEYS.NOTES, notes);
  return notes[idx];
}

export function deleteLocalNote(noteId) {
  let notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  notes = notes.filter(n => String(n.id) !== String(noteId));
  setStored(STORAGE_KEYS.NOTES, notes);
  return true;
}

/**
 * Offline-First Local Storage Engine for Notes Workstation
 * Provides instant, zero-latency local persistence on mobile & desktop.
 * Seamlessly stores Lessons, Units, and Notes in localStorage.
 */

const STORAGE_KEYS = {
  LESSONS: 'notes_offline_lessons',
  UNITS: 'notes_offline_units',
  NOTES: 'notes_offline_notes',
  SERVER_URL: 'notes_server_url'
};

// Default initial data for brand new installations
const DEFAULT_LESSONS = [
  { id: 'les-default-1', name: 'Biology 101' },
  { id: 'les-default-2', name: 'Physics & Calculus' }
];

const DEFAULT_UNITS = [
  { id: 'unit-default-1', lesson_id: 'les-default-1', name: 'Cellular Respiration' },
  { id: 'unit-default-2', lesson_id: 'les-default-1', name: 'Genetics & DNA' },
  { id: 'unit-default-3', lesson_id: 'les-default-2', name: 'Classical Mechanics' }
];

const DEFAULT_NOTES = [
  {
    id: 'note-default-1',
    unit_id: 'unit-default-1',
    title: 'Cellular Respiration & ATP Synthesis',
    content: `# Cellular Respiration & ATP Synthesis

Cellular respiration is the biochemical process by which cells harvest chemical energy from glucose.

## Net Reaction
$$\\text{C}_6\\text{H}_{12}\\text{O}_6 + 6\\text{O}_2 \\longrightarrow 6\\text{CO}_2 + 6\\text{H}_2\\text{O} + 36\\text{-}38 \\text{ ATP}$$

- **Glycolysis** occurs in the cytosol (Net: 2 ATP, 2 NADH).
- **Citric Acid Cycle** occurs in the mitochondrial matrix.
- **Oxidative Phosphorylation** produces the bulk of ATP through the electron transport chain.
`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  }
];

function getStored(key, defaultVal) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
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

// Lessons
export function getLocalLessons() {
  return getStored(STORAGE_KEYS.LESSONS, DEFAULT_LESSONS);
}

export function saveLocalLesson(name) {
  const lessons = getLocalLessons();
  const newLesson = {
    id: `les-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    name: name.trim()
  };
  lessons.push(newLesson);
  setStored(STORAGE_KEYS.LESSONS, lessons);
  return newLesson;
}

// Units
export function getLocalUnits(lessonId) {
  const units = getStored(STORAGE_KEYS.UNITS, DEFAULT_UNITS);
  if (!lessonId) return units;
  return units.filter(u => String(u.lesson_id) === String(lessonId));
}

export function saveLocalUnit(lessonId, name) {
  const units = getStored(STORAGE_KEYS.UNITS, DEFAULT_UNITS);
  const newUnit = {
    id: `unit-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    lesson_id: lessonId,
    name: name.trim()
  };
  units.push(newUnit);
  setStored(STORAGE_KEYS.UNITS, units);
  return newUnit;
}

// Notes
export function getLocalNotes(unitId) {
  const notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  if (!unitId) return notes;
  return notes.filter(n => String(n.unit_id) === String(unitId));
}

export function getLocalNote(noteId) {
  const notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  return notes.find(n => String(n.id) === String(noteId)) || null;
}

export function saveLocalNote(unitId, { title, content }) {
  const notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  const newNote = {
    id: `note-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    unit_id: unitId,
    title: (title || 'New Lecture Note').trim(),
    content: content || '# New Lecture Note\n\n',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
  notes.unshift(newNote);
  setStored(STORAGE_KEYS.NOTES, notes);
  return newNote;
}

export function updateLocalNote(noteId, { title, content }) {
  const notes = getStored(STORAGE_KEYS.NOTES, DEFAULT_NOTES);
  const idx = notes.findIndex(n => String(n.id) === String(noteId));
  if (idx === -1) return null;
  notes[idx] = {
    ...notes[idx],
    title: title !== undefined ? title : notes[idx].title,
    content: content !== undefined ? content : notes[idx].content,
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

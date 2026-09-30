/**
 * Main JavaScript file for the Notes App.
 * This file handles all frontend logic, including API interactions,
 * UI rendering, event handling, and third-party library initializations.
 */
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const lessonsList = document.getElementById('lessons-list');
    const addLessonBtn = document.getElementById('add-lesson-btn');
    const unitsList = document.getElementById('units-list');
    const addUnitBtn = document.getElementById('add-unit-btn');
    const notesList = document.getElementById('notes-list');
    const addNoteBtn = document.getElementById('add-note-btn');
    const noteTitleInput = document.getElementById('note-title');
    const saveNoteBtn = document.getElementById('save-note-btn');
    const aiFormatBtn = document.getElementById('ai-format-btn');
    const searchBar = document.getElementById('search-bar');
    const searchResults = document.getElementById('search-results');
    const uploadImageBtn = document.getElementById('upload-image-btn');
    const imageUploadInput = document.getElementById('image-upload-input');
    const settingsBtn = document.getElementById('settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const closeBtn = document.querySelector('.close-btn');
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    const primaryColorInput = document.getElementById('primary-color');
    const llmApiKeyInput = document.getElementById('llm-api-key');
    const llmApiBaseInput = document.getElementById('llm-api-base');
    const llmModelInput = document.getElementById('llm-model');
    const embeddingsApiKeyInput = document.getElementById('embeddings-api-key');
    const embeddingsApiBaseInput = document.getElementById('embeddings-api-base');
    const embeddingsModelInput = document.getElementById('embeddings-model');

    // State variables
    let selectedLessonId = null;
    let selectedUnitId = null;
    let selectedNoteId = null;
    let debounceTimer;

    // --- Initializations ---
    tinymce.init({
        selector: '#note-editor',
        plugins: 'autolink lists link image charmap print preview hr anchor pagebreak',
        toolbar_mode: 'floating',
        height: 500,
    });

    Sortable.create(lessonsList, { animation: 150, onEnd: () => reorderLessons(Array.from(lessonsList.children).map(li => li.dataset.id)) });
    Sortable.create(unitsList, { animation: 150, onEnd: () => reorderUnits(Array.from(unitsList.children).map(li => li.dataset.id)) });

    // --- Settings ---
    async function loadSettings() {
        try {
            const response = await fetch('/api/settings/');
            if (!response.ok) throw new Error('Failed to load settings');
            const settings = await response.json();
            primaryColorInput.value = settings.primary_color || '#007bff';
            llmApiKeyInput.value = settings.llm_api_key || '';
            llmApiBaseInput.value = settings.llm_api_base || '';
            llmModelInput.value = settings.llm_model || '';
            embeddingsApiKeyInput.value = settings.embeddings_api_key || '';
            embeddingsApiBaseInput.value = settings.embeddings_api_base || '';
            embeddingsModelInput.value = settings.embeddings_model || '';
            document.documentElement.style.setProperty('--primary-color', primaryColorInput.value);
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    async function saveSettings() {
        const settings = [
            { key: 'primary_color', value: primaryColorInput.value },
            { key: 'llm_api_key', value: llmApiKeyInput.value },
            { key: 'llm_api_base', value: llmApiBaseInput.value },
            { key: 'llm_model', value: llmModelInput.value },
            { key: 'embeddings_api_key', value: embeddingsApiKeyInput.value },
            { key: 'embeddings_api_base', value: embeddingsApiBaseInput.value },
            { key: 'embeddings_model', value: embeddingsModelInput.value },
        ];
        try {
            for (const setting of settings) {
                await fetch('/api/settings/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(setting),
                });
            }
            alert('Settings saved successfully!');
            closeModal();
            loadSettings();
        } catch (error) {
            console.error('Error saving settings:', error);
            alert('Failed to save settings.');
        }
    }

    function openModal() { settingsModal.style.display = 'block'; }
    function closeModal() { settingsModal.style.display = 'none'; }

    // --- Data Fetching and Rendering ---
    async function fetchLessons() {
        try {
            const response = await fetch('/api/lessons/');
            if (!response.ok) throw new Error('Failed to fetch lessons');
            const lessons = await response.json();
            renderList(lessonsList, lessons, 'lesson');
        } catch (error) {
            console.error('Error fetching lessons:', error);
        }
    }

    async function fetchUnits(lessonId) {
        try {
            const response = await fetch(`/api/units/by-lesson/${lessonId}`);
            if (!response.ok) throw new Error('Failed to fetch units');
            const units = await response.json();
            renderList(unitsList, units, 'unit');
        } catch (error) {
            console.error('Error fetching units:', error);
        }
    }

    async function fetchNotes(unitId) {
        try {
            const response = await fetch(`/api/notes/by-unit/${unitId}`);
            if (!response.ok) throw new Error('Failed to fetch notes');
            const notes = await response.json();
            renderList(notesList, notes, 'note');
        } catch (error) {
            console.error('Error fetching notes:', error);
        }
    }

    function renderList(listElement, items, type) {
        listElement.innerHTML = '';
        items.forEach(item => {
            const li = document.createElement('li');
            li.dataset.id = item.id;
            li.dataset.type = type;

            const span = document.createElement('span');
            span.className = 'name';
            span.textContent = item.name || item.title;
            li.appendChild(span);

            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'edit-name';
            input.value = item.name || item.title;
            input.style.display = 'none';
            li.appendChild(input);

            listElement.appendChild(li);
        });
    }

    async function loadNote(noteId) {
        try {
            const response = await fetch(`/api/notes/${noteId}`);
            if (!response.ok) throw new Error('Failed to load note');
            const note = await response.json();
            noteTitleInput.value = note.title;
            tinymce.get('note-editor').setContent(note.content || '');
        } catch (error) {
            console.error('Error loading note:', error);
        }
    }

    // --- Search ---
    function debounce(func, delay) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(func, delay);
    }

    async function performSearch() {
        const query = searchBar.value;
        if (query.length < 2) {
            searchResults.innerHTML = '';
            searchResults.style.display = 'none';
            return;
        }
        try {
            const response = await fetch(`/api/ai/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Search failed');
            const results = await response.json();
            renderSearchResults(results);
        } catch (error) {
            console.error('Error performing search:', error);
        }
    }

    function renderSearchResults(results) {
        searchResults.innerHTML = '';
        searchResults.style.display = 'block';
        if (results.length === 0) {
            searchResults.innerHTML = '<div class="search-result-item">No results found.</div>';
        } else {
            results.forEach(result => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                item.dataset.noteId = result.note_id;
                item.innerHTML = `<strong>Note ID: ${result.note_id}</strong> (Similarity: ${(result.similarity * 100).toFixed(2)}%)<p>${result.phrase}</p>`;
                searchResults.appendChild(item);
            });
        }
    }

    // --- CRUD, Reordering, and AI Operations ---
    async function createLesson() {
        const lessonName = prompt('Enter lesson name:');
        if (!lessonName) return;
        await fetch('/api/lessons/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: lessonName }),
        });
        fetchLessons();
    }

    async function reorderLessons(lessonIds) {
        try {
            await fetch('/api/lessons/reorder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(lessonIds.map(id => parseInt(id, 10))),
            });
        } catch (error) {
            console.error('Error reordering lessons:', error);
            fetchLessons();
        }
    }

    async function createUnit() {
        if (!selectedLessonId) return alert('Select a lesson first.');
        const unitName = prompt('Enter unit name:');
        if (!unitName) return;
        await fetch(`/api/units/by-lesson/${selectedLessonId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: unitName, lesson_id: selectedLessonId }),
        });
        fetchUnits(selectedLessonId);
    }

    async function reorderUnits(unitIds) {
        try {
            await fetch('/api/units/reorder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(unitIds.map(id => parseInt(id, 10))),
            });
        } catch (error) {
            console.error('Error reordering units:', error);
            fetchUnits(selectedLessonId);
        }
    }

    async function createNote() {
        if (!selectedUnitId) return alert('Select a unit first.');
        const noteTitle = prompt('Enter note title:');
        if (!noteTitle) return;
        await fetch(`/api/notes/by-unit/${selectedUnitId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: noteTitle, unit_id: selectedUnitId }),
        });
        fetchNotes(selectedUnitId);
    }

    async function saveNote() {
        if (!selectedNoteId) return alert('Select a note first.');
        const title = noteTitleInput.value;
        const content = tinymce.get('note-editor').getContent();
        await fetch(`/api/notes/${selectedNoteId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content }),
        });
        fetchNotes(selectedUnitId);
    }

    async function formatNoteWithAI() {
        if (!selectedNoteId) return alert('Select a note first.');
        aiFormatBtn.disabled = true;
        aiFormatBtn.textContent = 'Formatting...';
        try {
            const response = await fetch(`/api/ai/format-note/${selectedNoteId}`, {
                method: 'POST',
            });
            if (!response.ok) throw new Error('Failed to format note');
            const data = await response.json();
            tinymce.get('note-editor').setContent(data.formatted_content);
        } catch (error) {
            console.error('Error formatting note:', error);
            alert('Failed to format note with AI.');
        } finally {
            aiFormatBtn.disabled = false;
            aiFormatBtn.textContent = 'AI Format';
        }
    }

    async function handleImageUpload() {
        if (!selectedNoteId) {
            alert('Please select a note to add the image to.');
            return;
        }
        imageUploadInput.click();
    }

    async function uploadImage(event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`/api/images/upload/${selectedNoteId}`, {
                method: 'POST',
                body: formData,
            });
            if (!response.ok) throw new Error('Image upload failed');
            const data = await response.json();

            tinymce.get('note-editor').execCommand('mceInsertContent', false, `<img src="${data.url}" alt="${file.name}" />`);
        } catch (error) {
            console.error('Error uploading image:', error);
            alert('Failed to upload image.');
        }
    }

    async function updateItemName(type, id, newName) {
        try {
            await fetch(`/api/${type}s/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newName }),
            });
        } catch (error) {
            console.error(`Error updating ${type} name:`, error);
        }
    }

    // --- Event Handlers ---
    function handleLessonClick(event) {
        if (event.target.tagName !== 'LI' || event.target.querySelector('input:visible')) return;
        selectedLessonId = event.target.dataset.id;
        document.querySelectorAll('#lessons-list .active').forEach(el => el.classList.remove('active'));
        event.target.classList.add('active');
        addUnitBtn.style.display = 'inline-block';
        addNoteBtn.style.display = 'none';
        unitsList.innerHTML = '';
        notesList.innerHTML = '';
        selectedUnitId = null;
        selectedNoteId = null;
        noteTitleInput.value = '';
        tinymce.get('note-editor').setContent('');
        fetchUnits(selectedLessonId);
    }

    function handleUnitClick(event) {
        if (event.target.tagName !== 'LI' || event.target.querySelector('input:visible')) return;
        selectedUnitId = event.target.dataset.id;
        document.querySelectorAll('#units-list .active').forEach(el => el.classList.remove('active'));
        event.target.classList.add('active');
        addNoteBtn.style.display = 'inline-block';
        notesList.innerHTML = '';
        selectedNoteId = null;
        noteTitleInput.value = '';
        tinymce.get('note-editor').setContent('');
        fetchNotes(selectedUnitId);
    }

    function handleNoteClick(event) {
        if (event.target.tagName !== 'LI' || event.target.querySelector('input:visible')) return;
        selectedNoteId = event.target.dataset.id;
        document.querySelectorAll('#notes-list .active').forEach(el => el.classList.remove('active'));
        event.target.classList.add('active');
        loadNote(selectedNoteId);
    }

    function handleSearchResultClick(event) {
        const item = event.target.closest('.search-result-item');
        if (item) {
            const noteId = item.dataset.noteId;
            loadNote(noteId);
            selectedNoteId = noteId;
            searchResults.innerHTML = '';
            searchResults.style.display = 'none';
            searchBar.value = '';
        }
    }

    function handleDoubleClick(event) {
        const li = event.target.closest('li');
        if (!li) return;

        const span = li.querySelector('.name');
        const input = li.querySelector('.edit-name');
        span.style.display = 'none';
        input.style.display = 'block';
        input.focus();

        const saveEdit = async () => {
            const newName = input.value;
            const id = li.dataset.id;
            const type = li.dataset.type;

            span.textContent = newName;
            input.style.display = 'none';
            span.style.display = 'block';

            await updateItemName(type, id, newName);
        };

        input.addEventListener('blur', saveEdit, { once: true });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                input.blur();
            }
        });
    }

    // --- Event Listeners ---
    lessonsList.addEventListener('click', handleLessonClick);
    lessonsList.addEventListener('dblclick', handleDoubleClick);
    addLessonBtn.addEventListener('click', createLesson);
    unitsList.addEventListener('click', handleUnitClick);
    unitsList.addEventListener('dblclick', handleDoubleClick);
    addUnitBtn.addEventListener('click', createUnit);
    notesList.addEventListener('click', handleNoteClick);
    addNoteBtn.addEventListener('click', createNote);
    saveNoteBtn.addEventListener('click', saveNote);
    aiFormatBtn.addEventListener('click', formatNoteWithAI);
    searchBar.addEventListener('input', () => debounce(performSearch, 300));
    searchResults.addEventListener('click', handleSearchResultClick);
    uploadImageBtn.addEventListener('click', handleImageUpload);
    imageUploadInput.addEventListener('change', uploadImage);
    settingsBtn.addEventListener('click', openModal);
    closeBtn.addEventListener('click', closeModal);
    saveSettingsBtn.addEventListener('click', saveSettings);
    window.addEventListener('click', (e) => { if (e.target == settingsModal) closeModal(); });

    // --- Initial Load ---
    fetchLessons();
    loadSettings();
});

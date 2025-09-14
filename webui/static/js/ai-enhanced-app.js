// AI-Enhanced Notes App with Semantic Search and Editing

class AIEnhancedNotesApp extends EnhancedNotesApp {
    constructor() {
        super();
        this.searchTimeout = null;
        this.searchCache = new Map();
        this.editMode = {
            lessons: false,
            units: false
        };
        this.sortableInstances = {
            lessons: null,
            units: null
        };
        this.currentSearchResults = [];
    }

    async init() {
        await super.init();
        
        // Initialize AI-specific features
        this.initSearchFunctionality();
        this.initEditingFunctionality();
        this.initAIFeatures();
        this.initDragAndDrop();
    }

    // Search Functionality
    initSearchFunctionality() {
        const searchInput = document.getElementById('search-input');
        const searchResults = document.getElementById('search-results');
        const searchLoading = document.getElementById('search-loading');

        if (!searchInput) return;

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            this.handleSearch(query);
        });

        searchInput.addEventListener('focus', () => {
            if (this.currentSearchResults.length > 0) {
                searchResults.classList.remove('hidden');
            }
        });

        searchInput.addEventListener('blur', (e) => {
            // Delay hiding to allow clicking on results
            setTimeout(() => {
                if (!e.relatedTarget || !searchResults.contains(e.relatedTarget)) {
                    searchResults.classList.add('hidden');
                }
            }, 200);
        });

        // Click outside to close
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.classList.add('hidden');
            }
        });
    }

    handleSearch(query) {
        const searchResults = document.getElementById('search-results');
        const searchLoading = document.getElementById('search-loading');

        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        // Hide results if query is empty
        if (!query) {
            searchResults.classList.add('hidden');
            this.currentSearchResults = [];
            return;
        }

        // Check cache first
        if (this.searchCache.has(query)) {
            this.displaySearchResults(this.searchCache.get(query));
            return;
        }

        // Show loading
        searchLoading.classList.remove('hidden');

        // Debounce search
        this.searchTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/api/ai/search?q=${encodeURIComponent(query)}&limit=${this.settings.max_search_results || 10}`);
                const result = await response.json();

                searchLoading.classList.add('hidden');

                if (result.success) {
                    this.searchCache.set(query, result.data.results);
                    this.displaySearchResults(result.data.results);
                } else {
                    console.error('Search failed:', result.error);
                    this.displaySearchResults([]);
                }
            } catch (error) {
                searchLoading.classList.add('hidden');
                console.error('Search error:', error);
                this.displaySearchResults([]);
            }
        }, 300); // Wait 300ms after user stops typing
    }

    displaySearchResults(results) {
        const searchResults = document.getElementById('search-results');
        this.currentSearchResults = results;

        if (results.length === 0) {
            searchResults.innerHTML = '<div class="p-4 text-text-muted text-center">No results found</div>';
        } else {
            searchResults.innerHTML = results.map(result => `
                <div class="p-3 hover:bg-accent-light cursor-pointer border-b border-border-subtle transition-colors search-result-item" data-note-id="${result.id}">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <div class="font-medium text-sm">${this.escapeHtml(result.title)}</div>
                            <div class="text-xs text-text-muted mt-1">${this.escapeHtml(result.highlight)}</div>
                            <div class="flex items-center gap-2 mt-2 text-xs text-text-muted">
                                <span class="px-2 py-1 bg-accent-light rounded">${result.type}</span>
                                <span>Similarity: ${Math.round(result.similarity * 100)}%</span>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');

            // Add click handlers
            searchResults.querySelectorAll('.search-result-item').forEach(item => {
                item.addEventListener('click', () => {
                    const noteId = item.dataset.noteId;
                    this.openNoteFromSearch(noteId);
                    searchResults.classList.add('hidden');
                    document.getElementById('search-input').blur();
                });
            });
        }

        searchResults.classList.remove('hidden');
    }

    async openNoteFromSearch(noteId) {
        try {
            // First, find which lesson and unit this note belongs to
            const response = await fetch(`/api/notes/${noteId}`);
            if (response.ok) {
                const result = await response.json();
                const note = result.data;
                
                // Switch to the correct lesson and unit
                this.currentLessonId = note.lesson_id;
                this.currentUnitId = note.unit_id;
                
                // Refresh the UI
                await this.renderLessons();
                await this.renderUnits();
                await this.renderNotes();
                
                // Open the note in editor
                this.openEditNoteEditor(note);
            }
        } catch (error) {
            console.error('Failed to open note from search:', error);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Editing Functionality
    initEditingFunctionality() {
        const toggleLessonEdit = document.getElementById('toggle-lesson-edit');
        const toggleUnitEdit = document.getElementById('toggle-unit-edit');

        if (toggleLessonEdit) {
            toggleLessonEdit.addEventListener('click', () => {
                this.toggleEditMode('lessons');
            });
        }

        if (toggleUnitEdit) {
            toggleUnitEdit.addEventListener('click', () => {
                this.toggleEditMode('units');
            });
        }
    }

    toggleEditMode(type) {
        this.editMode[type] = !this.editMode[type];
        
        const button = document.getElementById(`toggle-${type.slice(0, -1)}-edit`);
        const list = document.getElementById(`${type}-list`);
        
        if (this.editMode[type]) {
            button.innerHTML = '<i class="fas fa-check text-green-500"></i>';
            button.title = `Finish editing ${type}`;
            list.classList.add('edit-mode');
            this.enableSorting(type);
            this.showEditableItems(type);
        } else {
            button.innerHTML = '<i class="fas fa-pencil-alt"></i>';
            button.title = `Edit ${type}`;
            list.classList.remove('edit-mode');
            this.disableSorting(type);
            this.hideEditableItems(type);
        }
    }

    enableSorting(type) {
        const listElement = document.getElementById(`${type}-list`);
        if (!listElement) return;

        this.sortableInstances[type] = new Sortable(listElement, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            onEnd: (evt) => {
                this.handleReorder(type, evt);
            }
        });
    }

    disableSorting(type) {
        if (this.sortableInstances[type]) {
            this.sortableInstances[type].destroy();
            this.sortableInstances[type] = null;
        }
    }

    async handleReorder(type, evt) {
        try {
            const items = Array.from(document.getElementById(`${type}-list`).children);
            const reorderData = items.map((item, index) => ({
                id: parseInt(item.dataset.id),
                display_order: index + 1
            }));

            const endpoint = type === 'lessons' 
                ? '/api/lessons/reorder'
                : `/api/lessons/${this.currentLessonId}/units/reorder`;

            const payload = type === 'lessons'
                ? { lesson_orders: reorderData }
                : { unit_orders: reorderData };

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error('Reorder failed');
            }

            this.showNotification(`${type} reordered successfully`, 'success');
        } catch (error) {
            console.error('Reorder failed:', error);
            this.showNotification(`Failed to reorder ${type}`, 'error');
        }
    }

    showEditableItems(type) {
        const items = document.querySelectorAll(`#${type}-list .sidebar-item`);
        items.forEach(item => {
            if (!item.querySelector('.edit-controls')) {
                const controls = this.createEditControls(type, item);
                item.appendChild(controls);
            }
        });
    }

    hideEditableItems(type) {
        const controls = document.querySelectorAll(`#${type}-list .edit-controls`);
        controls.forEach(control => control.remove());
    }

    createEditControls(type, item) {
        const controls = document.createElement('div');
        controls.className = 'edit-controls flex gap-1 ml-auto';
        
        const editBtn = document.createElement('button');
        editBtn.innerHTML = '<i class="fas fa-edit text-xs"></i>';
        editBtn.className = 'text-text-muted hover:text-accent transition-colors p-1';
        editBtn.onclick = (e) => {
            e.stopPropagation();
            this.editItem(type, item.dataset.id, item.querySelector('span').textContent);
        };

        const deleteBtn = document.createElement('button');
        deleteBtn.innerHTML = '<i class="fas fa-trash text-xs"></i>';
        deleteBtn.className = 'text-red-500 hover:text-red-700 transition-colors p-1';
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            this.deleteItem(type, item.dataset.id, item.querySelector('span').textContent);
        };

        controls.appendChild(editBtn);
        controls.appendChild(deleteBtn);
        
        return controls;
    }

    async editItem(type, id, currentName) {
        const newName = prompt(`Edit ${type.slice(0, -1)} name:`, currentName);
        if (!newName || newName === currentName) return;

        try {
            const endpoint = type === 'lessons' 
                ? `/api/lessons/${id}`
                : `/api/units/${id}`;

            const response = await fetch(endpoint, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newName })
            });

            if (response.ok) {
                this.showNotification(`${type.slice(0, -1)} updated successfully`, 'success');
                if (type === 'lessons') {
                    this.renderLessons();
                } else {
                    this.renderUnits();
                }
            } else {
                throw new Error('Update failed');
            }
        } catch (error) {
            console.error('Edit failed:', error);
            this.showNotification(`Failed to update ${type.slice(0, -1)}`, 'error');
        }
    }

    async deleteItem(type, id, name) {
        if (!confirm(`Delete ${type.slice(0, -1)} "${name}"? This will also delete all associated content.`)) {
            return;
        }

        try {
            const endpoint = type === 'lessons' 
                ? `/api/lessons/${id}`
                : `/api/units/${id}`;

            const response = await fetch(endpoint, { method: 'DELETE' });

            if (response.ok) {
                this.showNotification(`${type.slice(0, -1)} deleted successfully`, 'success');
                if (type === 'lessons') {
                    this.renderLessons();
                    this.renderUnits();
                } else {
                    this.renderUnits();
                }
                this.renderNotes();
            } else {
                throw new Error('Delete failed');
            }
        } catch (error) {
            console.error('Delete failed:', error);
            this.showNotification(`Failed to delete ${type.slice(0, -1)}`, 'error');
        }
    }

    // AI Features
    initAIFeatures() {
        const aiFormatBtn = document.getElementById('ai-format-btn');
        const testAIConnection = document.getElementById('test-ai-connection');
        const batchEmbedNotes = document.getElementById('batch-embed-notes');

        if (aiFormatBtn) {
            aiFormatBtn.addEventListener('click', () => {
                this.formatNoteWithAI();
            });
        }

        if (testAIConnection) {
            testAIConnection.addEventListener('click', () => {
                this.testAIConnection();
            });
        }

        if (batchEmbedNotes) {
            batchEmbedNotes.addEventListener('click', () => {
                this.batchGenerateEmbeddings();
            });
        }

        // Add AI settings form handlers
        this.initAISettingsHandlers();
    }

    initAISettingsHandlers() {
        const maxSearchResults = document.getElementById('max-search-results');
        if (maxSearchResults) {
            maxSearchResults.addEventListener('input', (e) => {
                document.getElementById('max-search-results-display').textContent = e.target.value;
            });
        }

        // Auto-fetch models when base URL changes
        const baseUrlInput = document.getElementById('ai-base-url');
        const apiKeyInput = document.getElementById('ai-api-key');
        
        if (baseUrlInput && apiKeyInput) {
            const updateModels = async () => {
                const baseUrl = baseUrlInput.value;
                const apiKey = apiKeyInput.value;
                
                if (baseUrl && apiKey) {
                    try {
                        const response = await fetch('/api/ai/test-connection', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ base_url: baseUrl, api_key: apiKey })
                        });
                        
                        const result = await response.json();
                        if (result.success && result.data.models) {
                            this.updateModelOptions(result.data.models, result.data.embedding_models);
                        }
                    } catch (error) {
                        console.error('Failed to fetch models:', error);
                    }
                }
            };
            
            baseUrlInput.addEventListener('blur', updateModels);
            apiKeyInput.addEventListener('blur', updateModels);
        }
    }

    updateModelOptions(models, embeddingModels) {
        const chatModelSelect = document.getElementById('ai-model');
        const embeddingModelSelect = document.getElementById('ai-embedding-model');
        
        if (chatModelSelect && models.length > 0) {
            const currentValue = chatModelSelect.value;
            chatModelSelect.innerHTML = '';
            
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                chatModelSelect.appendChild(option);
            });
            
            // Restore previous value if still available
            if (models.includes(currentValue)) {
                chatModelSelect.value = currentValue;
            }
        }
        
        if (embeddingModelSelect && embeddingModels.length > 0) {
            const currentValue = embeddingModelSelect.value;
            embeddingModelSelect.innerHTML = '';
            
            embeddingModels.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                embeddingModelSelect.appendChild(option);
            });
            
            // Restore previous value if still available
            if (embeddingModels.includes(currentValue)) {
                embeddingModelSelect.value = currentValue;
            }
        }
    }

    async formatNoteWithAI() {
        if (!this.currentNoteId) {
            this.showNotification('Please select a note to format', 'warning');
            return;
        }

        const aiFormatBtn = document.getElementById('ai-format-btn');
        const originalText = aiFormatBtn.innerHTML;
        
        aiFormatBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Formatting...';
        aiFormatBtn.disabled = true;

        try {
            const response = await fetch(`/api/ai/format-note/${this.currentNoteId}`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Update editor with formatted content
                if (this.editor) {
                    this.editor.setContent(result.data.formatted_content);
                }
                this.showNotification('Note formatted successfully!', 'success');
                
                // Generate embeddings for the formatted note
                this.generateEmbeddings(this.currentNoteId);
            } else {
                this.showNotification(result.error || 'Formatting failed', 'error');
            }
        } catch (error) {
            console.error('AI formatting failed:', error);
            this.showNotification('AI formatting failed', 'error');
        } finally {
            aiFormatBtn.innerHTML = originalText;
            aiFormatBtn.disabled = false;
        }
    }

    async testAIConnection() {
        const baseUrl = document.getElementById('ai-base-url').value;
        const apiKey = document.getElementById('ai-api-key').value;
        const testBtn = document.getElementById('test-ai-connection');
        
        if (!baseUrl || !apiKey) {
            this.showNotification('Please enter both base URL and API key', 'warning');
            return;
        }

        const originalText = testBtn.innerHTML;
        testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        testBtn.disabled = true;

        try {
            const response = await fetch('/api/ai/test-connection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ base_url: baseUrl, api_key: apiKey })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('AI connection successful!', 'success');
                if (result.data.models) {
                    this.updateModelOptions(result.data.models, result.data.embedding_models);
                }
            } else {
                this.showNotification(result.error || 'Connection test failed', 'error');
            }
        } catch (error) {
            console.error('Connection test failed:', error);
            this.showNotification('Connection test failed', 'error');
        } finally {
            testBtn.innerHTML = originalText;
            testBtn.disabled = false;
        }
    }

    async batchGenerateEmbeddings() {
        const batchBtn = document.getElementById('batch-embed-notes');
        const originalText = batchBtn.innerHTML;
        
        if (!confirm('This will generate embeddings for all notes. This process may take several minutes and consume API credits. Continue?')) {
            return;
        }

        batchBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
        batchBtn.disabled = true;

        try {
            const response = await fetch('/api/ai/batch-embed', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                const { total_notes, processed, failed } = result.data;
                this.showNotification(`Embeddings generated! Processed: ${processed}, Failed: ${failed}, Total: ${total_notes}`, 'success');
            } else {
                this.showNotification(result.error || 'Batch embedding failed', 'error');
            }
        } catch (error) {
            console.error('Batch embedding failed:', error);
            this.showNotification('Batch embedding failed', 'error');
        } finally {
            batchBtn.innerHTML = originalText;
            batchBtn.disabled = false;
        }
    }

    async generateEmbeddings(noteId) {
        try {
            const response = await fetch(`/api/ai/embed-note/${noteId}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                console.log('Embeddings generated for note:', noteId);
            }
        } catch (error) {
            console.error('Failed to generate embeddings:', error);
        }
    }

    // Drag and Drop Initialization
    initDragAndDrop() {
        // Add CSS for drag and drop visual feedback
        const style = document.createElement('style');
        style.textContent = `
            .sortable-ghost {
                opacity: 0.4;
                background: var(--color-accent-light);
            }
            .sortable-chosen {
                cursor: grabbing;
            }
            .edit-mode {
                background: rgba(var(--color-accent), 0.05);
                border-radius: 8px;
                padding: 4px;
            }
            .edit-mode .sidebar-item {
                cursor: grab;
                background: var(--color-background-secondary);
                border: 1px solid var(--color-border-subtle);
                border-radius: 6px;
                margin: 2px 0;
            }
            .edit-mode .sidebar-item:hover {
                border-color: var(--color-accent);
            }
        `;
        document.head.appendChild(style);
    }

    // Override settings collection to include AI settings
    collectSettingsFromUI() {
        super.collectSettingsFromUI();
        
        // AI settings
        this.settings.ai_enabled = document.getElementById('ai-enabled')?.checked || false;
        this.settings.ai_base_url = document.getElementById('ai-base-url')?.value || 'https://api.openai.com/v1';
        this.settings.ai_api_key = document.getElementById('ai-api-key')?.value || '';
        this.settings.ai_model = document.getElementById('ai-model')?.value || 'gpt-3.5-turbo';
        this.settings.ai_embedding_model = document.getElementById('ai-embedding-model')?.value || 'text-embedding-ada-002';
        this.settings.ai_auto_format = document.getElementById('ai-auto-format')?.checked || false;
        this.settings.search_enabled = document.getElementById('search-enabled')?.checked || true;
        this.settings.max_search_results = parseInt(document.getElementById('max-search-results')?.value || 10);
    }

    // Override settings population to include AI settings
    populateSettingsForm() {
        super.populateSettingsForm();
        
        // AI settings
        if (document.getElementById('ai-enabled')) {
            document.getElementById('ai-enabled').checked = this.settings.ai_enabled || false;
        }
        if (document.getElementById('ai-base-url')) {
            document.getElementById('ai-base-url').value = this.settings.ai_base_url || 'https://api.openai.com/v1';
        }
        if (document.getElementById('ai-api-key') && this.settings.ai_api_key && this.settings.ai_api_key !== '***') {
            document.getElementById('ai-api-key').value = this.settings.ai_api_key;
        }
        if (document.getElementById('ai-model')) {
            document.getElementById('ai-model').value = this.settings.ai_model || 'gpt-3.5-turbo';
        }
        if (document.getElementById('ai-embedding-model')) {
            document.getElementById('ai-embedding-model').value = this.settings.ai_embedding_model || 'text-embedding-ada-002';
        }
        if (document.getElementById('ai-auto-format')) {
            document.getElementById('ai-auto-format').checked = this.settings.ai_auto_format || false;
        }
        if (document.getElementById('search-enabled')) {
            document.getElementById('search-enabled').checked = this.settings.search_enabled !== false;
        }
        if (document.getElementById('max-search-results')) {
            document.getElementById('max-search-results').value = this.settings.max_search_results || 10;
            document.getElementById('max-search-results-display').textContent = this.settings.max_search_results || 10;
        }
    }

    // Override settings tab switching to include AI tab
    switchSettingsTab(tabName) {
        super.switchSettingsTab(tabName);
        
        // Update title for AI tab
        const titles = {
            appearance: 'Appearance Settings',
            editor: 'Editor Settings',
            content: 'Content Settings',
            advanced: 'Advanced Settings',
            ai: 'AI Features Settings'
        };
        
        if (titles[tabName]) {
            document.getElementById('settings-tab-title').textContent = titles[tabName];
        }
    }

    // Enhanced note saving with auto-embedding
    async saveNoteFromEditor() {
        const result = await super.saveNoteFromEditor();
        
        // Auto-generate embeddings after saving if AI is enabled
        if (this.currentNoteId && this.settings.ai_enabled) {
            this.generateEmbeddings(this.currentNoteId);
        }
        
        return result;
    }

    // Enhanced lesson and unit rendering with edit capabilities
    async renderLessons() {
        try {
            const response = await fetch('/api/lessons');
            const result = await response.json();
            
            if (result.success) {
                const lessonsList = document.getElementById('lessons-list');
                lessonsList.innerHTML = '';
                
                result.data.lessons.forEach(lesson => {
                    const lessonItem = document.createElement('li');
                    lessonItem.className = 'sidebar-item flex items-center gap-3 py-2 px-3 rounded-lg cursor-pointer transition-colors hover:bg-accent-light hover:text-accent';
                    lessonItem.dataset.id = lesson.id;
                    
                    if (this.currentLessonId === lesson.id) {
                        lessonItem.classList.add('bg-accent-light', 'font-medium');
                    }
                    
                    lessonItem.innerHTML = `
                        <i class="fas fa-folder text-text-muted"></i>
                        <span class="flex-1">${lesson.title}</span>
                    `;
                    
                    lessonItem.addEventListener('click', () => {
                        if (!this.editMode.lessons) {
                            this.selectLesson(lesson.id);
                        }
                    });
                    
                    lessonsList.appendChild(lessonItem);
                });

                // Re-enable sorting if in edit mode
                if (this.editMode.lessons) {
                    this.enableSorting('lessons');
                    this.showEditableItems('lessons');
                }
            }
        } catch (error) {
            console.error('Failed to render lessons:', error);
        }
    }

    async renderUnits() {
        try {
            const response = await fetch(`/api/lessons/${this.currentLessonId}/units`);
            const result = await response.json();
            
            if (result.success) {
                const unitsList = document.getElementById('units-list');
                unitsList.innerHTML = '';
                
                result.data.units.forEach(unit => {
                    const unitItem = document.createElement('li');
                    unitItem.className = 'sidebar-item flex items-center gap-3 py-2 px-3 rounded-lg cursor-pointer transition-colors hover:bg-accent-light hover:text-accent';
                    unitItem.dataset.id = unit.id;
                    
                    if (this.currentUnitId === unit.id) {
                        unitItem.classList.add('bg-accent-light', 'font-medium');
                    }
                    
                    unitItem.innerHTML = `
                        <i class="fas fa-book text-text-muted"></i>
                        <span class="flex-1">${unit.title}</span>
                    `;
                    
                    unitItem.addEventListener('click', () => {
                        if (!this.editMode.units) {
                            this.selectUnit(unit.id);
                        }
                    });
                    
                    unitsList.appendChild(unitItem);
                });

                // Re-enable sorting if in edit mode
                if (this.editMode.units) {
                    this.enableSorting('units');
                    this.showEditableItems('units');
                }
            }
        } catch (error) {
            console.error('Failed to render units:', error);
        }
    }

    selectLesson(lessonId) {
        // Remove active class from all lessons
        document.querySelectorAll('#lessons-list .sidebar-item').forEach(item => {
            item.classList.remove('bg-accent-light', 'font-medium');
        });
        
        // Add active class to selected lesson
        document.querySelector(`#lessons-list .sidebar-item[data-id="${lessonId}"]`).classList.add('bg-accent-light', 'font-medium');
        
        this.currentLessonId = lessonId;
        
        // Auto-select the first unit
        this.renderUnits().then(() => {
            const firstUnit = document.querySelector('#units-list .sidebar-item');
            if (firstUnit) {
                this.currentUnitId = parseInt(firstUnit.dataset.id);
                this.selectUnit(this.currentUnitId);
            }
        });
        
        this.selectedNotes = [];
        this.updateActionButtons();
    }

    selectUnit(unitId) {
        // Remove active class from all units
        document.querySelectorAll('#units-list .sidebar-item').forEach(item => {
            item.classList.remove('bg-accent-light', 'font-medium');
        });
        
        // Add active class to selected unit
        document.querySelector(`#units-list .sidebar-item[data-id="${unitId}"]`).classList.add('bg-accent-light', 'font-medium');
        
        this.currentUnitId = unitId;
        this.renderNotes();
        this.updateCurrentUnitTitle();
    }
}

// Initialize the AI-enhanced app
let aiApp;
document.addEventListener('DOMContentLoaded', () => {
    aiApp = new AIEnhancedNotesApp();
});

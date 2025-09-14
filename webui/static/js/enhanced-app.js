// Enhanced Notes App with Rich Text Editor and Advanced Features

class EnhancedNotesApp {
    constructor() {
        this.currentLessonId = 1;
        this.currentUnitId = 1;
        this.currentNoteId = null;
        this.selectedNotes = [];
        this.settings = {};
        this.editor = null;
        this.colorPicker = null;
        this.noteColorPicker = null;
        this.autoSaveInterval = null;
        
        this.init();
    }
    
    async init() {
        // Load settings first
        await this.loadSettings();
        
        // Initialize UI components
        this.initEditor();
        this.initColorPickers();
        this.initEventListeners();
        this.applySettings();
        
        // Load initial data
        this.renderLessons();
        this.renderUnits();
        this.renderNotes();
    }
    
    // Settings Management
    async loadSettings() {
        try {
            const response = await fetch('/api/settings');
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    this.settings = result.data;
                } else {
                    console.warn('Invalid settings response, using defaults');
                    this.settings = this.getDefaultSettings();
                }
            } else {
                console.warn('Settings API not available, using defaults. Status:', response.status);
                this.settings = this.getDefaultSettings();
            }
        } catch (error) {
            console.warn('Failed to load settings from API, using defaults:', error.message);
            this.settings = this.getDefaultSettings();
        }
    }
    
    getDefaultSettings() {
        return {
            primary_color: '#4299e1',
            color_palette: null,
            dark_mode: false,
            editor_font_family: 'Inter, system-ui, sans-serif',
            editor_font_size: 16,
            editor_line_height: '1.6',
            auto_save_interval: 30,
            spell_check: true,
            auto_detect_titles: true,
            auto_generate_schema: true,
            default_note_color: '#f7fafc',
            export_format: 'markdown',
            image_quality: 'medium',
            max_image_size: 5
        };
    }
    
    async saveSettings() {
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.settings)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.settings = result.data;
                this.applySettings();
                this.showNotification('Settings saved successfully', 'success');
            } else {
                throw new Error('Failed to save settings');
            }
        } catch (error) {
            console.error('Failed to save settings:', error);
            this.showNotification('Failed to save settings', 'error');
        }
    }
    
    applySettings() {
        // Apply theme
        document.body.classList.toggle('dark', this.settings.dark_mode);

        // Apply color palette
        if (this.settings.color_palette) {
            this.applyColorPalette(this.settings.color_palette);
        }

        // Apply editor settings
        if (this.editor && this.editor.getDoc()) {
            const editorDoc = this.editor.getDoc();
            if (editorDoc.body) {
                editorDoc.body.style.fontFamily = this.settings.editor_font_family;
                editorDoc.body.style.fontSize = this.settings.editor_font_size + 'px';
                editorDoc.body.style.lineHeight = this.settings.editor_line_height;
            }
        }

        // Setup auto-save
        this.setupAutoSave();
    }
    
    applyColorPalette(palette) {
        const root = document.documentElement;
        root.style.setProperty('--color-accent', palette.primary);
        root.style.setProperty('--color-accent-light', palette.light);
        root.style.setProperty('--color-text-primary', palette.dark);
        // Add more color mappings as needed
    }
    
    // Rich Text Editor
    initEditor() {
        // Set base URL for self-hosted TinyMCE
        tinymce.baseURL = '/static/js/tinymce';
        
        tinymce.init({
            selector: '#editor-content',
            height: '100%',
            menubar: false,
            branding: false, // Remove TinyMCE branding for self-hosted version
            license_key: 'gpl', // Use GPL license for self-hosted version
            external_plugins: {}, // Disable external plugins that may not be available
            plugins: [
                'advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview',
                'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                'insertdatetime', 'media', 'table', 'help', 'wordcount'
            ],
            toolbar: 'undo redo | blocks | ' +
                'bold italic underline strikethrough | alignleft aligncenter ' +
                'alignright alignjustify | bullist numlist outdent indent | ' +
                'removeformat | image | help | wordcount',
            content_style: 'body { font-family:' + this.settings.editor_font_family + '; font-size:' + this.settings.editor_font_size + 'px; line-height: ' + this.settings.editor_line_height + '; margin: 1rem; }',
            // Image upload configuration
            image_title: true,
            automatic_uploads: true,
            file_picker_types: 'image',
            file_picker_callback: (cb, value, meta) => {
                if (meta.filetype === 'image') {
                    const input = document.createElement('input');
                    input.setAttribute('type', 'file');
                    input.setAttribute('accept', 'image/*');
                    
                    input.addEventListener('change', (e) => {
                        const file = e.target.files[0];
                        if (file) {
                            this.uploadImageForEditor(file, cb);
                        }
                    });
                    
                    input.click();
                }
            },
            setup: (editor) => {
                this.editor = editor;
                editor.on('input', () => {
                    this.updateWordCount();
                    this.updateSchema();
                });
                editor.on('change', () => {
                    this.updateWordCount();
                    this.updateSchema();
                });
                editor.on('init', () => {
                    console.log('TinyMCE initialized successfully (self-hosted)');
                });
            }
        });
    }
    
    async uploadImageForEditor(file, cb) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('note_id', this.currentNoteId); // Assuming currentNoteId is available
        formData.append('quality', this.settings.image_quality);
        
        try {
            const response = await fetch('/api/images/upload', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                // Assuming the API returns the URL of the uploaded image
                cb(result.data.url, { title: file.name });
                this.showNotification('Image uploaded successfully', 'success');
                this.updateAttachedImages(); // Refresh attached images list
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error('Upload failed:', error);
            this.showNotification('Failed to upload image', 'error');
        }
    }
    
    // Color Pickers
    initColorPickers() {
        // Only initialize if DOM elements exist
        const colorPickerEl = document.getElementById('color-picker');
        const noteColorPickerEl = document.getElementById('note-color-picker');

        if (colorPickerEl) {
            // Main color picker
            this.colorPicker = Pickr.create({
                el: '#color-picker',
                theme: 'classic',
                default: this.settings.primary_color,
                components: {
                    preview: true,
                    opacity: true,
                    hue: true,
                    interaction: {
                        hex: true,
                        input: true,
                        save: true
                    }
                }
            });

            this.colorPicker.on('change', (color) => {
                const hexColor = color.toHEXA().toString();
                const colorInput = document.getElementById('color-input');
                if (colorInput) {
                    colorInput.value = hexColor;
                }
                this.generateColorPalette(hexColor);
            });
        }

        if (noteColorPickerEl) {
            // Note color picker
            this.noteColorPicker = Pickr.create({
                el: '#note-color-picker',
                theme: 'classic',
                default: this.settings.default_note_color,
                components: {
                    preview: true,
                    opacity: false,
                    hue: true,
                    interaction: {
                        hex: true,
                        input: true,
                        save: true
                    }
                }
            });
        }
    }
    
    async generateColorPalette(primaryColor) {
        try {
            const response = await fetch('/api/settings/generate-palette', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ primary_color: primaryColor })
            });

            if (response.ok) {
                const result = await response.json();
                let palette = null;

                // Handle different response structures
                if (result.success && result.data && result.data.palette) {
                    palette = result.data.palette;
                } else if (result.palette) {
                    // Direct palette response
                    palette = result.palette;
                } else if (result.data && typeof result.data === 'object' && !Array.isArray(result.data)) {
                    // The palette might be directly in result.data
                    palette = result.data;
                }

                if (palette) {
                    this.displayColorPalette(palette);
                    this.settings.color_palette = palette;
                } else {
                    console.error('Invalid palette response structure:', result);
                }
            } else {
                console.error('Palette generation failed:', response.status);
            }
        } catch (error) {
            console.error('Failed to generate color palette:', error);
        }
    }
    
    displayColorPalette(palette) {
        const paletteContainer = document.getElementById('color-palette');
        paletteContainer.innerHTML = '';
        
        Object.entries(palette).forEach(([name, color]) => {
            const colorDiv = document.createElement('div');
            colorDiv.className = 'flex flex-col items-center';
            colorDiv.innerHTML = `
                <div class="w-12 h-12 rounded-lg border border-border-subtle" style="background-color: ${color}"></div>
                <div class="text-xs mt-1 text-center">
                    <div class="font-medium capitalize">${name.replace('_', ' ')}</div>
                    <div class="text-text-muted">${color}</div>
                </div>
            `;
            paletteContainer.appendChild(colorDiv);
        });
    }
    
    // Event Listeners
    initEventListeners() {
        // Settings modal
        document.getElementById('settings-btn').addEventListener('click', () => {
            this.openSettingsModal();
        });
        
        document.getElementById('close-settings-modal').addEventListener('click', () => {
            this.closeSettingsModal();
        });
        
        document.getElementById('save-settings').addEventListener('click', () => {
            this.collectSettingsFromUI();
            this.saveSettings();
            this.closeSettingsModal();
        });
        
        document.getElementById('cancel-settings').addEventListener('click', () => {
            this.closeSettingsModal();
        });
        
        document.getElementById('reset-settings').addEventListener('click', () => {
            this.resetSettings();
        });
        
        // Settings tabs
        document.querySelectorAll('.settings-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchSettingsTab(e.target.dataset.tab);
            });
        });
        
        // Image upload
        document.getElementById('attach-image-btn').addEventListener('click', () => {
            this.openImageUploadModal();
        });
        
        document.getElementById('close-image-upload-modal').addEventListener('click', () => {
            this.closeImageUploadModal();
        });
        
        document.getElementById('browse-image').addEventListener('click', () => {
            document.getElementById('image-file-input').click();
        });
        
        document.getElementById('image-file-input').addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleImageSelection(e.target.files[0]);
            }
        });
        
        document.getElementById('upload-image').addEventListener('click', () => {
            this.uploadImage();
        });
        
        // Schema toggle
        document.getElementById('toggle-schema').addEventListener('click', () => {
            this.toggleSchema();
        });
        
        // Enhanced note editor buttons
        document.getElementById('save-note-btn').addEventListener('click', () => {
            this.saveNoteFromEditor();
        });
        
        document.getElementById('delete-note-btn').addEventListener('click', () => {
            this.deleteCurrentNote();
        });
        
        // Settings form elements
        document.getElementById('editor-font-size').addEventListener('input', (e) => {
            document.getElementById('font-size-display').textContent = e.target.value + 'px';
        });
        
        document.getElementById('auto-save-interval').addEventListener('input', (e) => {
            document.getElementById('autosave-display').textContent = e.target.value + ' seconds';
        });
        
        document.getElementById('max-image-size').addEventListener('input', (e) => {
            document.getElementById('max-image-size-display').textContent = e.target.value + ' MB';
        });
    }
    
    // Modal Management
    openSettingsModal() {
        document.getElementById('settings-modal').classList.remove('hidden');
        this.populateSettingsForm();
    }
    
    closeSettingsModal() {
        document.getElementById('settings-modal').classList.add('hidden');
    }
    
    openImageUploadModal() {
        document.getElementById('image-upload-modal').classList.remove('hidden');
    }
    
    closeImageUploadModal() {
        document.getElementById('image-upload-modal').classList.add('hidden');
        this.resetImageUploadForm();
    }
    
    // Settings UI Management
    switchSettingsTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.settings-tab-btn').forEach(btn => {
            btn.classList.remove('active', 'bg-accent-light');
        });
        
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active', 'bg-accent-light');
        
        // Update tab content
        document.querySelectorAll('.settings-tab-content').forEach(content => {
            content.classList.add('hidden');
        });
        
        document.getElementById(`${tabName}-tab`).classList.remove('hidden');
        
        // Update title
        const titles = {
            appearance: 'Appearance Settings',
            editor: 'Editor Settings',
            content: 'Content Settings',
            advanced: 'Advanced Settings'
        };
        
        document.getElementById('settings-tab-title').textContent = titles[tabName];
    }
    
    populateSettingsForm() {
        // Populate form fields with current settings
        document.getElementById('color-input').value = this.settings.primary_color;
        document.getElementById('dark-mode-setting').checked = this.settings.dark_mode;
        document.getElementById('custom-css').value = this.settings.custom_css || '';
        document.getElementById('editor-font-family').value = this.settings.editor_font_family;
        document.getElementById('editor-font-size').value = this.settings.editor_font_size;
        document.getElementById('font-size-display').textContent = this.settings.editor_font_size + 'px';
        document.getElementById('editor-line-height').value = this.settings.editor_line_height;
        document.getElementById('auto-save-interval').value = this.settings.auto_save_interval;
        document.getElementById('autosave-display').textContent = this.settings.auto_save_interval + ' seconds';
        document.getElementById('spell-check-setting').checked = this.settings.spell_check;
        document.getElementById('auto-detect-titles').checked = this.settings.auto_detect_titles;
        document.getElementById('auto-generate-schema').checked = this.settings.auto_generate_schema;
        document.getElementById('export-format').value = this.settings.export_format;
        document.getElementById('image-quality').value = this.settings.image_quality;
        document.getElementById('max-image-size').value = this.settings.max_image_size;
        document.getElementById('max-image-size-display').textContent = this.settings.max_image_size + ' MB';
        
        // Update color pickers
        if (this.colorPicker) {
            this.colorPicker.setColor(this.settings.primary_color);
        }
        
        if (this.noteColorPicker) {
            this.noteColorPicker.setColor(this.settings.default_note_color);
        }
        
        // Display color palette
        if (this.settings.color_palette) {
            this.displayColorPalette(this.settings.color_palette);
        }
    }
    
    collectSettingsFromUI() {
        this.settings.primary_color = document.getElementById('color-input').value;
        this.settings.dark_mode = document.getElementById('dark-mode-setting').checked;
        this.settings.custom_css = document.getElementById('custom-css').value;
        this.settings.editor_font_family = document.getElementById('editor-font-family').value;
        this.settings.editor_font_size = parseInt(document.getElementById('editor-font-size').value);
        this.settings.editor_line_height = document.getElementById('editor-line-height').value;
        this.settings.auto_save_interval = parseInt(document.getElementById('auto-save-interval').value);
        this.settings.spell_check = document.getElementById('spell-check-setting').checked;
        this.settings.auto_detect_titles = document.getElementById('auto-detect-titles').checked;
        this.settings.auto_generate_schema = document.getElementById('auto-generate-schema').checked;
        this.settings.export_format = document.getElementById('export-format').value;
        this.settings.image_quality = document.getElementById('image-quality').value;
        this.settings.max_image_size = parseInt(document.getElementById('max-image-size').value);
        
        if (this.noteColorPicker) {
            this.settings.default_note_color = this.noteColorPicker.getColor().toHEXA().toString();
        }
    }
    
    async resetSettings() {
        if (confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
            try {
                const response = await fetch('/api/settings/reset', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ user_id: 'default' })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    this.settings = result.data;
                    this.populateSettingsForm();
                    this.applySettings();
                    this.showNotification('Settings reset to defaults', 'success');
                } else {
                    throw new Error('Failed to reset settings');
                }
            } catch (error) {
                console.error('Failed to reset settings:', error);
                this.showNotification('Failed to reset settings', 'error');
            }
        }
    }
    
    // Image Upload Management
    handleImageSelection(file) {
        if (!file.type.startsWith('image/')) {
            this.showNotification('Please select an image file', 'error');
            return;
        }
        
        if (file.size > this.settings.max_image_size * 1024 * 1024) {
            this.showNotification(`Image size must be less than ${this.settings.max_image_size}MB`, 'error');
            return;
        }
        
        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('image-preview');
            const img = document.getElementById('preview-image');
            const info = document.getElementById('image-info');
            
            img.src = e.target.result;
            info.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            preview.classList.remove('hidden');
            
            document.getElementById('upload-image').disabled = false;
        };
        
        reader.readAsDataURL(file);
    }
    
    async uploadImage() {
        const fileInput = document.getElementById('image-file-input');
        const file = fileInput.files[0];
        
        if (!file) return;
        
        const uploadBtn = document.getElementById('upload-image');
        const uploadText = document.getElementById('upload-text');
        const uploadSpinner = document.getElementById('upload-spinner');
        
        uploadBtn.disabled = true;
        uploadText.textContent = 'Uploading...';
        uploadSpinner.classList.remove('hidden');
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('note_id', this.currentNoteId);
            formData.append('quality', this.settings.image_quality);
            
            const response = await fetch('/api/images/upload', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showNotification('Image uploaded successfully', 'success');
                this.updateAttachedImages();
                this.closeImageUploadModal();
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error('Upload failed:', error);
            this.showNotification('Failed to upload image', 'error');
        } finally {
            uploadBtn.disabled = false;
            uploadText.textContent = 'Upload Image';
            uploadSpinner.classList.add('hidden');
        }
    }
    
    resetImageUploadForm() {
        document.getElementById('image-file-input').value = '';
        document.getElementById('image-preview').classList.add('hidden');
        document.getElementById('upload-image').disabled = true;
    }
    
    // Schema and Content Analysis
    toggleSchema() {
        const sidebar = document.getElementById('schema-sidebar');
        const toggleBtn = document.getElementById('toggle-schema');
        
        sidebar.classList.toggle('hidden');
        
        if (sidebar.classList.contains('hidden')) {
            toggleBtn.innerHTML = '<i class="fas fa-list-ul"></i>';
        } else {
            toggleBtn.innerHTML = '<i class="fas fa-times"></i>';
            this.updateSchema();
        }
    }
    
    updateSchema() {
        if (!this.settings.auto_generate_schema) return;
        
        const content = this.editor ? this.editor.getContent({ format: 'text' }) : '';
        
        if (!content.trim()) {
            document.getElementById('schema-content').innerHTML = 
                '<div class="text-sm text-text-muted">Start typing to see document structure...</div>';
            return;
        }
        
        // Simple heading detection
        const lines = content.split('\n');
        const headings = [];
        
        lines.forEach((line, index) => {
            line = line.trim();
            if (line.startsWith('#')) {
                const level = (line.match(/^#+/) || [''])[0].length;
                const text = line.replace(/^#+\s*/, '');
                if (text) {
                    headings.push({ level, text, line: index + 1 });
                }
            }
        });
        
        const schemaContent = document.getElementById('schema-content');
        
        if (headings.length === 0) {
            schemaContent.innerHTML = '<div class="text-sm text-text-muted">No headings found</div>';
        } else {
            const schemaHTML = headings.map(heading => `
                <div class="py-1 pl-${(heading.level - 1) * 4} border-l-2 border-accent hover:bg-accent-light cursor-pointer text-sm">
                    ${heading.text}
                </div>
            `).join('');
            
            schemaContent.innerHTML = schemaHTML;
        }
    }
    
    updateWordCount() {
        const content = this.editor ? this.editor.getContent({ format: 'text' }) : '';
        const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;
        const readingTime = Math.max(1, Math.round(wordCount / 200));
        
        document.getElementById('note-stats').textContent = `${wordCount} words • ${readingTime} min read`;
    }
    
    async updateAttachedImages() {
        if (!this.currentNoteId) return;
        
        try {
            const response = await fetch(`/api/images/list/${this.currentNoteId}`);
            if (response.ok) {
                const result = await response.json();
                const images = result.data.images;
                
                const container = document.getElementById('attached-images');
                
                if (!images || images.length === 0) {
                    container.innerHTML = '<div class="text-xs text-text-muted">No images attached</div>';
                } else {
                    container.innerHTML = images.map(image => `
                        <div class="flex items-center gap-2 p-2 bg-background-primary rounded text-xs">
                            <img src="${image.path}" alt="${image.original_name}" class="w-8 h-8 object-cover rounded">
                            <span class="flex-1 truncate">${image.original_name}</span>
                            <button onclick="app.deleteImage('${image.id}')" class="text-red-500 hover:text-red-700">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    `).join('');
                }
            }
        } catch (error) {
            console.error('Failed to load attached images:', error);
        }
    }
    
    async deleteImage(imageId) {
        if (!confirm('Delete this image?')) return;
        
        try {
            const response = await fetch(`/api/images/delete/${imageId}?note_id=${this.currentNoteId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.updateAttachedImages();
                this.showNotification('Image deleted', 'success');
            } else {
                throw new Error('Delete failed');
            }
        } catch (error) {
            console.error('Failed to delete image:', error);
            this.showNotification('Failed to delete image', 'error');
        }
    }
    
    // Auto-save functionality
    setupAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        
        this.autoSaveInterval = setInterval(() => {
            if (this.currentNoteId && this.editor) {
                this.autoSaveNote();
            }
        }, this.settings.auto_save_interval * 1000);
    }
    
    async autoSaveNote() {
        if (!this.currentNoteId || !this.editor) return;
        
        const content = this.editor.getContent();
        const textContent = this.editor.getContent({ format: 'text' });
        
        try {
            await fetch(`/api/notes/${this.currentNoteId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: textContent,
                    formatted_content: content
                })
            });
            
            // Show subtle auto-save indicator
            this.showAutoSaveIndicator();
        } catch (error) {
            console.error('Auto-save failed:', error);
        }
    }
    
    showAutoSaveIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'fixed top-4 right-4 bg-green-500 text-white px-3 py-1 rounded-lg text-sm opacity-75 transition-opacity';
        indicator.textContent = 'Auto-saved';
        
        document.body.appendChild(indicator);
        
        setTimeout(() => {
            indicator.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(indicator);
            }, 300);
        }, 2000);
    }
    
    // Enhanced note operations
    async saveNoteFromEditor() {
        if (!this.editor) return;
        
        const content = this.editor.getContent({ format: 'text' });
        const formattedContent = this.editor.getContent();
        const title = document.getElementById('editor-title').textContent;
        
        if (!content.trim()) {
            this.showNotification('Note content cannot be empty', 'error');
            return;
        }
        
        try {
            let response;
            
            if (this.currentNoteId) {
                // Update existing note
                response = await fetch(`/api/notes/${this.currentNoteId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        content: content,
                        formatted_content: formattedContent
                    })
                });
            } else {
                // Create new note
                response = await fetch('/api/notes', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        title: title,
                        content: content,
                        formatted_content: formattedContent,
                        lesson_id: this.currentLessonId,
                        unit_id: this.currentUnitId
                    })
                });
            }
            
            if (response.ok) {
                const result = await response.json();
                this.currentNoteId = result.data.id;
                this.showNotification('Note saved successfully', 'success');
                this.renderNotes(); // Refresh notes list
            } else {
                throw new Error('Save failed');
            }
        } catch (error) {
            console.error('Failed to save note:', error);
            this.showNotification('Failed to save note', 'error');
        }
    }
    
    async deleteCurrentNote() {
        if (!this.currentNoteId) return;
        
        if (!confirm('Are you sure you want to delete this note? This cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/notes/${this.currentNoteId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.showNotification('Note deleted successfully', 'success');
                this.closeNoteEditor();
                this.renderNotes();
            } else {
                throw new Error('Delete failed');
            }
        } catch (error) {
            console.error('Failed to delete note:', error);
            this.showNotification('Failed to delete note', 'error');
        }
    }
    
    // Enhanced note editor operations
    openNoteEditor() {
        document.getElementById('note-editor').classList.remove('hidden');
        this.currentNoteId = null;
        document.getElementById('editor-title').textContent = 'New Note';
        document.getElementById('delete-note-btn').classList.add('hidden');
        
        if (this.editor) {
            this.editor.setContent('');
        }
        
        this.updateWordCount();
        this.updateAttachedImages();
    }
    
    openEditNoteEditor(note) {
        document.getElementById('note-editor').classList.remove('hidden');
        this.currentNoteId = note.id;
        document.getElementById('editor-title').textContent = 'Edit Note: ' + note.title;
        document.getElementById('delete-note-btn').classList.remove('hidden');
        
        if (this.editor) {
            this.editor.setContent(note.formatted_content || note.content);
        }
        
        this.updateWordCount();
        this.updateAttachedImages();
        this.updateSchema();
    }
    
    closeNoteEditor() {
        document.getElementById('note-editor').classList.add('hidden');
        this.currentNoteId = null;
    }
    
    // Notification system
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        const colors = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        };
        
        notification.className = `fixed top-4 right-4 ${colors[type]} text-white px-4 py-2 rounded-lg shadow-lg z-[60] transition-all duration-300 transform translate-x-full`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 10);
        
        // Animate out
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
    
    // Legacy compatibility - these would need to be implemented based on existing app structure
    renderLessons() {
        // Implementation needed based on existing code
        console.log('renderLessons - to be implemented');
    }
    
    renderUnits() {
        // Implementation needed based on existing code
        console.log('renderUnits - to be implemented');
    }
    
    renderNotes() {
        // Implementation needed based on existing code
        console.log('renderNotes - to be implemented');
    }
}

// Initialize the enhanced app
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new EnhancedNotesApp();
});

<script>
  import { onMount } from 'svelte';
  import { theme } from './lib/theme.svelte.js';
  import {
    fetchLessons,
    createLesson,
    updateLesson,
    deleteLesson,
    fetchUnits,
    createUnit,
    updateUnit,
    deleteUnit,
    fetchNotes,
    fetchAllNotes,
    createNote,
    updateNote,
    deleteNote
  } from './lib/api.js';

  // Modal Components
  import Editor from './lib/components/Editor.svelte';
  import MathPalette from './lib/components/MathPalette.svelte';
  import MermaidBlock from './lib/components/MermaidBlock.svelte';
  import DrawingCanvas from './lib/components/DrawingCanvas.svelte';
  import FunctionPlotter from './lib/components/FunctionPlotter.svelte';
  import Omnibox from './lib/components/Omnibox.svelte';
  import FactCheckPanel from './lib/components/FactCheckPanel.svelte';
  import SlideIngestionModal from './lib/components/SlideIngestionModal.svelte';
  import TailscalePairingModal from './lib/components/TailscalePairingModal.svelte';
  import FloatingAccessoryBar from './lib/components/FloatingAccessoryBar.svelte';
  import SettingsModal from './lib/components/SettingsModal.svelte';
  import ItemCustomizerModal from './lib/components/ItemCustomizerModal.svelte';
  import ModalDialog from './lib/components/ModalDialog.svelte';
  import { analyzeAndCategorize } from './lib/organizer.js';

  // State
  let lessons = $state([]);
  let activeLesson = $state(null);
  let units = $state([]);
  let activeUnit = $state(null);
  let notes = $state([]);
  let activeNote = $state(null);
  let allNotes = $state([]);

  // Tree & Explorer State
  let expandedFolders = $state({});
  let notesByUnit = $state({});

  // Item Customizer Modal
  let showCustomizer = $state(false);
  let customizingItem = $state(null);

  // In-App Accessible Dialog System (replaces window.prompt & window.confirm)
  let dialogState = $state({
    isOpen: false,
    type: 'prompt',
    title: '',
    message: '',
    icon: '📝',
    defaultValue: '',
    placeholder: '',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    danger: false,
    onConfirm: () => {},
    onCancel: () => {}
  });

  function showPromptDialog({ title, message = '', icon = '📝', defaultValue = '', placeholder = '', confirmText = 'Create' }) {
    return new Promise((resolve) => {
      dialogState = {
        isOpen: true,
        type: 'prompt',
        title,
        message,
        icon,
        defaultValue,
        placeholder,
        confirmText,
        cancelText: 'Cancel',
        danger: false,
        onConfirm: (val) => resolve(val),
        onCancel: () => resolve(null)
      };
    });
  }

  function showConfirmDialog({ title, message = '', icon = '⚠️', confirmText = 'Confirm', danger = false }) {
    return new Promise((resolve) => {
      dialogState = {
        isOpen: true,
        type: 'confirm',
        title,
        message,
        icon,
        defaultValue: '',
        placeholder: '',
        confirmText,
        cancelText: 'Cancel',
        danger,
        onConfirm: () => resolve(true),
        onCancel: () => resolve(false)
      };
    });
  }

  // Auto-organizer toast notification
  let organizerToast = $state('');

  // Editor ref
  let editorRef = $state(null);

  // Modals visibility
  let showOmnibox = $state(false);
  let showMath = $state(false);
  let showMermaid = $state(false);
  let showCanvas = $state(false);
  let showPlotter = $state(false);
  let showFactCheck = $state(false);
  let showSlides = $state(false);
  let showPairing = $state(false);
  let showSettings = $state(false);
  let settingsTab = $state('appearance');

  function openSettings(tab = 'appearance') {
    settingsTab = tab;
    showSettings = true;
  }

  // Responsive Drawer toggle for mobile (<768px)
  let showMobileSidebar = $state(false);

  onMount(async () => {
    await loadInitialData();

    const handleServerChange = async () => {
      await loadInitialData();
    };
    window.addEventListener('notes-server-changed', handleServerChange);
    window.addEventListener('keydown', handleGlobalKeydown);
    return () => {
      window.removeEventListener('notes-server-changed', handleServerChange);
      window.removeEventListener('keydown', handleGlobalKeydown);
    };
  });

  async function loadInitialData() {
    lessons = await fetchLessons();
    if (lessons.length > 0) {
      activeLesson = lessons[0];
    } else {
      activeLesson = null;
      activeUnit = null;
      activeNote = null;
    }
    await refreshTree();
  }

  async function refreshTree() {
    if (!activeLesson && lessons.length > 0) {
      activeLesson = lessons[0];
    }
    if (activeLesson) {
      units = await fetchUnits(activeLesson.id);
      const newNotesByUnit = {};
      for (const u of units) {
        if (expandedFolders[u.id] === undefined) {
          expandedFolders[u.id] = true;
        }
        const uNotes = await fetchNotes(u.id);
        newNotesByUnit[u.id] = uNotes;
      }
      notesByUnit = newNotesByUnit;
      allNotes = await fetchAllNotes();
      notes = activeUnit ? (notesByUnit[activeUnit.id] || []) : allNotes;
      if (!activeNote && units.length > 0) {
        const firstNotes = notesByUnit[units[0].id] || [];
        if (firstNotes.length > 0) {
          activeNote = firstNotes[0];
          activeUnit = units[0];
        }
      }
    } else {
      units = [];
      notesByUnit = {};
      notes = [];
      activeUnit = null;
      activeNote = null;
    }
  }

  async function selectLesson(lesson) {
    activeLesson = lesson;
    // Keep sidebar OPEN!
    await refreshTree();
  }

  function toggleFolder(unit) {
    expandedFolders[unit.id] = !expandedFolders[unit.id];
    activeUnit = unit;
    // Keep sidebar OPEN!
  }

  function handleSelectNote(note) {
    activeNote = note;
    activeUnit = units.find(u => u.id === note.unit_id) || activeUnit;
    showMobileSidebar = false; // Only close drawer when clicking a note!
  }

  async function handleCreateLesson() {
    const name = await showPromptDialog({
      title: 'New Course / Subject',
      message: 'Enter a name for your course (e.g. CS101, Linear Algebra, Biology)',
      icon: '📚',
      placeholder: 'Course name...'
    });
    if (name && name.trim()) {
      const l = await createLesson(name.trim(), '📚', '#3b82f6');
      if (l) {
        lessons = [...lessons, l];
        activeLesson = l;
        await refreshTree();
      }
    }
  }

  async function handleDeleteLesson(lesson) {
    const confirmed = await showConfirmDialog({
      title: 'Delete Course',
      message: `Are you sure you want to delete course "${lesson.name}" and all its folders and notes? This cannot be undone.`,
      icon: '🗑️',
      confirmText: 'Delete Course',
      danger: true
    });
    if (confirmed) {
      await deleteLesson(lesson.id);
      lessons = lessons.filter(l => l.id !== lesson.id);
      if (activeLesson?.id === lesson.id) {
        activeLesson = lessons.length > 0 ? lessons[0] : null;
        activeUnit = null;
        activeNote = null;
      }
      await refreshTree();
    }
  }

  async function handleCreateFolder() {
    if (!activeLesson) {
      if (lessons.length > 0) activeLesson = lessons[0];
      else await handleCreateLesson();
    }
    if (!activeLesson) return;
    const name = await showPromptDialog({
      title: `New Folder in ${activeLesson.name}`,
      message: 'Enter a folder or unit name (e.g. Week 1, Homework, Exam Prep)',
      icon: '📁',
      placeholder: 'Folder name...'
    });
    if (name && name.trim()) {
      const u = await createUnit(activeLesson.id, name.trim(), '📁', '#10b981');
      if (u) {
        expandedFolders[u.id] = true;
        activeUnit = u;
        await refreshTree();
      }
    }
  }

  async function handleCreateNoteInFolder(unit) {
    activeUnit = unit;
    const existing = notesByUnit[unit.id] || [];
    const count = existing.length + 1;
    const newNote = await createNote(unit.id, {
      title: `Note ${count}`,
      content: `# Note ${count}\n\n`,
      icon: '📝',
      color: unit.color || '#3b82f6'
    });
    if (newNote) {
      expandedFolders[unit.id] = true;
      await refreshTree();
      handleSelectNote(newNote);
    }
  }

  async function handleCreateNewNote() {
    if (!activeLesson) {
      if (lessons.length > 0) {
        activeLesson = lessons[0];
      } else {
        const name = await showPromptDialog({
          title: 'Create Your First Course',
          message: 'To create notes, you need at least one course / subject.',
          icon: '📚',
          placeholder: 'Course name (e.g. Computer Science)...'
        });
        if (!name || !name.trim()) return;
        const l = await createLesson(name.trim(), '📚', '#3b82f6');
        if (!l) return;
        lessons = [l];
        activeLesson = l;
      }
    }
    if (!activeUnit) {
      const existingUnits = await fetchUnits(activeLesson.id);
      if (existingUnits.length > 0) {
        activeUnit = existingUnits[0];
      } else {
        const uName = await showPromptDialog({
          title: `Create Folder in ${activeLesson.name}`,
          message: 'Enter a folder name to organize your notes.',
          icon: '📁',
          placeholder: 'Folder name (e.g. Chapter 1)...'
        });
        if (!uName || !uName.trim()) return;
        const u = await createUnit(activeLesson.id, uName.trim(), '📁', '#10b981');
        if (!u) return;
        units = [u];
        activeUnit = u;
      }
    }
    await handleCreateNoteInFolder(activeUnit);
  }

  async function handleDeleteActiveNote() {
    if (!activeNote) return;
    const confirmed = await showConfirmDialog({
      title: 'Delete Note',
      message: `Are you sure you want to delete note "${activeNote.title}"?`,
      icon: '🗑️',
      confirmText: 'Delete Note',
      danger: true
    });
    if (confirmed) {
      await deleteNote(activeNote.id);
      activeNote = null;
      await refreshTree();
    }
  }

  function openCustomizer(item, type) {
    customizingItem = { ...item, type };
    showCustomizer = true;
  }

  async function handleSaveCustomizer(data) {
    if (data.type === 'lesson') {
      await updateLesson(data.id, { name: data.name, icon: data.icon, color: data.color });
    } else if (data.type === 'unit') {
      await updateUnit(data.id, { name: data.name, icon: data.icon, color: data.color });
    } else if (data.type === 'note') {
      await updateNote(data.id, {
        title: data.title,
        icon: data.icon,
        color: data.color,
        unit_id: data.unit_id
      });
      if (activeNote?.id === data.id) {
        activeNote.title = data.title;
        activeNote.icon = data.icon;
        activeNote.color = data.color;
        activeNote.unit_id = data.unit_id;
      }
    }
    await refreshTree();
  }

  async function handleDeleteCustomizer(item) {
    if (item.type === 'lesson') {
      await deleteLesson(item.id);
      lessons = lessons.filter(l => l.id !== item.id);
      if (activeLesson?.id === item.id) {
        activeLesson = lessons.length > 0 ? lessons[0] : null;
        activeUnit = null;
        activeNote = null;
      }
    } else if (item.type === 'unit') {
      await deleteUnit(item.id);
      units = units.filter(u => u.id !== item.id);
      if (activeUnit?.id === item.id) activeUnit = null;
      if (activeNote?.unit_id === item.id) activeNote = null;
    } else if (item.type === 'note') {
      await deleteNote(item.id);
      if (activeNote?.id === item.id) activeNote = null;
    }
    await refreshTree();
  }

  async function handleAutoOrganizeActiveNote() {
    if (!activeNote) return;
    const res = analyzeAndCategorize(activeNote.title, activeNote.content, units);
    if (res.type === 'existing_folder') {
      await updateNote(activeNote.id, {
        unit_id: res.unitId,
        icon: res.suggestedIcon,
        color: res.suggestedColor
      });
      activeNote.unit_id = res.unitId;
      activeNote.icon = res.suggestedIcon;
      activeNote.color = res.suggestedColor;
      expandedFolders[res.unitId] = true;
      showToast(`🪄 Moved note into folder "${res.unitName}" with ${res.suggestedIcon}!`);
      await refreshTree();
    } else if (res.type === 'new_folder') {
      const confirmed = await showConfirmDialog({
        title: 'Auto-Organize Note',
        message: `Auto-Organizer suggests creating new folder "${res.unitName}" (${res.suggestedIcon}) for this note. Proceed?`,
        icon: '🪄',
        confirmText: 'Create & Organize'
      });
      if (confirmed) {
        const newUnit = await createUnit(activeLesson?.id || 'default', res.unitName, res.suggestedIcon, res.suggestedColor);
        if (newUnit) {
          await updateNote(activeNote.id, {
            unit_id: newUnit.id,
            icon: res.suggestedIcon,
            color: res.suggestedColor
          });
          activeNote.unit_id = newUnit.id;
          activeNote.icon = res.suggestedIcon;
          activeNote.color = res.suggestedColor;
          expandedFolders[newUnit.id] = true;
          showToast(`🪄 Created folder "${res.unitName}" and organized note!`);
          await refreshTree();
        }
      }
    }
  }

  function showToast(msg) {
    organizerToast = msg;
    setTimeout(() => organizerToast = '', 4000);
  }

  async function handleSaveNote(updatedData) {
    if (!activeNote) return;
    const res = await updateNote(activeNote.id, updatedData);
    if (res) {
      activeNote.title = res.title;
      activeNote.content = res.content;
      await refreshTree();
    }
  }

  function handleInsertContent(textSnippet) {
    if (editorRef) {
      editorRef.insertText(textSnippet);
    }
    // Close any opened tool modal
    showMath = false;
    showMermaid = false;
    showCanvas = false;
    showPlotter = false;
  }

  function handleApplyCorrection(disputedClaim, correctionText) {
    if (!activeNote || !editorRef) return;
    let current = activeNote.content;
    if (current.includes(disputedClaim)) {
      current = current.replace(disputedClaim, `${correctionText} [🟢 Verified from Course Slides]`);
      handleSaveNote({ title: activeNote.title, content: current });
      activeNote.content = current;
      if (editorRef.setContent) {
        editorRef.setContent(current);
      }
    }
  }

  function handleGlobalKeydown(e) {
    // Ctrl+K / Cmd+K: Omnibox
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      showOmnibox = !showOmnibox;
    }
    // Ctrl+Shift+F: Fact-Check
    else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'f') {
      e.preventDefault();
      showFactCheck = !showFactCheck;
    }
    // Ctrl+E: Math Palette
    else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'e') {
      e.preventDefault();
      showMath = !showMath;
    }
    // Ctrl+M: Mermaid
    else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'm') {
      e.preventDefault();
      showMermaid = !showMermaid;
    }
    // Ctrl+D: Stylus Drawing Canvas
    else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'd') {
      e.preventDefault();
      showCanvas = !showCanvas;
    }
    // Ctrl+P: Function Plotter
    else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'p') {
      e.preventDefault();
      showPlotter = !showPlotter;
    }
  }
</script>

<div class="h-screen w-screen flex flex-col bg-[var(--bg-primary)] text-[var(--text-primary)] select-none overflow-hidden">
  <!-- Top App Navigation Bar -->
  <header 
    class="border-b border-[var(--border)] bg-[var(--bg-secondary)] flex items-center justify-between px-3 shrink-0 pt-[max(env(safe-area-inset-top,0px),1.75rem)] sm:pt-2 pb-2 min-h-12 pl-[max(env(safe-area-inset-left,0px),0.75rem)] pr-[max(env(safe-area-inset-right,0px),0.75rem)]"
  >
    <div class="flex items-center gap-2">
      <!-- Mobile Drawer Button (<768px) -->
      <button
        class="md:hidden p-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs text-[var(--text-primary)]"
        onclick={() => showMobileSidebar = !showMobileSidebar}
      >
        ☰
      </button>

      <!-- App Logo -->
      <div class="flex items-center gap-2">
        <span class="w-6 h-6 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center font-bold text-xs shadow-xs">N</span>
        <span class="font-bold text-sm tracking-tight text-[var(--text-primary)] hidden sm:inline">Ultimate University Notes</span>
      </div>
    </div>

    <!-- Center Omnibox Trigger Button -->
    <button
      class="flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-xs text-[var(--text-secondary)] transition-colors shadow-xs truncate max-w-[140px] sm:max-w-xs"
      onclick={() => showOmnibox = true}
    >
      <span class="truncate">Search notes & tools...</span>
      <kbd class="hidden sm:inline px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] border border-[var(--border)] text-[10px] font-mono">Ctrl+K</kbd>
    </button>

    <!-- Top Right Action Controls -->
    <div class="flex items-center gap-2">
      <!-- Course Slides RAG button -->
      <button
        class="px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--accent)] hidden sm:flex items-center gap-1 shadow-xs"
        onclick={() => showSlides = true}
        title="Upload & Index Lecture Slide PDFs"
      >
        <span>📑 Slides RAG</span>
      </button>

      <!-- Tailscale P2P Sync button -->
      <button
        class="px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-950/40 hover:bg-emerald-900/50 border border-emerald-500/40 text-emerald-300 flex items-center gap-1 shadow-xs"
        onclick={() => showPairing = true}
        title="Tailscale Mesh Peer-to-Peer Sync"
      >
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span class="hidden sm:inline">P2P Mesh</span>
      </button>

      <!-- Settings button -->
      <button
        class="p-1.5 rounded-lg text-xs font-medium bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center justify-center shadow-xs"
        onclick={() => openSettings('appearance')}
        title="Workstation Hub & Settings (Themes, Server, AI, Updates)"
      >
        <span>⚙️</span>
      </button>
    </div>
  </header>

  <!-- Main Multi-Pane Content Area -->
  <div class="flex-1 min-h-0 flex relative overflow-hidden">
    <!-- Sidebar: Lessons, Units & Notes List -->
    <aside
      class="w-80 border-r border-[var(--border)] bg-[var(--bg-secondary)] flex flex-col shrink-0 transition-transform duration-200 z-30 absolute md:static inset-y-0 left-0 pt-[max(env(safe-area-inset-top,0px),1.75rem)] md:pt-0 pb-[max(env(safe-area-inset-bottom,0px),1rem)] md:pb-0 {showMobileSidebar ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0'}"
    >
      <!-- Mobile Drawer Close Header (Mobile Only) -->
      <div class="md:hidden px-3 py-2 border-b border-[var(--border)] flex items-center justify-between bg-[var(--bg-tertiary)]">
        <span class="text-xs font-bold text-[var(--text-primary)]">Courses & Folders</span>
        <button
          class="p-1 px-2 rounded-lg bg-[var(--card)] text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border)]"
          onclick={() => showMobileSidebar = false}
        >✕ Close</button>
      </div>

      <!-- Explorer Top Bar: Course Selector + Actions -->
      <div class="p-3 border-b border-[var(--border)] flex flex-col gap-2">
        <div class="flex items-center justify-between text-[11px] font-bold text-[var(--text-secondary)] uppercase tracking-wider">
          <span>Courses</span>
          <div class="flex items-center gap-1">
            <button
              class="px-2 py-0.5 rounded-lg bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-xs text-[var(--accent)] font-semibold transition-colors"
              onclick={handleCreateLesson}
              title="Add New Course"
            >+ Course</button>
            <button
              class="px-2 py-0.5 rounded-lg bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-xs text-[var(--accent)] font-semibold transition-colors"
              onclick={handleCreateFolder}
              title="Add New Folder in Course"
            >+ Folder</button>
          </div>
        </div>

        <!-- Course Tabs with Customizer Trigger & Direct Delete -->
        <div class="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none items-center">
          {#if lessons.length === 0}
            <span class="text-xs text-[var(--text-secondary)] italic py-1 px-1">No courses yet. Click "+ Course" to add one.</span>
          {:else}
            {#each lessons as l}
              <div class="shrink-0 flex items-center rounded-xl border transition-all {activeLesson?.id === l.id ? 'border-[var(--accent)] bg-[var(--card)] shadow-xs' : 'border-[var(--border)] bg-[var(--bg-primary)] opacity-80'}">
                <button
                  class="px-2.5 py-1 text-xs font-semibold flex items-center gap-1.5 {activeLesson?.id === l.id ? 'text-[var(--accent)]' : 'text-[var(--text-secondary)]'}"
                  onclick={() => selectLesson(l)}
                >
                  <span>{l.icon || '📚'}</span>
                  <span>{l.name}</span>
                </button>
                <button
                  class="px-1 py-1 text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] opacity-60 hover:opacity-100"
                  onclick={() => openCustomizer(l, 'lesson')}
                  title="Customize Course"
                >⚙️</button>
                <button
                  class="pr-2 pl-0.5 py-1 text-[11px] text-rose-400 hover:text-rose-300 opacity-60 hover:opacity-100"
                  onclick={() => handleDeleteLesson(l)}
                  title="Delete Course '{l.name}'"
                >🗑️</button>
              </div>
            {/each}
          {/if}
        </div>
      </div>

      <!-- Folders & Notes Hierarchical Tree -->
      <div class="flex-1 min-h-0 flex flex-col p-2 overflow-y-auto">
        <div class="flex items-center justify-between px-2 py-1 mb-1 text-[11px] font-bold text-[var(--text-secondary)] uppercase tracking-wider">
          <span>{activeLesson?.name || 'Explorer'} ({units.length} folders)</span>
          <button
            class="px-2 py-0.5 rounded-lg bg-[var(--accent)] text-white text-[11px] font-semibold hover:opacity-90 transition-opacity"
            onclick={handleCreateFolder}
            title="Create new folder"
          >+ Folder</button>
        </div>

        {#if !activeLesson}
          <div class="text-xs text-[var(--text-secondary)] text-center py-12 flex flex-col items-center gap-2">
            <span>📚 No courses created yet.</span>
            <button
              class="px-3 py-1.5 rounded-xl bg-[var(--accent)] text-white text-xs font-semibold"
              onclick={handleCreateLesson}
            >Create First Course</button>
          </div>
        {:else if units.length === 0}
          <div class="text-xs text-[var(--text-secondary)] text-center py-8 flex flex-col items-center gap-2">
            <span>📁 No folders in this course yet.</span>
            <button
              class="px-3 py-1.5 rounded-xl bg-[var(--accent)] text-white text-xs font-semibold"
              onclick={handleCreateFolder}
            >Create First Folder</button>
          </div>
        {:else}
          <div class="flex flex-col gap-1">
            {#each units as u}
              <div class="rounded-xl border border-transparent transition-colors {activeUnit?.id === u.id ? 'bg-[var(--card)]/50 border-[var(--border)]/60' : 'hover:bg-[var(--card)]/30'}">
                <!-- Folder Header Row -->
                <div class="flex items-center justify-between px-2 py-1.5 rounded-lg group">
                  <button
                    class="flex-1 flex items-center gap-2 text-left text-xs font-semibold text-[var(--text-primary)] truncate"
                    onclick={() => toggleFolder(u)}
                  >
                    <!-- Expand/Collapse Chevron -->
                    <span class="text-[10px] text-[var(--text-secondary)] transition-transform duration-150 inline-block w-3 text-center">
                      {expandedFolders[u.id] ? '▼' : '▶'}
                    </span>
                    <!-- Folder Custom Icon with Color Dot -->
                    <span class="text-sm">{u.icon || '📁'}</span>
                    <span class="truncate">{u.name}</span>
                    <!-- Count Badge -->
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full bg-[var(--bg-tertiary)] text-[var(--text-secondary)] font-normal">
                      {(notesByUnit[u.id] || []).length}
                    </span>
                  </button>

                  <!-- Folder Action Buttons -->
                  <div class="flex items-center gap-1 opacity-80 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                    <!-- + Note in this folder -->
                    <button
                      class="p-1 rounded-md hover:bg-[var(--bg-tertiary)] text-[var(--accent)] text-xs font-bold"
                      onclick={() => handleCreateNoteInFolder(u)}
                      title="Add note in {u.name}"
                    >+</button>
                    <!-- Customize folder -->
                    <button
                      class="p-1 rounded-md hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] text-[11px]"
                      onclick={() => openCustomizer(u, 'unit')}
                      title="Customize folder icon & color"
                    >⚙️</button>
                    <!-- Delete folder -->
                    <button
                      class="p-1 rounded-md hover:bg-rose-950/30 text-rose-400 text-[11px]"
                      onclick={() => handleDeleteCustomizer({ id: u.id, type: 'unit', name: u.name })}
                      title="Delete folder"
                    >🗑️</button>
                  </div>
                </div>

                <!-- Notes inside this Folder (Expanded) -->
                {#if expandedFolders[u.id]}
                  <div class="ml-5 pl-2.5 border-l-2 border-[var(--border)] flex flex-col gap-0.5 pb-1 pt-0.5">
                    {#if (notesByUnit[u.id] || []).length === 0}
                      <button
                        class="text-left py-1 px-2 text-[11px] text-[var(--text-secondary)] hover:text-[var(--accent)] italic"
                        onclick={() => handleCreateNoteInFolder(u)}
                      >
                        + Empty folder. Click to add note.
                      </button>
                    {:else}
                      {#each notesByUnit[u.id] || [] as n}
                        <div class="flex items-center justify-between rounded-lg group/note {activeNote?.id === n.id ? 'bg-[var(--card)] border border-[var(--accent)] shadow-xs' : 'hover:bg-[var(--card)]/60 border border-transparent'}">
                          <button
                            class="flex-1 text-left px-2 py-1.5 flex items-center gap-2 truncate"
                            onclick={() => handleSelectNote(n)}
                          >
                            <span class="text-xs">{n.icon || '📝'}</span>
                            <span class="text-xs text-[var(--text-primary)] truncate font-medium">{n.title || 'Untitled Note'}</span>
                          </button>

                          <!-- Note Actions -->
                          <div class="flex items-center gap-0.5 pr-1 opacity-80 md:opacity-0 md:group-note:opacity-100 transition-opacity">
                            <button
                              class="p-1 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] text-[10px]"
                              onclick={() => openCustomizer(n, 'note')}
                              title="Customize note icon/color or move"
                            >⚙️</button>
                            <button
                              class="p-1 rounded hover:bg-rose-950/30 text-rose-400 text-[10px]"
                              onclick={() => handleDeleteCustomizer({ id: n.id, type: 'note', name: n.title })}
                              title="Delete note"
                            >🗑️</button>
                          </div>
                        </div>
                      {/each}
                    {/if}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </aside>

    <!-- Overlay when mobile drawer is open -->
    {#if showMobileSidebar}
      <div
        class="fixed inset-0 bg-black/50 z-20 md:hidden"
        onclick={() => showMobileSidebar = false}
      ></div>
    {/if}

    <!-- Main Editor Pane -->
    <main class="flex-1 h-full min-w-0 flex flex-col">
      {#if activeNote}
        <Editor
          bind:this={editorRef}
          note={activeNote}
          onSave={handleSaveNote}
          onFactCheck={() => showFactCheck = true}
          onOpenMath={() => showMath = true}
          onOpenMermaid={() => showMermaid = true}
          onOpenCanvas={() => showCanvas = true}
          onOpenPlotter={() => showPlotter = true}
          onAutoOrganize={handleAutoOrganizeActiveNote}
        />
      {:else if lessons.length === 0}
        <div class="flex-1 flex flex-col items-center justify-center p-8 text-center text-[var(--text-secondary)] gap-3">
          <div class="w-16 h-16 rounded-2xl bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center text-3xl">📚</div>
          <h2 class="text-base font-bold text-[var(--text-primary)]">Welcome to Notes Workstation</h2>
          <p class="text-xs max-w-sm">No courses exist yet. Create your first course or subject to begin organizing your lecture notes.</p>
          <button
            class="px-4 py-2 rounded-xl bg-[var(--accent)] text-white text-xs font-semibold hover:opacity-90 shadow-md"
            onclick={handleCreateLesson}
          >
            + Create First Course
          </button>
        </div>
      {:else}
        <div class="flex-1 flex flex-col items-center justify-center p-8 text-center text-[var(--text-secondary)] gap-3">
          <div class="w-16 h-16 rounded-2xl bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center text-2xl">📝</div>
          <h2 class="text-base font-bold text-[var(--text-primary)]">Select or Create a Note</h2>
          <p class="text-xs max-w-sm">Choose a folder from the sidebar or click below to start taking notes in {activeLesson?.name || 'your course'}.</p>
          <button
            class="px-4 py-2 rounded-xl bg-[var(--accent)] text-white text-xs font-semibold hover:opacity-90 shadow-md"
            onclick={handleCreateNewNote}
          >
            Create New Note
          </button>
        </div>
      {/if}

      <!-- Android Floating Keyboard Accessory Bar -->
      <FloatingAccessoryBar
        onInsertText={(txt) => handleInsertContent(txt)}
        onOpenMath={() => showMath = true}
        onOpenMermaid={() => showMermaid = true}
        onOpenCanvas={() => showCanvas = true}
        onOpenPlotter={() => showPlotter = true}
        onFactCheck={() => showFactCheck = true}
        onAutoOrganize={handleAutoOrganizeActiveNote}
        onUndo={() => editorRef?.undoAction?.()}
        onRedo={() => editorRef?.redoAction?.()}
      />
    </main>
  </div>

  <!-- Mobile Bottom Navigation Bar (sm:hidden) -->
  <nav class="sm:hidden border-t border-[var(--border)] bg-[var(--bg-secondary)] flex items-center justify-around px-2 pt-1.5 pb-[max(env(safe-area-inset-bottom,0px),1rem)] z-20 shrink-0">
    <!-- Courses Drawer -->
    <button
      class="flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl text-[10px] font-medium transition-colors {showMobileSidebar ? 'text-[var(--accent)] font-bold' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
      onclick={() => showMobileSidebar = !showMobileSidebar}
    >
      <span class="text-base leading-none">📚</span>
      <span>Courses</span>
    </button>

    <!-- Editor Tab -->
    <button
      class="flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl text-[10px] font-medium transition-colors {!showMobileSidebar ? 'text-[var(--accent)] font-bold' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
      onclick={() => showMobileSidebar = false}
    >
      <span class="text-base leading-none">✏️</span>
      <span>Editor</span>
    </button>

    <!-- + New Note (Primary Action) -->
    <button
      class="flex flex-col items-center gap-0.5 py-1 px-3.5 rounded-2xl bg-[var(--accent)] text-white text-[10px] font-bold shadow-md active:scale-95 transition-transform"
      onclick={handleCreateNewNote}
    >
      <span class="text-base leading-none font-bold">➕</span>
      <span>New Note</span>
    </button>

    <!-- Search / Tools -->
    <button
      class="flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl text-[10px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
      onclick={() => showOmnibox = true}
    >
      <span class="text-base leading-none">🔍</span>
      <span>Search</span>
    </button>

    <!-- Settings Tab -->
    <button
      class="flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl text-[10px] font-medium transition-colors {showSettings ? 'text-[var(--accent)] font-bold' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
      onclick={() => showSettings = true}
    >
      <span class="text-base leading-none">⚙️</span>
      <span>Settings</span>
    </button>
  </nav>

  <!-- Interactive Modals & Studios -->
  <Omnibox
    bind:isOpen={showOmnibox}
    {notes}
    onSelectNote={handleSelectNote}
    onNewNote={handleCreateNewNote}
    onOpenMath={() => showMath = true}
    onOpenMermaid={() => showMermaid = true}
    onOpenCanvas={() => showCanvas = true}
    onOpenPlotter={() => showPlotter = true}
    onOpenFactCheck={() => showFactCheck = true}
    onOpenSlides={() => showSlides = true}
    onOpenPairing={() => showPairing = true}
  />

  {#if showMath}
    <MathPalette
      onInsert={handleInsertContent}
      onClose={() => showMath = false}
    />
  {/if}

  {#if showMermaid}
    <MermaidBlock
      onInsert={handleInsertContent}
      onClose={() => showMermaid = false}
    />
  {/if}

  {#if showCanvas}
    <DrawingCanvas
      onInsert={handleInsertContent}
      onClose={() => showCanvas = false}
    />
  {/if}

  {#if showPlotter}
    <FunctionPlotter
      onInsert={handleInsertContent}
      onClose={() => showPlotter = false}
    />
  {/if}

  <FactCheckPanel
    bind:isOpen={showFactCheck}
    noteContent={activeNote?.content || ''}
    noteId={activeNote?.id}
    onApplyCorrection={handleApplyCorrection}
  />

  <SlideIngestionModal
    bind:isOpen={showSlides}
  />

  <TailscalePairingModal
    bind:isOpen={showPairing}
  />

  <SettingsModal
    bind:isOpen={showSettings}
    initialTab={settingsTab}
    onOpenPairing={() => showPairing = true}
  />

  <ItemCustomizerModal
    bind:isOpen={showCustomizer}
    item={customizingItem}
    {units}
    onSave={handleSaveCustomizer}
    onDelete={handleDeleteCustomizer}
  />

  <ModalDialog
    bind:isOpen={dialogState.isOpen}
    type={dialogState.type}
    title={dialogState.title}
    message={dialogState.message}
    icon={dialogState.icon}
    defaultValue={dialogState.defaultValue}
    placeholder={dialogState.placeholder}
    confirmText={dialogState.confirmText}
    cancelText={dialogState.cancelText}
    danger={dialogState.danger}
    onConfirm={dialogState.onConfirm}
    onCancel={dialogState.onCancel}
  />

  {#if organizerToast}
    <div class="fixed bottom-20 left-1/2 -translate-x-1/2 max-w-sm w-[90%] bg-[var(--surface)] text-[var(--text-primary)] border border-[var(--border)] rounded-2xl shadow-2xl p-3 z-50 flex items-center justify-between gap-3 text-xs animate-in fade-in slide-in-from-bottom-2">
      <div class="flex items-center gap-2">
        <span class="text-base">🪄</span>
        <span>{organizerToast}</span>
      </div>
      <button
        class="text-xs px-2 py-1 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--surface-hover)] text-[var(--text-secondary)] font-medium"
        onclick={() => organizerToast = ''}
      >
        ✕
      </button>
    </div>
  {/if}
</div>

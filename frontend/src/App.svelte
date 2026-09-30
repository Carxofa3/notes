<script>
  import { onMount } from 'svelte';
  import { theme } from './lib/theme.svelte.js';
  import {
    fetchLessons,
    createLesson,
    fetchUnits,
    createUnit,
    fetchNotes,
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

  // State
  let lessons = $state([]);
  let activeLesson = $state(null);
  let units = $state([]);
  let activeUnit = $state(null);
  let notes = $state([]);
  let activeNote = $state(null);

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

  // Responsive Drawer toggle for mobile (<768px)
  let showMobileSidebar = $state(false);

  onMount(async () => {
    await loadInitialData();
    window.addEventListener('keydown', handleGlobalKeydown);
    return () => window.removeEventListener('keydown', handleGlobalKeydown);
  });

  async function loadInitialData() {
    lessons = await fetchLessons();
    if (lessons.length > 0) {
      await selectLesson(lessons[0]);
    } else {
      // Create initial starter lesson & unit if brand new database
      const starterLesson = await createLesson('Biology 101');
      if (starterLesson) {
        lessons = [starterLesson];
        const starterUnit = await createUnit(starterLesson.id, 'Cellular Respiration');
        if (starterUnit) {
          units = [starterUnit];
          const starterNote = await createNote(starterUnit.id, {
            title: 'Cellular Respiration & ATP Synthesis',
            content: `# Cellular Respiration & ATP Synthesis

Cellular respiration is the biochemical process by which cells harvest chemical energy from glucose.

## Net Reaction
$$\\text{C}_6\\text{H}_{12}\\text{O}_6 + 6\\text{O}_2 \\longrightarrow 6\\text{CO}_2 + 6\\text{H}_2\\text{O} + 36\\text{-}38 \\text{ ATP}$$

- Glycolysis occurs in the cytosol (Net: 2 ATP, 2 NADH).
- The Citric Acid Cycle occurs in the mitochondrial matrix.
- Oxidative phosphorylation produces the bulk of ATP through the electron transport chain.
`
          });
          if (starterNote) {
            notes = [starterNote];
            activeLesson = starterLesson;
            activeUnit = starterUnit;
            activeNote = starterNote;
          }
        }
      }
    }
  }

  async function selectLesson(lesson) {
    activeLesson = lesson;
    units = await fetchUnits(lesson.id);
    if (units.length > 0) {
      await selectUnit(units[0]);
    } else {
      activeUnit = null;
      notes = [];
      activeNote = null;
    }
  }

  async function selectUnit(unit) {
    activeUnit = unit;
    notes = await fetchNotes(unit.id);
    if (notes.length > 0) {
      activeNote = notes[0];
    } else {
      activeNote = null;
    }
    showMobileSidebar = false; // Close drawer on mobile
  }

  function handleSelectNote(note) {
    activeNote = note;
    showMobileSidebar = false;
  }

  async function handleCreateNewNote() {
    if (!activeUnit) {
      if (lessons.length === 0) {
        const l = await createLesson('General Lecture');
        lessons = [l];
        activeLesson = l;
      }
      const u = await createUnit(activeLesson.id, 'Lecture Notes');
      units = [u];
      activeUnit = u;
    }

    const newNote = await createNote(activeUnit.id, {
      title: 'New Lecture Note',
      content: '# New Lecture Note\n\n'
    });
    if (newNote) {
      notes = [newNote, ...notes];
      activeNote = newNote;
    }
  }

  async function handleSaveNote(updatedData) {
    if (!activeNote) return;
    const res = await updateNote(activeNote.id, updatedData);
    if (res) {
      activeNote.title = res.title;
      activeNote.content = res.content;
      // Update in notes list
      const idx = notes.findIndex(n => n.id === activeNote.id);
      if (idx !== -1) {
        notes[idx] = { ...notes[idx], title: res.title, content: res.content };
      }
    }
  }

  async function handleDeleteActiveNote() {
    if (!activeNote) return;
    if (confirm(`Delete note "${activeNote.title}"?`)) {
      const ok = await deleteNote(activeNote.id);
      if (ok) {
        notes = notes.filter(n => n.id !== activeNote.id);
        activeNote = notes.length > 0 ? notes[0] : null;
      }
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
  <header class="h-12 border-b border-[var(--border)] bg-[var(--bg-secondary)] flex items-center justify-between px-3 shrink-0">
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
      class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-xs text-[var(--text-secondary)] transition-colors shadow-xs"
      onclick={() => showOmnibox = true}
    >
      <span>Search notes & tools...</span>
      <kbd class="px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] border border-[var(--border)] text-[10px] font-mono">Ctrl+K</kbd>
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
    </div>
  </header>

  <!-- Main Multi-Pane Content Area -->
  <div class="flex-1 min-h-0 flex relative overflow-hidden">
    <!-- Sidebar: Lessons, Units & Notes List -->
    <aside
      class="w-72 border-r border-[var(--border)] bg-[var(--bg-secondary)] flex flex-col shrink-0 transition-transform duration-200 z-30 absolute md:static inset-y-0 left-0 {showMobileSidebar ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}"
    >
      <!-- Lessons Selector -->
      <div class="p-3 border-b border-[var(--border)] flex flex-col gap-2">
        <div class="flex items-center justify-between text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
          <span>Courses / Lessons</span>
          <button
            class="hover:text-[var(--text-primary)] text-sm px-1"
            onclick={async () => {
              const name = prompt('New Course/Lesson Name:');
              if (name && name.trim()) {
                const l = await createLesson(name.trim());
                if (l) {
                  lessons = [...lessons, l];
                  selectLesson(l);
                }
              }
            }}
          >+</button>
        </div>

        <div class="flex gap-1 overflow-x-auto pb-1">
          {#each lessons as l}
            <button
              class="px-2.5 py-1 rounded-lg text-xs font-medium shrink-0 transition-colors {activeLesson?.id === l.id ? 'bg-[var(--accent)] text-white' : 'bg-[var(--card)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'}"
              onclick={() => selectLesson(l)}
            >
              {l.name}
            </button>
          {/each}
        </div>
      </div>

      <!-- Units List -->
      <div class="p-3 border-b border-[var(--border)] flex flex-col gap-1.5">
        <div class="flex items-center justify-between text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
          <span>Units / Chapters</span>
          <button
            class="hover:text-[var(--text-primary)] text-sm px-1"
            onclick={async () => {
              if (!activeLesson) return;
              const name = prompt('New Unit Name:');
              if (name && name.trim()) {
                const u = await createUnit(activeLesson.id, name.trim());
                if (u) {
                  units = [...units, u];
                  selectUnit(u);
                }
              }
            }}
          >+</button>
        </div>

        <div class="flex flex-col gap-1 max-h-28 overflow-y-auto">
          {#each units as u}
            <button
              class="text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors {activeUnit?.id === u.id ? 'bg-[var(--card)] text-[var(--accent)] border border-[var(--border)]' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'}"
              onclick={() => selectUnit(u)}
            >
              📂 {u.name}
            </button>
          {/each}
        </div>
      </div>

      <!-- Notes List -->
      <div class="flex-1 min-h-0 flex flex-col p-3">
        <div class="flex items-center justify-between text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
          <span>Notes ({notes.length})</span>
          <button
            class="px-2 py-0.5 rounded bg-[var(--accent)] text-white text-xs font-semibold hover:opacity-90"
            onclick={handleCreateNewNote}
          >+ Note</button>
        </div>

        <div class="flex-1 overflow-y-auto flex flex-col gap-1 pr-1">
          {#if notes.length === 0}
            <div class="text-xs text-[var(--text-secondary)] text-center py-6">
              No notes in this unit yet.
            </div>
          {:else}
            {#each notes as n}
              <button
                class="text-left p-2.5 rounded-xl border transition-all {activeNote?.id === n.id ? 'bg-[var(--card)] border-[var(--accent)] shadow-xs' : 'bg-transparent border-transparent hover:bg-[var(--card)] text-[var(--text-secondary)]'}"
                onclick={() => handleSelectNote(n)}
              >
                <div class="font-semibold text-xs text-[var(--text-primary)] truncate">{n.title || 'Untitled Note'}</div>
                <div class="text-[10px] text-[var(--text-secondary)] truncate mt-0.5">{n.content?.substring(0, 45) || 'Empty note...'}</div>
              </button>
            {/each}
          {/if}
        </div>

        <!-- Note Deletion option if active -->
        {#if activeNote}
          <div class="pt-2 border-t border-[var(--border)] mt-2">
            <button
              class="w-full py-1 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 rounded-lg transition-colors text-center"
              onclick={handleDeleteActiveNote}
            >
              Delete Active Note
            </button>
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
        />
      {:else}
        <div class="flex-1 flex flex-col items-center justify-center p-8 text-center text-[var(--text-secondary)] gap-3">
          <div class="w-16 h-16 rounded-2xl bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center text-2xl">📝</div>
          <h2 class="text-base font-bold text-[var(--text-primary)]">Select or Create a Note</h2>
          <p class="text-xs max-w-sm">Choose a lesson and unit from the sidebar or click the button below to start taking lecture notes.</p>
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
      />
    </main>
  </div>

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
</div>

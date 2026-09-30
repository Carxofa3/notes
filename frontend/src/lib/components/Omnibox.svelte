<script>
  import { onMount } from 'svelte';
  import { theme } from '../theme.svelte.js';
  import { THEMES } from '../types.js';

  let {
    isOpen = $bindable(false),
    notes = [],
    onSelectNote = () => {},
    onNewNote = () => {},
    onOpenMath = () => {},
    onOpenMermaid = () => {},
    onOpenCanvas = () => {},
    onOpenPlotter = () => {},
    onOpenFactCheck = () => {},
    onOpenSlides = () => {},
    onOpenPairing = () => {}
  } = $props();

  let query = $state('');
  let inputEl = $state(null);

  $effect(() => {
    if (isOpen && inputEl) {
      setTimeout(() => inputEl.focus(), 50);
    }
  });

  const SYSTEM_ACTIONS = [
    { id: 'new_note', title: 'New Note', category: 'Action', shortcut: 'Ctrl+N', run: () => onNewNote() },
    { id: 'fact_check', title: 'Autonomous Fact-Check Claims', category: 'AI', shortcut: 'Ctrl+Shift+F', run: () => onOpenFactCheck() },
    { id: 'math_palette', title: 'MathLive Equation Builder', category: 'Math', shortcut: 'Ctrl+E', run: () => onOpenMath() },
    { id: 'mermaid', title: 'Mermaid Diagram Studio', category: 'Diagrams', shortcut: 'Ctrl+M', run: () => onOpenMermaid() },
    { id: 'canvas', title: 'Freeform Stylus Sketch Canvas', category: 'Canvas', shortcut: 'Ctrl+D', run: () => onOpenCanvas() },
    { id: 'plotter', title: '2D Function Curve Plotter', category: 'Math', shortcut: 'Ctrl+P', run: () => onOpenPlotter() },
    { id: 'upload_slides', title: 'Upload & Index Lecture Slides (PDF)', category: 'RAG', shortcut: '', run: () => onOpenSlides() },
    { id: 'pair_tailscale', title: 'Pair Tailscale Peer Device (QR Code)', category: 'Sync', shortcut: '', run: () => onOpenPairing() }
  ];

  let filteredActions = $derived.by(() => {
    const q = query.toLowerCase().trim();
    if (!q) return SYSTEM_ACTIONS;
    return SYSTEM_ACTIONS.filter(a => a.title.toLowerCase().includes(q) || a.category.toLowerCase().includes(q));
  });

  let filteredNotes = $derived.by(() => {
    const q = query.toLowerCase().trim();
    if (!q) return notes.slice(0, 5);
    return notes.filter(n => (n.title || '').toLowerCase().includes(q) || (n.content || '').toLowerCase().includes(q)).slice(0, 8);
  });

  function executeAction(act) {
    isOpen = false;
    query = '';
    act.run();
  }

  function handleSelectNote(note) {
    isOpen = false;
    query = '';
    onSelectNote(note);
  }

  function selectTheme(tId) {
    theme.set(tId);
    isOpen = false;
  }
</script>

{#if isOpen}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/60 backdrop-blur-xs p-4" onclick={() => isOpen = false}>
    <div 
      class="w-full max-w-xl rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl overflow-hidden flex flex-col max-h-[70vh]"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Search Input Bar -->
      <div class="p-3 border-b border-[var(--border)] flex items-center gap-3 bg-[var(--bg-secondary)]">
        <span class="text-[var(--text-secondary)] font-mono text-sm">⌘ / Ctrl+K</span>
        <input
          bind:this={inputEl}
          type="text"
          bind:value={query}
          placeholder="Search notes, commands, or math tools..."
          class="w-full bg-transparent text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-hidden text-sm"
        />
        {#if query}
          <button class="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]" onclick={() => query = ''}>Clear</button>
        {/if}
      </div>

      <!-- Results list -->
      <div class="overflow-y-auto p-2 flex flex-col gap-3">
        <!-- Notes Section -->
        {#if filteredNotes.length > 0}
          <div>
            <div class="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider px-2 py-1">Notes</div>
            <div class="flex flex-col gap-0.5">
              {#each filteredNotes as n}
                <button
                  class="flex items-center justify-between px-3 py-2 rounded-xl text-left hover:bg-[var(--bg-tertiary)] transition-colors text-sm text-[var(--text-primary)]"
                  onclick={() => handleSelectNote(n)}
                >
                  <span class="font-medium truncate">{n.title || 'Untitled Note'}</span>
                  <span class="text-xs text-[var(--text-secondary)]">Open</span>
                </button>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Commands Section -->
        <div>
          <div class="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider px-2 py-1">Commands & Tools</div>
          <div class="flex flex-col gap-0.5">
            {#each filteredActions as act}
              <button
                class="flex items-center justify-between px-3 py-2 rounded-xl text-left hover:bg-[var(--bg-tertiary)] transition-colors text-sm text-[var(--text-primary)]"
                onclick={() => executeAction(act)}
              >
                <div class="flex items-center gap-2">
                  <span class="px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] border border-[var(--border)] text-[10px] font-mono text-[var(--accent)]">{act.category}</span>
                  <span>{act.title}</span>
                </div>
                {#if act.shortcut}
                  <kbd class="px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] border border-[var(--border)] text-[10px] font-mono text-[var(--text-secondary)]">{act.shortcut}</kbd>
                {/if}
              </button>
            {/each}
          </div>
        </div>

        <!-- Quick Theme Switcher -->
        <div>
          <div class="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider px-2 py-1">Theme Presets</div>
          <div class="grid grid-cols-2 gap-1.5 px-1">
            {#each THEMES as t}
              <button
                class="flex items-center gap-2 p-2 rounded-xl border border-[var(--border)] hover:bg-[var(--bg-tertiary)] transition-colors text-left text-xs {theme.current === t.id ? 'border-[var(--accent)] bg-[var(--bg-tertiary)]' : 'bg-[var(--bg-secondary)]'}"
                onclick={() => selectTheme(t.id)}
              >
                <span class="w-3.5 h-3.5 rounded-full border border-white/20" style="background-color: {t.accent};"></span>
                <span class="text-[var(--text-primary)] font-medium truncate">{t.name}</span>
              </button>
            {/each}
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}

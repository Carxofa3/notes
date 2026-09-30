<script>
  import { onMount, onDestroy } from 'svelte';
  import katex from 'katex';
  import 'katex/dist/katex.min.css';
  import { EditorState, Compartment } from '@codemirror/state';
  import { EditorView, keymap, highlightActiveLine, placeholder } from '@codemirror/view';
  import { defaultKeymap, history, historyKeymap, undo, redo } from '@codemirror/commands';
  import { markdown } from '@codemirror/lang-markdown';
  import { Table } from '@lezer/markdown';
  import {
    livePreviewPlugin,
    markdownStylePlugin,
    editorTheme,
    mouseSelectingField,
    collapseOnSelectionFacet,
    setMouseSelecting,
    mathPlugin,
    blockMathField,
    tableField,
    codeBlockField,
    imageField,
    linkPlugin
  } from 'codemirror-live-markdown';
  import { synthesizeLectureNotes } from '../api.js';

  let {
    note = null,
    onSave = () => {},
    onFactCheck = () => {},
    onAutoOrganize = () => {},
    onOpenMath = () => {},
    onOpenMermaid = () => {},
    onOpenCanvas = () => {},
    onOpenPlotter = () => {}
  } = $props();

  let title = $state('');
  let content = $state('');
  let isLivePreview = $state(true);
  let isSaving = $state(false);
  let isSynthesizing = $state(false);
  let wordCount = $state(0);
  let charCount = $state(0);

  let editorContainer = $state(null);
  let editorView = null;
  const livePreviewCompartment = new Compartment();
  let currentNoteId = null;
  let saveTimer = null;

  function updateCounts(text) {
    if (!text) {
      wordCount = 0;
      charCount = 0;
      return;
    }
    charCount = text.length;
    wordCount = text.trim().split(/\s+/).filter(Boolean).length;
  }

  function triggerSave() {
    clearTimeout(saveTimer);
    isSaving = true;
    saveTimer = setTimeout(() => {
      onSave({ title, content });
      isSaving = false;
    }, 1000);
  }

  function handleTitleChange() {
    triggerSave();
  }

  // Reactive effect when active note changes
  $effect(() => {
    if (note && note.id !== currentNoteId) {
      currentNoteId = note.id;
      title = note.title || '';
      content = note.content || '';
      updateCounts(content);
      if (editorView) {
        const curDoc = editorView.state.doc.toString();
        if (curDoc !== content) {
          editorView.dispatch({
            changes: { from: 0, to: curDoc.length, insert: content }
          });
        }
      }
    } else if (!note) {
      currentNoteId = null;
      title = '';
      content = '';
      updateCounts('');
      if (editorView) {
        editorView.dispatch({
          changes: { from: 0, to: editorView.state.doc.length, insert: '' }
        });
      }
    }
  });

  onMount(() => {
    initCodeMirror();
  });

  onDestroy(() => {
    clearTimeout(saveTimer);
    if (editorView) {
      editorView.destroy();
      editorView = null;
    }
  });

  function initCodeMirror() {
    if (!editorContainer || editorView) return;

    const baseTheme = EditorView.theme({
      '&': {
        height: '100%',
        backgroundColor: 'transparent',
        color: 'var(--text-primary)',
        fontSize: '15px'
      },
      '.cm-scroller': {
        overflow: 'auto',
        fontFamily: 'inherit',
        lineHeight: '1.7'
      },
      '.cm-content': {
        caretColor: 'var(--accent)',
        color: 'var(--text-primary)',
        padding: '1.5rem 1.25rem 8rem 1.25rem',
        maxWidth: '880px',
        margin: '0 auto',
        minHeight: '100%'
      },
      '.cm-line': {
        color: 'var(--text-primary)'
      },
      '.cm-cursor, .cm-dropCursor': {
        borderLeftColor: 'var(--accent)',
        borderLeftWidth: '2.5px'
      },
      '&.cm-focused': {
        outline: 'none'
      },
      '.cm-activeLine': {
        backgroundColor: 'rgba(255, 255, 255, 0.03)'
      }
    });

    const startState = EditorState.create({
      doc: content,
      extensions: [
        history(),
        highlightActiveLine(),
        EditorView.lineWrapping,
        placeholder('Start typing your lecture note... (Markdown, $inline math$, $$block math$$, tables, code blocks)'),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        markdown({ extensions: [Table] }),
        livePreviewCompartment.of(collapseOnSelectionFacet.of(isLivePreview)),
        mouseSelectingField,
        livePreviewPlugin,
        markdownStylePlugin,
        editorTheme,
        baseTheme,
        mathPlugin,
        blockMathField,
        tableField,
        codeBlockField({ copyButton: true }),
        imageField({ maxWidth: '100%' }),
        linkPlugin(),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            content = update.state.doc.toString();
            updateCounts(content);
            triggerSave();
          }
        })
      ]
    });

    editorView = new EditorView({
      state: startState,
      parent: editorContainer
    });

    // Required selection state handlers for codemirror-live-markdown
    editorView.contentDOM.addEventListener('mousedown', () => {
      editorView?.dispatch({ effects: setMouseSelecting.of(true) });
    });
    const handleMouseUp = () => {
      requestAnimationFrame(() => {
        if (editorView && !editorView.isDestroyed) {
          editorView.dispatch({ effects: setMouseSelecting.of(false) });
        }
      });
    };
    document.addEventListener('mouseup', handleMouseUp);

    // Touch selection support for Android/iOS
    editorView.contentDOM.addEventListener('touchstart', () => {
      editorView?.dispatch({ effects: setMouseSelecting.of(true) });
    }, { passive: true });
    const handleTouchEnd = () => {
      requestAnimationFrame(() => {
        if (editorView && !editorView.isDestroyed) {
          editorView.dispatch({ effects: setMouseSelecting.of(false) });
        }
      });
    };
    document.addEventListener('touchend', handleTouchEnd, { passive: true });
  }

  export function toggleLivePreview() {
    isLivePreview = !isLivePreview;
    if (editorView) {
      editorView.dispatch({
        effects: livePreviewCompartment.reconfigure(collapseOnSelectionFacet.of(isLivePreview))
      });
    }
  }

  export function insertText(snippet) {
    if (editorView) {
      const mainSel = editorView.state.selection.main;
      const transaction = editorView.state.update({
        changes: {
          from: mainSel.from,
          to: mainSel.to,
          insert: snippet
        },
        selection: {
          anchor: mainSel.from + snippet.length
        },
        scrollIntoView: true
      });
      editorView.dispatch(transaction);
      editorView.focus();
    } else {
      content += snippet;
      updateCounts(content);
      triggerSave();
    }
  }

  export function setContent(newContent) {
    content = newContent || '';
    updateCounts(content);
    if (editorView) {
      const curDoc = editorView.state.doc.toString();
      if (curDoc !== content) {
        editorView.dispatch({
          changes: { from: 0, to: curDoc.length, insert: content }
        });
      }
    }
    triggerSave();
  }

  export function undoAction() {
    if (editorView) {
      undo(editorView);
      editorView.focus();
    }
  }

  export function redoAction() {
    if (editorView) {
      redo(editorView);
      editorView.focus();
    }
  }

  function formatSelection(prefix, suffix = prefix, defaultPlaceholder = '') {
    if (!editorView) return;
    const mainSel = editorView.state.selection.main;
    const selectedText = editorView.state.sliceDoc(mainSel.from, mainSel.to);
    const textToInsert = selectedText ? `${prefix}${selectedText}${suffix}` : `${prefix}${defaultPlaceholder}${suffix}`;
    const insertPos = mainSel.from + prefix.length;
    const selectEnd = selectedText ? insertPos + selectedText.length : insertPos + defaultPlaceholder.length;

    editorView.dispatch({
      changes: { from: mainSel.from, to: mainSel.to, insert: textToInsert },
      selection: { anchor: insertPos, head: selectEnd },
      scrollIntoView: true
    });
    editorView.focus();
  }

  function formatLinePrefix(prefix) {
    if (!editorView) return;
    const mainSel = editorView.state.selection.main;
    const line = editorView.state.doc.lineAt(mainSel.from);
    editorView.dispatch({
      changes: { from: line.from, to: line.from, insert: prefix },
      selection: { anchor: mainSel.from + prefix.length },
      scrollIntoView: true
    });
    editorView.focus();
  }

  async function handleSynthesizeStudyGuide() {
    if (!content.trim()) return;
    isSynthesizing = true;
    try {
      const res = await synthesizeLectureNotes(content);
      if (res && res.synthesized_content) {
        insertText(`\n\n## 🎓 AI Lecture Study Guide & Key Formulas\n${res.synthesized_content}\n`);
      }
    } catch (e) {
      console.error('Study guide synthesis failed:', e);
    } finally {
      isSynthesizing = false;
    }
  }
</script>

<div class="h-full flex flex-col bg-[var(--bg-primary)] overflow-hidden">
  <!-- Top Editor Header Toolbar -->
  <div class="flex flex-wrap items-center justify-between p-3 border-b border-[var(--border)] bg-[var(--bg-secondary)] gap-2 shrink-0">
    <!-- Note Title with explicit high-contrast text color & caret -->
    <input
      type="text"
      bind:value={title}
      oninput={handleTitleChange}
      placeholder="Lecture Note Title..."
      class="text-base font-bold bg-transparent text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-hidden flex-1 min-w-[180px]"
      style="color: var(--text-primary) !important; caret-color: var(--accent) !important;"
    />

    <!-- Action Shortcuts & Obsidian Live Preview Toggle -->
    <div class="flex items-center gap-1.5 flex-wrap">
      <!-- Obsidian Live Preview Toggle -->
      <button
        class="px-2.5 py-1 rounded-lg text-xs font-semibold transition-all flex items-center gap-1 border shadow-xs {isLivePreview ? 'bg-[var(--accent)] text-white border-[var(--accent)]' : 'bg-[var(--card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border-[var(--border)]'}"
        onclick={toggleLivePreview}
        title="Toggle Obsidian Live Preview (WYSIWYG Markdown Rendering)"
      >
        <span>{isLivePreview ? '✨ Live Preview' : '📝 Source Mode'}</span>
      </button>

      <!-- Formatting Helpers -->
      <div class="hidden sm:flex items-center gap-1 border-l border-r border-[var(--border)] px-1.5">
        <button
          class="px-2 py-0.5 rounded hover:bg-[var(--card)] font-bold text-xs text-[var(--text-primary)]"
          onclick={() => formatSelection('**', '**', 'bold')}
          title="Bold (Ctrl+B)"
        >B</button>
        <button
          class="px-2 py-0.5 rounded hover:bg-[var(--card)] italic text-xs text-[var(--text-primary)]"
          onclick={() => formatSelection('*', '*', 'italic')}
          title="Italic (Ctrl+I)"
        >I</button>
        <button
          class="px-2 py-0.5 rounded hover:bg-[var(--card)] font-semibold text-xs text-[var(--text-primary)]"
          onclick={() => formatLinePrefix('## ')}
          title="Heading 2"
        >H2</button>
        <button
          class="px-2 py-0.5 rounded hover:bg-[var(--card)] text-xs text-[var(--text-primary)]"
          onclick={() => formatLinePrefix('- ')}
          title="Bullet List"
        >• List</button>
        <button
          class="px-2 py-0.5 rounded hover:bg-[var(--card)] text-xs text-[var(--text-primary)]"
          onclick={() => formatLinePrefix('- [ ] ')}
          title="Task Checkbox"
        >[ ]</button>
      </div>

      <button
        class="px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--accent)] flex items-center gap-1 shadow-xs"
        onclick={onOpenMath}
        title="Open Visual Formula Builder (Ctrl+E)"
      >
        <span>∫ Math</span>
      </button>

      <button
        class="px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--accent)] flex items-center gap-1 shadow-xs"
        onclick={onOpenMermaid}
        title="Mermaid Diagrams (Ctrl+M)"
      >
        <span>📊 Mermaid</span>
      </button>

      <button
        class="px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--accent)] flex items-center gap-1 shadow-xs"
        onclick={onOpenCanvas}
        title="Stylus Drawing Canvas (Ctrl+D)"
      >
        <span>✏️ Sketch</span>
      </button>

      <button
        class="px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--accent)] flex items-center gap-1 shadow-xs"
        onclick={onOpenPlotter}
        title="2D Function Curve Plotter (Ctrl+P)"
      >
        <span>📈 Plot</span>
      </button>

      <!-- AI Study Guide Synthesis -->
      <button
        class="px-2.5 py-1 rounded-lg text-xs font-medium bg-indigo-950/40 hover:bg-indigo-900/50 border border-indigo-500/40 text-indigo-300 flex items-center gap-1 shadow-xs transition-colors"
        onclick={handleSynthesizeStudyGuide}
        disabled={isSynthesizing}
        title="Synthesize Structured Study Guide with Formulas"
      >
        {#if isSynthesizing}
          <span class="animate-spin inline-block w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full"></span>
          <span>Synthesizing...</span>
        {:else}
          <span>✨ Study Guide</span>
        {/if}
      </button>

      <button
        class="px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--accent)] flex items-center gap-1 shadow-xs transition-colors"
        onclick={onAutoOrganize}
        title="Auto-organize note into smart folder & assign domain icon"
      >
        <span>🪄 Organize</span>
      </button>

      <button
        class="px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 shadow-sm transition-colors"
        onclick={onFactCheck}
        title="Run Autonomous Fact-Checking (Ctrl+Shift+F)"
      >
        <span>🔍 Fact-Check</span>
      </button>
    </div>
  </div>

  <!-- Obsidian-Style Live Preview CodeMirror Workspace (Single Unified Pane) -->
  <div class="flex-1 min-h-0 h-full w-full relative overflow-hidden bg-[var(--bg-primary)]">
    <div
      bind:this={editorContainer}
      class="h-full w-full"
    ></div>
  </div>

  <!-- Status Bar Footer -->
  <div class="px-3 py-1.5 border-t border-[var(--border)] bg-[var(--bg-secondary)] flex items-center justify-between text-[11px] text-[var(--text-secondary)] shrink-0">
    <div class="flex items-center gap-3">
      <span class="flex items-center gap-1.5">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
        <span class="font-mono">{isLivePreview ? 'Obsidian Live Preview' : 'Source Mode'}</span>
      </span>
      <span>•</span>
      <span>{wordCount} words ({charCount} chars)</span>
    </div>

    <div class="flex items-center gap-2">
      {#if isSaving}
        <span class="text-[var(--accent)] font-medium">Saving...</span>
      {:else}
        <span class="text-emerald-400">✓ Saved Offline</span>
      {/if}
    </div>
  </div>
</div>

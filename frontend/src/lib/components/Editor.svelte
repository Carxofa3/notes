<script>
  import { onMount, onDestroy } from 'svelte';
  import katex from 'katex';
  import 'katex/dist/katex.min.css';
  import * as Y from 'yjs';
  import { Editor } from '@tiptap/core';
  import StarterKit from '@tiptap/starter-kit';
  import Placeholder from '@tiptap/extension-placeholder';
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
  let isSaving = $state(false);
  let isSynthesizing = $state(false);
  let saveTimer = null;
  let syncStatus = $state('Local-first (CRDT ready)');
  let editorMode = $state('markdown'); // 'markdown' | 'tiptap'

  // TipTap element & instance
  let editorElement = $state(null);
  let editorInstance = null;

  // Yjs CRDT & WebSocket P2P State
  let ydoc = null;
  let ytext = null;
  let ws = null;
  let isRemoteSync = false;

  $effect(() => {
    if (note) {
      title = note.title || '';
      content = note.content || '';
      setupYjsSync(note.id);
      if (editorInstance && !editorInstance.isDestroyed) {
        editorInstance.commands.setContent(formatMarkdownToHtml(content), false);
      }
    }
  });

  $effect(() => {
    if (editorMode === 'tiptap') {
      setTimeout(initTipTap, 50);
    }
  });

  onMount(() => {
    if (editorMode === 'tiptap') {
      initTipTap();
    }
  });

  onDestroy(() => {
    if (ws) {
      try { ws.close(); } catch (_) {}
    }
    if (editorInstance) {
      editorInstance.destroy();
      editorInstance = null;
    }
  });

  function setupYjsSync(noteId) {
    if (!noteId) return;

    if (ws) {
      try { ws.close(); } catch (_) {}
    }

    ydoc = new Y.Doc();
    ytext = ydoc.getText('note-content');

    if (content && ytext.length === 0) {
      ydoc.transact(() => {
        ytext.insert(0, content);
      }, 'init');
    }

    // Broadcast local CRDT deltas over Tailscale WebSocket
    ydoc.on('update', (update, origin) => {
      if (origin !== 'remote' && ws && ws.readyState === WebSocket.OPEN) {
        const msg = new Uint8Array(1 + update.length);
        msg[0] = 1; // Message type 1: CRDT update delta
        msg.set(update, 1);
        ws.send(msg);
      }
    });

    try {
      const wsUrl = `ws://${window.location.hostname || '127.0.0.1'}:58855/note-${noteId}`;
      ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        syncStatus = 'P2P Tailscale Connected (0.0.0.0:58855)';
        // Step 1: Send client state vector to server
        const sv = Y.encodeStateVector(ydoc);
        const msg = new Uint8Array(1 + sv.length);
        msg[0] = 0; // Message type 0: state vector
        msg.set(sv, 1);
        ws.send(msg);
      };

      ws.onmessage = (event) => {
        try {
          const buf = new Uint8Array(event.data);
          if (buf.length === 0) return;
          const msgType = buf[0];
          const payload = buf.subarray(1);

          if (msgType === 0) {
            // Server sent state vector -> reply with missing update
            const diff = Y.encodeStateAsUpdate(ydoc, payload);
            if (diff.length > 0) {
              const reply = new Uint8Array(1 + diff.length);
              reply[0] = 1;
              reply.set(diff, 1);
              ws.send(reply);
            }
          } else if (msgType === 1) {
            // Server or peer sent CRDT delta -> apply to doc
            isRemoteSync = true;
            Y.applyUpdate(ydoc, payload, 'remote');
            const updated = ytext.toString();
            if (updated && updated !== content) {
              content = updated;
              if (editorInstance && !editorInstance.isDestroyed) {
                editorInstance.commands.setContent(formatMarkdownToHtml(content), false);
              }
              onSave({ title, content });
            }
            isRemoteSync = false;
          }
        } catch (err) {
          console.error('[CRDT WS] Delta processing error:', err);
        }
      };

      ws.onclose = () => {
        syncStatus = 'Local-only (P2P mesh standby)';
      };

      ws.onerror = () => {
        syncStatus = 'Local-first offline mode';
      };
    } catch (_) {
      syncStatus = 'Local-first offline mode';
    }
  }

  function initTipTap() {
    if (!editorElement || editorInstance) return;
    try {
      editorInstance = new Editor({
        element: editorElement,
        extensions: [
          StarterKit,
          Placeholder.configure({
            placeholder: 'Type rich lecture notes here with headings, lists, bold, and code blocks...'
          })
        ],
        content: formatMarkdownToHtml(content),
        onUpdate: ({ editor }) => {
          if (!isRemoteSync) {
            content = htmlToMarkdown(editor.getHTML());
            handleContentChange();
          }
        }
      });
    } catch (e) {
      console.error('Failed to initialize TipTap:', e);
    }
  }

  function handleContentChange() {
    if (!isRemoteSync && ydoc && ytext) {
      const currentY = ytext.toString();
      if (currentY !== content) {
        ydoc.transact(() => {
          ytext.delete(0, ytext.length);
          ytext.insert(0, content);
        }, 'local');
      }
    }

    clearTimeout(saveTimer);
    isSaving = true;
    saveTimer = setTimeout(() => {
      onSave({ title, content });
      isSaving = false;
    }, 1200);
  }

  export function insertText(snippet) {
    content += snippet;
    if (editorInstance && !editorInstance.isDestroyed) {
      editorInstance.commands.setContent(formatMarkdownToHtml(content), false);
    }
    handleContentChange();
  }

  async function handleSynthesizeStudyGuide() {
    if (!content.trim()) return;
    isSynthesizing = true;
    try {
      const res = await synthesizeLectureNotes(content);
      if (res && res.synthesized_content) {
        content += `\n\n## 🎓 AI Lecture Study Guide & Key Formulas\n${res.synthesized_content}\n`;
        if (editorInstance && !editorInstance.isDestroyed) {
          editorInstance.commands.setContent(formatMarkdownToHtml(content), false);
        }
        handleContentChange();
      }
    } catch (e) {
      console.error('Study guide synthesis failed:', e);
    } finally {
      isSynthesizing = false;
    }
  }

  function formatMarkdownToHtml(md) {
    if (!md) return '<p></p>';
    return md
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/`([^`]+)`/gim, '<code>$1</code>')
      .replace(/\n\n/g, '<p></p>')
      .replace(/\n/g, '<br/>');
  }

  function htmlToMarkdown(html) {
    if (!html) return '';
    let text = html
      .replace(/<h1>(.*?)<\/h1>/gi, '# $1\n\n')
      .replace(/<h2>(.*?)<\/h2>/gi, '## $1\n\n')
      .replace(/<h3>(.*?)<\/h3>/gi, '### $1\n\n')
      .replace(/<strong>(.*?)<\/strong>/gi, '**$1**')
      .replace(/<b>(.*?)<\/b>/gi, '**$1**')
      .replace(/<em>(.*?)<\/em>/gi, '*$1*')
      .replace(/<i>(.*?)<\/i>/gi, '*$1*')
      .replace(/<code>(.*?)<\/code>/gi, '`$1`')
      .replace(/<li>(.*?)<\/li>/gi, '- $1\n')
      .replace(/<p>(.*?)<\/p>/gi, '$1\n\n')
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]+>/g, '');
    return text.trim();
  }

  // Render live Markdown preview with KaTeX equations
  let renderedPreview = $derived.by(() => {
    if (!content) return '<p class="text-[var(--text-secondary)] italic">Start typing your lecture notes or insert math & diagrams...</p>';

    let text = content;

    // 1. Block math: $$ ... $$
    text = text.replace(/\$\$([\s\S]+?)\$\$/g, (match, formula) => {
      try {
        return `<div class="my-4 py-2 px-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] overflow-x-auto text-center">${katex.renderToString(formula, { displayMode: true, throwOnError: false })}</div>`;
      } catch {
        return match;
      }
    });

    // 2. Inline math: $ ... $
    text = text.replace(/\$([^\$\n]+?)\$/g, (match, formula) => {
      try {
        return `<span class="px-1 py-0.5 rounded bg-[var(--bg-secondary)] text-[var(--accent)] font-serif">${katex.renderToString(formula, { displayMode: false, throwOnError: false })}</span>`;
      } catch {
        return match;
      }
    });

    // 3. Inline Fact-check annotations
    text = text.replace(/\[🟢 Verified: (.*?)\]/g, '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-500/50">🟢 Verified: $1</span>');
    text = text.replace(/\[🔴 Disputed: (.*?)\]/g, '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-950/60 text-rose-300 border border-rose-500/50">🔴 Disputed: $1</span>');

    // Basic markdown formatting
    text = text
      .replace(/^### (.*$)/gim, '<h3 class="text-base font-bold text-[var(--text-primary)] mt-3 mb-1">$1</h3>')
      .replace(/^## (.*$)/gim, '<h2 class="text-lg font-bold text-[var(--text-primary)] mt-4 mb-2">$1</h2>')
      .replace(/^# (.*$)/gim, '<h1 class="text-xl font-extrabold text-[var(--accent)] mt-5 mb-2">$1</h1>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/!\[(.*?)\]\((.*?)\)/gim, '<img alt="$1" src="$2" class="max-w-full rounded-xl border border-[var(--border)] my-3 shadow-md" />')
      .replace(/\n/gim, '<br/>');

    return text;
  });

  let wordCount = $derived(content ? content.trim().split(/\s+/).filter(Boolean).length : 0);
  let charCount = $derived(content ? content.length : 0);
</script>

<div class="h-full flex flex-col bg-[var(--bg-primary)] overflow-hidden">
  <!-- Top Editor Toolbar -->
  <div class="flex flex-wrap items-center justify-between p-3 border-b border-[var(--border)] bg-[var(--bg-secondary)] gap-2">
    <!-- Title Input -->
    <input
      type="text"
      bind:value={title}
      oninput={handleContentChange}
      placeholder="Lecture Note Title..."
      class="text-base font-bold bg-transparent text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-hidden flex-1 min-w-[180px]"
    />

    <!-- Editor Mode Toggle & Action Shortcuts -->
    <div class="flex items-center gap-1.5 flex-wrap">
      <!-- Mode Toggle: TipTap vs Dual-Pane Markdown -->
      <div class="flex rounded-lg bg-[var(--bg-tertiary)] p-0.5 border border-[var(--border)]">
        <button
          class="px-2 py-1 rounded-md text-xs font-semibold transition-colors {editorMode === 'markdown' ? 'bg-[var(--accent)] text-white shadow-xs' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
          onclick={() => editorMode = 'markdown'}
          title="Markdown & KaTeX Split Preview Mode"
        >
          MD + KaTeX
        </button>
        <button
          class="px-2 py-1 rounded-md text-xs font-semibold transition-colors {editorMode === 'tiptap' ? 'bg-[var(--accent)] text-white shadow-xs' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
          onclick={() => { editorMode = 'tiptap'; setTimeout(initTipTap, 50); }}
          title="TipTap ProseMirror Rich Visual Editor"
        >
          TipTap Rich
        </button>
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

      <!-- Heavy LLM Synthesis Button -->
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

  <!-- TipTap Sub-Toolbar (When in TipTap Rich Mode) -->
  {#if editorMode === 'tiptap'}
    <div class="px-3 py-1.5 border-b border-[var(--border)] bg-[var(--bg-tertiary)] flex items-center gap-1 flex-wrap text-xs">
      <button
        class="px-2 py-0.5 rounded hover:bg-[var(--card)] font-bold {editorInstance?.isActive('bold') ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-primary)]'}"
        onclick={() => editorInstance?.chain().focus().toggleBold().run()}
      >B</button>
      <button
        class="px-2 py-0.5 rounded hover:bg-[var(--card)] italic {editorInstance?.isActive('italic') ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-primary)]'}"
        onclick={() => editorInstance?.chain().focus().toggleItalic().run()}
      >I</button>
      <button
        class="px-2 py-0.5 rounded hover:bg-[var(--card)] {editorInstance?.isActive('heading', { level: 1 }) ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-primary)]'}"
        onclick={() => editorInstance?.chain().focus().toggleHeading({ level: 1 }).run()}
      >H1</button>
      <button
        class="px-2 py-0.5 rounded hover:bg-[var(--card)] {editorInstance?.isActive('heading', { level: 2 }) ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-primary)]'}"
        onclick={() => editorInstance?.chain().focus().toggleHeading({ level: 2 }).run()}
      >H2</button>
      <button
        class="px-2 py-0.5 rounded hover:bg-[var(--card)] {editorInstance?.isActive('bulletList') ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-primary)]'}"
        onclick={() => editorInstance?.chain().focus().toggleBulletList().run()}
      >• List</button>
      <button
        class="px-2 py-0.5 rounded hover:bg-[var(--card)] {editorInstance?.isActive('codeBlock') ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-primary)]'}"
        onclick={() => editorInstance?.chain().focus().toggleCodeBlock().run()}
      >&lt;/&gt; Code</button>
      <button
        class="px-2 py-0.5 rounded hover:bg-[var(--card)] {editorInstance?.isActive('blockquote') ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-primary)]'}"
        onclick={() => editorInstance?.chain().focus().toggleBlockquote().run()}
      >“ Quote</button>
      <div class="h-4 w-px bg-[var(--border)] mx-1"></div>
      <button
        class="px-2 py-0.5 rounded hover:bg-[var(--card)] text-[var(--text-secondary)]"
        onclick={() => editorInstance?.chain().focus().undo().run()}
      >↶ Undo</button>
      <button
        class="px-2 py-0.5 rounded hover:bg-[var(--card)] text-[var(--text-secondary)]"
        onclick={() => editorInstance?.chain().focus().redo().run()}
      >↷ Redo</button>
    </div>
  {/if}

  <!-- Main Split Editor Workspace -->
  <div class="flex-1 min-h-0 overflow-hidden">
    {#if editorMode === 'markdown'}
      <div class="h-full grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-[var(--border)] overflow-hidden">
        <!-- Editor Input Pane -->
        <div class="h-full flex flex-col p-4 bg-[var(--bg-primary)]">
          <textarea
            bind:value={content}
            oninput={handleContentChange}
            placeholder="Type lecture notes here... Supports Markdown, $inline math$, $$block math$$, Mermaid code blocks, and embedded canvas sketches."
            class="w-full flex-1 bg-transparent text-[var(--text-primary)] placeholder-[var(--text-secondary)] font-mono text-sm leading-relaxed resize-none focus:outline-hidden"
          ></textarea>
        </div>

        <!-- Live KaTeX & Rich-Text Preview Pane -->
        <div class="h-full flex flex-col p-4 bg-[var(--card)] overflow-y-auto">
          <div class="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>Live KaTeX & Layout Preview</span>
            <span class="text-emerald-400 font-mono">Instant Render</span>
          </div>
          <div class="prose-editor text-[var(--text-primary)] text-sm leading-relaxed">
            {@html renderedPreview}
          </div>
        </div>
      </div>
    {:else}
      <!-- TipTap ProseMirror Rich Visual Editor View -->
      <div class="h-full p-6 bg-[var(--card)] overflow-y-auto">
        <div
          bind:this={editorElement}
          class="prose-editor text-[var(--text-primary)] text-sm leading-relaxed min-h-[400px] focus:outline-hidden"
        ></div>
      </div>
    {/if}
  </div>

  <!-- Status Bar Footer -->
  <div class="px-3 py-1.5 border-t border-[var(--border)] bg-[var(--bg-secondary)] flex items-center justify-between text-[11px] text-[var(--text-secondary)]">
    <div class="flex items-center gap-3">
      <span class="flex items-center gap-1.5">
        <span class="w-1.5 h-1.5 rounded-full {syncStatus.includes('Connected') ? 'bg-emerald-400' : 'bg-amber-400'}"></span>
        <span class="font-mono">{syncStatus}</span>
      </span>
      <span>•</span>
      <span>{wordCount} words ({charCount} chars)</span>
    </div>

    <div class="flex items-center gap-2">
      {#if isSaving}
        <span class="text-[var(--accent)] font-medium">Saving...</span>
      {:else}
        <span class="text-emerald-400">✓ Saved (Tier 1/2)</span>
      {/if}
    </div>
  </div>
</div>

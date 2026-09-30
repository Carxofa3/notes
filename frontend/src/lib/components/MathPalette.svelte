<script>
  import { MATH_SYMBOLS } from '../types.js';
  import katex from 'katex';
  import 'katex/dist/katex.min.css';

  let { onInsert = () => {}, onClose = () => {} } = $props();

  let activeCategory = $state('Calculus');
  let currentLatex = $state('\\int_{0}^{\\infty} e^{-x^2} \\, dx = \\frac{\\sqrt{\\pi}}{2}');
  let displayMode = $state(true);

  let renderedHtml = $derived.by(() => {
    try {
      return katex.renderToString(currentLatex || ' ', {
        throwOnError: false,
        displayMode: displayMode
      });
    } catch (err) {
      return `<span class="text-red-400">Syntax Error: ${err.message}</span>`;
    }
  });

  function appendSymbol(latexSnippet) {
    if (!currentLatex || currentLatex.trim() === '') {
      currentLatex = latexSnippet;
    } else {
      currentLatex += ' ' + latexSnippet;
    }
  }

  function handleInsert() {
    if (currentLatex.trim()) {
      const formatted = displayMode ? `\n\n$$${currentLatex}$$\n\n` : `$${currentLatex}$`;
      onInsert(formatted);
    }
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
  <div class="w-full max-w-2xl rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl p-6 flex flex-col gap-4">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
      <div>
        <h2 class="text-lg font-bold text-[var(--text-primary)]">MathLive Visual Formula Builder</h2>
        <p class="text-xs text-[var(--text-secondary)]">Click math templates or type LaTeX directly for instant lecture notes</p>
      </div>
      <button 
        class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1"
        onclick={onClose}
      >&times;</button>
    </div>

    <!-- Live KaTeX Preview Box -->
    <div class="p-6 rounded-xl bg-[var(--card)] border border-[var(--border)] min-h-[90px] flex items-center justify-center overflow-x-auto text-[var(--text-primary)]">
      {@html renderedHtml}
    </div>

    <!-- LaTeX Code Input -->
    <div class="flex flex-col gap-1.5">
      <div class="flex items-center justify-between text-xs text-[var(--text-secondary)]">
        <span>LaTeX Code</span>
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" bind:checked={displayMode} class="accent-[var(--accent)]" />
          <span>Block Mode ($$)</span>
        </label>
      </div>
      <input 
        type="text" 
        bind:value={currentLatex}
        class="w-full px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-primary)] font-mono text-sm focus:outline-hidden focus:border-[var(--accent)]"
        placeholder="Type or click symbols below..."
      />
    </div>

    <!-- Category Tabs -->
    <div class="flex gap-1 border-b border-[var(--border)] pb-1 overflow-x-auto">
      {#each Object.keys(MATH_SYMBOLS) as cat}
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors {activeCategory === cat ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'}"
          onclick={() => activeCategory = cat}
        >
          {cat}
        </button>
      {/each}
    </div>

    <!-- Visual Symbol Palette Grid -->
    <div class="grid grid-cols-4 sm:grid-cols-6 gap-2 max-h-40 overflow-y-auto p-1">
      {#each MATH_SYMBOLS[activeCategory] || [] as item}
        <button
          class="flex flex-col items-center justify-center p-2 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] transition-transform hover:scale-105 active:scale-95"
          onclick={() => appendSymbol(item.latex)}
          title={item.latex}
        >
          <span class="text-xs font-semibold text-[var(--text-primary)]">{item.label}</span>
          <span class="text-[10px] text-[var(--text-secondary)] font-mono truncate max-w-[80px]">{item.latex}</span>
        </button>
      {/each}
    </div>

    <!-- Footer Controls -->
    <div class="flex justify-end gap-3 pt-2 border-t border-[var(--border)]">
      <button
        class="px-4 py-2 rounded-xl text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
        onclick={onClose}
      >
        Cancel
      </button>
      <button
        class="px-5 py-2 rounded-xl text-sm font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity shadow-md"
        onclick={handleInsert}
      >
        Insert Formula into Note
      </button>
    </div>
  </div>
</div>

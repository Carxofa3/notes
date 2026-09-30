<script>
  import mermaid from 'mermaid';
  import { onMount } from 'svelte';
  import { MERMAID_TEMPLATES } from '../types.js';

  let { onInsert = () => {}, onClose = () => {} } = $props();

  let code = $state(MERMAID_TEMPLATES[0].code);
  let svgContainer = $state(null);
  let renderError = $state('');
  let zoomLevel = $state(1.0);
  let diagramId = 'mermaid-' + Math.random().toString(36).substring(2, 9);

  onMount(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose'
    });
    renderDiagram();
  });

  async function renderDiagram() {
    renderError = '';
    if (!code.trim() || !svgContainer) return;
    try {
      diagramId = 'mermaid-' + Math.random().toString(36).substring(2, 9);
      const { svg } = await mermaid.render(diagramId, code);
      if (svgContainer) {
        svgContainer.innerHTML = svg;
      }
    } catch (err) {
      renderError = err.message || 'Syntax error in Mermaid definition';
    }
  }

  function handleInsert() {
    if (code.trim()) {
      onInsert(`\n\n\`\`\`mermaid\n${code}\n\`\`\`\n\n`);
    }
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 sm:p-4">
  <div class="w-full max-w-[95vw] sm:max-w-4xl max-h-[92vh] overflow-y-auto rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl p-4 sm:p-6 flex flex-col gap-3.5">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
      <div>
        <h2 class="text-base sm:text-lg font-bold text-[var(--text-primary)]">Mermaid.js Diagram Studio</h2>
        <p class="text-[11px] sm:text-xs text-[var(--text-secondary)]">Create flowcharts, sequence diagrams, class hierarchies & state machines</p>
      </div>
      <button 
        class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1"
        onclick={onClose}
      >&times;</button>
    </div>

    <!-- Template Pills (Smooth swipe on mobile) -->
    <div class="flex gap-1.5 items-center text-xs text-[var(--text-secondary)] overflow-x-auto no-scrollbar flex-nowrap shrink-0">
      <span class="shrink-0 font-medium">Templates:</span>
      {#each MERMAID_TEMPLATES as tmpl}
        <button
          class="shrink-0 px-2.5 py-1 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] font-medium"
          onclick={() => { code = tmpl.code; renderDiagram(); }}
        >
          {tmpl.name}
        </button>
      {/each}
    </div>

    <!-- Main Workspace (Editor + SVG Preview) -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3 flex-1 min-h-[350px]">
      <!-- Code Editor Side -->
      <div class="flex flex-col gap-2 h-full">
        <span class="text-xs font-semibold text-[var(--text-secondary)]">Mermaid DSL Code</span>
        <textarea
          bind:value={code}
          oninput={renderDiagram}
          class="w-full flex-1 p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-primary)] font-mono text-xs resize-none focus:outline-hidden focus:border-[var(--accent)] leading-relaxed"
          placeholder="graph TD..."
        ></textarea>
        {#if renderError}
          <div class="p-2 rounded-lg bg-red-950/40 border border-red-500/50 text-red-300 text-xs">
            {renderError}
          </div>
        {/if}
      </div>

      <!-- Live Diagram Preview Side -->
      <div class="flex flex-col gap-2 h-full">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-[var(--text-secondary)]">Live SVG Preview</span>
          <div class="flex items-center gap-2">
            <button
              class="px-2 py-0.5 rounded bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-xs border border-[var(--border)]"
              onclick={() => zoomLevel = Math.max(0.5, zoomLevel - 0.2)}
            >-</button>
            <span class="text-xs font-mono">{Math.round(zoomLevel * 100)}%</span>
            <button
              class="px-2 py-0.5 rounded bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-xs border border-[var(--border)]"
              onclick={() => zoomLevel = Math.min(2.5, zoomLevel + 0.2)}
            >+</button>
          </div>
        </div>

        <div class="flex-1 overflow-auto rounded-xl bg-[var(--card)] border border-[var(--border)] p-4 flex items-center justify-center">
          <div
            bind:this={svgContainer}
            class="transition-transform duration-100 flex items-center justify-center w-full h-full"
            style="transform: scale({zoomLevel});"
          ></div>
        </div>
      </div>
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
        Insert Diagram into Note
      </button>
    </div>
  </div>
</div>

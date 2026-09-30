<script>
  import { onMount } from 'svelte';

  let { onInsert = () => {}, onClose = () => {} } = $props();

  let canvas = $state(null);
  let ctx = null;

  let activeTool = $state('pen'); // 'pen' | 'highlighter' | 'eraser' | 'rect' | 'circle' | 'arrow' | 'line'
  let strokeColor = $state('#89b4fa');
  let strokeWidth = $state(3);
  let palmRejection = $state(true); // S-Pen / Stylus only mode

  let isDrawing = false;
  let startX = 0;
  let startY = 0;
  let snapshot = null;

  // History stack for Undo/Redo
  let history = $state([]);
  let historyStep = $state(-1);

  const COLORS = ['#89b4fa', '#a6e3a1', '#f9e2af', '#f38ba8', '#cba6f7', '#cdd6f4', '#11111b'];

  onMount(() => {
    if (canvas) {
      // Responsive canvas size matching screen
      canvas.width = canvas.parentElement.clientWidth || 800;
      canvas.height = canvas.parentElement.clientHeight || 500;
      ctx = canvas.getContext('2d', { willReadFrequently: true });
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      saveHistory();
    }
  });

  function saveHistory() {
    if (!ctx || !canvas) return;
    historyStep++;
    history = history.slice(0, historyStep);
    history.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
  }

  function undo() {
    if (historyStep > 0) {
      historyStep--;
      ctx.putImageData(history[historyStep], 0, 0);
    }
  }

  function redo() {
    if (historyStep < history.length - 1) {
      historyStep++;
      ctx.putImageData(history[historyStep], 0, 0);
    }
  }

  function clearCanvas() {
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    saveHistory();
  }

  function handlePointerDown(e) {
    // Palm rejection: if enabled, ignore touch if pen is detected
    if (palmRejection && e.pointerType === 'touch') {
      return;
    }

    isDrawing = true;
    const rect = canvas.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;

    ctx.beginPath();
    ctx.moveTo(startX, startY);

    if (activeTool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.lineWidth = strokeWidth * 4;
    } else if (activeTool === 'highlighter') {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = strokeColor + '55'; // 33% opacity
      ctx.lineWidth = strokeWidth * 3;
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = strokeColor;
      // Stylus pressure sensitivity
      const pressureMultiplier = e.pressure > 0 ? (0.5 + e.pressure) : 1;
      ctx.lineWidth = strokeWidth * pressureMultiplier;
    }

    snapshot = ctx.getImageData(0, 0, canvas.width, canvas.height);
  }

  function handlePointerMove(e) {
    if (!isDrawing) return;
    if (palmRejection && e.pointerType === 'touch') return;

    const rect = canvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    if (['pen', 'highlighter', 'eraser'].includes(activeTool)) {
      if (activeTool === 'pen' && e.pressure > 0) {
        ctx.lineWidth = strokeWidth * (0.5 + e.pressure);
      }
      ctx.lineTo(currentX, currentY);
      ctx.stroke();
    } else {
      // Geometric shapes: restore snapshot then draw preview
      ctx.putImageData(snapshot, 0, 0);
      ctx.beginPath();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = strokeWidth;

      if (activeTool === 'line') {
        ctx.moveTo(startX, startY);
        ctx.lineTo(currentX, currentY);
        ctx.stroke();
      } else if (activeTool === 'rect') {
        ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
      } else if (activeTool === 'circle') {
        const radius = Math.hypot(currentX - startX, currentY - startY);
        ctx.arc(startX, startY, radius, 0, Math.PI * 2);
        ctx.stroke();
      } else if (activeTool === 'arrow') {
        drawArrow(ctx, startX, startY, currentX, currentY);
      }
    }
  }

  function handlePointerUp() {
    if (!isDrawing) return;
    isDrawing = false;
    ctx.closePath();
    saveHistory();
  }

  function drawArrow(context, fromx, fromy, tox, toy) {
    const headlen = 12;
    const dx = tox - fromx;
    const dy = toy - fromy;
    const angle = Math.atan2(dy, dx);
    context.moveTo(fromx, fromy);
    context.lineTo(tox, toy);
    context.lineTo(tox - headlen * Math.cos(angle - Math.PI / 6), toy - headlen * Math.sin(angle - Math.PI / 6));
    context.moveTo(tox, toy);
    context.lineTo(tox - headlen * Math.cos(angle + Math.PI / 6), toy - headlen * Math.sin(angle + Math.PI / 6));
    context.stroke();
  }

  function handleInsert() {
    if (!canvas) return;
    const dataUrl = canvas.toDataURL('image/png');
    onInsert(`\n\n![Stylus Drawing](${dataUrl})\n\n`);
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
  <div class="w-full max-w-5xl h-[85vh] rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl p-6 flex flex-col gap-3">
    <!-- Header with controls -->
    <div class="flex flex-wrap items-center justify-between border-b border-[var(--border)] pb-3 gap-3">
      <div>
        <h2 class="text-lg font-bold text-[var(--text-primary)]">Freeform Stylus & Diagram Canvas</h2>
        <p class="text-xs text-[var(--text-secondary)]">Excalidraw-style sketching with native S-Pen / stylus palm rejection</p>
      </div>

      <!-- Action Tools -->
      <div class="flex items-center gap-2">
        <label class="flex items-center gap-1.5 text-xs text-[var(--text-secondary)] bg-[var(--bg-secondary)] px-2.5 py-1.5 rounded-lg border border-[var(--border)] cursor-pointer">
          <input type="checkbox" bind:checked={palmRejection} class="accent-[var(--accent)]" />
          <span>Palm Rejection (Stylus Priority)</span>
        </label>
        <button
          class="px-2.5 py-1.5 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-xs border border-[var(--border)]"
          onclick={undo}
          disabled={historyStep <= 0}
        >Undo</button>
        <button
          class="px-2.5 py-1.5 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-xs border border-[var(--border)]"
          onclick={redo}
          disabled={historyStep >= history.length - 1}
        >Redo</button>
        <button
          class="px-2.5 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/50 text-red-300 text-xs border border-red-500/30"
          onclick={clearCanvas}
        >Clear</button>
        <button 
          class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1 ml-2"
          onclick={onClose}
        >&times;</button>
      </div>
    </div>

    <!-- Toolbar: Drawing Tools, Shapes, Colors, Size -->
    <div class="flex flex-wrap items-center justify-between gap-3 p-2 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)]">
      <!-- Tools -->
      <div class="flex items-center gap-1">
        {#each [
          { id: 'pen', label: 'Pen' },
          { id: 'highlighter', label: 'Highlighter' },
          { id: 'eraser', label: 'Eraser' },
          { id: 'rect', label: 'Rectangle' },
          { id: 'circle', label: 'Circle' },
          { id: 'arrow', label: 'Arrow' },
          { id: 'line', label: 'Line' }
        ] as t}
          <button
            class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors {activeTool === t.id ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'}"
            onclick={() => activeTool = t.id}
          >
            {t.label}
          </button>
        {/each}
      </div>

      <!-- Color Swatches -->
      <div class="flex items-center gap-1.5">
        {#each COLORS as col}
          <button
            class="w-6 h-6 rounded-full border-2 transition-transform hover:scale-110 {strokeColor === col ? 'border-white scale-110 shadow-md' : 'border-transparent'}"
            style="background-color: {col};"
            onclick={() => strokeColor = col}
          ></button>
        {/each}
      </div>

      <!-- Stroke Width Slider -->
      <div class="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
        <span>Size</span>
        <input type="range" min="1" max="16" bind:value={strokeWidth} class="w-20 accent-[var(--accent)]" />
        <span class="font-mono w-4">{strokeWidth}</span>
      </div>
    </div>

    <!-- Drawing Surface -->
    <div class="flex-1 w-full h-full relative rounded-xl overflow-hidden bg-[var(--card)] border border-[var(--border)] touch-none cursor-crosshair">
      <canvas
        bind:this={canvas}
        onpointerdown={handlePointerDown}
        onpointermove={handlePointerMove}
        onpointerup={handlePointerUp}
        class="w-full h-full block"
      ></canvas>
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
        Insert Sketch into Note
      </button>
    </div>
  </div>
</div>

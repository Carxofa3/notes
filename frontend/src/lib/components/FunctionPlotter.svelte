<script>
  import { onMount } from 'svelte';

  let { onInsert = () => {}, onClose = () => {} } = $props();

  let canvas = $state(null);
  let ctx = null;

  let equation = $state('sin(x) * x');
  let paramA = $state(1.0);
  let paramB = $state(2.0);
  let xRange = $state([-10, 10]);
  let yRange = $state([-6, 6]);

  const PRESETS = [
    { name: 'Damped Sine', eq: 'sin(x) * exp(-0.2 * abs(x))' },
    { name: 'Normal Bell Curve', eq: 'exp(-0.5 * (x^2)) / sqrt(2 * pi)' },
    { name: 'Sigmoid / Logistic', eq: '1 / (1 + exp(-x))' },
    { name: 'Cubic Polynomial', eq: '0.1 * x^3 - x' }
  ];

  onMount(() => {
    if (canvas) {
      canvas.width = canvas.parentElement.clientWidth || 700;
      canvas.height = canvas.parentElement.clientHeight || 400;
      ctx = canvas.getContext('2d');
      drawPlot();
    }
  });

  // Safe mathematical parser
  function evaluateFunc(xVal, expr) {
    try {
      let sanitized = expr
        .replace(/\bpi\b/g, 'Math.PI')
        .replace(/\be\b/g, 'Math.E')
        .replace(/\bsin\b/g, 'Math.sin')
        .replace(/\bcos\b/g, 'Math.cos')
        .replace(/\btan\b/g, 'Math.tan')
        .replace(/\bexp\b/g, 'Math.exp')
        .replace(/\bsqrt\b/g, 'Math.sqrt')
        .replace(/\babs\b/g, 'Math.abs')
        .replace(/\ba\b/g, `(${paramA})`)
        .replace(/\bb\b/g, `(${paramB})`)
        .replace(/\^/g, '**');

      const fn = new Function('x', `return ${sanitized};`);
      const val = fn(xVal);
      return Number.isFinite(val) ? val : null;
    } catch {
      return null;
    }
  }

  function drawPlot() {
    if (!ctx || !canvas) return;
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    const [xMin, xMax] = xRange;
    const [yMin, yMax] = yRange;

    // Helper conversion
    const toCanvasX = (x) => ((x - xMin) / (xMax - xMin)) * w;
    const toCanvasY = (y) => h - ((y - yMin) / (yMax - yMin)) * h;

    // 1. Draw Grid lines
    ctx.strokeStyle = '#313244';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    for (let x = Math.ceil(xMin); x <= Math.floor(xMax); x += 2) {
      const cx = toCanvasX(x);
      ctx.beginPath();
      ctx.moveTo(cx, 0);
      ctx.lineTo(cx, h);
      ctx.stroke();
    }

    for (let y = Math.ceil(yMin); y <= Math.floor(yMax); y += 2) {
      const cy = toCanvasY(y);
      ctx.beginPath();
      ctx.moveTo(0, cy);
      ctx.lineTo(w, cy);
      ctx.stroke();
    }

    ctx.setLineDash([]); // Reset line dash

    // 2. Draw Axes
    ctx.strokeStyle = '#89b4fa';
    ctx.lineWidth = 2;
    const originX = toCanvasX(0);
    const originY = toCanvasY(0);

    // X Axis
    ctx.beginPath();
    ctx.moveTo(0, originY);
    ctx.lineTo(w, originY);
    ctx.stroke();

    // Y Axis
    ctx.beginPath();
    ctx.moveTo(originX, 0);
    ctx.lineTo(originX, h);
    ctx.stroke();

    // Axis numbers
    ctx.fillStyle = '#a6adc8';
    ctx.font = '11px monospace';
    for (let x = Math.ceil(xMin); x <= Math.floor(xMax); x += 2) {
      if (x !== 0) ctx.fillText(x.toString(), toCanvasX(x) - 6, originY + 14);
    }
    for (let y = Math.ceil(yMin); y <= Math.floor(yMax); y += 2) {
      if (y !== 0) ctx.fillText(y.toString(), originX + 6, toCanvasY(y) + 4);
    }

    // 3. Plot Curve
    ctx.strokeStyle = '#a6e3a1';
    ctx.lineWidth = 2.5;
    ctx.beginPath();

    let isStarting = true;
    const step = (xMax - xMin) / (w * 1.5);

    for (let x = xMin; x <= xMax; x += step) {
      const y = evaluateFunc(x, equation);
      if (y !== null && y >= yMin * 2 && y <= yMax * 2) {
        const cx = toCanvasX(x);
        const cy = toCanvasY(y);
        if (isStarting) {
          ctx.moveTo(cx, cy);
          isStarting = false;
        } else {
          ctx.lineTo(cx, cy);
        }
      } else {
        isStarting = true;
      }
    }
    ctx.stroke();
  }

  function handleInsert() {
    if (!canvas) return;
    const dataUrl = canvas.toDataURL('image/png');
    onInsert(`\n\n![2D Plot: f(x) = ${equation}](${dataUrl})\n*Figure: 2D Curve $f(x) = ${equation}$*\n\n`);
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 sm:p-4">
  <div class="w-full max-w-[95vw] sm:max-w-4xl max-h-[92vh] overflow-y-auto rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl p-4 sm:p-6 flex flex-col gap-3.5">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
      <div>
        <h2 class="text-base sm:text-lg font-bold text-[var(--text-primary)]">2D Function Curve Plotter</h2>
        <p class="text-[11px] sm:text-xs text-[var(--text-secondary)]">Calculus & physics curve visualization with dynamic parameter tuning</p>
      </div>
      <button 
        class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1"
        onclick={onClose}
      >&times;</button>
    </div>

    <!-- Presets (Smooth swipe on mobile) -->
    <div class="flex gap-1.5 items-center text-xs text-[var(--text-secondary)] overflow-x-auto no-scrollbar flex-nowrap shrink-0">
      <span class="shrink-0 font-medium">Presets:</span>
      {#each PRESETS as p}
        <button
          class="shrink-0 px-2.5 py-1 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] font-medium"
          onclick={() => { equation = p.eq; drawPlot(); }}
        >
          {p.name}
        </button>
      {/each}
    </div>

    <!-- Controls Bar -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] items-center">
      <!-- Equation Input -->
      <div class="flex flex-col gap-1 sm:col-span-2">
        <span class="text-xs font-semibold text-[var(--text-secondary)]">Equation: f(x) =</span>
        <input
          type="text"
          bind:value={equation}
          oninput={drawPlot}
          class="w-full px-3 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-[var(--text-primary)] font-mono text-sm focus:outline-hidden focus:border-[var(--accent)]"
          placeholder="e.g. sin(x) * x or exp(-x^2)"
        />
      </div>

      <!-- Parameter Sliders -->
      <div class="flex items-center gap-3">
        <div class="flex flex-col gap-1 w-1/2">
          <span class="text-[10px] text-[var(--text-secondary)]">Param a: {paramA.toFixed(1)}</span>
          <input type="range" min="0.1" max="5" step="0.1" bind:value={paramA} oninput={drawPlot} class="w-full accent-[var(--accent)]" />
        </div>
        <div class="flex flex-col gap-1 w-1/2">
          <span class="text-[10px] text-[var(--text-secondary)]">Param b: {paramB.toFixed(1)}</span>
          <input type="range" min="0.1" max="5" step="0.1" bind:value={paramB} oninput={drawPlot} class="w-full accent-[var(--accent)]" />
        </div>
      </div>
    </div>

    <!-- Canvas Surface -->
    <div class="flex-1 w-full h-full relative rounded-xl overflow-hidden bg-[var(--card)] border border-[var(--border)]">
      <canvas
        bind:this={canvas}
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
        Insert Plot into Note
      </button>
    </div>
  </div>
</div>

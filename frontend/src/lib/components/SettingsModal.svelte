<script>
  import { onMount } from 'svelte';
  import { getServerUrl, setServerUrl, pingServer } from '../api.js';
  import { theme } from '../theme.svelte.js';

  let { isOpen = $bindable(false) } = $props();

  let serverInput = $state('');
  let isTesting = $state(false);
  let pingResult = $state(null);
  let savedMessage = $state('');

  onMount(() => {
    serverInput = getServerUrl();
  });

  function handleSave() {
    const clean = setServerUrl(serverInput);
    serverInput = clean;
    savedMessage = 'Settings saved successfully!';
    setTimeout(() => savedMessage = '', 3000);
  }

  async function handleTest() {
    isTesting = true;
    pingResult = null;
    try {
      const res = await pingServer(serverInput);
      pingResult = res;
    } catch (e) {
      pingResult = { ok: false, error: e.message };
    } finally {
      isTesting = false;
    }
  }

  function handleClearStorage() {
    if (confirm('Warning: This will clear local offline notes on this device. Proceed?')) {
      localStorage.removeItem('notes_offline_lessons');
      localStorage.removeItem('notes_offline_units');
      localStorage.removeItem('notes_offline_notes');
      alert('Local storage reset. Please reload the app.');
      window.location.reload();
    }
  }
</script>

{#if isOpen}
  <div 
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
    onclick={() => isOpen = false}
    role="dialog"
    aria-modal="true"
  >
    <div 
      class="w-full max-w-lg rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl p-6 flex flex-col gap-5 max-h-[90vh] overflow-y-auto"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Modal Header -->
      <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div class="flex items-center gap-2">
          <span class="text-xl">⚙️</span>
          <h2 class="text-base font-bold text-[var(--text-primary)]">Workstation Settings</h2>
        </div>
        <button 
          class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-lg px-2"
          onclick={() => isOpen = false}
        >✕</button>
      </div>

      <!-- Server Connection Section -->
      <div class="flex flex-col gap-2">
        <label class="text-xs font-bold text-[var(--text-primary)] flex items-center justify-between">
          <span>Backend Server / Tailscale Node</span>
          <span class="text-[10px] text-[var(--text-secondary)] font-normal">Optional (offline mode default)</span>
        </label>
        <p class="text-xs text-[var(--text-secondary)]">
          Enter your PC or server's local LAN IP or Tailscale IP to sync notes, run slide RAG, and escalate to your <code class="text-[var(--accent)] font-mono">llama.cpp</code> server.
        </p>
        <div class="flex gap-2">
          <input
            type="text"
            placeholder="e.g. http://192.168.0.45:5000 or http://100.x.y.z:5000"
            bind:value={serverInput}
            class="flex-1 px-3 py-2 text-xs rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--accent)] font-mono"
          />
          <button
            class="px-3 py-2 rounded-xl text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-colors shrink-0"
            onclick={handleTest}
            disabled={isTesting}
          >
            {isTesting ? 'Testing...' : 'Test Ping'}
          </button>
        </div>

        <!-- Quick Connection Presets -->
        <div class="flex flex-wrap items-center gap-1.5 pt-1">
          <span class="text-[11px] text-[var(--text-secondary)] font-medium mr-1">Quick Presets:</span>
          <button
            type="button"
            class="px-2.5 py-1 rounded-lg text-[11px] font-mono bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--accent)] transition-colors"
            onclick={() => { serverInput = 'http://192.168.0.45:5000'; handleTest(); }}
            title="Connect to PC on current home Wi-Fi"
          >
            📡 Home Wi-Fi (192.168.0.45:5000)
          </button>
          <button
            type="button"
            class="px-2.5 py-1 rounded-lg text-[11px] font-mono bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            onclick={() => { serverInput = 'http://127.0.0.1:5000'; handleTest(); }}
            title="Use localhost (for PC desktop app)"
          >
            💻 Localhost (127.0.0.1:5000)
          </button>
        </div>

        <!-- Connection Instructions Card -->
        <div class="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-1.5 text-xs text-[var(--text-secondary)]">
          <span class="font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
            <span>💡 How to connect phone to your computer:</span>
          </span>
          <ol class="list-decimal list-inside space-y-1 text-[11px] leading-relaxed">
            <li>Ensure phone & PC are on the same Wi-Fi network (or both connected via Tailscale).</li>
            <li>On your computer, run <code class="font-mono text-[var(--accent)] px-1 py-0.5 rounded bg-[var(--card)]">python main.py</code> in a terminal.</li>
            <li>Tap <strong class="text-[var(--text-primary)]">Home Wi-Fi (192.168.0.45:5000)</strong> above, test the ping, then tap <strong class="text-[var(--text-primary)]">Save Configuration</strong>!</li>
          </ol>
        </div>

        {#if pingResult}
          <div class="p-2.5 rounded-xl text-xs {pingResult.ok ? 'bg-emerald-950/40 border border-emerald-500/40 text-emerald-300' : 'bg-rose-950/40 border border-rose-500/40 text-rose-300'}">
            {#if pingResult.ok}
              🟢 Connected successfully! Latency: {pingResult.latency}ms
            {:else}
              🔴 Connection failed: {pingResult.error}
            {/if}
          </div>
        {/if}

        <div class="flex items-center justify-between pt-1">
          <button
            class="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
            onclick={handleSave}
          >
            Save Configuration
          </button>
          {#if savedMessage}
            <span class="text-xs text-emerald-400 font-medium">{savedMessage}</span>
          {/if}
        </div>
      </div>

      <!-- Theme Switcher -->
      <div class="flex flex-col gap-2 pt-3 border-t border-[var(--border)]">
        <label class="text-xs font-bold text-[var(--text-primary)]">Application Theme</label>
        <div class="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <button
            class="p-2 rounded-xl text-xs font-medium border text-center transition-all {theme.current === 'dark' ? 'border-[var(--accent)] bg-[var(--card)] text-[var(--accent)] font-bold' : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--card)]'}"
            onclick={() => theme.set('dark')}
          >
            🌙 Midnight
          </button>
          <button
            class="p-2 rounded-xl text-xs font-medium border text-center transition-all {theme.current === 'light' ? 'border-[var(--accent)] bg-[var(--card)] text-[var(--accent)] font-bold' : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--card)]'}"
            onclick={() => theme.set('light')}
          >
            ☀️ Paper White
          </button>
          <button
            class="p-2 rounded-xl text-xs font-medium border text-center transition-all {theme.current === 'solarized' ? 'border-[var(--accent)] bg-[var(--card)] text-[var(--accent)] font-bold' : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--card)]'}"
            onclick={() => theme.set('solarized')}
          >
            🌿 Solarized
          </button>
          <button
            class="p-2 rounded-xl text-xs font-medium border text-center transition-all {theme.current === 'cyberpunk' ? 'border-[var(--accent)] bg-[var(--card)] text-[var(--accent)] font-bold' : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--card)]'}"
            onclick={() => theme.set('cyberpunk')}
          >
            ⚡ Cyberpunk
          </button>
          <button
            class="p-2 rounded-xl text-xs font-medium border text-center transition-all {theme.current === 'amoled' ? 'border-[var(--accent)] bg-[var(--card)] text-[var(--accent)] font-bold' : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--card)]'}"
            onclick={() => theme.set('amoled')}
          >
            🖤 OLED Black
          </button>
        </div>
      </div>

      <!-- Device Storage Info -->
      <div class="flex flex-col gap-2 pt-3 border-t border-[var(--border)]">
        <label class="text-xs font-bold text-[var(--text-primary)]">Offline Local Storage</label>
        <p class="text-xs text-[var(--text-secondary)]">
          All your course lessons, units, and notes are cached locally on this phone with instant zero-lag loading.
        </p>
        <div>
          <button
            class="px-3 py-1.5 rounded-lg text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 border border-rose-500/20 transition-colors"
            onclick={handleClearStorage}
          >
            Clear Local Data Cache
          </button>
        </div>
      </div>

      <!-- Close Button -->
      <div class="pt-2 border-t border-[var(--border)] flex justify-end">
        <button
          class="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-colors"
          onclick={() => isOpen = false}
        >
          Close
        </button>
      </div>
    </div>
  </div>
{/if}

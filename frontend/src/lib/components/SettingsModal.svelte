<script>
  import { onMount } from 'svelte';
  import { 
    getServerUrl, 
    setServerUrl, 
    pingServer,
    checkAppUpdates,
    fetchGlinerStatus,
    triggerGlinerDownload,
    checkLocalLlamaCppHealth,
    fetchClusterOverview
  } from '../api.js';
  import {
    getLocalLessons,
    getAllLocalNotes,
    getAllLocalUnits
  } from '../storage.js';
  import { theme } from '../theme.svelte.js';

  let { 
    isOpen = $bindable(false),
    initialTab = 'appearance',
    onOpenPairing = null 
  } = $props();

  let activeTab = $state('appearance');

  // Network & Server State
  let serverInput = $state('');
  let isTesting = $state(false);
  let pingResult = $state(null);
  let savedMessage = $state('');

  // AI & Compute State
  let glinerStatus = $state(null);
  let isTriggeringGliner = $state(false);
  let llamaPort = $state(8080);
  let isTestingLlama = $state(false);
  let llamaHealth = $state(null);
  let hardwareSpecs = $state(null);

  // Storage Stats
  let storageStats = $state({ lessons: 0, units: 0, notes: 0 });

  // About & Auto-Updater State
  let currentAppVer = $state(`v${typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '2.1.7'}`);
  let updateInfo = $state(null);
  let isCheckingUpdate = $state(false);
  let updateError = $state('');

  $effect(() => {
    if (isOpen) {
      if (initialTab) {
        activeTab = initialTab;
      }
      loadSettingsData();
    }
  });

  async function loadSettingsData() {
    serverInput = getServerUrl();
    loadStorageStats();
    if (activeTab === 'compute') {
      await loadComputeData();
    }
  }

  function loadStorageStats() {
    try {
      const lessons = getLocalLessons();
      const units = getAllLocalUnits();
      const notes = getAllLocalNotes();
      storageStats = {
        lessons: lessons ? lessons.length : 0,
        units: units ? units.length : 0,
        notes: notes ? notes.length : 0
      };
    } catch (_) {}
  }

  async function loadComputeData() {
    try {
      const gliner = await fetchGlinerStatus();
      if (gliner) glinerStatus = gliner;
      const cluster = await fetchClusterOverview();
      if (cluster && cluster.hardware) {
        hardwareSpecs = cluster.hardware;
      }
    } catch (_) {}
  }

  function handleSaveServer() {
    const clean = setServerUrl(serverInput);
    serverInput = clean;
    savedMessage = 'Server URL saved!';
    setTimeout(() => savedMessage = '', 3000);
  }

  async function handleTestServer() {
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

  async function handleStartGlinerDownload() {
    isTriggeringGliner = true;
    try {
      const res = await triggerGlinerDownload();
      if (res) {
        glinerStatus = { ...glinerStatus, downloading: true, progress: res.progress || 10 };
      }
    } catch (e) {
      console.error('Failed to trigger GLiNER download:', e);
    } finally {
      isTriggeringGliner = false;
    }
  }

  async function handleTestLlama() {
    isTestingLlama = true;
    llamaHealth = null;
    try {
      const res = await checkLocalLlamaCppHealth();
      llamaHealth = res;
    } catch (e) {
      llamaHealth = { status: 'offline', error: e.message };
    } finally {
      isTestingLlama = false;
    }
  }

  function handleClearStorage() {
    if (confirm('Warning: This will clear locally cached notes on this device. Cloud / PC notes are preserved. Proceed?')) {
      localStorage.removeItem('notes_offline_lessons');
      localStorage.removeItem('notes_offline_units');
      localStorage.removeItem('notes_offline_notes');
      alert('Local storage cleared. The app will now reload.');
      window.location.reload();
    }
  }

  function handleExportNotes() {
    try {
      const exportData = {
        app: 'Notes Workstation',
        version: currentAppVer,
        exported_at: new Date().toISOString(),
        lessons: getLocalLessons(),
        units: getAllLocalUnits(),
        notes: getAllLocalNotes()
      };
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `notes-backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Export failed: ${e.message}`);
    }
  }

  function getPlatformBadge() {
    if (typeof navigator === 'undefined') return 'Desktop';
    if (/android/i.test(navigator.userAgent)) return 'Android Universal';
    if (/win/i.test(navigator.userAgent)) return 'Windows x64';
    return 'Web / Linux';
  }

  // --- Auto-Updater Logic ---
  async function handleCheckForUpdates() {
    isCheckingUpdate = true;
    updateError = '';
    try {
      const detectedPlatform = /android/i.test(navigator.userAgent) ? 'android' : (/linux/i.test(navigator.userAgent) ? 'linux' : 'windows');
      const res = await checkAppUpdates(detectedPlatform);
      if (res) {
        updateInfo = res;
      } else {
        updateError = 'Could not reach GitHub. Check your network connection.';
      }
    } catch (e) {
      console.warn('Update check failed:', e);
      updateError = `Update check failed: ${e.message || 'Unknown error'}`;
    } finally {
      isCheckingUpdate = false;
    }
  }
</script>

{#if isOpen}
  <div 
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/65 backdrop-blur-xs p-3 sm:p-4 animate-in fade-in duration-150"
    onclick={() => isOpen = false}
    role="dialog"
    aria-modal="true"
  >
    <div 
      class="w-full max-w-2xl rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl flex flex-col max-h-[92vh] overflow-hidden"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Modal Header -->
      <div class="px-5 py-3.5 border-b border-[var(--border)] flex items-center justify-between bg-[var(--bg-secondary)] shrink-0">
        <div class="flex items-center gap-2.5">
          <span class="text-xl">⚙️</span>
          <div>
            <h2 class="text-sm font-bold text-[var(--text-primary)]">Workstation Hub & Settings</h2>
            <p class="text-[11px] text-[var(--text-secondary)]">Preferences, mesh networking, AI models, and system updates</p>
          </div>
        </div>
        <button 
          class="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--card)] transition-colors text-base"
          onclick={() => isOpen = false}
          aria-label="Close settings"
        >✕</button>
      </div>

      <!-- Navigation Tabs -->
      <div class="flex border-b border-[var(--border)] bg-[var(--bg-secondary)] px-3 overflow-x-auto no-scrollbar shrink-0 gap-1">
        <button
          type="button"
          class="px-3 py-2 text-xs font-medium border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap {activeTab === 'appearance' ? 'border-[var(--accent)] text-[var(--accent)] font-semibold' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
          onclick={() => activeTab = 'appearance'}
        >
          <span>🎨</span>
          <span>Appearance</span>
        </button>
        <button
          type="button"
          class="px-3 py-2 text-xs font-medium border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap {activeTab === 'network' ? 'border-[var(--accent)] text-[var(--accent)] font-semibold' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
          onclick={() => activeTab = 'network'}
        >
          <span>🌐</span>
          <span>Network & Mesh</span>
        </button>
        <button
          type="button"
          class="px-3 py-2 text-xs font-medium border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap {activeTab === 'compute' ? 'border-[var(--accent)] text-[var(--accent)] font-semibold' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
          onclick={() => { activeTab = 'compute'; loadComputeData(); }}
        >
          <span>🧠</span>
          <span>AI & Compute</span>
        </button>
        <button
          type="button"
          class="px-3 py-2 text-xs font-medium border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap {activeTab === 'storage' ? 'border-[var(--accent)] text-[var(--accent)] font-semibold' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
          onclick={() => { activeTab = 'storage'; loadStorageStats(); }}
        >
          <span>💾</span>
          <span>Storage</span>
        </button>
        <button
          type="button"
          class="px-3 py-2 text-xs font-medium border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap {activeTab === 'about' ? 'border-[var(--accent)] text-[var(--accent)] font-semibold' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
          onclick={() => { activeTab = 'about'; if (!updateInfo && !isCheckingUpdate) handleCheckForUpdates(); }}
        >
          <span>ℹ️</span>
          <span>About & Updates</span>
          {#if updateInfo && updateInfo.update_available}
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          {/if}
        </button>
      </div>

      <!-- Tab Content Area -->
      <div class="p-5 overflow-y-auto flex-1 flex flex-col gap-5 text-xs text-[var(--text-secondary)]">

        <!-- ── TAB 1: APPEARANCE ── -->
        {#if activeTab === 'appearance'}
          <div class="flex flex-col gap-4">
            <div>
              <h3 class="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider mb-1">Color Palette & Theme</h3>
              <p class="text-[11px] text-[var(--text-secondary)]">Choose your preferred workspace aesthetic. Themes apply instantly across all panes.</p>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
              <button
                class="p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 {theme.current === 'dark' ? 'border-[var(--accent)] bg-[var(--card)] text-[var(--accent)] ring-2 ring-[var(--accent)]/30 font-bold' : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--card)]'}"
                onclick={() => theme.set('dark')}
              >
                <span class="text-lg">🌙</span>
                <span class="text-xs font-medium">Midnight</span>
              </button>
              <button
                class="p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 {theme.current === 'light' ? 'border-[var(--accent)] bg-[var(--card)] text-[var(--accent)] ring-2 ring-[var(--accent)]/30 font-bold' : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--card)]'}"
                onclick={() => theme.set('light')}
              >
                <span class="text-lg">☀️</span>
                <span class="text-xs font-medium">Paper White</span>
              </button>
              <button
                class="p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 {theme.current === 'solarized' ? 'border-[var(--accent)] bg-[var(--card)] text-[var(--accent)] ring-2 ring-[var(--accent)]/30 font-bold' : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--card)]'}"
                onclick={() => theme.set('solarized')}
              >
                <span class="text-lg">🌿</span>
                <span class="text-xs font-medium">Solarized</span>
              </button>
              <button
                class="p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 {theme.current === 'cyberpunk' ? 'border-[var(--accent)] bg-[var(--card)] text-[var(--accent)] ring-2 ring-[var(--accent)]/30 font-bold' : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--card)]'}"
                onclick={() => theme.set('cyberpunk')}
              >
                <span class="text-lg">⚡</span>
                <span class="text-xs font-medium">Cyberpunk</span>
              </button>
              <button
                class="p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 {theme.current === 'amoled' ? 'border-[var(--accent)] bg-[var(--card)] text-[var(--accent)] ring-2 ring-[var(--accent)]/30 font-bold' : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--card)]'}"
                onclick={() => theme.set('amoled')}
              >
                <span class="text-lg">🖤</span>
                <span class="text-xs font-medium">OLED Black</span>
              </button>
            </div>

            <div class="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-1.5">
              <span class="font-semibold text-[var(--text-primary)]">Tip: Full Screen & Focus Mode</span>
              <p class="text-[11px] leading-relaxed">
                Use the accessory bar (<kbd class="px-1 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[10px]">Ctrl</kbd> + <kbd class="px-1 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[10px]">K</kbd> to toggle) for rapid LaTeX formulas, Mermaid diagrams, and freehand whiteboard sketches.
              </p>
            </div>
          </div>
        {/if}

        <!-- ── TAB 2: NETWORK & MESH SYNC ── -->
        {#if activeTab === 'network'}
          <div class="flex flex-col gap-4">
            <div>
              <h3 class="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider mb-1">Backend Server & Mesh Node</h3>
              <p class="text-[11px] text-[var(--text-secondary)]">Connect this client to your workstation PC over home Wi-Fi or Tailscale WireGuard mesh.</p>
            </div>

            <!-- Server Input Box -->
            <div class="flex flex-col gap-2">
              <div class="flex gap-2">
                <input
                  type="text"
                  placeholder="e.g. http://192.168.0.45:58850 or http://100.x.y.z:58850"
                  bind:value={serverInput}
                  class="flex-1 px-3 py-2 text-xs rounded-xl bg-[var(--card)] border border-[var(--border)] text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--accent)] font-mono"
                />
                <button
                  class="px-3.5 py-2 rounded-xl text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-colors shrink-0 disabled:opacity-50"
                  onclick={handleTestServer}
                  disabled={isTesting}
                >
                  {isTesting ? 'Pinging...' : 'Test Ping'}
                </button>
              </div>

              <!-- Quick Presets -->
              <div class="flex flex-wrap items-center gap-1.5 pt-1">
                <span class="text-[11px] text-[var(--text-secondary)] font-medium mr-1">Presets:</span>
                <button
                  type="button"
                  class="px-2.5 py-1 rounded-lg text-[11px] font-mono bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--accent)] transition-colors"
                  onclick={() => { serverInput = 'http://192.168.0.45:58850'; handleTestServer(); }}
                  title="Connect to PC on current home Wi-Fi"
                >
                  📡 Home Wi-Fi (:58850)
                </button>
                <button
                  type="button"
                  class="px-2.5 py-1 rounded-lg text-[11px] font-mono bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                  onclick={() => { serverInput = 'http://127.0.0.1:58850'; handleTestServer(); }}
                  title="Connect to local server on this computer"
                >
                  💻 Localhost (:58850)
                </button>
                <button
                  type="button"
                  class="px-2.5 py-1 rounded-lg text-[11px] font-mono bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                  onclick={() => { serverInput = ''; handleSaveServer(); }}
                  title="Reset to offline standalone mode"
                >
                  🔌 Standalone Mode
                </button>
              </div>
            </div>

            <!-- Ping Result -->
            {#if pingResult}
              <div class="p-2.5 rounded-xl text-xs {pingResult.ok ? 'bg-emerald-950/40 border border-emerald-500/40 text-emerald-300' : 'bg-rose-950/40 border border-rose-500/40 text-rose-300'}">
                {#if pingResult.ok}
                  🟢 Connected successfully! Roundtrip latency: {pingResult.latency}ms
                {:else}
                  🔴 Connection failed: {pingResult.error}
                {/if}
              </div>
            {/if}

            <div class="flex items-center justify-between pt-1">
              <button
                class="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
                onclick={handleSaveServer}
              >
                Save Server Config
              </button>
              {#if savedMessage}
                <span class="text-xs text-emerald-400 font-medium">{savedMessage}</span>
              {/if}
            </div>

            <!-- QR Code Pairing Banner -->
            <div class="p-3.5 rounded-xl bg-gradient-to-r from-blue-950/40 to-indigo-950/40 border border-blue-500/30 flex items-center justify-between gap-3">
              <div class="flex flex-col gap-0.5">
                <span class="font-bold text-blue-200 flex items-center gap-1.5">
                  <span>📱</span>
                  <span>One-Scan Universal QR Pairing</span>
                </span>
                <span class="text-[11px] text-blue-300/80">
                  Scan your computer screen with your phone camera to pair over Wi-Fi and Tailscale automatically.
                </span>
              </div>
              <button
                type="button"
                class="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs shrink-0 transition-colors shadow-sm cursor-pointer"
                onclick={() => {
                  isOpen = false;
                  if (onOpenPairing) onOpenPairing();
                }}
              >
                Open QR Pairing
              </button>
            </div>
          </div>
        {/if}

        <!-- ── TAB 3: AI & COMPUTE HUB ── -->
        {#if activeTab === 'compute'}
          <div class="flex flex-col gap-4">
            <div>
              <h3 class="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider mb-1">AI Inference & Academic Verification</h3>
              <p class="text-[11px] text-[var(--text-secondary)]">Neural fact-checking, lecture slide RAG, and local LLM acceleration.</p>
            </div>

            <!-- GLiNER Model Card -->
            <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-2.5">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="text-base">🧬</span>
                  <div>
                    <span class="text-xs font-bold text-[var(--text-primary)]">GLiNER Neural Entity Extractor</span>
                    <p class="text-[10px] text-[var(--text-secondary)]">urchade/gliner_small-v2.1 • Zero-shot fact claim parsing</p>
                  </div>
                </div>
                {#if glinerStatus && glinerStatus.model_ready}
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 border border-emerald-500/50 text-emerald-400">
                    🟢 Ready ({glinerStatus.device || 'CPU'})
                  </span>
                {:else if glinerStatus && glinerStatus.downloading}
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-950 border border-blue-500/50 text-blue-300">
                    ⏳ Downloading {glinerStatus.progress || 0}%
                  </span>
                {:else}
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700">
                    ⚪ Not Downloaded
                  </span>
                {/if}
              </div>

              <p class="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                Extracts key concepts, definitions, and claims from course notes with sub-millisecond latency. Operates 100% locally on your computer.
              </p>

              <div class="flex items-center justify-between pt-1">
                <span class="text-[10px] text-[var(--text-secondary)]">Weight size: ~165 MB</span>
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-all flex items-center gap-1.5 disabled:opacity-50"
                  disabled={isTriggeringGliner || (glinerStatus && glinerStatus.model_ready)}
                  onclick={handleStartGlinerDownload}
                >
                  <span>{glinerStatus && glinerStatus.model_ready ? '✓ Model Cached' : '⬇️ Download Weights'}</span>
                </button>
              </div>
            </div>

            <!-- llama.cpp Proxy Card -->
            <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-2.5">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="text-base">🦙</span>
                  <div>
                    <span class="text-xs font-bold text-[var(--text-primary)]">llama.cpp Reverse Proxy</span>
                    <p class="text-[10px] text-[var(--text-secondary)]">Routes study guide synthesis and fact-check contradiction escalation</p>
                  </div>
                </div>
                {#if llamaHealth && llamaHealth.status === 'ok'}
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 border border-emerald-500/50 text-emerald-400">
                    🟢 llama-server Active
                  </span>
                {:else if llamaHealth}
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-950 border border-amber-500/50 text-amber-400">
                    ⚠️ Offline (:8080)
                  </span>
                {/if}
              </div>

              <p class="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                The workstation proxies LLM requests to your local <code class="font-mono text-[var(--accent)]">llama-server</code> at <code class="font-mono text-[var(--text-primary)]">127.0.0.1:{llamaPort}</code>. Connected smartphones automatically use this compute power over the mesh!
              </p>

              <div class="flex items-center justify-between pt-1">
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-all flex items-center gap-1.5 disabled:opacity-50"
                  disabled={isTestingLlama}
                  onclick={handleTestLlama}
                >
                  <span>{isTestingLlama ? 'Testing...' : 'Test llama-server Status'}</span>
                </button>
              </div>
            </div>

            <!-- Hardware Specs Overview (if available) -->
            {#if hardwareSpecs}
              <div class="p-3.5 rounded-xl bg-[var(--card)] border border-[var(--border)] flex flex-col gap-1.5">
                <span class="font-bold text-xs text-[var(--text-primary)]">Workstation Host Hardware</span>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] pt-1">
                  <div><span class="text-[var(--text-secondary)]">CPU:</span> {hardwareSpecs.cpu_cores || 'N/A'} Cores ({hardwareSpecs.cpu_usage_pct || 0}%)</div>
                  <div><span class="text-[var(--text-secondary)]">RAM:</span> {hardwareSpecs.ram_free_gb || 0} GB Free / {hardwareSpecs.ram_total_gb || 0} GB</div>
                  <div><span class="text-[var(--text-secondary)]">GPU:</span> {hardwareSpecs.gpu_name || 'Integrated / CPU'}</div>
                </div>
              </div>
            {/if}
          </div>
        {/if}

        <!-- ── TAB 4: STORAGE & DATA ── -->
        {#if activeTab === 'storage'}
          <div class="flex flex-col gap-4">
            <div>
              <h3 class="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider mb-1">Local Storage & Offline Data</h3>
              <p class="text-[11px] text-[var(--text-secondary)]">Notes Workstation stores course data locally on device for instantaneous, offline-ready retrieval.</p>
            </div>

            <!-- Stats Overview -->
            <div class="grid grid-cols-3 gap-3">
              <div class="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] text-center">
                <span class="text-xl font-bold text-[var(--accent)]">{storageStats.lessons}</span>
                <p class="text-[11px] text-[var(--text-secondary)] mt-0.5">Courses</p>
              </div>
              <div class="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] text-center">
                <span class="text-xl font-bold text-emerald-400">{storageStats.units}</span>
                <p class="text-[11px] text-[var(--text-secondary)] mt-0.5">Units</p>
              </div>
              <div class="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] text-center">
                <span class="text-xl font-bold text-blue-400">{storageStats.notes}</span>
                <p class="text-[11px] text-[var(--text-secondary)] mt-0.5">Notes</p>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex flex-col gap-2 pt-2">
              <div class="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-between gap-3">
                <div class="flex flex-col gap-0.5">
                  <span class="font-semibold text-xs text-[var(--text-primary)]">Export Notes Backup (JSON)</span>
                  <span class="text-[11px] text-[var(--text-secondary)]">Save all courses, units, and markdown notes as a single file.</span>
                </div>
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-all shrink-0 cursor-pointer"
                  onclick={handleExportNotes}
                >
                  Export Data
                </button>
              </div>

              <div class="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/20 flex items-center justify-between gap-3">
                <div class="flex flex-col gap-0.5">
                  <span class="font-semibold text-xs text-rose-300">Clear Local Cache</span>
                  <span class="text-[11px] text-rose-300/70">Wipe locally cached notes on this device. (Does not affect server SQLite DB).</span>
                </div>
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-900/40 hover:bg-rose-800/50 border border-rose-500/40 text-rose-200 transition-all shrink-0 cursor-pointer"
                  onclick={handleClearStorage}
                >
                  Clear Cache
                </button>
              </div>
            </div>
          </div>
        {/if}

        <!-- ── TAB 5: ABOUT & SYSTEM UPDATES (OFFICIAL HOME OF UPDATER) ── -->
        {#if activeTab === 'about'}
          <div class="flex flex-col gap-4">
            <div>
              <h3 class="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider mb-1">Application Information & Updates</h3>
              <p class="text-[11px] text-[var(--text-secondary)]">Check GitHub for new releases, read release notes, and install updates.</p>
            </div>

            <!-- Version Hero Card -->
            <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-[var(--accent)]/15 border border-[var(--accent)]/30 flex items-center justify-center text-xl shrink-0">
                  📚
                </div>
                <div class="flex flex-col">
                  <span class="text-sm font-bold text-[var(--text-primary)]">Notes Workstation</span>
                  <div class="flex items-center gap-2 mt-0.5">
                    <span class="text-xs font-mono text-[var(--accent)] font-semibold">{currentAppVer}</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--text-secondary)]">
                      {getPlatformBadge()}
                    </span>
                  </div>
                </div>
              </div>
              <button
                type="button"
                class="px-3.5 py-2 rounded-xl text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shrink-0 shadow-sm"
                disabled={isCheckingUpdate}
                onclick={handleCheckForUpdates}
              >
                <span>{isCheckingUpdate ? '⏳ Checking...' : '🔄 Check for Updates'}</span>
              </button>
            </div>

            <!-- Update Results Banner -->
            {#if updateInfo}
              {#if updateInfo.update_available}
                <div class="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/50 flex flex-col gap-3">
                  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div class="flex flex-col">
                      <span class="font-bold text-xs text-emerald-300 flex items-center gap-1.5">
                        🚀 New Version Available: {updateInfo.latest_version}
                      </span>
                      <span class="text-[11px] text-emerald-200/90 mt-0.5">{updateInfo.release_title}</span>
                      {#if updateInfo.recommended_asset}
                        <span class="text-[10px] text-emerald-300/80 font-mono mt-0.5">
                          Matched for your platform: {updateInfo.recommended_asset.name} ({updateInfo.recommended_asset.size_mb} MB)
                        </span>
                      {/if}
                    </div>

                    {#if updateInfo.recommended_asset}
                      <a
                        href={updateInfo.recommended_asset.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs text-center shrink-0 shadow-md transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        ⬇️ Download {updateInfo.recommended_asset.name.endsWith('.apk') ? 'APK' : 'Installer'}
                      </a>
                    {:else}
                      <a
                        href={updateInfo.html_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs text-center shrink-0 cursor-pointer"
                      >
                        View Release on GitHub
                      </a>
                    {/if}
                  </div>

                  {#if updateInfo.changelog}
                    <div class="p-3 rounded-lg bg-black/30 border border-emerald-500/20 text-[11px] text-emerald-100/80 font-mono max-h-36 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                      {updateInfo.changelog}
                    </div>
                  {/if}
                </div>
              {:else}
                <div class="p-3 rounded-xl bg-[var(--card)] border border-emerald-500/40 text-xs text-emerald-400 flex items-center gap-2">
                  <span>✅</span>
                  <span>Notes Workstation is up to date ({currentAppVer}). You have the latest features installed.</span>
                </div>
              {/if}
            {/if}

            {#if updateError && !updateInfo}
              <div class="p-3 rounded-xl bg-amber-950/30 border border-amber-500/40 text-xs text-amber-300 flex items-center gap-2">
                <span>⚠️</span>
                <span>{updateError}</span>
              </div>
            {/if}

            <!-- Community & Open Source Links -->
            <div class="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-2">
              <span class="text-xs font-bold text-[var(--text-primary)]">Open Source & Support</span>
              <div class="flex flex-wrap items-center gap-3 text-xs pt-0.5">
                <a 
                  href="https://github.com/Carxofa3/notes" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="text-[var(--accent)] hover:underline flex items-center gap-1"
                >
                  <span>🐙</span>
                  <span>GitHub Repository</span>
                </a>
                <span class="text-[var(--border)]">•</span>
                <a 
                  href="https://github.com/Carxofa3/notes/releases" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="text-[var(--accent)] hover:underline flex items-center gap-1"
                >
                  <span>📦</span>
                  <span>All Releases</span>
                </a>
                <span class="text-[var(--border)]">•</span>
                <a 
                  href="https://github.com/Carxofa3/notes/issues" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="text-[var(--accent)] hover:underline flex items-center gap-1"
                >
                  <span>🐛</span>
                  <span>Report an Issue</span>
                </a>
              </div>
            </div>
          </div>
        {/if}

      </div>

      <!-- Modal Footer -->
      <div class="px-5 py-3 border-t border-[var(--border)] flex items-center justify-between bg-[var(--bg-secondary)] shrink-0">
        <span class="text-[11px] text-[var(--text-secondary)] font-mono">
          Notes Workstation {currentAppVer}
        </span>
        <button
          type="button"
          class="px-4 py-1.5 rounded-xl text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-colors cursor-pointer"
          onclick={() => isOpen = false}
        >
          Close
        </button>
      </div>
    </div>
  </div>
{/if}

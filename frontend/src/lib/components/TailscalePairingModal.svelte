<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import QRCode from 'qrcode';
  import { Html5Qrcode } from 'html5-qrcode';
  import {
    fetchPairInfo,
    fetchPeers,
    registerPeer,
    getServerUrl,
    setServerUrl,
    fetchClusterOverview,
    updateSelfConfig,
    checkLocalLlamaCppHealth,
    renamePeerNode,
    triggerRemoteGliner,
    selectActiveLlm,
    fetchGlinerStatus,
    triggerGlinerDownload,
    checkAppUpdates,
    fetchAppVersion
  } from '../api.js';

  let { isOpen = $bindable(false) } = $props();

  let pairInfo = $state(null);
  let peers = $state([]);
  let inputToken = $state('');
  let registerMessage = $state('');
  let qrDataUrl = $state('');
  let isGeneratingQr = $state(false);
  let activeTab = $state('wifi'); // 'wifi' | 'tailscale' | 'cluster'
  let copyFeedback = $state(false);
  let isScanning = $state(false);
  let scannerError = $state('');
  let scannerInstance = null;

  // Cluster & Nodes State
  let clusterData = $state(null);
  let localNodeName = $state('');
  let llamacppEnabled = $state(false);
  let llamacppPort = $state(8080);
  let llamacppHealth = $state(null);
  let isTestingLlama = $state(false);
  let isSavingLocalConfig = $state(false);
  let glinerStatus = $state(null);
  let isTriggeringGliner = $state(false);
  let editingPeerId = $state(null);
  let editingPeerAlias = $state('');
  let clusterMessage = $state('');

  // Auto-Updater State
  let updateInfo = $state(null);
  let isCheckingUpdate = $state(false);
  let currentAppVer = $state('v2.1.3');
  let clusterPollTimer = null;
  let glinerPollTimer = null;

  onDestroy(() => {
    stopScanner();
    stopClusterPolling();
  });

  const defaultHost = '192.168.0.45:5000';

  $effect(() => {
    if (isOpen) {
      if (activeTab !== 'cluster') {
        updateQrCode();
      }
      loadInfo();
      loadAppVersion();
      if (activeTab === 'cluster') {
        loadClusterData();
        startClusterPolling();
      }
    } else {
      stopClusterPolling();
      stopScanner();
    }
  });

  $effect(() => {
    if (isOpen && activeTab !== 'cluster') {
      updateQrCode();
    }
  });

  function startClusterPolling() {
    stopClusterPolling();
    clusterPollTimer = setInterval(() => {
      if (isOpen && activeTab === 'cluster') {
        loadClusterData(false);
      }
    }, 4000);
  }

  function stopClusterPolling() {
    if (clusterPollTimer) {
      clearInterval(clusterPollTimer);
      clusterPollTimer = null;
    }
    if (glinerPollTimer) {
      clearInterval(glinerPollTimer);
      glinerPollTimer = null;
    }
  }

  async function loadAppVersion() {
    try {
      const v = await fetchAppVersion();
      if (v && v.version) {
        currentAppVer = v.version;
      }
    } catch (_) {}
  }

  async function updateQrCode() {
    isGeneratingQr = true;
    try {
      let payloadToEncode = '';
      if (activeTab === 'wifi') {
        const customUrl = getServerUrl();
        payloadToEncode = customUrl || `http://${defaultHost}`;
      } else {
        if (pairInfo) {
          payloadToEncode = JSON.stringify(pairInfo.pairing_payload || pairInfo);
        } else {
          payloadToEncode = JSON.stringify({
            v: 1,
            magic_dns: 'desktop.tailnet.ts.net',
            ip: '192.168.0.45',
            port: 58855,
            name: 'Desktop Workstation',
            ts: Date.now()
          });
        }
      }

      const url = await QRCode.toDataURL(payloadToEncode, {
        width: 220,
        margin: 2,
        color: {
          dark: '#0f172a',
          light: '#ffffff'
        }
      });
      qrDataUrl = url;
    } catch (err) {
      console.error('QR code generation error:', err);
    } finally {
      isGeneratingQr = false;
    }
  }

  async function loadInfo() {
    try {
      const info = await fetchPairInfo();
      if (info) {
        pairInfo = info;
        if (activeTab !== 'cluster') updateQrCode();
      }
    } catch (e) {
      console.warn('Could not fetch pair info:', e);
    }

    try {
      peers = await fetchPeers();
    } catch (e) {
      console.warn('Could not fetch peers:', e);
    }
  }

  async function loadClusterData(showSpinner = true) {
    try {
      const c = await fetchClusterOverview();
      if (c) {
        clusterData = c;
        if (c.local_node) {
          if (!localNodeName) {
            localNodeName = c.local_node.name || '';
          }
          if (c.local_node.services && c.local_node.services.llamacpp) {
            llamacppEnabled = !!c.local_node.services.llamacpp.enabled;
            llamacppPort = c.local_node.services.llamacpp.local_port || 8080;
          }
          if (c.local_node.services && c.local_node.services.gliner) {
            glinerStatus = c.local_node.services.gliner;
          }
        }
      }
    } catch (e) {
      console.warn('Could not fetch cluster overview:', e);
    }
  }

  async function handleSaveLocalConfig() {
    isSavingLocalConfig = true;
    clusterMessage = '';
    try {
      const res = await updateSelfConfig({
        name: localNodeName,
        llamacpp_enabled: llamacppEnabled,
        llamacpp_local_port: Number(llamacppPort)
      });
      if (res) {
        clusterMessage = '✅ Workstation node configuration updated!';
        await loadClusterData();
      }
    } catch (e) {
      clusterMessage = `Failed to save configuration: ${e.message}`;
    } finally {
      isSavingLocalConfig = false;
      setTimeout(() => clusterMessage = '', 4000);
    }
  }

  async function handleTestLlamaPort() {
    isTestingLlama = true;
    llamacppHealth = null;
    try {
      const res = await checkLocalLlamaCppHealth();
      llamacppHealth = res;
    } catch (e) {
      llamacppHealth = { running: false, error: e.message };
    } finally {
      isTestingLlama = false;
    }
  }

  async function handleTriggerLocalGliner() {
    isTriggeringGliner = true;
    try {
      await triggerGlinerDownload();
      // Start polling status
      glinerPollTimer = setInterval(async () => {
        const stat = await fetchGlinerStatus();
        if (stat) {
          glinerStatus = stat;
          if (stat.ready || stat.error) {
            clearInterval(glinerPollTimer);
            glinerPollTimer = null;
            isTriggeringGliner = false;
          }
        }
      }, 2000);
    } catch (e) {
      isTriggeringGliner = false;
    }
  }

  async function handleTriggerRemoteGliner(peer) {
    if (!peer.lan_ip && !peer.sender_ip) return;
    const peerUrl = `http://${peer.lan_ip || peer.sender_ip}:${peer.http_port || 5000}`;
    clusterMessage = `Sending download trigger to ${peer.name || peer.node_id}...`;
    try {
      const res = await triggerRemoteGliner(peer.node_id, peerUrl);
      if (res && res.success) {
        clusterMessage = `✅ Triggered GLiNER download on ${peer.name || peer.node_id}!`;
        await loadClusterData();
      } else {
        clusterMessage = `Could not trigger download: ${res?.error || 'Remote error'}`;
      }
    } catch (e) {
      clusterMessage = `Error: ${e.message}`;
    }
    setTimeout(() => clusterMessage = '', 4000);
  }

  async function handleSelectActiveLlm(endpoint) {
    clusterMessage = 'Updating cluster LLM routing...';
    try {
      const current = clusterData?.active_llm_provider;
      const newTarget = (current === endpoint) ? null : endpoint;
      const res = await selectActiveLlm(newTarget);
      if (res) {
        clusterMessage = newTarget ? `🎯 Switched LLM provider to ${endpoint}` : 'Switched LLM provider back to local engine';
        await loadClusterData();
      }
    } catch (e) {
      clusterMessage = `Error setting LLM provider: ${e.message}`;
    }
    setTimeout(() => clusterMessage = '', 4000);
  }

  async function handleSavePeerRename(peerId) {
    if (!editingPeerAlias.trim()) {
      editingPeerId = null;
      return;
    }
    try {
      await renamePeerNode(peerId, editingPeerAlias.trim());
      editingPeerId = null;
      editingPeerAlias = '';
      await loadClusterData();
    } catch (e) {
      console.error('Rename failed:', e);
    }
  }

  async function handleCheckForUpdates() {
    isCheckingUpdate = true;
    try {
      const detectedPlatform = /android/i.test(navigator.userAgent) ? 'android' : (/linux/i.test(navigator.userAgent) ? 'linux' : 'windows');
      const res = await checkAppUpdates(detectedPlatform);
      if (res) {
        updateInfo = res;
      }
    } catch (e) {
      console.warn('Update check failed:', e);
    } finally {
      isCheckingUpdate = false;
    }
  }

  async function handleCopyPayload() {
    let payload = '';
    if (activeTab === 'wifi') {
      payload = getServerUrl() || `http://${defaultHost}`;
    } else {
      payload = pairInfo ? JSON.stringify(pairInfo.pairing_payload || pairInfo, null, 2) : `http://${defaultHost}`;
    }
    try {
      await navigator.clipboard.writeText(payload);
      copyFeedback = true;
      setTimeout(() => copyFeedback = false, 2000);
    } catch (err) {
      console.error('Clipboard copy failed:', err);
    }
  }

  async function handleConnectPeer() {
    const trimmed = inputToken.trim();
    if (!trimmed) return;
    registerMessage = 'Pairing with peer...';

    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      setServerUrl(trimmed);
      registerMessage = `Successfully connected! Server set to ${trimmed}`;
      await loadInfo();
      return;
    }

    try {
      let parsed = JSON.parse(trimmed);
      const res = await registerPeer(parsed);
      if (res && res.peer_id) {
        registerMessage = `Successfully paired with "${res.device_name}"!`;
        inputToken = '';
        await loadInfo();
      } else {
        registerMessage = 'Failed to pair. Invalid peer payload.';
      }
    } catch (e) {
      registerMessage = 'Error: Input must be a valid server URL (e.g. http://192.168.0.45:5000) or JSON pairing payload.';
    }
  }

  async function startScanner() {
    scannerError = '';
    isScanning = true;
    registerMessage = '';
    await tick();

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        stream.getTracks().forEach(t => t.stop());
      } catch (permErr) {
        if (permErr.name === 'NotAllowedError' || permErr.name === 'PermissionDeniedError') {
          scannerError = 'Camera permission was denied. Please allow Camera in phone Settings > Apps > Notes Workstation.';
          isScanning = false;
          return;
        }
      }
    }

    try {
      scannerInstance = new Html5Qrcode('qr-reader');
      const config = { fps: 10, qrbox: { width: 220, height: 220 } };

      await scannerInstance.start(
        { facingMode: 'environment' },
        config,
        async (decodedText) => {
          await stopScanner();
          handleScannedContent(decodedText);
        },
        (errorMessage) => {
          // Normal frame scanning tick
        }
      );
    } catch (err) {
      scannerError = err.message || 'Could not start camera scanner.';
      isScanning = false;
      scannerInstance = null;
    }
  }

  async function stopScanner() {
    if (scannerInstance) {
      try {
        await scannerInstance.stop();
        scannerInstance.clear();
      } catch (e) {
        console.warn('Error stopping scanner:', e);
      }
      scannerInstance = null;
    }
    isScanning = false;
  }

  async function handleScannedContent(text) {
    const trimmed = text.trim();
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      setServerUrl(trimmed);
      registerMessage = `Connected! Server set to ${trimmed}`;
      await loadInfo();
    } else {
      inputToken = trimmed;
      try {
        const parsed = JSON.parse(trimmed);
        const res = await registerPeer(parsed);
        if (res && res.peer_id) {
          registerMessage = `Successfully paired with "${res.device_name}"!`;
          inputToken = '';
          await loadInfo();
        } else {
          registerMessage = 'Scanned code loaded. Click Connect & Pair below.';
        }
      } catch {
        registerMessage = `Scanned code: ${trimmed}`;
      }
    }
  }

  function handleCloseModal() {
    stopScanner();
    stopClusterPolling();
    isOpen = false;
  }
</script>

{#if isOpen}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-2 sm:p-4" onclick={handleCloseModal}>
    <div 
      class="w-full max-w-3xl max-h-[92vh] rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl p-4 sm:p-6 flex flex-col gap-4 overflow-y-auto"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-base sm:text-lg font-bold text-[var(--text-primary)]">Device Mesh & Cluster Hub</h2>
            <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950/40 text-emerald-300 border border-emerald-500/40 font-mono">P2P Cluster Ready</span>
            <span class="px-2 py-0.5 rounded text-[10px] bg-[var(--bg-tertiary)] text-[var(--accent)] font-mono">{currentAppVer}</span>
          </div>
          <p class="text-xs text-[var(--text-secondary)]">Pair phones, expose local llama.cpp servers, and manage models across your cluster</p>
        </div>
        <button 
          class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1 cursor-pointer"
          onclick={handleCloseModal}
        >&times;</button>
      </div>

      <!-- Mode Tabs (3 tabs: WiFi, Tailscale, Cluster) -->
      <div class="flex rounded-xl bg-[var(--bg-secondary)] p-1 border border-[var(--border)]">
        <button
          type="button"
          class="flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all {activeTab === 'wifi' ? 'bg-[var(--accent)] text-white shadow-xs' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'} cursor-pointer"
          onclick={() => { activeTab = 'wifi'; stopClusterPolling(); updateQrCode(); }}
        >
          📡 Wi-Fi Connect
        </button>
        <button
          type="button"
          class="flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all {activeTab === 'tailscale' ? 'bg-[var(--accent)] text-white shadow-xs' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'} cursor-pointer"
          onclick={() => { activeTab = 'tailscale'; stopClusterPolling(); updateQrCode(); }}
        >
          🔒 Tailscale Mesh
        </button>
        <button
          type="button"
          class="flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all {activeTab === 'cluster' ? 'bg-[var(--accent)] text-white shadow-xs' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'} cursor-pointer"
          onclick={() => { activeTab = 'cluster'; stopScanner(); loadClusterData(); startClusterPolling(); }}
        >
          🖥️ Nodes & Models
        </button>
      </div>

      {#if activeTab === 'cluster'}
        <!-- ── TAB 3: NODES & CLUSTER MANAGEMENT ── -->
        <div class="flex flex-col gap-4">
          <!-- Auto-Updater Banner -->
          <div class="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-[var(--text-primary)]">Application Updates</span>
                <span class="text-[11px] font-mono text-[var(--text-secondary)]">Current: {currentAppVer}</span>
              </div>
              <button
                type="button"
                class="px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                disabled={isCheckingUpdate}
                onclick={handleCheckForUpdates}
              >
                <span>{isCheckingUpdate ? '⏳ Checking...' : '🔄 Check for Updates'}</span>
              </button>
            </div>

            {#if updateInfo}
              {#if updateInfo.update_available}
                <div class="p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div class="flex flex-col gap-0.5">
                    <span class="font-bold text-emerald-300 flex items-center gap-1.5">
                      🚀 New Version Available: {updateInfo.latest_version}
                    </span>
                    <span class="text-[11px] text-emerald-200/90">{updateInfo.release_title}</span>
                    {#if updateInfo.recommended_asset}
                      <span class="text-[10px] text-emerald-300/80 font-mono mt-0.5">
                        Matched for your device: {updateInfo.recommended_asset.name} ({updateInfo.recommended_asset.size_mb} MB)
                      </span>
                    {/if}
                  </div>
                  {#if updateInfo.recommended_asset}
                    <a
                      href={updateInfo.recommended_asset.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs text-center shrink-0 shadow-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      ⬇️ Download {updateInfo.recommended_asset.name.endsWith('.apk') ? 'APK' : 'Update'}
                    </a>
                  {:else}
                    <a
                      href={updateInfo.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs text-center shrink-0 cursor-pointer"
                    >
                      View GitHub Release
                    </a>
                  {/if}
                </div>
              {:else}
                <div class="p-2 rounded-lg bg-[var(--card)] border border-[var(--border)] text-[11px] text-[var(--text-secondary)] flex items-center gap-1.5">
                  <span>✅ Notes Workstation is completely up to date ({currentAppVer}).</span>
                </div>
              {/if}
            {/if}
          </div>

          {#if clusterMessage}
            <div class="p-2.5 rounded-lg border text-xs font-mono {clusterMessage.includes('Failed') || clusterMessage.includes('Error') ? 'bg-red-950/30 border-red-500/40 text-red-400' : 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'}">
              {clusterMessage}
            </div>
          {/if}

          <!-- Local Workstation Node Settings & Exposure Card -->
          {#if clusterData?.local_node}
            {@const loc = clusterData.local_node}
            <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-3">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
                <div class="flex items-center gap-2">
                  <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span class="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">This Workstation (Local Peer)</span>
                  <span class="px-2 py-0.5 rounded text-[10px] bg-[var(--card)] border border-[var(--border)] font-mono text-[var(--accent)]">{loc.node_id}</span>
                </div>
                <!-- Hardware Badge -->
                <div class="flex items-center gap-1 text-[11px] font-mono text-[var(--text-secondary)]">
                  <span class="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)]">
                    {loc.hardware?.summary || 'Hardware Polled'}
                  </span>
                </div>
              </div>

              <!-- Friendly Node Name -->
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center">
                <label for="workstation-name" class="text-xs font-medium text-[var(--text-secondary)]">Device Friendly Name:</label>
                <div class="sm:col-span-2 flex gap-2">
                  <input
                    id="workstation-name"
                    type="text"
                    bind:value={localNodeName}
                    placeholder="e.g. Workstation RTX 4090"
                    class="flex-1 px-3 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--accent)]"
                  />
                  <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 disabled:opacity-50 cursor-pointer"
                    disabled={isSavingLocalConfig}
                    onclick={handleSaveLocalConfig}
                  >
                    Save
                  </button>
                </div>
              </div>

              <!-- Llama.cpp Server Exposure -->
              <div class="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)] flex flex-col gap-2.5">
                <div class="flex items-center justify-between">
                  <div class="flex flex-col">
                    <span class="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      ⚡ Expose llama.cpp to Peer Mesh
                    </span>
                    <span class="text-[10px] text-[var(--text-secondary)]">
                      Proxies requests from phones & peers directly to your local llama-server without firewall hurdles.
                    </span>
                  </div>
                  <label class="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      bind:checked={llamacppEnabled}
                      onchange={handleSaveLocalConfig}
                      class="sr-only peer"
                    />
                    <div class="w-9 h-5 bg-slate-700 peer-focus:outline-hidden rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[var(--accent)]"></div>
                  </label>
                </div>

                {#if llamacppEnabled}
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-[var(--border)] text-xs">
                    <div class="flex items-center gap-2">
                      <label for="local-llama-port" class="text-[11px] text-[var(--text-secondary)] shrink-0">Localhost Port:</label>
                      <input
                        id="local-llama-port"
                        type="number"
                        bind:value={llamacppPort}
                        class="w-24 px-2 py-1 rounded bg-[var(--bg-secondary)] border border-[var(--border)] text-xs font-mono text-[var(--text-primary)]"
                      />
                      <button
                        type="button"
                        class="px-2 py-1 rounded text-[11px] bg-[var(--bg-tertiary)] hover:bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-primary)] cursor-pointer"
                        onclick={handleTestLlamaPort}
                      >
                        {isTestingLlama ? 'Testing...' : '🔌 Test'}
                      </button>
                    </div>

                    <div class="flex items-center justify-end text-[10px] font-mono text-[var(--text-secondary)]">
                      {#if llamacppHealth}
                        {#if llamacppHealth.running}
                          <span class="text-emerald-400 font-semibold">🟢 llama-server active on port {llamacppPort}</span>
                        {:else}
                          <span class="text-amber-400">⚠️ No server responding on 127.0.0.1:{llamacppPort}</span>
                        {/if}
                      {:else}
                        <span class="text-[var(--text-secondary)]">Endpoint: {loc.services?.llamacpp?.endpoint}</span>
                      {/if}
                    </div>
                  </div>
                {/if}
              </div>

              <!-- GLiNER Neural Engine Service -->
              <div class="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)] flex items-center justify-between text-xs">
                <div class="flex flex-col">
                  <span class="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                    🏷️ GLiNER Neural Entity Extraction
                  </span>
                  <span class="text-[10px] text-[var(--text-secondary)]">
                    Zero-shot academic entity extraction on {loc.hardware?.gpu_name || 'CPU'}.
                  </span>
                </div>

                <div class="flex items-center gap-2">
                  {#if glinerStatus?.ready}
                    <span class="px-2 py-1 rounded text-[10px] bg-emerald-950/40 text-emerald-300 border border-emerald-500/40 font-mono">
                      Ready ({glinerStatus.device?.toUpperCase() || 'CPU'})
                    </span>
                  {:else if glinerStatus?.downloading}
                    <span class="px-2 py-1 rounded text-[10px] bg-amber-950/40 text-amber-300 border border-amber-500/40 font-mono animate-pulse">
                      Downloading weights...
                    </span>
                  {:else}
                    <button
                      type="button"
                      class="px-3 py-1 rounded text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 cursor-pointer disabled:opacity-50"
                      disabled={isTriggeringGliner}
                      onclick={handleTriggerLocalGliner}
                    >
                      {isTriggeringGliner ? 'Starting...' : '⬇️ Download GLiNER'}
                    </button>
                  {/if}
                </div>
              </div>
            </div>
          {/if}

          <!-- Discovered & Paired Mesh Peers List -->
          <div class="flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                Discovered Cluster Peers ({clusterData?.discovered_nodes?.length || 0})
              </span>
              <button
                type="button"
                class="text-[11px] text-[var(--accent)] hover:underline cursor-pointer"
                onclick={() => loadClusterData()}
              >
                🔄 Refresh Mesh
              </button>
            </div>

            {#if !clusterData?.discovered_nodes || clusterData.discovered_nodes.length === 0}
              <div class="p-6 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] text-center flex flex-col items-center justify-center gap-2">
                <span class="text-2xl">📡</span>
                <span class="text-xs font-semibold text-[var(--text-primary)]">Listening for Peers on Network...</span>
                <span class="text-[11px] text-[var(--text-secondary)] max-w-sm">
                  Run Notes Workstation on your laptop or Android phone connected to the same Wi-Fi or Tailnet. They will automatically appear here!
                </span>
              </div>
            {:else}
              {#each clusterData.discovered_nodes as peer}
                <div class="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-2.5">
                  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div class="flex items-center gap-2">
                      <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                      {#if editingPeerId === peer.node_id}
                        <input
                          type="text"
                          bind:value={editingPeerAlias}
                          class="px-2 py-0.5 rounded text-xs bg-[var(--card)] border border-[var(--border)] text-[var(--text-primary)] font-semibold"
                          placeholder="Custom name..."
                        />
                        <button
                          type="button"
                          class="text-xs text-emerald-400 font-bold hover:underline cursor-pointer"
                          onclick={() => handleSavePeerRename(peer.node_id)}
                        >
                          Save
                        </button>
                      {:else}
                        <span class="text-xs font-bold text-[var(--text-primary)]">
                          {peer.custom_alias || peer.name || peer.hostname}
                        </span>
                        <button
                          type="button"
                          class="text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
                          onclick={() => { editingPeerId = peer.node_id; editingPeerAlias = peer.custom_alias || peer.name || ''; }}
                          title="Rename peer"
                        >
                          ✏️
                        </button>
                      {/if}
                      <span class="text-[10px] font-mono text-[var(--text-secondary)]">({peer.lan_ip}:{peer.http_port})</span>
                    </div>

                    <!-- Peer Hardware Badge -->
                    <div class="flex items-center gap-1.5 text-[10px] font-mono">
                      {#if peer.hardware}
                        <span class="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--text-secondary)]">
                          🧠 {peer.hardware.ram_total_gb} GB RAM
                        </span>
                        {#if peer.hardware.gpu_name}
                          <span class="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--text-secondary)]">
                            🎮 {peer.hardware.gpu_name} {peer.hardware.vram_total_gb ? `(${peer.hardware.vram_total_gb} GB VRAM)` : ''}
                          </span>
                        {/if}
                      {/if}
                    </div>
                  </div>

                  <!-- Peer Services Bar -->
                  <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--border)] text-xs">
                    <!-- Llama.cpp Offering -->
                    <div class="flex items-center gap-2">
                      {#if peer.services?.llamacpp?.enabled}
                        <span class="px-2 py-0.5 rounded text-[10px] bg-indigo-950/40 text-indigo-300 border border-indigo-500/40 font-mono">
                          ⚡ llama.cpp (Port {peer.services.llamacpp.local_port})
                        </span>
                        <button
                          type="button"
                          class="px-2.5 py-1 rounded text-[11px] font-semibold transition-all cursor-pointer {clusterData.active_llm_provider === peer.services.llamacpp.endpoint ? 'bg-emerald-600 text-white' : 'bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)]'}"
                          onclick={() => handleSelectActiveLlm(peer.services.llamacpp.endpoint)}
                        >
                          {clusterData.active_llm_provider === peer.services.llamacpp.endpoint ? '✅ Active Cluster LLM' : '🎯 Use as LLM'}
                        </button>
                      {:else}
                        <span class="text-[11px] text-[var(--text-secondary)]">No LLM server exposed</span>
                      {/if}
                    </div>

                    <!-- GLiNER Offering -->
                    <div class="flex items-center gap-2">
                      {#if peer.services?.gliner?.ready}
                        <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950/40 text-emerald-300 border border-emerald-500/40 font-mono">
                          🏷️ GLiNER Ready ({peer.services.gliner.device || 'CPU'})
                        </span>
                      {:else}
                        <button
                          type="button"
                          class="px-2.5 py-1 rounded text-[11px] font-medium bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-all cursor-pointer"
                          onclick={() => handleTriggerRemoteGliner(peer)}
                        >
                          ⬇️ Trigger Remote GLiNER
                        </button>
                      {/if}
                    </div>
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </div>
      {:else}
        <!-- ── TAB 1 & 2: WI-FI & TAILSCALE PAIRING WITH QR & SCANNER ── -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- QR Code Card -->
          <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col items-center justify-center gap-3 text-center">
            <span class="text-xs font-semibold text-[var(--text-primary)]">
              {activeTab === 'wifi' ? 'Scan to Connect via Home Wi-Fi' : 'Scan to Connect via Tailscale Mesh'}
            </span>
            
            <div class="bg-white rounded-2xl p-3 flex flex-col items-center justify-center shadow-md border border-slate-200">
              {#if qrDataUrl}
                <img src={qrDataUrl} alt="Pairing QR Code" class="w-44 h-44 rounded-lg object-contain" />
              {:else}
                <div class="w-44 h-44 flex flex-col items-center justify-center text-slate-400 gap-2">
                  <span class="text-2xl animate-spin">⏳</span>
                  <span class="text-xs font-medium">Generating QR...</span>
                </div>
              {/if}
            </div>

            <div class="flex flex-col gap-1 text-xs w-full max-w-xs">
              {#if activeTab === 'wifi'}
                <span class="font-mono text-[var(--accent)] font-semibold text-xs break-all">
                  {getServerUrl() || `http://${defaultHost}`}
                </span>
                <span class="text-[10px] text-[var(--text-secondary)]">Scan with your phone camera or the Scan button on the right</span>
              {:else}
                <span class="font-mono text-[var(--accent)] font-semibold text-xs break-all">
                  {pairInfo?.magic_dns || 'desktop.tailnet.ts.net'}
                </span>
                <span class="text-[10px] text-[var(--text-secondary)] font-mono">
                  Port: {pairInfo?.port || 58855} • Fingerprint: {pairInfo?.fingerprint ? pairInfo.fingerprint.substring(0, 14) + '...' : 'local'}
                </span>
              {/if}
            </div>

            <button
              type="button"
              class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-colors flex items-center gap-1.5 cursor-pointer"
              onclick={handleCopyPayload}
            >
              <span>{copyFeedback ? '✅ Copied to Clipboard!' : '📋 Copy Connection URL'}</span>
            </button>
          </div>

          <!-- Camera Scanner or Manual Connect Form -->
          <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-3">
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-semibold text-[var(--text-primary)]">Pair Remote Device</span>
              <button
                type="button"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shadow-xs cursor-pointer {isScanning ? 'bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30' : 'bg-[var(--accent)] text-white hover:opacity-90'}"
                onclick={isScanning ? stopScanner : startScanner}
              >
                <span>{isScanning ? '⏹ Stop Scanner' : '📷 Scan QR Code'}</span>
              </button>
            </div>

            {#if isScanning}
              <div class="rounded-xl overflow-hidden border border-[var(--accent)] bg-black/95 p-3 flex flex-col items-center gap-2 shadow-inner">
                <div id="qr-reader" class="w-full max-w-[240px] rounded-lg overflow-hidden bg-black"></div>
                <span class="text-[11px] text-slate-300 font-medium animate-pulse">📷 Align camera over the QR code on PC</span>
                <button
                  type="button"
                  class="text-[11px] text-red-400 hover:text-red-300 font-medium hover:underline cursor-pointer"
                  onclick={stopScanner}
                >
                  Cancel Scanner
                </button>
              </div>
            {/if}

            {#if scannerError}
              <div class="p-2.5 rounded-lg bg-red-950/40 border border-red-500/40 text-[11px] text-red-300 flex flex-col gap-1">
                <span class="font-semibold">⚠️ Camera error</span>
                <span>{scannerError}</span>
                <span class="text-[10px] text-slate-400">Make sure camera permissions are granted, or paste the connection URL below.</span>
              </div>
            {/if}

            <p class="text-[11px] text-[var(--text-secondary)]">Or paste the peer token or backend URL manually:</p>

            <textarea
              bind:value={inputToken}
              placeholder={`http://192.168.0.45:5000 or {"magic_dns": "...", "fingerprint": "..."}`}
              class="w-full flex-1 min-h-[75px] p-2.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs font-mono text-[var(--text-primary)] resize-none focus:outline-hidden focus:border-[var(--accent)]"
            ></textarea>

            <button
              class="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity cursor-pointer"
              onclick={handleConnectPeer}
            >
              Connect & Pair Device
            </button>

            {#if registerMessage}
              <div class="p-2 rounded-lg border text-[11px] font-mono {registerMessage.includes('Error') || registerMessage.includes('Failed') ? 'bg-red-950/30 border-red-500/40 text-red-400' : 'bg-emerald-950/30 border-emerald-500/40 text-emerald-400'}">
                {registerMessage}
              </div>
            {/if}
          </div>
        </div>

        <!-- Paired Peers List -->
        <div class="flex-1 overflow-y-auto min-h-0 flex flex-col gap-2">
          <span class="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">Paired Mesh Peers ({peers.length})</span>
          {#if peers.length === 0}
            <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] text-xs text-[var(--text-secondary)] text-center">
              No remote peers paired yet. Open the Notes app on your Android device to connect.
            </div>
          {:else}
            {#each peers as peer}
              <div class="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-between text-xs">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full {peer.is_active ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}"></span>
                  <div class="flex flex-col">
                    <span class="font-semibold text-[var(--text-primary)]">{peer.device_name}</span>
                    <span class="text-[10px] text-[var(--text-secondary)] font-mono">{peer.magic_dns} • {peer.fingerprint?.substring(0, 18)}...</span>
                  </div>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] bg-[var(--bg-tertiary)] text-[var(--accent)] font-mono">Port {peer.port}</span>
              </div>
            {/each}
          {/if}
        </div>
      {/if}

      <!-- Footer -->
      <div class="flex justify-end pt-2 border-t border-[var(--border)]">
        <button
          class="px-4 py-2 rounded-xl text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] cursor-pointer"
          onclick={handleCloseModal}
        >
          Done
        </button>
      </div>
    </div>
  </div>
{/if}

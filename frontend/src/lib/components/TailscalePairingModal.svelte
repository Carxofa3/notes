<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import QRCode from 'qrcode';
  import { Html5Qrcode } from 'html5-qrcode';
  import {
    probeServer,
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
    fetchAppVersion
  } from '../api.js';
  import { setPairedConnection, clearPairedConnection } from '../storage.js';

  let { isOpen = $bindable(false) } = $props();

  let currentAppVer = $state('v2.1.11');
  let pairInfo = $state(null);
  let peers = $state([]);
  let inputToken = $state('');
  let registerMessage = $state('');
  let qrDataUrl = $state('');
  let isGeneratingQr = $state(false);
  let activeTab = $state('pairing'); // 'pairing' | 'cluster'
  let copyFeedback = $state(false);
  let isScanning = $state(false);
  let scannerError = $state('');
  let scannerInstance = null;
  let currentServerUrl = $state('');

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

  let clusterPollTimer = null;
  let glinerPollTimer = null;

  onDestroy(() => {
    stopScanner();
    stopClusterPolling();
  });

  $effect(() => {
    if (isOpen) {
      currentServerUrl = getServerUrl();
      if (activeTab === 'pairing') {
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
    if (isOpen && activeTab === 'pairing') {
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

  function getMobileDeviceName() {
    if (typeof navigator !== 'undefined' && navigator.userAgent) {
      if (/android/i.test(navigator.userAgent)) {
        const match = navigator.userAgent.match(/;\s*([^;)]+)\s*Build/i);
        if (match && match[1]) return match[1].trim();
        return 'Android Device';
      }
      if (/iphone|ipad|ipod/i.test(navigator.userAgent)) return 'iOS Device';
      if (/windows/i.test(navigator.userAgent)) return 'Windows Workstation';
      if (/mac/i.test(navigator.userAgent)) return 'Mac Client';
      if (/linux/i.test(navigator.userAgent)) return 'Linux Client';
    }
    return 'Mobile Peer';
  }

  async function updateQrCode() {
    isGeneratingQr = true;
    try {
      let payloadToEncode = '';
      if (pairInfo && pairInfo.pairing_payload) {
        payloadToEncode = JSON.stringify(pairInfo.pairing_payload);
      } else if (pairInfo && (pairInfo.lan_url || pairInfo.lan_ip || pairInfo.tailscale_url)) {
        const port = pairInfo.http_port || 58850;
        payloadToEncode = JSON.stringify({
          type: 'NOTES_PAIR',
          v: 2,
          name: pairInfo.device_name || 'Desktop Workstation',
          lan_url: pairInfo.lan_url || (pairInfo.lan_ip ? `http://${pairInfo.lan_ip}:${port}` : null),
          tailscale_url: pairInfo.tailscale_url || (pairInfo.tailscale_ip ? `http://${pairInfo.tailscale_ip}:${port}` : null),
          lan_ip: pairInfo.lan_ip || null,
          tailscale_ip: pairInfo.tailscale_ip || null,
          http_port: port,
          fingerprint: pairInfo.fingerprint || 'local'
        });
      } else {
        const customUrl = getServerUrl();
        if (customUrl) {
          payloadToEncode = JSON.stringify({
            type: 'NOTES_PAIR',
            v: 2,
            name: 'Notes Workstation',
            lan_url: customUrl,
            tailscale_url: null
          });
        } else {
          qrDataUrl = '';
          return;
        }
      }

      const url = await QRCode.toDataURL(payloadToEncode, {
        width: 240,
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
        if (activeTab === 'pairing') updateQrCode();
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
    const peerUrl = `http://${peer.lan_ip || peer.sender_ip}:${peer.http_port || 58850}`;
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



  async function handleCopyPayload() {
    let payload = '';
    if (pairInfo && pairInfo.pairing_payload) {
      payload = JSON.stringify(pairInfo.pairing_payload, null, 2);
    } else {
      payload = getServerUrl() || `http://${defaultHost}`;
    }
    try {
      await navigator.clipboard.writeText(payload);
      copyFeedback = true;
      setTimeout(() => copyFeedback = false, 2000);
    } catch (err) {
      console.error('Clipboard copy failed:', err);
    }
  }

  function handleDisconnect() {
    clearPairedConnection();
    currentServerUrl = '';
    window.dispatchEvent(new CustomEvent('notes-server-changed', { detail: '' }));
    registerMessage = 'ℹ️ Disconnected from workstation. Operating in standalone offline mode.';
    setTimeout(() => { if (registerMessage.includes('Disconnected')) registerMessage = ''; }, 3500);
  }

  async function handleConnectPayload(rawInput) {
    const text = (rawInput || '').trim();
    if (!text) return;
    registerMessage = '🔍 Analyzing pairing payload...';

    // 1. Plain HTTP / HTTPS URL
    if (text.startsWith('http://') || text.startsWith('https://')) {
      const cleanUrl = text.replace(/\/+$/, '');
      registerMessage = `Testing connection to ${cleanUrl}...`;
      const probe = await probeServer(cleanUrl, 3000);
      if (probe.ok) {
        setServerUrl(cleanUrl);
        currentServerUrl = cleanUrl;
        window.dispatchEvent(new CustomEvent('notes-server-changed', { detail: cleanUrl }));
        try {
          await registerPeer({
            device_name: getMobileDeviceName(),
            fingerprint: `client-${Date.now()}`
          }, cleanUrl);
        } catch (_) {}
        registerMessage = `🎉 Successfully connected to ${cleanUrl}!`;
        inputToken = '';
        await loadInfo();
        setTimeout(() => {
          if (isOpen && registerMessage.startsWith('🎉')) isOpen = false;
        }, 2200);
        return;
      } else {
        registerMessage = `⚠️ Could not reach server at ${cleanUrl}. Ensure host is running.`;
        return;
      }
    }

    // 2. JSON pairing payload
    try {
      const payload = JSON.parse(text);
      const hostName = payload.name || payload.device_name || 'Workstation';
      registerMessage = `🔍 Discovered "${hostName}"! Probing connection...`;

      // Extract candidate URLs in order of priority (LAN Wi-Fi first, then Tailscale mesh)
      const port = payload.http_port || payload.port || 58850;
      const candidates = [];
      if (payload.lan_url) candidates.push({ name: 'Home Wi-Fi', url: payload.lan_url.replace(/\/+$/, '') });
      if (payload.tailscale_url) candidates.push({ name: 'Tailscale Mesh', url: payload.tailscale_url.replace(/\/+$/, '') });
      if (payload.lan_ip) candidates.push({ name: 'LAN IP', url: `http://${payload.lan_ip}:${port}` });
      if (payload.tailscale_ip || payload.ip) candidates.push({ name: 'Tailscale IP', url: `http://${payload.tailscale_ip || payload.ip}:${port}` });
      if (payload.magic_dns) candidates.push({ name: 'MagicDNS', url: `http://${payload.magic_dns}:${port}` });

      const uniqueCandidates = [];
      const seenUrls = new Set();
      for (const c of candidates) {
        if (c.url && !seenUrls.has(c.url)) {
          seenUrls.add(c.url);
          uniqueCandidates.push(c);
        }
      }

      if (uniqueCandidates.length === 0) {
        registerMessage = '❌ Invalid QR payload: No network endpoints found in scanned code.';
        return;
      }

      let winner = null;

      // Stage 1: Probe local Wi-Fi / LAN first with 1.2s timeout (fastest route)
      for (const cand of uniqueCandidates) {
        registerMessage = `Testing ${cand.name} (${cand.url})...`;
        const probe = await probeServer(cand.url, 1200, payload.access_token || '');
        if (probe.ok) {
          winner = cand;
          break;
        }
      }

      // Stage 2: If Wi-Fi did not reply, probe Tailscale candidates with 3s timeout
      if (!winner) {
        for (const cand of uniqueCandidates) {
          if (cand.name.toLowerCase().includes('tailscale') || cand.url.includes('100.')) {
            registerMessage = `Testing Tailscale route (${cand.url})...`;
            const probe = await probeServer(cand.url, 3000, payload.access_token || '');
            if (probe.ok) {
              winner = cand;
              break;
            }
          }
        }
      }

      if (winner) {
        setPairedConnection(payload, winner.url);
        currentServerUrl = winner.url;
        window.dispatchEvent(new CustomEvent('notes-server-changed', { detail: winner.url }));

        // Register our identity on the workstation host
        try {
          await registerPeer({
            device_name: getMobileDeviceName(),
            fingerprint: `client-${Date.now()}`
          }, winner.url);
        } catch (e) {
          console.warn('Peer registration notice:', e);
        }

        registerMessage = `🎉 Boom, connected to "${hostName}" via ${winner.name} (${winner.url})!`;
        inputToken = '';
        await loadInfo();
        setTimeout(() => {
          if (isOpen && registerMessage.startsWith('🎉')) isOpen = false;
        }, 2200);
      } else {
        // Fallback: Configure primary candidate anyway
        const fallback = uniqueCandidates[0];
        setPairedConnection(payload, fallback.url);
        currentServerUrl = fallback.url;
        window.dispatchEvent(new CustomEvent('notes-server-changed', { detail: fallback.url }));
        registerMessage = `⚠️ Configured server to ${fallback.url}, but host did not respond immediately. Check network and firewall.`;
      }
    } catch (err) {
      registerMessage = `❌ Could not parse QR code: ${err.message}`;
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
          await handleConnectPayload(decodedText);
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
          <p class="text-xs text-[var(--text-secondary)]">One-scan instant pairing over Wi-Fi & Tailscale, and cluster model orchestration</p>
        </div>
        <button 
          class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1 cursor-pointer"
          onclick={handleCloseModal}
        >&times;</button>
      </div>

      <!-- Mode Tabs (2 tabs: Quick Pair & Nodes/Models) -->
      <div class="flex rounded-xl bg-[var(--bg-secondary)] p-1 border border-[var(--border)]">
        <button
          type="button"
          class="flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all {activeTab === 'pairing' ? 'bg-[var(--accent)] text-white shadow-xs' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'} cursor-pointer"
          onclick={() => { activeTab = 'pairing'; stopClusterPolling(); updateQrCode(); }}
        >
          🔗 Quick Pair & Mesh
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
        <!-- ── TAB 2: NODES & CLUSTER MANAGEMENT ── -->
        <div class="flex flex-col gap-4">


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
        <!-- ── TAB 1: ONE UNIVERSAL QR CODE & ONE-SCAN PAIRING ── -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Universal QR Code Card -->
          <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col items-center justify-between gap-3 text-center">
            <div class="flex flex-col gap-0.5 items-center">
              <span class="text-xs font-bold text-[var(--text-primary)]">
                Universal Pairing QR
              </span>
              <span class="text-[11px] text-[var(--text-secondary)]">
                Scan with your phone's camera in Notes to connect instantly
              </span>
            </div>
            
            <div class="bg-white rounded-2xl p-3 flex flex-col items-center justify-center shadow-md border border-slate-200">
              {#if qrDataUrl}
                <img src={qrDataUrl} alt="Universal Pairing QR Code" class="w-48 h-48 rounded-lg object-contain" />
              {:else if isGeneratingQr}
                <div class="w-48 h-48 flex flex-col items-center justify-center text-slate-400 gap-2">
                  <span class="text-2xl animate-spin">⏳</span>
                  <span class="text-xs font-medium">Generating QR...</span>
                </div>
              {:else}
                <div class="w-48 h-48 flex flex-col items-center justify-center text-slate-400 gap-2 text-center p-2">
                  <span class="text-3xl">📱</span>
                  <span class="text-xs font-semibold text-slate-700">Client / Standalone</span>
                  <span class="text-[10px] text-slate-500 leading-tight">Tap "Scan QR Code" on the right to pair with your PC.</span>
                </div>
              {/if}
            </div>

            <!-- Auto-Discovered Endpoints -->
            <div class="w-full flex flex-col gap-1.5 text-xs text-left bg-[var(--card)] p-2.5 rounded-lg border border-[var(--border)]">
              <!-- LAN / Wi-Fi route -->
              <div class="flex items-center justify-between gap-1 text-[11px]">
                <div class="flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full {pairInfo?.lan_url ? 'bg-emerald-400' : 'bg-slate-500'}"></span>
                  <span class="text-[var(--text-secondary)]">🏠 Local Wi-Fi:</span>
                </div>
                <span class="font-mono font-medium text-[var(--text-primary)] truncate">
                  {#if pairInfo?.lan_url}
                    {pairInfo.lan_url}
                  {:else if currentServerUrl}
                    {currentServerUrl}
                  {:else}
                    <span class="text-[var(--text-secondary)] italic">Detecting...</span>
                  {/if}
                </span>
              </div>

              <!-- Tailscale Mesh route -->
              <div class="flex items-center justify-between gap-1 text-[11px]">
                <div class="flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full {pairInfo?.tailscale_ip ? 'bg-indigo-400' : 'bg-slate-500'}"></span>
                  <span class="text-[var(--text-secondary)]">🔒 Tailscale:</span>
                </div>
                <span class="font-mono font-medium text-[var(--text-primary)] truncate">
                  {#if pairInfo?.tailscale_ip}
                    {pairInfo.tailscale_url || `http://${pairInfo.tailscale_ip}:${pairInfo.http_port || 58850}`}
                  {:else}
                    <span class="text-[var(--text-secondary)] italic">Offline / Not detected</span>
                  {/if}
                </span>
              </div>
            </div>

            <button
              type="button"
              class="w-full py-2 rounded-lg text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
              onclick={handleCopyPayload}
            >
              <span>{copyFeedback ? '✅ Copied to Clipboard!' : '📋 Copy Pairing Code / Link'}</span>
            </button>
          </div>

          <!-- Camera Scanner or Manual Connect Form -->
          <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-3">
            <!-- Connection Status Pill -->
            <div class="p-2.5 rounded-lg border flex items-center justify-between gap-2 {currentServerUrl ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300' : 'bg-[var(--card)] border-[var(--border)] text-[var(--text-secondary)]'}">
              <div class="flex flex-col text-xs">
                {#if currentServerUrl}
                  <span class="font-bold flex items-center gap-1.5">🟢 Connected to Server</span>
                  <span class="font-mono text-[10px] text-emerald-200 truncate">{currentServerUrl}</span>
                {:else}
                  <span class="font-bold text-[var(--text-primary)]">📱 Standalone / Offline Mode</span>
                  <span class="text-[10px]">Notes stored locally. Scan PC screen to link.</span>
                {/if}
              </div>
              {#if currentServerUrl}
                <button
                  type="button"
                  class="px-2 py-1 rounded text-[11px] bg-red-950/40 hover:bg-red-900/40 text-red-300 border border-red-500/40 transition-colors cursor-pointer shrink-0"
                  onclick={handleDisconnect}
                >
                  Disconnect
                </button>
              {/if}
            </div>

            <!-- Scanner Launch Button -->
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-semibold text-[var(--text-primary)]">Scan Remote Screen</span>
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

            <p class="text-[11px] text-[var(--text-secondary)]">Or paste pairing code or backend URL manually:</p>

            <textarea
              bind:value={inputToken}
              placeholder={`http://192.168.0.45:5000 or {"v": 2, "name": "...", "lan_url": "..."}`}
              class="w-full flex-1 min-h-[75px] p-2.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs font-mono text-[var(--text-primary)] resize-none focus:outline-hidden focus:border-[var(--accent)]"
            ></textarea>

            <button
              class="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity cursor-pointer"
              onclick={() => handleConnectPayload(inputToken)}
            >
              Connect & Pair Device
            </button>

            {#if registerMessage}
              <div class="p-2.5 rounded-lg border text-[11px] font-mono {registerMessage.includes('❌') || registerMessage.includes('Error') || registerMessage.includes('Failed') ? 'bg-red-950/30 border-red-500/40 text-red-400' : (registerMessage.includes('🎉') ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300' : 'bg-slate-800 border-slate-700 text-slate-200')}">
                {registerMessage}
              </div>
            {/if}
          </div>
        </div>

        <!-- Paired Peers List -->
        <div class="flex-1 overflow-y-auto min-h-0 flex flex-col gap-2">
          <span class="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">Paired Mesh Devices ({peers.length})</span>
          {#if peers.length === 0}
            <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] text-xs text-[var(--text-secondary)] text-center">
              No remote devices paired yet. Open Notes Workstation on your Android phone and scan this screen to connect!
            </div>
          {:else}
            {#each peers as peer}
              <div class="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-between text-xs">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full {peer.is_active ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}"></span>
                  <div class="flex flex-col">
                    <span class="font-semibold text-[var(--text-primary)]">{peer.device_name}</span>
                    <span class="text-[10px] text-[var(--text-secondary)] font-mono">{peer.magic_dns || peer.tailscale_ip || 'Paired Device'} • {peer.fingerprint?.substring(0, 18)}...</span>
                  </div>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] bg-[var(--bg-tertiary)] text-[var(--accent)] font-mono">Mesh Active</span>
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

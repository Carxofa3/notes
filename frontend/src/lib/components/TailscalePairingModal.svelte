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
  import { setPairedConnection, clearPairedConnection, getPairedConnection, getDeviceId } from '../storage.js';

  let { isOpen = $bindable(false) } = $props();

  let currentAppVer = $state('v2.1.14');
  let pairInfo = $state(null);
  let localWifiUrl = $derived(
    pairInfo?.pairing_payload?.lan_url ||
    pairInfo?.lan_url ||
    (pairInfo?.lan_ip ? `http://${pairInfo.lan_ip}:${pairInfo.http_port || 58850}` : null)
  );
  let tailscaleUrl = $derived(
    pairInfo?.pairing_payload?.tailscale_url ||
    pairInfo?.tailscale_url ||
    (pairInfo?.tailscale_ip ? `http://${pairInfo.tailscale_ip}:${pairInfo.http_port || 58850}` : null)
  );
  let peers = $state([]);
  let inputToken = $state('');
  let registerMessage = $state('');
  let peerListError = $state('');
  let qrDataUrl = $state('');
  let isGeneratingQr = $state(false);
  let qrPayloadKey = '';
  let isConnecting = $state(false);
  let connectionState = $state('offline');
  let connectionRoute = $state('');
  let hasPairedConnection = $state(false);
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
  let peerPollTimer = null;
  let heartbeatTimer = null;
  let hasOpenedModal = false;

  onDestroy(() => {
    stopScanner();
    stopClusterPolling();
    stopPeerPolling();
    if (heartbeatTimer) clearInterval(heartbeatTimer);
  });

  $effect(() => {
    if (isOpen) {
      if (hasOpenedModal) return;
      hasOpenedModal = true;
      currentServerUrl = getServerUrl();
      const paired = getPairedConnection();
      hasPairedConnection = !!paired;
      connectionState = paired ? 'checking' : 'offline';
      if (paired) heartbeatPairedDevice();
      loadInfo();
      loadAppVersion();
      startPeerPolling();
      if (activeTab === 'cluster') {
        loadClusterData();
        startClusterPolling();
      }
    } else {
      hasOpenedModal = false;
      stopClusterPolling();
      stopPeerPolling();
      stopScanner();
    }
  });

  onMount(() => {
    heartbeatPairedDevice();
    heartbeatTimer = setInterval(heartbeatPairedDevice, 30000);
    return () => {
      if (heartbeatTimer) clearInterval(heartbeatTimer);
    };
  });

  function startPeerPolling() {
    stopPeerPolling();
    peerPollTimer = setInterval(() => {
      if (isOpen && activeTab === 'pairing') loadPeerList();
    }, 5000);
  }

  function stopPeerPolling() {
    if (peerPollTimer) {
      clearInterval(peerPollTimer);
      peerPollTimer = null;
    }
  }

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

  function peerIdentity() {
    return {
      device_name: getMobileDeviceName(),
      fingerprint: getDeviceId()
    };
  }

  async function heartbeatPairedDevice() {
    const paired = getPairedConnection();
    if (!paired?.activeUrl || !paired?.accessToken) {
      if (!paired) {
        hasPairedConnection = false;
        connectionState = 'offline';
      }
      return;
    }
    hasPairedConnection = true;
    try {
      await registerPeer(peerIdentity());
      connectionState = 'online';
      const active = getPairedConnection()?.activeUrl || paired.activeUrl;
      connectionRoute = active.includes('100.') || active.includes('.ts.net') ? 'Tailscale' : 'Wi-Fi';
      currentServerUrl = active;
    } catch (_) {
      connectionState = 'offline';
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
    // A client must never turn around and display the host's pairing secret.
    if (getPairedConnection()) {
      qrDataUrl = '';
      qrPayloadKey = '';
      isGeneratingQr = false;
      return;
    }

    isGeneratingQr = true;
    try {
      let payloadToEncode = '';
      if (pairInfo && pairInfo.pairing_payload) {
        const { ts: _volatileTimestamp, ...stablePayload } = pairInfo.pairing_payload;
        payloadToEncode = JSON.stringify(stablePayload);
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
        qrDataUrl = '';
        qrPayloadKey = '';
        return;
      }

      if (!payloadToEncode || payloadToEncode === qrPayloadKey && qrDataUrl) return;
      qrPayloadKey = payloadToEncode;

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
        if (activeTab === 'pairing') await updateQrCode();
      }
    } catch (e) {
      console.warn('Could not fetch pair info:', e);
    }

    await loadPeerList();
  }

  async function loadPeerList() {
    try {
      peers = await fetchPeers();
      peerListError = '';
    } catch (e) {
      console.warn('Could not fetch peers:', e);
      peerListError = e.message || 'Paired devices could not be loaded.';
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
    const payload = pairInfo?.pairing_payload
      ? JSON.stringify(pairInfo.pairing_payload, null, 2)
      : '';
    if (!payload) return;
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
    hasPairedConnection = false;
    currentServerUrl = '';
    connectionState = 'offline';
    connectionRoute = '';
    window.dispatchEvent(new CustomEvent('notes-server-changed', { detail: '' }));
    registerMessage = 'Disconnected. This device will keep its local notes until you pair again.';
    setTimeout(() => { if (registerMessage.includes('Disconnected')) registerMessage = ''; }, 3500);
  }

  async function finishPairing(payload, winner, accessToken) {
    const identity = peerIdentity();
    const registration = await registerPeer(identity, winner.url, accessToken);
    if (registration.fingerprint && registration.fingerprint !== identity.fingerprint) {
      throw new Error('The workstation returned a different device identity. Pairing was not saved.');
    }

    const confirmedPeers = await fetchPeers(winner.url, accessToken);
    if (!confirmedPeers.some(peer => peer.fingerprint === identity.fingerprint)) {
      throw new Error('The workstation did not list this device after pairing. Try scanning again.');
    }

    setPairedConnection(payload, winner.url);
    hasPairedConnection = true;
    currentServerUrl = winner.url;
    connectionState = 'online';
    connectionRoute = winner.name;
    window.dispatchEvent(new CustomEvent('notes-server-changed', { detail: winner.url }));
    await loadInfo();
  }

  async function handleConnectPayload(rawInput) {
    const text = (rawInput || '').trim();
    if (!text || isConnecting) return;
    isConnecting = true;
    registerMessage = 'Checking the pairing code…';

    try {
      let payload;
      if (/^https?:\/\//i.test(text)) {
        const saved = getPairedConnection();
        if (!saved?.accessToken) {
          throw new Error('A server address alone cannot pair securely. Scan the QR shown in Notes Workstation.');
        }
        payload = {
          type: 'NOTES_PAIR',
          v: 2,
          name: saved.name,
          lan_url: text.replace(/\/+$/, ''),
          access_token: saved.accessToken
        };
      } else {
        payload = JSON.parse(text);
      }

      if (payload.type && payload.type !== 'NOTES_PAIR') {
        throw new Error('This code is not a Notes Workstation pairing code.');
      }
      if (!payload.access_token) {
        throw new Error('This pairing code has no device credential. Reopen the QR in Notes Workstation and scan it again.');
      }

      const hostName = payload.name || payload.device_name || 'Workstation';
      const port = payload.http_port || payload.port || 58850;
      const candidates = [];
      const addCandidate = (name, rawUrl) => {
        if (!rawUrl) return;
        try {
          const parsed = new URL(rawUrl);
          if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) return;
          const url = parsed.toString().replace(/\/+$/, '');
          if (!candidates.some(candidate => candidate.url === url)) candidates.push({ name, url });
        } catch (_) {}
      };
      addCandidate('Wi-Fi', payload.lan_url);
      addCandidate('Tailscale', payload.tailscale_url);
      addCandidate('Wi-Fi', payload.lan_ip ? `http://${payload.lan_ip}:${port}` : null);
      addCandidate('Tailscale', (payload.tailscale_ip || payload.ip) ? `http://${payload.tailscale_ip || payload.ip}:${port}` : null);
      addCandidate('Tailscale', payload.magic_dns ? `http://${payload.magic_dns}:${port}` : null);
      if (candidates.length === 0) throw new Error('This QR code has no usable network addresses.');

      let winner = null;

      for (const cand of candidates) {
        registerMessage = `Finding ${hostName} over ${cand.name}…`;
        const probe = await probeServer(cand.url, cand.name === 'Tailscale' ? 3500 : 1800, payload.access_token);
        if (probe.ok) {
          if (payload.fingerprint && probe.data?.fingerprint && probe.data.fingerprint !== payload.fingerprint) {
            throw new Error('The QR code belongs to a different workstation. Scan its current QR code.');
          }
          winner = cand;
          break;
        }
      }

      if (!winner) throw new Error(`Could not reach ${hostName}. Check that both devices are on Wi-Fi or Tailscale, then scan again.`);

      await finishPairing(payload, winner, payload.access_token);
      registerMessage = `Paired with ${hostName}. Connected over ${winner.name}; it will switch routes automatically when networks change.`;
      inputToken = '';
    } catch (err) {
      registerMessage = err instanceof SyntaxError
        ? 'This is not a valid Notes Workstation pairing code.'
        : (err.message || 'Pairing could not be completed. Try scanning again.');
    } finally {
      isConnecting = false;
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
            <h2 class="text-base sm:text-lg font-bold text-[var(--text-primary)]">Connect devices</h2>
            <span class="px-2 py-0.5 rounded text-[10px] bg-[var(--bg-tertiary)] text-[var(--accent)] border border-[var(--border)]">{hasPairedConnection ? 'Paired' : 'Ready to pair'}</span>
            <span class="px-2 py-0.5 rounded text-[10px] bg-[var(--bg-tertiary)] text-[var(--accent)] font-mono">{currentAppVer}</span>
          </div>
          <p class="text-xs text-[var(--text-secondary)]">Scan once. Notes switches between Wi-Fi and Tailscale automatically when either route is available.</p>
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
          onclick={() => { activeTab = 'pairing'; stopClusterPolling(); startPeerPolling(); updateQrCode(); }}
        >
          🔗 Pair devices
        </button>
        <button
          type="button"
          class="flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all {activeTab === 'cluster' ? 'bg-[var(--accent)] text-white shadow-xs' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'} cursor-pointer"
          onclick={() => { activeTab = 'cluster'; stopPeerPolling(); stopScanner(); loadClusterData(); startClusterPolling(); }}
        >
          🖥️ Devices & models
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

          <div class="flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                Paired devices ({clusterData?.paired_peers?.length || 0})
              </span>
              <span class="text-[10px] text-[var(--text-secondary)]">Pairing is saved across restarts</span>
            </div>

            {#if !clusterData?.paired_peers || clusterData.paired_peers.length === 0}
              <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] text-xs text-[var(--text-secondary)] text-center">
                Devices appear here after Notes confirms their pairing. Network discovery alone does not mark a device as paired.
              </div>
            {:else}
              {#each clusterData.paired_peers as pairedPeer}
                {@const liveNode = clusterData.discovered_nodes?.find(node => node.node_id === pairedPeer.fingerprint)}
                <div class="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-1.5">
                  <div class="flex items-center justify-between gap-3">
                    <span class="text-xs font-semibold text-[var(--text-primary)]">{pairedPeer.device_name}</span>
                    <span class="px-2 py-0.5 rounded text-[10px] {pairedPeer.is_online ? 'bg-emerald-950/40 text-emerald-300' : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'}">
                      {pairedPeer.is_online ? 'Online now' : 'Paired · offline'}
                    </span>
                  </div>
                  <span class="text-[10px] text-[var(--text-secondary)]">
                    {#if pairedPeer.is_online}
                      Connection confirmed by this device. Notes will retry both saved routes automatically.
                    {:else}
                      Pairing is saved. It will reconnect automatically when this device is available.
                    {/if}
                  </span>
                  {#if liveNode?.services?.llamacpp?.enabled}
                    <span class="text-[10px] text-indigo-300">Model endpoint available · llama.cpp</span>
                  {:else}
                    <span class="text-[10px] text-[var(--text-secondary)]">No model endpoint is being shared by this device.</span>
                  {/if}
                </div>
              {/each}
            {/if}
          </div>

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
        <!-- ── ONE-TIME DEVICE PAIRING ── -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Universal QR Code Card -->
          <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col items-center justify-between gap-3 text-center">
            <div class="flex flex-col gap-0.5 items-center">
              <span class="text-xs font-bold text-[var(--text-primary)]">
                Pair this device
              </span>
              <span class="text-[11px] text-[var(--text-secondary)]">
                Scan once from Notes on your phone. This code stays stable.
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
                  <span class="text-3xl">{hasPairedConnection ? '✓' : '📱'}</span>
                  <span class="text-xs font-semibold text-slate-700">{hasPairedConnection ? 'Already paired' : 'Waiting for workstation'}</span>
                  <span class="text-[10px] text-slate-500 leading-tight">{hasPairedConnection ? 'This device keeps its pairing. No repeat scan needed.' : 'Open this screen on your workstation to show its pairing code.'}</span>
                </div>
              {/if}
            </div>

            <!-- Auto-Discovered Endpoints -->
            <div class="w-full flex flex-col gap-1.5 text-xs text-left bg-[var(--card)] p-2.5 rounded-lg border border-[var(--border)]">
              <!-- LAN / Wi-Fi route -->
              <div class="flex items-center justify-between gap-1 text-[11px]">
                <div class="flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full {localWifiUrl ? 'bg-emerald-400' : 'bg-slate-500'}"></span>
                  <span class="text-[var(--text-secondary)]">🏠 Local Wi-Fi:</span>
                </div>
                <span class="font-mono font-medium text-[var(--text-primary)] truncate">
                  {#if localWifiUrl}
                    {localWifiUrl}
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
                    {tailscaleUrl}
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
            {#if pairInfo?.pairing_payload && !hasPairedConnection}
              <div class="flex flex-col gap-3 h-full justify-center">
                <div class="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/40 text-emerald-300">
                  <span class="block text-sm font-bold">Workstation ready</span>
                  <span class="block mt-1 text-xs text-emerald-100">Scan the code once with Notes on your phone. The phone will confirm here after the workstation saves the pairing.</span>
                </div>
                <div class="p-3 rounded-xl bg-[var(--card)] border border-[var(--border)] text-xs flex flex-col gap-2">
                  <span class="font-semibold text-[var(--text-primary)]">Automatic connection routes</span>
                  <span class="text-[var(--text-secondary)]">Wi-Fi: {localWifiUrl || 'Not available on this network'}</span>
                  <span class="text-[var(--text-secondary)]">Tailscale: {tailscaleUrl || 'Not detected (Wi-Fi pairing still works)'}</span>
                </div>
                {#if registerMessage}
                  <div class="p-2.5 rounded-lg border text-[11px] text-[var(--text-secondary)]" role="status" aria-live="polite">{registerMessage}</div>
                {/if}
              </div>
            {:else if hasPairedConnection}
              <div class="flex flex-col gap-3 h-full justify-center">
                <div class="p-3 rounded-xl border {connectionState === 'online' ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300' : 'bg-amber-950/30 border-amber-500/40 text-amber-200'}" role="status" aria-live="polite">
                  <span class="block text-sm font-bold">{connectionState === 'online' ? 'Paired · Online' : 'Paired · reconnecting'}</span>
                  <span class="block mt-1 text-xs">{connectionState === 'online' ? `Using ${connectionRoute || 'the best available route'}` : 'Your pairing is saved. Notes is retrying Wi-Fi and Tailscale.'}</span>
                </div>
                <p class="text-xs text-[var(--text-secondary)]">You only need to scan once. If you want to connect to a different workstation, disconnect and scan its code.</p>
                <button
                  type="button"
                  class="self-start px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-950/40 hover:bg-red-900/40 text-red-300 border border-red-500/40 cursor-pointer"
                  onclick={handleDisconnect}
                >Disconnect</button>
                {#if registerMessage}
                  <div class="p-2.5 rounded-lg border text-[11px] {registerMessage.startsWith('Paired with') ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300' : 'bg-red-950/30 border-red-500/40 text-red-300'}" role="status" aria-live="polite">{registerMessage}</div>
                {/if}
              </div>
            {:else}
              <div class="flex flex-col gap-3">
                <div class="flex items-center justify-between gap-2">
                  <div class="flex flex-col text-xs">
                    <span class="font-bold text-[var(--text-primary)]">Pair with your workstation</span>
                    <span class="text-[10px] text-[var(--text-secondary)]">Scan its QR code. Pairing is saved only after the workstation confirms it.</span>
                  </div>
                  <button
                    type="button"
                    disabled={isConnecting}
                    class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shadow-xs cursor-pointer disabled:opacity-50 {isScanning ? 'bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30' : 'bg-[var(--accent)] text-white hover:opacity-90'}"
                    onclick={isScanning ? stopScanner : startScanner}
                  >
                    <span>{isScanning ? '⏹ Stop Scanner' : (isConnecting ? 'Connecting…' : '📷 Scan QR Code')}</span>
                  </button>
                </div>

                {#if isScanning}
                  <div class="rounded-xl overflow-hidden border border-[var(--accent)] bg-black/95 p-3 flex flex-col items-center gap-2 shadow-inner">
                    <div id="qr-reader" class="w-full max-w-[240px] rounded-lg overflow-hidden bg-black"></div>
                    <span class="text-[11px] text-slate-300 font-medium animate-pulse">Align the camera with the workstation code</span>
                    <button type="button" class="text-[11px] text-red-400 hover:text-red-300 font-medium hover:underline cursor-pointer" onclick={stopScanner}>Cancel</button>
                  </div>
                {/if}

                {#if scannerError}
                  <div class="p-2.5 rounded-lg bg-red-950/40 border border-red-500/40 text-[11px] text-red-300 flex flex-col gap-1">
                    <span class="font-semibold">Camera unavailable</span>
                    <span>{scannerError}</span>
                  </div>
                {/if}

                <label for="pairing-code" class="text-[11px] text-[var(--text-secondary)]">Or paste the pairing code copied from the workstation.</label>
                <textarea
                  id="pairing-code"
                  bind:value={inputToken}
                  placeholder={`{"type":"NOTES_PAIR","name":"...","lan_url":"...","access_token":"…"}`}
                  class="w-full min-h-[75px] p-2.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs font-mono text-[var(--text-primary)] resize-none focus:outline-hidden focus:border-[var(--accent)]"
                ></textarea>
                <button
                  class="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
                  disabled={isConnecting || !inputToken.trim()}
                  onclick={() => handleConnectPayload(inputToken)}
                >
                  {isConnecting ? 'Checking and pairing…' : 'Pair with code'}
                </button>
                {#if registerMessage}
                  <div class="p-2.5 rounded-lg border text-[11px] {registerMessage.startsWith('Paired with') ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300' : (isConnecting ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-red-950/30 border-red-500/40 text-red-300')}" role="status" aria-live="polite">
                    {registerMessage}
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        </div>

        <!-- Paired Peers List -->
        <div class="flex-1 overflow-y-auto min-h-0 flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">Paired devices ({peers.length})</span>
            <span class="text-[10px] text-[var(--text-secondary)]">Pair once · reconnects automatically</span>
          </div>
          {#if peers.length === 0}
            <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] text-xs text-[var(--text-secondary)] text-center">
              {peerListError || 'No devices have paired yet. Scan this workstation’s code from Notes on your phone.'}
            </div>
          {:else}
            {#each peers as peer}
              <div class="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-between text-xs">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full {peer.is_online ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}"></span>
                  <div class="flex flex-col">
                    <span class="font-semibold text-[var(--text-primary)]">{peer.device_name}</span>
                    <span class="text-[10px] text-[var(--text-secondary)]">{peer.is_online ? 'Connected now · network routes switch automatically' : 'Paired · will reconnect when available'}</span>
                  </div>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] {peer.is_online ? 'bg-emerald-950/40 text-emerald-300' : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'}">{peer.is_online ? 'Online' : 'Paired'}</span>
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

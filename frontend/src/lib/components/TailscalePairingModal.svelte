<script>
  import { onMount } from 'svelte';
  import QRCode from 'qrcode';
  import { fetchPairInfo, fetchPeers, registerPeer, getServerUrl } from '../api.js';

  let { isOpen = $bindable(false) } = $props();

  let pairInfo = $state(null);
  let peers = $state([]);
  let inputToken = $state('');
  let registerMessage = $state('');
  let qrDataUrl = $state('');
  let isGeneratingQr = $state(false);
  let activeTab = $state('wifi'); // 'wifi' | 'tailscale'
  let copyFeedback = $state(false);

  // Local fallback server URL
  const defaultHost = '192.168.0.45:5000';

  $effect(() => {
    if (isOpen) {
      updateQrCode();
      loadInfo();
    }
  });

  $effect(() => {
    // Re-generate QR when tab or pairInfo changes
    if (isOpen) {
      updateQrCode();
    }
  });

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
        updateQrCode();
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
    if (!inputToken.trim()) return;
    registerMessage = 'Pairing with peer...';
    try {
      let parsed = JSON.parse(inputToken.trim());
      const res = await registerPeer(parsed);
      if (res && res.peer_id) {
        registerMessage = `Successfully paired with "${res.device_name}"!`;
        inputToken = '';
        await loadInfo();
      } else {
        registerMessage = 'Failed to pair. Invalid peer payload.';
      }
    } catch (e) {
      registerMessage = 'Error: Input must be a valid JSON pairing payload.';
    }
  }
</script>

{#if isOpen}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-2 sm:p-4" onclick={() => isOpen = false}>
    <div 
      class="w-full max-w-2xl max-h-[90vh] rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl p-4 sm:p-6 flex flex-col gap-4 overflow-y-auto"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-base sm:text-lg font-bold text-[var(--text-primary)]">Device Sync & Pairing</h2>
            <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950/40 text-emerald-300 border border-emerald-500/40 font-mono">P2P Ready</span>
          </div>
          <p class="text-xs text-[var(--text-secondary)]">Connect your Android phone or secondary computer to sync lecture notes in real time</p>
        </div>
        <button 
          class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1"
          onclick={() => isOpen = false}
        >&times;</button>
      </div>

      <!-- Pairing Mode Tabs -->
      <div class="flex rounded-xl bg-[var(--bg-secondary)] p-1 border border-[var(--border)]">
        <button
          type="button"
          class="flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all {activeTab === 'wifi' ? 'bg-[var(--accent)] text-white shadow-xs' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
          onclick={() => { activeTab = 'wifi'; updateQrCode(); }}
        >
          📡 Wi-Fi Quick Connect
        </button>
        <button
          type="button"
          class="flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all {activeTab === 'tailscale' ? 'bg-[var(--accent)] text-white shadow-xs' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}"
          onclick={() => { activeTab = 'tailscale'; updateQrCode(); }}
        >
          🔒 Tailscale P2P Mesh
        </button>
      </div>

      <!-- Main Pairing Section -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- QR Code Card -->
        <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col items-center justify-center gap-3 text-center">
          <span class="text-xs font-semibold text-[var(--text-primary)]">
            {activeTab === 'wifi' ? 'Scan to Connect via Home Wi-Fi' : 'Scan to Connect via Tailscale Mesh'}
          </span>
          
          <!-- High-Contrast Scannable QR Image -->
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
              <span class="text-[10px] text-[var(--text-secondary)]">Scan with your phone camera or enter in Settings</span>
            {:else}
              <span class="font-mono text-[var(--accent)] font-semibold text-xs break-all">
                {pairInfo?.magic_dns || 'desktop.tailnet.ts.net'}
              </span>
              <span class="text-[10px] text-[var(--text-secondary)] font-mono">
                Port: {pairInfo?.port || 58855} • Fingerprint: {pairInfo?.fingerprint ? pairInfo.fingerprint.substring(0, 14) + '...' : 'local'}
              </span>
            {/if}
          </div>

          <!-- Copy Button -->
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] transition-colors flex items-center gap-1.5"
            onclick={handleCopyPayload}
          >
            <span>{copyFeedback ? '✅ Copied to Clipboard!' : '📋 Copy Connection URL'}</span>
          </button>
        </div>

        <!-- Manual Connect or Scan Form -->
        <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-3">
          <span class="text-xs font-semibold text-[var(--text-primary)]">Pair Remote Device (Android / Laptop)</span>
          <p class="text-[11px] text-[var(--text-secondary)]">Paste the peer token or JSON payload scanned from your phone or secondary computer:</p>

          <textarea
            bind:value={inputToken}
            placeholder={`{"magic_dns": "phone.tailnet.ts.net", "fingerprint": "ed25519:..."}`}
            class="w-full flex-1 min-h-[90px] p-2.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs font-mono text-[var(--text-primary)] resize-none focus:outline-hidden focus:border-[var(--accent)]"
          ></textarea>

          <button
            class="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
            onclick={handleConnectPeer}
          >
            Pair & Pin Certificate
          </button>

          {#if registerMessage}
            <span class="text-[11px] {registerMessage.includes('Error') || registerMessage.includes('Failed') ? 'text-red-400' : 'text-emerald-400'} font-mono">{registerMessage}</span>
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

      <!-- Footer -->
      <div class="flex justify-end pt-2 border-t border-[var(--border)]">
        <button
          class="px-4 py-2 rounded-xl text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]"
          onclick={() => isOpen = false}
        >
          Done
        </button>
      </div>
    </div>
  </div>
{/if}

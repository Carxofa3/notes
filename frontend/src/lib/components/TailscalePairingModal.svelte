<script>
  import { onMount } from 'svelte';
  import QRCode from 'qrcode';
  import { fetchPairInfo, fetchPeers, registerPeer } from '../api.js';

  let { isOpen = $bindable(false) } = $props();

  let pairInfo = $state(null);
  let peers = $state([]);
  let inputToken = $state('');
  let registerMessage = $state('');
  let qrCanvas = $state(null);

  $effect(() => {
    if (isOpen) {
      loadInfo();
    }
  });

  $effect(() => {
    if (pairInfo && qrCanvas) {
      const payloadStr = JSON.stringify(pairInfo.pairing_payload || pairInfo);
      QRCode.toCanvas(qrCanvas, payloadStr, {
        width: 150,
        margin: 1,
        color: {
          dark: '#000000',
          light: '#ffffff'
        }
      }).catch(err => console.error('QR code render error:', err));
    }
  });

  async function loadInfo() {
    pairInfo = await fetchPairInfo();
    peers = await fetchPeers();
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
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4" onclick={() => isOpen = false}>
    <div 
      class="w-full max-w-2xl max-h-[85vh] rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl p-6 flex flex-col gap-4 overflow-hidden"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-lg font-bold text-[var(--text-primary)]">Tailscale Peer-to-Peer Mesh Sync</h2>
            <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950/40 text-emerald-300 border border-emerald-500/40 font-mono">P2P mTLS</span>
          </div>
          <p class="text-xs text-[var(--text-secondary)]">Zero-cloud CRDT note synchronization between Desktop (Windows/Linux) and Android</p>
        </div>
        <button 
          class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1"
          onclick={() => isOpen = false}
        >&times;</button>
      </div>

      <!-- Main Pairing Section -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- QR Code / MagicDNS Card -->
        <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col items-center justify-center gap-3 text-center">
          <span class="text-xs font-semibold text-[var(--text-primary)]">Desktop Pairing QR Code</span>
          
          <!-- Real scannable QR Code Canvas -->
          <div class="bg-white rounded-xl p-2 flex flex-col items-center justify-center shadow-md">
            <canvas bind:this={qrCanvas} class="rounded-lg"></canvas>
          </div>

          <div class="flex flex-col gap-0.5 text-xs">
            <span class="font-mono text-[var(--accent)] font-semibold">{pairInfo?.magic_dns || 'desktop.tailnet.ts.net'}</span>
            <span class="text-[10px] text-[var(--text-secondary)] font-mono">Port: {pairInfo?.port || 58855} • Fingerprint: {pairInfo?.fingerprint?.substring(0, 16)}...</span>
          </div>
        </div>

        <!-- Manual Connect or Scan Form -->
        <div class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-3">
          <span class="text-xs font-semibold text-[var(--text-primary)]">Pair Remote Device (Android / Laptop)</span>
          <p class="text-[11px] text-[var(--text-secondary)]">Paste the peer token or JSON payload scanned from your phone or secondary computer:</p>

          <textarea
            bind:value={inputToken}
            placeholder={`{"magic_dns": "phone.tailnet.ts.net", "fingerprint": "ed25519:..."}`}
            class="w-full flex-1 p-2 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs font-mono text-[var(--text-primary)] resize-none focus:outline-hidden focus:border-[var(--accent)]"
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
            No remote peers paired yet. Open this app on Android to pair via MagicDNS.
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
          Close
        </button>
      </div>
    </div>
  </div>
{/if}

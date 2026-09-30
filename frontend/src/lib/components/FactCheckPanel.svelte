<script>
  import { evaluateDecide, verifyClaimAgainstSlides, verifyClaimAcademic, escalateContradiction } from '../api.js';

  let {
    isOpen = $bindable(false),
    noteContent = '',
    noteId = null,
    onApplyCorrection = () => {}
  } = $props();

  let isScanning = $state(false);
  let claims = $state([]);
  let activeTab = $state('all'); // 'all' | 'verified' | 'contradiction' | 'unverified'
  let escalatingIndex = $state(null);

  async function handleEscalate(index, item) {
    escalatingIndex = index;
    try {
      const res = await escalateContradiction(item.claim, item.evidence || item.citation || '', item.citation || '');
      if (res && res.resolution) {
        item.llmResolution = res.resolution;
      }
    } catch (e) {
      console.error('Escalation error:', e);
    } finally {
      escalatingIndex = null;
    }
  }

  $effect(() => {
    if (isOpen && noteContent) {
      runFactCheck();
    }
  });

  async function runFactCheck() {
    isScanning = true;
    claims = [];

    try {
      // 1. System 1: GLiNER2.5-Decide Claim Extraction & Triage
      const decideRes = await evaluateDecide(noteContent);
      const extractedClaims = (decideRes && decideRes.triaged_claims) ? decideRes.triaged_claims : [];

      if (extractedClaims.length === 0) {
        // Fallback sentence split if no structured propositions found
        const sents = noteContent.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 15);
        for (const s of sents.slice(0, 5)) {
          extractedClaims.push({ claim: s.trim(), status: 'unverified', confidence: 0.5 });
        }
      }

      // 2. Autonomous Multi-Tier Verification for each claim
      const verifiedList = [];
      for (const item of extractedClaims) {
        // First check Tier 1: Local Course Slides (Private & Offline)
        let slideRes = await verifyClaimAgainstSlides(item.claim, noteId);
        
        if (slideRes && slideRes.status !== 'unverified') {
          verifiedList.push({
            claim: item.claim,
            status: slideRes.status,
            confidence: slideRes.confidence,
            tier: 'Tier 1 (Course Slides)',
            citation: slideRes.citation,
            evidence: slideRes.evidence_text,
            correction: slideRes.suggested_correction
          });
        } else {
          // Fallback to Tier 2: Wikipedia / Semantic Scholar
          let academicRes = await verifyClaimAcademic(item.claim);
          if (academicRes && academicRes.citation) {
            verifiedList.push({
              claim: item.claim,
              status: academicRes.status || 'plausible',
              confidence: academicRes.confidence || 0.8,
              tier: 'Tier 2 (Academic Web)',
              citation: academicRes.citation,
              evidence: academicRes.snippet,
              correction: null
            });
          } else {
            verifiedList.push({
              claim: item.claim,
              status: item.status || 'unverified',
              confidence: item.confidence || 0.4,
              tier: 'Pending Verification',
              citation: 'No match in slides or academic index',
              evidence: '',
              correction: null
            });
          }
        }
      }

      claims = verifiedList;
    } catch (err) {
      console.error('Fact check error:', err);
    } finally {
      isScanning = false;
    }
  }

  let filteredClaims = $derived.by(() => {
    if (activeTab === 'all') return claims;
    return claims.filter(c => c.status === activeTab);
  });

  function getBadgeClasses(status) {
    switch (status) {
      case 'verified':
        return 'bg-emerald-950/40 text-emerald-300 border-emerald-500/40';
      case 'contradiction':
        return 'bg-rose-950/40 text-rose-300 border-rose-500/40';
      case 'plausible':
        return 'bg-amber-950/40 text-amber-300 border-amber-500/40';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
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
            <h2 class="text-lg font-bold text-[var(--text-primary)]">Autonomous Academic Fact-Checker</h2>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--accent)] text-white">GLiNER2.5 + Course RAG</span>
          </div>
          <p class="text-xs text-[var(--text-secondary)]">Multi-source verification against local lecture slide PDFs & academic papers</p>
        </div>
        <button 
          class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1"
          onclick={() => isOpen = false}
        >&times;</button>
      </div>

      <!-- Filters & Scan Action -->
      <div class="flex items-center justify-between gap-2">
        <div class="flex gap-1">
          {#each [
            { id: 'all', label: `All (${claims.length})` },
            { id: 'verified', label: `Verified (${claims.filter(c=>c.status==='verified').length})` },
            { id: 'contradiction', label: `Disputed (${claims.filter(c=>c.status==='contradiction').length})` },
            { id: 'unverified', label: `Unchecked (${claims.filter(c=>c.status==='unverified').length})` }
          ] as tab}
            <button
              class="px-2.5 py-1 rounded-lg text-xs font-medium transition-colors {activeTab === tab.id ? 'bg-[var(--accent)] text-white' : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'}"
              onclick={() => activeTab = tab.id}
            >
              {tab.label}
            </button>
          {/each}
        </div>

        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] flex items-center gap-1.5"
          onclick={runFactCheck}
          disabled={isScanning}
        >
          {#if isScanning}
            <span class="animate-spin inline-block w-3 h-3 border-2 border-[var(--accent)] border-t-transparent rounded-full"></span>
            <span>Verifying...</span>
          {:else}
            <span>Re-scan Note</span>
          {/if}
        </button>
      </div>

      <!-- Claims List -->
      <div class="flex-1 overflow-y-auto min-h-0 flex flex-col gap-3 pr-1">
        {#if isScanning && claims.length === 0}
          <div class="flex flex-col items-center justify-center p-8 gap-3 text-[var(--text-secondary)]">
            <span class="animate-spin inline-block w-8 h-8 border-3 border-[var(--accent)] border-t-transparent rounded-full"></span>
            <p class="text-sm">Triaging claims with GLiNER2.5-Decide and cross-referencing lecture slides...</p>
          </div>
        {:else if filteredClaims.length === 0}
          <div class="text-center p-8 text-sm text-[var(--text-secondary)]">
            No claims found in this category.
          </div>
        {:else}
          {#each filteredClaims as item}
            <div class="p-3.5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-2">
              <!-- Top Badge row -->
              <div class="flex items-center justify-between gap-2">
                <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold border {getBadgeClasses(item.status)} uppercase tracking-wide">
                  {item.status}
                </span>
                <span class="text-[10px] text-[var(--text-secondary)] font-mono">{item.tier} • {(item.confidence * 100).toFixed(0)}% conf</span>
              </div>

              <!-- Claim statement -->
              <p class="text-sm font-medium text-[var(--text-primary)] italic">"{item.claim}"</p>

              <!-- Citation & Excerpt -->
              {#if item.citation}
                <div class="p-2.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs flex flex-col gap-1">
                  <span class="font-semibold text-[var(--accent)]">{item.citation}</span>
                  {#if item.evidence}
                    <p class="text-[var(--text-secondary)] line-clamp-3">{item.evidence}</p>
                  {/if}
                </div>
              {/if}

              <!-- 1-Click Diff Correction if Contradicted -->
              {#if item.status === 'contradiction' && item.correction}
                <div class="p-2.5 rounded-lg bg-rose-950/30 border border-rose-500/40 text-xs flex flex-col gap-2">
                  <span class="font-semibold text-rose-300">Suggested Correction from Slide:</span>
                  <p class="font-mono text-emerald-300">{item.correction}</p>
                  <button
                    class="self-start px-3 py-1 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white font-medium shadow-sm transition-colors"
                    onclick={() => onApplyCorrection(item.claim, item.correction)}
                  >
                    Apply 1-Click Correction
                  </button>
                </div>
              {/if}

              <!-- Heavy LLM Escalation (llama.cpp / Tailscale GPU) -->
              <div class="flex items-center justify-between pt-1 border-t border-[var(--border)]">
                <button
                  class="text-[11px] font-medium text-[var(--accent)] hover:underline flex items-center gap-1"
                  onclick={() => handleEscalate(index, item)}
                  disabled={escalatingIndex === index}
                >
                  {#if escalatingIndex === index}
                    <span class="animate-spin inline-block w-2.5 h-2.5 border-2 border-[var(--accent)] border-t-transparent rounded-full"></span>
                    <span>Querying llama.cpp over Tailscale...</span>
                  {:else}
                    <span>⚡ Escalate to llama.cpp (:8080)</span>
                  {/if}
                </button>
              </div>

              {#if item.llmResolution}
                <div class="p-2.5 rounded-lg bg-[var(--card)] border border-[var(--accent)] text-xs flex flex-col gap-1.5 shadow-xs">
                  <div class="flex items-center gap-1.5 text-[var(--accent)] font-semibold">
                    <span>🤖 Stage 2 LLM Resolution:</span>
                  </div>
                  <p class="text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">{item.llmResolution}</p>
                </div>
              {/if}
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

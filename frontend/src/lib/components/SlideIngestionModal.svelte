<script>
  import { onMount } from 'svelte';
  import { fetchSlideDocuments, uploadSlideDeck } from '../api.js';

  let { isOpen = $bindable(false) } = $props();

  let documents = $state([]);
  let isUploading = $state(false);
  let uploadStatus = $state('');
  let fileInput = $state(null);
  let courseName = $state('General Course');
  let customTitle = $state('');

  $effect(() => {
    if (isOpen) {
      loadDocuments();
    }
  });

  async function loadDocuments() {
    documents = await fetchSlideDocuments();
  }

  async function handleUpload(e) {
    e.preventDefault();
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) return;

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('course_name', courseName);
    if (customTitle.trim()) {
      formData.append('title', customTitle.trim());
    }

    isUploading = true;
    uploadStatus = 'Extracting slides & indexing BM25 chunks...';

    try {
      const res = await uploadSlideDeck(formData);
      if (res && res.document_id) {
        uploadStatus = `Successfully indexed "${res.title}" (${res.total_pages} slides)!`;
        customTitle = '';
        fileInput.value = '';
        await loadDocuments();
      } else {
        uploadStatus = 'Upload failed. Ensure the file is a readable PDF.';
      }
    } catch (err) {
      uploadStatus = `Error: ${err.message}`;
    } finally {
      isUploading = false;
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
          <h2 class="text-lg font-bold text-[var(--text-primary)]">Course Slide & Textbook Indexer (RAG)</h2>
          <p class="text-xs text-[var(--text-secondary)]">All uploaded slides remain strictly private and local for offline lecture fact-checking</p>
        </div>
        <button 
          class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl p-1"
          onclick={() => isOpen = false}
        >&times;</button>
      </div>

      <!-- Upload Form -->
      <form onsubmit={handleUpload} class="p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex flex-col gap-3">
        <span class="text-xs font-semibold text-[var(--text-primary)]">Upload Lecture Deck (PDF)</span>
        
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <input
            type="text"
            bind:value={courseName}
            placeholder="Course Name (e.g. Bio 101)"
            class="px-3 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--accent)]"
          />
          <input
            type="text"
            bind:value={customTitle}
            placeholder="Deck Title (optional)"
            class="px-3 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--accent)]"
          />
        </div>

        <div class="flex items-center gap-3">
          <input
            bind:this={fileInput}
            type="file"
            accept=".pdf"
            required
            class="text-xs text-[var(--text-secondary)] file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-[var(--accent)] file:text-white hover:file:opacity-90 cursor-pointer"
          />

          <button
            type="submit"
            disabled={isUploading}
            class="ml-auto px-4 py-1.5 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {isUploading ? 'Indexing...' : 'Index Slide Deck'}
          </button>
        </div>

        {#if uploadStatus}
          <div class="text-xs {uploadStatus.includes('Error') || uploadStatus.includes('failed') ? 'text-red-400' : 'text-emerald-400'}">
            {uploadStatus}
          </div>
        {/if}
      </form>

      <!-- Indexed Decks List -->
      <div class="flex-1 overflow-y-auto min-h-0 flex flex-col gap-2">
        <span class="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">Indexed Documents ({documents.length})</span>
        {#if documents.length === 0}
          <div class="text-center p-6 text-xs text-[var(--text-secondary)]">
            No course slide decks indexed yet. Upload your first lecture PDF above.
          </div>
        {:else}
          {#each documents as doc}
            <div class="p-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] flex items-center justify-between text-xs">
              <div class="flex flex-col gap-0.5">
                <span class="font-semibold text-[var(--text-primary)]">{doc.title}</span>
                <span class="text-[10px] text-[var(--text-secondary)]">{doc.course_name} • {doc.total_pages} slides • {doc.chunks_count} chunks</span>
              </div>
              <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950/40 text-emerald-300 border border-emerald-500/30">Local RAG Ready</span>
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

<script>
  let {
    isOpen = $bindable(false),
    type = 'prompt', // 'prompt' | 'confirm' | 'alert'
    title = '',
    message = '',
    icon = '📝',
    defaultValue = '',
    placeholder = '',
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    danger = false,
    onConfirm = () => {},
    onCancel = () => {}
  } = $props();

  let inputVal = $state('');
  let inputRef = $state(null);

  $effect(() => {
    if (isOpen) {
      inputVal = defaultValue || '';
      // Autofocus input on next tick if prompt
      if (type === 'prompt') {
        setTimeout(() => {
          if (inputRef) {
            inputRef.focus();
            inputRef.select();
          }
        }, 50);
      }
    }
  });

  function handleConfirm() {
    const val = inputVal;
    isOpen = false;
    if (onConfirm) onConfirm(val);
  }

  function handleCancel() {
    isOpen = false;
    if (onCancel) onCancel();
  }

  function handleKeydown(e) {
    if (!isOpen) return;
    if (e.key === 'Enter') {
      e.preventDefault();
      handleConfirm();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancel();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
  <div 
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/65 backdrop-blur-xs p-4 animate-in fade-in duration-150"
    onclick={handleCancel}
    role="dialog"
    aria-modal="true"
  >
    <div 
      class="w-full max-w-md rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl p-5 flex flex-col gap-4 animate-in zoom-in-95 duration-150"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Title & Icon -->
      <div class="flex items-center gap-3">
        {#if icon}
          <span class="text-2xl p-2 rounded-xl bg-[var(--card)] border border-[var(--border)] flex items-center justify-center shrink-0">
            {icon}
          </span>
        {/if}
        <div class="flex-1 min-w-0">
          <h3 class="text-sm font-bold text-[var(--text-primary)] leading-tight">{title}</h3>
          {#if message}
            <p class="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">{message}</p>
          {/if}
        </div>
      </div>

      <!-- Input if Prompt -->
      {#if type === 'prompt'}
        <div class="flex flex-col gap-1.5">
          <input
            bind:this={inputRef}
            bind:value={inputVal}
            type="text"
            {placeholder}
            class="w-full px-3.5 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)] text-xs text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--accent)] font-medium transition-colors"
          />
        </div>
      {/if}

      <!-- Actions -->
      <div class="flex items-center justify-end gap-2 pt-1">
        {#if type !== 'alert'}
          <button
            type="button"
            class="px-3.5 py-2 rounded-xl text-xs font-semibold bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
            onclick={handleCancel}
          >
            {cancelText}
          </button>
        {/if}
        <button
          type="button"
          class="px-4 py-2 rounded-xl text-xs font-semibold text-white transition-opacity shadow-sm cursor-pointer {danger ? 'bg-rose-600 hover:bg-rose-500' : 'bg-[var(--accent)] hover:opacity-90'}"
          onclick={handleConfirm}
        >
          {confirmText}
        </button>
      </div>
    </div>
  </div>
{/if}

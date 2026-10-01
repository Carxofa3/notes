<script>
  import { PRESET_ICONS, PRESET_COLORS } from '../organizer.js';

  let {
    isOpen = $bindable(false),
    item = null, // { id, type: 'lesson'|'unit'|'note', name/title, icon, color, unit_id }
    units = [], // available units if type === 'note'
    onSave = () => {},
    onDelete = () => {}
  } = $props();

  let name = $state('');
  let icon = $state('📁');
  let color = $state('#3b82f6');
  let selectedUnitId = $state('');

  $effect(() => {
    if (item) {
      name = item.title || item.name || '';
      icon = item.icon || (item.type === 'note' ? '📝' : item.type === 'lesson' ? '📚' : '📁');
      color = item.color || '#3b82f6';
      selectedUnitId = item.unit_id || '';
    }
  });

  function handleSave() {
    if (!name.trim()) return;
    onSave({
      id: item.id,
      type: item.type,
      name: name.trim(),
      title: name.trim(),
      icon,
      color,
      unit_id: selectedUnitId
    });
    isOpen = false;
  }

  let confirmDelete = $state(false);

  $effect(() => {
    if (!isOpen) {
      confirmDelete = false;
    }
  });

  function handleDelete() {
    onDelete(item);
    isOpen = false;
  }
</script>

{#if isOpen && item}
  <div 
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 sm:p-4"
    onclick={() => isOpen = false}
    role="dialog"
  >
    <div 
      class="w-full max-w-[95vw] sm:max-w-sm max-h-[90vh] overflow-y-auto rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-2xl p-4 sm:p-5 flex flex-col gap-3.5 text-[var(--text-primary)]"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
        <h3 class="font-bold text-sm flex items-center gap-2">
          <span>{icon}</span>
          <span>Customize {item.type === 'lesson' ? 'Course' : item.type === 'unit' ? 'Folder' : 'Note'}</span>
        </h3>
        <button 
          class="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-sm"
          onclick={() => isOpen = false}
        >✕</button>
      </div>

      <!-- Name Input -->
      <div class="flex flex-col gap-1.5">
        <label class="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
          Name / Title
        </label>
        <input 
          type="text"
          bind:value={name}
          placeholder="Name..."
          class="px-3 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] text-xs text-[var(--text-primary)] focus:outline-hidden focus:border-[var(--accent)]"
        />
      </div>

      <!-- Icon Picker -->
      <div class="flex flex-col gap-1.5">
        <label class="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
          Icon
        </label>
        <div class="grid grid-cols-8 gap-1.5 p-2 rounded-xl bg-[var(--card)] border border-[var(--border)] max-h-28 overflow-y-auto">
          {#each PRESET_ICONS as ic}
            <button
              class="w-7 h-7 flex items-center justify-center text-sm rounded-lg hover:bg-[var(--bg-tertiary)] transition-transform active:scale-90 {icon === ic ? 'bg-[var(--accent)] text-white shadow-xs' : ''}"
              onclick={() => icon = ic}
            >
              {ic}
            </button>
          {/each}
        </div>
      </div>

      <!-- Color Picker (wraps gracefully across 2 rows on mobile) -->
      <div class="flex flex-col gap-1.5">
        <label class="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
          Color Tag
        </label>
        <div class="flex flex-wrap items-center gap-2.5 max-w-full">
          {#each PRESET_COLORS as c}
            <button
              class="w-6 h-6 rounded-full border-2 transition-transform active:scale-90 {color === c.hex ? 'border-white scale-110 shadow-xs' : 'border-transparent'}"
              style="background-color: {c.hex};"
              onclick={() => color = c.hex}
              title={c.name}
            ></button>
          {/each}
        </div>
      </div>

      <!-- Folder relocation if Note -->
      {#if item.type === 'note' && units.length > 0}
        <div class="flex flex-col gap-1.5">
          <label class="text-[11px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
            Folder Location
          </label>
          <select 
            bind:value={selectedUnitId}
            class="px-3 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] text-xs text-[var(--text-primary)] focus:outline-hidden"
          >
            {#each units as u}
              <option value={u.id}>{u.icon || '📁'} {u.name}</option>
            {/each}
          </select>
        </div>
      {/if}

      <!-- Action buttons -->
      <div class="flex items-center justify-between pt-2 border-t border-[var(--border)]">
        {#if confirmDelete}
          <div class="flex items-center justify-between w-full gap-2">
            <span class="text-xs text-rose-300 font-medium">Delete permanently?</span>
            <div class="flex gap-2">
              <button
                type="button"
                class="px-2.5 py-1 text-xs rounded-lg bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-secondary)]"
                onclick={() => confirmDelete = false}
              >Cancel</button>
              <button
                type="button"
                class="px-3 py-1 text-xs rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold shadow-xs"
                onclick={handleDelete}
              >Yes, Delete</button>
            </div>
          </div>
        {:else}
          <button
            type="button"
            class="px-3 py-1.5 rounded-xl text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 transition-colors cursor-pointer"
            onclick={() => confirmDelete = true}
          >
            🗑️ Delete
          </button>

          <div class="flex gap-2">
            <button
              type="button"
              class="px-3 py-1.5 rounded-xl text-xs bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] cursor-pointer"
              onclick={() => isOpen = false}
            >
              Cancel
            </button>
            <button
              type="button"
              class="px-4 py-1.5 rounded-xl text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 cursor-pointer"
              onclick={handleSave}
            >
              Save
            </button>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

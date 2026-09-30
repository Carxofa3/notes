<script>
  let {
    onInsertText = () => {},
    onOpenMath = () => {},
    onOpenMermaid = () => {},
    onOpenCanvas = () => {},
    onOpenPlotter = () => {},
    onFactCheck = () => {},
    onAutoOrganize = () => {},
    onUndo = () => {},
    onRedo = () => {}
  } = $props();

  const QUICK_ITEMS = [
    { label: '$', title: 'Inline Math', action: () => onInsertText('$x$') },
    { label: '∫', title: 'MathLive Palette', action: () => onOpenMath() },
    { label: 'B', title: 'Bold', class: 'font-bold', action: () => onInsertText('**bold**') },
    { label: 'I', title: 'Italic', class: 'italic', action: () => onInsertText('*italic*') },
    { label: 'H2', title: 'Heading 2', class: 'font-semibold', action: () => onInsertText('\n## Heading\n') },
    { label: '• List', title: 'Bullet List', action: () => onInsertText('\n- ') },
    { label: '[ ]', title: 'Task Checkbox', action: () => onInsertText('\n- [ ] ') },
    { label: '`Code`', title: 'Inline Code', class: 'font-mono text-[11px]', action: () => onInsertText('`code`') },
    { label: '✏️ Draw', title: 'Stylus Canvas', action: () => onOpenCanvas() },
    { label: '📈 Plot', title: '2D Function Plot', action: () => onOpenPlotter() },
    { label: '📊 Diagram', title: 'Mermaid Diagram', action: () => onOpenMermaid() },
    { label: '🔍 Fact-Check', title: 'Fact-Check Document', action: () => onFactCheck() },
    { label: '🪄 Organize', title: 'Auto-Organize Note', action: () => onAutoOrganize() }
  ];
</script>

<div class="w-full bg-[var(--bg-secondary)] border-t border-[var(--border)] px-2 py-1.5 flex items-center justify-between gap-1 overflow-x-auto shadow-md">
  <div class="flex items-center gap-1">
    {#each QUICK_ITEMS as item}
      <button
        class="shrink-0 px-2.5 py-1 rounded-lg bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-xs text-[var(--text-primary)] transition-transform active:scale-95 {item.class || ''}"
        onclick={item.action}
        title={item.title}
      >
        {item.label}
      </button>
    {/each}
  </div>

  <div class="flex items-center gap-1 border-l border-[var(--border)] pl-1.5 shrink-0">
    <button
      class="px-2 py-1 rounded-lg bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-xs text-[var(--text-secondary)]"
      onclick={onUndo}
      title="Undo"
    >↩</button>
    <button
      class="px-2 py-1 rounded-lg bg-[var(--card)] hover:bg-[var(--bg-tertiary)] border border-[var(--border)] text-xs text-[var(--text-secondary)]"
      onclick={onRedo}
      title="Redo"
    >↪</button>
  </div>
</div>

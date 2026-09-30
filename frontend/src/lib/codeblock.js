import { EditorState, StateField } from '@codemirror/state';
import { EditorView, Decoration, WidgetType } from '@codemirror/view';
import { syntaxTree } from '@codemirror/language';
import {
  shouldShowSource,
  mouseSelectingField,
  highlightCode
} from 'codemirror-live-markdown';

const ALIASES = {
  py: 'python',
  js: 'javascript',
  ts: 'typescript',
  sh: 'bash',
  shell: 'bash',
  zsh: 'bash',
  yml: 'yaml',
  rb: 'ruby',
  cs: 'csharp',
  'c++': 'cpp',
  md: 'markdown',
  docker: 'dockerfile',
  golang: 'go',
  rs: 'rust',
  htm: 'html',
  svg: 'xml'
};

const CLIPBOARD_ICON = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
const CHECK_ICON = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

class ChatGptCodeBlockWidget extends WidgetType {
  constructor(data) {
    super();
    this.data = data;
  }

  eq(other) {
    return (
      other.data.code === this.data.code &&
      other.data.language === this.data.language &&
      other.data.from === this.data.from &&
      other.data.to === this.data.to
    );
  }

  toDOM() {
    const { code, language, from, to, lineStarts } = this.data;
    const widgetData = this.data;

    // Detect or resolve syntax highlighting language
    const rawLang = (language || '').trim().toLowerCase();
    const normalizedLang = ALIASES[rawLang] || rawLang;
    let highlightResult = null;

    if (normalizedLang) {
      highlightResult = highlightCode(code, normalizedLang);
    }

    // Auto-detect if language was not provided or not recognized by lowlight
    if (!highlightResult || !highlightResult.html || highlightResult.language === 'text') {
      const autoResult = highlightCode(code);
      if (autoResult && autoResult.html && autoResult.language !== 'text') {
        highlightResult = autoResult;
      }
    }

    const displayLang = (highlightResult?.language && highlightResult.language !== 'text')
      ? highlightResult.language
      : (rawLang || 'code');

    // Outer ChatGPT codebox container
    const container = document.createElement('div');
    container.className = 'chatgpt-codebox';
    container.dataset.from = String(from);
    container.dataset.to = String(to);

    // Header bar (ChatGPT style with language name on left, copy on right)
    const header = document.createElement('div');
    header.className = 'chatgpt-code-header';

    const langLabel = document.createElement('span');
    langLabel.className = 'chatgpt-code-lang';
    langLabel.textContent = displayLang;
    header.appendChild(langLabel);

    // Copy Button with animated icon and text
    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'chatgpt-code-copy';
    copyBtn.setAttribute('aria-label', 'Copy code to clipboard');

    const copyIcon = document.createElement('span');
    copyIcon.className = 'chatgpt-copy-icon';
    copyIcon.innerHTML = CLIPBOARD_ICON;
    copyBtn.appendChild(copyIcon);

    const copyText = document.createElement('span');
    copyText.className = 'chatgpt-copy-text';
    copyText.textContent = 'Copy code';
    copyBtn.appendChild(copyText);

    copyBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      try {
        await navigator.clipboard.writeText(code);
        copyBtn.classList.add('copied');
        copyIcon.innerHTML = CHECK_ICON;
        copyText.textContent = 'Copied!';
        setTimeout(() => {
          copyBtn.classList.remove('copied');
          copyIcon.innerHTML = CLIPBOARD_ICON;
          copyText.textContent = 'Copy code';
        }, 2000);
      } catch (err) {
        copyText.textContent = 'Failed';
        setTimeout(() => {
          copyText.textContent = 'Copy code';
        }, 2000);
      }
    });

    header.appendChild(copyBtn);
    container.appendChild(header);

    // Code area with Highlight.js syntax highlighting
    const pre = document.createElement('pre');
    pre.className = 'chatgpt-code-pre';
    const codeEl = document.createElement('code');
    codeEl.className = 'chatgpt-code-body';

    const originalLines = code.split('\n');
    let highlightedLines = (highlightResult?.html || '').split('\n');
    if (highlightedLines.length !== originalLines.length) {
      highlightedLines = originalLines.map((line) => {
        const lineResult = highlightCode(line, normalizedLang || undefined);
        return lineResult.html || escapeHtml(line) || ' ';
      });
    }

    const linesHtml = originalLines.map((_, index) => {
      const lineContent = highlightedLines[index] || ' ';
      return `<span class="cm-codeblock-line chatgpt-code-line" data-line-index="${index}">${lineContent}</span>`;
    });
    codeEl.innerHTML = linesHtml.join('');
    pre.appendChild(codeEl);
    container.appendChild(pre);

    // Interactive targeting: clicking code or header switches to live editor at exact offset
    const handleInteract = (event) => {
      const target = event.target;
      if (target.closest('.chatgpt-code-copy')) {
        return; // Ignore copy button clicks
      }
      event.stopPropagation();
      event.preventDefault();

      const lineEl = target.closest('.chatgpt-code-line');
      let targetPos = widgetData.from;

      if (lineEl && lineEl.dataset.lineIndex !== undefined) {
        const lineIndex = parseInt(lineEl.dataset.lineIndex, 10);
        if (lineIndex >= 0 && lineIndex < widgetData.lineStarts.length) {
          const clientX = (event.touches && event.touches[0]) ? event.touches[0].clientX : event.clientX;
          const charOffset = this.measureClickOffset(
            lineEl,
            clientX,
            widgetData.code.split('\n')[lineIndex] || ''
          );
          targetPos = widgetData.lineStarts[lineIndex] + charOffset;
        }
      }

      container.dispatchEvent(
        new CustomEvent('codeblock-click', {
          bubbles: true,
          detail: { targetPos }
        })
      );
    };

    container.addEventListener('mousedown', handleInteract, true);

    return container;
  }

  measureClickOffset(lineEl, clientX, sourceText) {
    if (!sourceText) return 0;
    const rect = lineEl.getBoundingClientRect();
    const clickX = clientX - rect.left;
    const style = window.getComputedStyle(lineEl);
    const paddingLeft = parseFloat(style.paddingLeft) || 0;
    const textClickX = clickX - paddingLeft;
    if (textClickX <= 0) return 0;

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      const fontSize = parseFloat(style.fontSize) || 14;
      const charWidth = fontSize * 0.6;
      return Math.min(Math.floor(textClickX / charWidth), sourceText.length);
    }

    ctx.font = `${style.fontSize} ${style.fontFamily}`;
    let left = 0;
    let right = sourceText.length;
    while (left < right) {
      const mid = Math.floor((left + right + 1) / 2);
      const width = ctx.measureText(sourceText.substring(0, mid)).width;
      if (width <= textClickX) {
        left = mid;
      } else {
        right = mid - 1;
      }
    }
    return Math.min(left, sourceText.length);
  }

  ignoreEvent(event) {
    if (event.type === 'mousedown') {
      return true;
    }
    return false;
  }
}

const SKIP_LANGUAGES = new Set(['math']);

function buildCodeBlockDecorations(state) {
  const decorations = [];
  const isDrag = state.field(mouseSelectingField, false);

  syntaxTree(state).iterate({
    enter: (node) => {
      if (node.name === 'FencedCode') {
        const codeInfo = node.node.getChild('CodeInfo');
        let language = '';
        if (codeInfo) {
          language = state.doc.sliceString(codeInfo.from, codeInfo.to).trim();
        }

        if (SKIP_LANGUAGES.has(language)) {
          return;
        }

        const codeText = node.node.getChild('CodeText');
        const code = codeText ? state.doc.sliceString(codeText.from, codeText.to) : '';
        const codeFrom = codeText ? codeText.from : node.from;
        const lineStarts = [];

        if (codeText) {
          const startPos = codeText.from;
          lineStarts.push(startPos);
          for (let i = 0; i < code.length; i++) {
            if (code[i] === '\n') {
              lineStarts.push(startPos + i + 1);
            }
          }
        }

        const isTouched = shouldShowSource(state, node.from, node.to);
        if (!isTouched && !isDrag) {
          const widget = new ChatGptCodeBlockWidget({
            code,
            language,
            from: node.from,
            to: node.to,
            codeFrom,
            lineStarts
          });
          decorations.push(
            Decoration.replace({ widget, block: true }).range(node.from, node.to)
          );
        } else {
          for (let pos = node.from; pos <= node.to; ) {
            const line = state.doc.lineAt(pos);
            decorations.push(
              Decoration.line({ class: 'cm-codeblock-source' }).range(line.from)
            );
            pos = line.to + 1;
          }
        }
      }
    }
  });

  return Decoration.set(decorations.sort((a, b) => a.from - b.from), true);
}

function createCodeBlockClickHandler() {
  return EditorView.domEventHandlers({
    'codeblock-click': (event, view) => {
      const targetPos = event.detail.targetPos;
      view.dispatch({
        selection: { anchor: targetPos },
        scrollIntoView: true
      });
      view.focus();
      return true;
    }
  });
}

export function chatGptCodeBlockField() {
  const field = StateField.define({
    create(state) {
      return buildCodeBlockDecorations(state);
    },
    update(deco, tr) {
      if (tr.docChanged || tr.reconfigured) {
        return buildCodeBlockDecorations(tr.state);
      }
      const isDragging = tr.state.field(mouseSelectingField, false);
      const wasDragging = tr.startState.field(mouseSelectingField, false);
      if (wasDragging && !isDragging) {
        return buildCodeBlockDecorations(tr.state);
      }
      if (isDragging) {
        return deco;
      }
      if (tr.selection) {
        return buildCodeBlockDecorations(tr.state);
      }
      return deco;
    },
    provide: (f) => EditorView.decorations.from(f)
  });

  const clickHandler = createCodeBlockClickHandler();
  return [field, clickHandler];
}

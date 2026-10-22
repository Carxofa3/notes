// frontend/src/lib/livePreviewEnhanced.js
import { ViewPlugin, Decoration } from '@codemirror/view';
import { syntaxTree } from '@codemirror/language';
import {
  shouldShowSource,
  mouseSelectingField,
  checkUpdateAction
} from 'codemirror-live-markdown';

const SKIP_PARENT_TYPES = new Set(['FencedCode', 'CodeBlock', 'CommentBlock', 'HTMLBlock']);

function isInsideSkippedParent(node) {
  let parent = node.node.parent;
  while (parent) {
    if (SKIP_PARENT_TYPES.has(parent.name)) {
      return true;
    }
    parent = parent.parent;
  }
  return false;
}

export const enhancedLivePreviewPlugin = ViewPlugin.fromClass(
  class {
    constructor(view) {
      this.decorations = this.build(view);
    }
    update(update) {
      if (checkUpdateAction(update) === 'rebuild' || update.selectionSet || update.docChanged) {
        this.decorations = this.build(update.view);
      }
    }
    build(view) {
      const decorations = [];
      const { state } = view;
      const activeLines = new Set();
      for (const range of state.selection.ranges) {
        const startLine = state.doc.lineAt(range.from).number;
        const endLine = state.doc.lineAt(range.to).number;
        for (let l = startLine; l <= endLine; l++) {
          activeLines.add(l);
        }
      }
      const isDrag = state.field(mouseSelectingField, false);

      syntaxTree(state).iterate({
        enter: (node) => {
          const markTypes = [
            'EmphasisMark',
            'StrikethroughMark',
            'CodeMark',
            'HeaderMark',
            'ListMark',
            'QuoteMark'
          ];
          if (!markTypes.includes(node.name)) return;
          if (isInsideSkippedParent(node)) return;

          if (node.name === 'CodeMark') {
            const parent = node.node.parent;
            if (parent && parent.name === 'InlineCode') {
              const text = state.doc.sliceString(parent.from, parent.to);
              if (text.startsWith('`$') && text.endsWith('$`')) return;
            }
          }

          const lineNum = state.doc.lineAt(node.from).number;
          const isActiveLine = activeLines.has(lineNum);

          // Handle Ordered vs Bullet Lists
          if (node.name === 'ListMark') {
            const grandParent = node.node.parent?.parent?.name;
            if (grandParent === 'OrderedList') {
              // Numbered list mark (e.g. 1., 2.) - NEVER hide or shrink!
              // Always display formatted and visible.
              decorations.push(
                Decoration.mark({ class: 'cm-list-mark-ordered' }).range(node.from, node.to)
              );
              return;
            } else {
              // Bullet list (- or * or +)
              if (isActiveLine && !isDrag) {
                decorations.push(
                  Decoration.mark({ class: 'cm-formatting-block cm-formatting-block-visible' }).range(node.from, node.to)
                );
              } else {
                decorations.push(
                  Decoration.mark({ class: 'cm-list-mark-bullet' }).range(node.from, node.to)
                );
              }
              return;
            }
          }

          const isBlock = ['HeaderMark', 'QuoteMark'].includes(node.name);
          if (isBlock) {
            const cls = isActiveLine && !isDrag
              ? 'cm-formatting-block cm-formatting-block-visible'
              : 'cm-formatting-block';
            decorations.push(
              Decoration.mark({ class: cls }).range(node.from, node.to)
            );
          } else {
            if (node.from >= node.to) return;
            const isTouched = shouldShowSource(state, node.from, node.to);
            const cls = isTouched && !isDrag
              ? 'cm-formatting-inline cm-formatting-inline-visible'
              : 'cm-formatting-inline';
            decorations.push(
              Decoration.mark({ class: cls }).range(node.from, node.to)
            );
          }
        }
      });

      return Decoration.set(
        decorations.sort((a, b) => a.from - b.from),
        true
      );
    }
  },
  {
    decorations: (v) => v.decorations
  }
);

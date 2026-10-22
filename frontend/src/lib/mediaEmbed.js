// frontend/src/lib/mediaEmbed.js
import { ViewPlugin, Decoration, WidgetType } from '@codemirror/view';
import { syntaxTree } from '@codemirror/language';
import { shouldShowSource, mouseSelectingField } from 'codemirror-live-markdown';

const AUDIO_EXTENSIONS = /\.(mp3|wav|ogg|m4a|aac|flac)(\?.*)?$/i;
const VIDEO_EXTENSIONS = /\.(mp4|webm|ogv|mov|m4v)(\?.*)?$/i;

class AudioWidget extends WidgetType {
  constructor(src, title) {
    super();
    this.src = src;
    this.title = title || 'Audio';
  }

  eq(other) {
    return other.src === this.src && other.title === this.title;
  }

  toDOM() {
    const wrap = document.createElement('div');
    wrap.className = 'cm-media-embed cm-audio-embed my-2 p-3 rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-xs';
    wrap.style.maxWidth = '640px';

    const header = document.createElement('div');
    header.className = 'flex items-center gap-2 mb-2 text-xs font-semibold text-[var(--text-secondary)]';
    header.innerHTML = `<span>🎵</span><span class="truncate">${this.title}</span>`;
    wrap.appendChild(header);

    const audio = document.createElement('audio');
    audio.controls = true;
    audio.src = this.src;
    audio.className = 'w-full h-10 outline-none';
    audio.style.width = '100%';
    wrap.appendChild(audio);

    return wrap;
  }

  ignoreEvent() {
    return false;
  }
}

class VideoWidget extends WidgetType {
  constructor(src, title) {
    super();
    this.src = src;
    this.title = title || 'Video';
  }

  eq(other) {
    return other.src === this.src && other.title === this.title;
  }

  toDOM() {
    const wrap = document.createElement('div');
    wrap.className = 'cm-media-embed cm-video-embed my-2 p-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-sm';
    wrap.style.maxWidth = '720px';

    if (this.title && this.title !== 'Video') {
      const header = document.createElement('div');
      header.className = 'flex items-center gap-2 mb-2 text-xs font-semibold text-[var(--text-secondary)]';
      header.innerHTML = `<span>🎬</span><span class="truncate">${this.title}</span>`;
      wrap.appendChild(header);
    }

    const video = document.createElement('video');
    video.controls = true;
    video.src = this.src;
    video.className = 'w-full rounded-lg bg-black/40';
    video.style.maxHeight = '420px';
    video.style.maxWidth = '100%';
    video.style.objectFit = 'contain';
    wrap.appendChild(video);

    return wrap;
  }

  ignoreEvent() {
    return false;
  }
}

function buildMediaDecorations(state) {
  const decorations = [];
  const isDrag = state.field(mouseSelectingField, false);
  const docText = state.doc.toString();

  // 1. Search for HTML <audio ... src="..."> and <video ... src="..."> tags
  const audioTagRegex = /<audio\b[^>]*\bsrc=["']([^"']+)["'][^>]*>(?:<\/audio>)?/gi;
  let match;
  while ((match = audioTagRegex.exec(docText)) !== null) {
    const from = match.index;
    const to = from + match[0].length;
    const isTouched = shouldShowSource(state, from, to);
    if (!isTouched && !isDrag) {
      const widget = new AudioWidget(match[1], 'Audio Player');
      decorations.push(Decoration.replace({ widget, block: true }).range(from, to));
    }
  }

  const videoTagRegex = /<video\b[^>]*\bsrc=["']([^"']+)["'][^>]*>(?:<\/video>)?/gi;
  while ((match = videoTagRegex.exec(docText)) !== null) {
    const from = match.index;
    const to = from + match[0].length;
    const isTouched = shouldShowSource(state, from, to);
    if (!isTouched && !isDrag) {
      const widget = new VideoWidget(match[1], 'Video Player');
      decorations.push(Decoration.replace({ widget, block: true }).range(from, to));
    }
  }

  // 2. Search for Markdown audio and video links: [title](url.mp3) or [title](url.mp4)
  const mdMediaRegex = /\[([^\]]*)\]\(([^)]+)\)/g;
  while ((match = mdMediaRegex.exec(docText)) !== null) {
    const from = match.index;
    const to = from + match[0].length;
    const label = match[1];
    const url = match[2].trim();

    if (AUDIO_EXTENSIONS.test(url)) {
      const isTouched = shouldShowSource(state, from, to);
      if (!isTouched && !isDrag) {
        const widget = new AudioWidget(url, label || 'Audio Recording');
        decorations.push(Decoration.replace({ widget, block: true }).range(from, to));
      }
    } else if (VIDEO_EXTENSIONS.test(url)) {
      const isTouched = shouldShowSource(state, from, to);
      if (!isTouched && !isDrag) {
        const widget = new VideoWidget(url, label || 'Video Lecture');
        decorations.push(Decoration.replace({ widget, block: true }).range(from, to));
      }
    }
  }

  return Decoration.set(decorations.sort((a, b) => a.from - b.from), true);
}

export const mediaEmbedPlugin = ViewPlugin.fromClass(
  class {
    constructor(view) {
      this.decorations = buildMediaDecorations(view.state);
    }
    update(update) {
      if (update.docChanged || update.selectionSet || update.viewportChanged) {
        this.decorations = buildMediaDecorations(update.view.state);
      }
    }
  },
  {
    decorations: (v) => v.decorations
  }
);

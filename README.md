# Notes — University Knowledge & Fact-Checking Workstation

> An offline-first, high-performance knowledge workstation and dual-mode note-taking ecosystem built specifically for university STEM students. Operates seamlessly across **Windows**, **Linux**, and **Android** with zero cloud lock-in.

---

## Key Capabilities

1. **Dual-Mode Editor (Visual Rich Text & Split Markdown)**
   - **TipTap ProseMirror**: Seamless WYSIWYG note editing with inline code blocks, tables, callouts, and shortcuts.
   - **Split Markdown**: Raw markdown editing with instant KaTeX math typesetting and live preview.
   - **Quick Shortcuts**:
     - `Ctrl+K`: Omnibox Quick Search & Command Palette
     - `Ctrl+Shift+F`: Real-time Fact-Check trigger
     - `Ctrl+E`: KaTeX & MathLive Formula Palette
     - `Ctrl+S`: Instant Local Save & Delta Flush

2. **STEM Visual Studios**
   - **KaTeX & MathLive Formula Palette**: Visual LaTeX equation builder with Greek letters, calculus symbols, and matrices.
   - **Mermaid.js Diagram Studio**: Live flowchart, sequence, state, class, and entity-relationship diagram editor.
   - **2D Function Curve Plotter**: Interactive canvas graphing tool with parametric evaluation, zoom, and axis panning.
   - **Stylus Freehand Canvas**: Smooth vector freehand drawing with palm rejection and eraser modes.

3. **Intelligent Auto-Classification**
   - Hierarchical structure: **Lesson** ➔ **Unit** ➔ **Note**.
   - Integrated Fastino **GLiNER2.5-Decide** Jev REST endpoint (`/v1/decide`): zero-shot note taxonomy sorting and lesson/unit suggestion.

4. **Multi-Source Fact-Checking & Academic Verification**
   - **Tier 1 (100% Offline)**: Course Lecture Slide PDF RAG with pure Python BM25 indexer, exact slide page citations, and semantic relevance scoring.
   - **Tier 2 (Academic Online)**: Real-time verification against Wikipedia REST API and Semantic Scholar paper abstracts.
   - **Interactive Diff Corrections**: Visual 1-click side-by-side diff review allowing students to accept verified corrections into their notes.

5. **Deep LLM Escalation (`llama.cpp`)**
   - Contradiction resolution and study guide generation escalated to a high-capacity **`llama.cpp`** server (default `http://localhost:8080`, configurable via `LLAMA_CPP_NODE` over Tailscale).
   - Supports native `/completion` with custom prompt framing as well as `/v1/chat/completions`.

6. **Zero-Cloud P2P Collaboration & Sync**
   - Real-time **Yjs CRDT** binary delta synchronization over an authenticated WebSocket listener.
   - QR pairing grants a persistent device credential; remote API and sync requests require that credential.
   - Paired devices keep both LAN and Tailscale routes and switch automatically when one becomes unreachable.
   - Android releases require Android 9 or newer.

### Pairing security

The QR code contains the workstation's pairing credential. Only scan it on devices you trust. The credential is stored in the workstation user's private data folder and in the paired phone's app storage. Tailscale encrypts traffic across the tailnet. LAN connections use HTTP, so pair only while both devices are on a trusted private network.

---

## Deployment & Running

### Option 1: Instant Native Desktop Window (Zero Rust Compilation)

Run the desktop client immediately using the built-in Microsoft Edge WebView2 (Windows) / WebKitGTK (Linux) runner:

```bash
# Windows
run_desktop.bat

# Linux / macOS
chmod +x run_desktop.sh
./run_desktop.sh

# Or via Python directly
python desktop.py
```

### Option 2: High-Performance Tauri 2.0 Desktop (Rust)

```bash
# Development mode with hot-reloading
npm run tauri:dev

# Production desktop binary build (.exe / .msi / .deb / .AppImage)
npm run tauri:build
```

### Option 3: Tauri 2.0 Android Build (Mobile / Tablet)

```bash
# Initialize Android project structure
npm run tauri:android

# Build standalone release APK
npm run tauri:android:build
```
> The compiled `.apk` will be output to `src-tauri/gen/android/app/build/outputs/apk/`.

### Option 4: Full-Stack Web Development Server

```bash
# Terminal 1: P2P Yjs Sync Server
npm run sync

# Terminal 2: Python Backend (Flask + RAG + Decide)
python main.py

# Terminal 3: Svelte 5 Frontend
npm run dev:frontend
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Configuration (`config/config.py` / `.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `LLAMA_CPP_NODE` | `http://localhost:8080` | URL of the heavy `llama.cpp` inference server (local or Tailscale IP) |
| `GLINER_JEV_URL` | `http://localhost:8000/v1/decide` | Fastino GLiNER2.5 Jev classification server endpoint |
| `SYNC_PORT` | `58855` | TCP port for Yjs P2P WebSocket synchronization |
| `SLIDES_UPLOAD_DIR` | `app/static/uploads/slides` | Storage folder for indexed lecture slide PDFs |
| `DATABASE_URL` | `sqlite:///notes.db` | Local SQLite database URI |

---

## Project Structure

```
notes/
├── app/                        # Flask backend API & services
│   ├── api/                    # REST endpoints (/api/notes, /api/rag, /v1/decide, etc.)
│   ├── models/                 # SQLAlchemy schemas (Lesson, Unit, Note, SlideIndex)
│   ├── services/               # BM25 RAG, Academic Fact-Checker, llama.cpp client
│   └── static/uploads/slides/  # Uploaded course lecture slides
├── frontend/                   # Modern Svelte 5 SPA
│   ├── src/
│   │   ├── lib/components/     # Dual-mode editor, MathLive, Mermaid, Canvas, FactCheckPanel
│   │   └── App.svelte          # Responsive layout (Desktop 3-pane / Mobile drawer)
│   └── dist/                   # Production compiled SPA bundle
├── src-tauri/                  # Tauri 2.0 Rust native application core
│   ├── src/                    # main.rs & lib.rs (with mobile entry point)
│   ├── capabilities/           # Tauri security & permission profiles
│   ├── tauri.conf.json         # Tauri 2.0 cross-platform configuration
│   └── Cargo.toml              # Rust crate dependencies
├── .github/workflows/          # GitHub Actions CI/CD (Windows, Linux, Android builds)
├── desktop.py                  # pywebview instant desktop launcher
├── run_desktop.bat             # One-click Windows runner
├── run_desktop.sh              # One-click Linux runner
├── sync_server.js              # Standalone Node.js Yjs P2P WebSocket server
└── main.py                     # Backend server entry point
```

---

## Automated Tests

Run the backend unit test suite (including lecture slide RAG indexing, academic verification mocks, and GLiNER taxonomy sorting):

```bash
python -m pytest tests/ -v
```

All 22 unit tests pass completely.

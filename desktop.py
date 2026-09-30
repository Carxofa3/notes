"""
Desktop Launcher for Notes Ecosystem
Powered by pywebview (Edge WebView2 on Windows / WebKitGTK on Linux / WebKit on macOS)
Provides an instant, zero-install native desktop window experience.
"""

import sys
import os
import time
import socket
import threading
import argparse
import subprocess
import urllib.request
import webbrowser

def find_free_port(start_port=5000, max_attempts=50):
    """Find an available TCP port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return start_port

def wait_for_server(url, timeout=15):
    """Wait until the HTTP server is responsive."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status in (200, 302, 404):
                    return True
        except Exception:
            time.sleep(0.2)
    return False

def start_flask(app, host, port):
    """Run Flask application in a dedicated thread."""
    from werkzeug.serving import make_server
    server = make_server(host, port, app, threaded=True)
    server.serve_forever()

def start_sync_server(root_dir, port=58855):
    """Optionally start node sync_server.js if Node.js is present."""
    sync_script = os.path.join(root_dir, 'sync_server.js')
    if not os.path.exists(sync_script):
        return None
    try:
        env = os.environ.copy()
        env['SYNC_PORT'] = str(port)
        proc = subprocess.Popen(
            ['node', sync_script],
            cwd=root_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return proc
    except Exception as e:
        print(f"[Desktop] Sync server notice (Node not in PATH or failed): {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Notes Desktop Application Launcher")
    parser.add_argument('--port', type=int, default=None, help="Flask backend port")
    parser.add_argument('--sync-port', type=int, default=58855, help="Yjs P2P Sync WebSocket port")
    parser.add_argument('--dev', action='store_true', help="Point to Vite dev server at http://localhost:5173")
    parser.add_argument('--fullscreen', action='store_true', help="Launch in fullscreen mode")
    parser.add_argument('--browser', action='store_true', help="Force open in default web browser instead of webview")
    args = parser.parse_args()

    root_dir = os.path.abspath(os.path.dirname(__file__))
    os.chdir(root_dir)

    # 1. Determine Flask port
    flask_port = args.port or find_free_port(5000)
    host = '0.0.0.0'
    local_check_url = f"http://127.0.0.1:{flask_port}"

    # 2. Start Yjs P2P sync server in background
    sync_proc = start_sync_server(root_dir, args.sync_port)
    if sync_proc:
        print(f"[Desktop] P2P Yjs WebSocket sync server active on ws://0.0.0.0:{args.sync_port}")

    # 3. Import and start Flask app in a daemon thread
    from app import create_app
    flask_app = create_app(os.getenv('FLASK_CONFIG') or 'default')

    flask_thread = threading.Thread(
        target=start_flask,
        args=(flask_app, host, flask_port),
        daemon=True
    )
    flask_thread.start()

    # 4. Wait for Flask to become ready
    print(f"[Desktop] Initializing backend on all interfaces port {flask_port} (LAN & Tailscale ready)...")
    if not wait_for_server(local_check_url, timeout=10):
        print(f"[Desktop] Warning: Backend server did not respond quickly, continuing anyway.")

    target_url = "http://localhost:5173" if args.dev else local_check_url

    # 5. Launch native WebView or browser fallback
    has_webview = False
    if not args.browser:
        try:
            import webview
            has_webview = True
        except ImportError:
            has_webview = False

    if has_webview:
        print(f"[Desktop] Launching native Edge/WebKit window for {target_url}...")
        try:
            window = webview.create_window(
                title="Notes — University Knowledge & Fact-Checking Workstation",
                url=target_url,
                width=1280,
                height=840,
                min_size=(800, 600),
                text_select=True,
                fullscreen=args.fullscreen
            )
            webview.start(debug=False)
        except Exception as e:
            print(f"[Desktop] Error starting pywebview: {e}. Falling back to default browser.")
            webbrowser.open(target_url)
    else:
        print(f"[Desktop] pywebview not detected or browser flag enabled. Opening {target_url} in browser...")
        webbrowser.open(target_url)
        print("[Desktop] Press Ctrl+C in this terminal to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    # Cleanup
    if sync_proc:
        try:
            sync_proc.terminate()
            sync_proc.wait(timeout=2)
        except Exception:
            sync_proc.kill()
    print("[Desktop] Clean exit completed.")

if __name__ == '__main__':
    main()

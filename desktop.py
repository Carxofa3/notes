"""
Desktop Launcher for Notes Ecosystem
Powered by pywebview (Edge WebView2 on Windows / WebKitGTK on Linux / WebKit on macOS)
Provides an instant, zero-install native desktop window experience.
Supports optional Tailscale integration for cross-network connectivity.
"""

import sys
import os
import time
import socket
import shutil
import threading
import argparse
import subprocess
import urllib.request
import webbrowser


# ─── Helpers ────────────────────────────────────────────────────────────────

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


# ─── Tailscale Integration ───────────────────────────────────────────────────

def _find_tailscale_bin():
    """Return path to the tailscale binary, or None if not found."""
    # Check common Windows install locations first, then PATH
    candidates = [
        r"C:\Program Files\Tailscale\tailscale.exe",
        r"C:\Program Files (x86)\Tailscale\tailscale.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tailscale", "tailscale.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return shutil.which('tailscale')


def get_tailscale_ip():
    """Return the Tailscale (100.x.x.x) IP of this device, or None."""
    ts = _find_tailscale_bin()
    if not ts:
        return None
    try:
        result = subprocess.run(
            [ts, 'ip', '-4'],
            capture_output=True, text=True, timeout=5
        )
        ip = result.stdout.strip()
        if ip and ip.startswith('100.'):
            return ip
    except Exception:
        pass
    return None


def start_tailscale():
    """
    Attempt to start the Tailscale daemon and bring the device up.

    Behaviour:
    - If tailscale is not installed → prints a helpful download URL and returns False.
    - If already connected → prints the Tailscale IP and returns True.
    - If not authenticated → opens the auth URL in the browser for the user to approve.
    - Returns True on success, False on failure.
    """
    ts = _find_tailscale_bin()
    if ts is None:
        print("[Desktop] ⚠  Tailscale not found.")
        print("[Desktop]    Download Tailscale from: https://tailscale.com/download")
        print("[Desktop]    After installing, re-launch the app with --tailscale.")
        return False

    print(f"[Desktop] Tailscale binary found at: {ts}")

    # Check current status first
    try:
        status = subprocess.run(
            [ts, 'status', '--json'],
            capture_output=True, text=True, timeout=10
        )
        import json
        data = json.loads(status.stdout or '{}')
        backend_state = data.get('BackendState', '')
        if backend_state == 'Running':
            ts_ip = get_tailscale_ip() or 'unknown'
            print(f"[Desktop] ✓ Tailscale already running. This device IP: {ts_ip}")
            return True
    except Exception:
        pass

    # Not running — try `tailscale up`
    print("[Desktop] Starting Tailscale (this may open a browser for authentication)...")
    try:
        proc = subprocess.Popen(
            [ts, 'up', '--accept-routes'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        # Print output in a background thread so we don't block
        def _pipe_output():
            for line in proc.stdout:
                line = line.strip()
                if line:
                    # Detect auth URL and open it
                    if line.startswith('https://'):
                        print(f"[Desktop] 🔐 Tailscale auth URL: {line}")
                        webbrowser.open(line)
                    else:
                        print(f"[Desktop]    {line}")

        t = threading.Thread(target=_pipe_output, daemon=True)
        t.start()
        proc.wait(timeout=120)  # wait up to 2 min for auth

        if proc.returncode == 0:
            ts_ip = get_tailscale_ip() or 'unknown'
            print(f"[Desktop] ✓ Tailscale connected. This device IP: {ts_ip}")
            return True
        else:
            print(f"[Desktop] ✗ Tailscale exited with code {proc.returncode}.")
            return False
    except subprocess.TimeoutExpired:
        print("[Desktop] Tailscale auth timed out. Please complete authentication in your browser.")
        return False
    except Exception as e:
        print(f"[Desktop] Exception while starting Tailscale: {e}")
        return False


def print_connection_info(flask_port):
    """Print LAN and Tailscale connection URLs for remote access."""
    lan_ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ip.startswith(('192.168.', '10.', '172.')):
                if ip not in lan_ips:
                    lan_ips.append(ip)
    except Exception:
        pass

    ts_ip = get_tailscale_ip()

    print("\n" + "─" * 55)
    print("  Notes Workstation — Connection Info")
    print("─" * 55)
    print(f"  Local:      http://localhost:{flask_port}")
    for ip in lan_ips:
        print(f"  LAN:        http://{ip}:{flask_port}")
    if ts_ip:
        print(f"  Tailscale:  http://{ts_ip}:{flask_port}  (works across networks!)")
    else:
        print("  Tailscale:  not connected (run with --tailscale to enable)")
    print("─" * 55 + "\n")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Notes Desktop Application Launcher")
    parser.add_argument('--port', type=int, default=None, help="Flask backend port")
    parser.add_argument('--sync-port', type=int, default=58855, help="Yjs P2P Sync WebSocket port")
    parser.add_argument('--dev', action='store_true', help="Point to Vite dev server at http://localhost:5173")
    parser.add_argument('--fullscreen', action='store_true', help="Launch in fullscreen mode")
    parser.add_argument('--browser', action='store_true', help="Force open in default web browser instead of webview")
    parser.add_argument('--tailscale', action='store_true',
                        help="Auto-start Tailscale on launch for cross-network access")
    args = parser.parse_args()

    root_dir = os.path.abspath(os.path.dirname(__file__))
    os.chdir(root_dir)

    # 1. Optionally start Tailscale before anything else
    if args.tailscale:
        start_tailscale()

    # 2. Determine Flask port
    flask_port = args.port or find_free_port(5000)
    host = '0.0.0.0'
    local_check_url = f"http://127.0.0.1:{flask_port}"

    # 3. Start Yjs P2P sync server in background
    sync_proc = start_sync_server(root_dir, args.sync_port)
    if sync_proc:
        print(f"[Desktop] P2P Yjs WebSocket sync server active on ws://0.0.0.0:{args.sync_port}")

    # 4. Import and start Flask app in a daemon thread
    from app import create_app
    flask_app = create_app(os.getenv('FLASK_CONFIG') or 'default')

    flask_thread = threading.Thread(
        target=start_flask,
        args=(flask_app, host, flask_port),
        daemon=True
    )
    flask_thread.start()

    # 5. Wait for Flask to become ready
    print(f"[Desktop] Initializing backend on all interfaces port {flask_port}...")
    if not wait_for_server(local_check_url, timeout=10):
        print("[Desktop] Warning: Backend server did not respond quickly, continuing anyway.")

    # 6. Print connection info (LAN + Tailscale)
    print_connection_info(flask_port)

    target_url = "http://localhost:5173" if args.dev else local_check_url

    # 7. Launch native WebView or browser fallback
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

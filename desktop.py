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

CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0

# Ensure Windows stdout/stderr handles UTF-8 without charmap crashes or windowed mode NoneType crashes
if sys.platform == 'win32':
    if sys.stdout is None:
        try:
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        except Exception:
            pass
    elif hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    if sys.stderr is None:
        try:
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')
        except Exception:
            pass
    elif hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


# ─── Helpers ────────────────────────────────────────────────────────────────

def wait_for_server(url, timeout=10):
    """Wait until the backend server is responding to HTTP requests."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NotesDesktopCheck/1.0'})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status in (200, 404):
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def find_free_port(start_port=58850, max_attempts=50):
    """Find an available TCP port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        # 1. Probe if another process is actively listening
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.settimeout(0.2)
                if probe.connect_ex(('127.0.0.1', port)) == 0:
                    continue
        except Exception:
            pass

        # 2. Test binding to both 0.0.0.0 and 127.0.0.1
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
            return port
        except OSError:
            continue
    return start_port


def create_flask_server(app, host='0.0.0.0', preferred_port=58850, max_attempts=50):
    """
    Directly bind Werkzeug WSGI server to an available port.
    If preferred_port (e.g. 58850) is in use, automatically tries subsequent ports
    (58851, 58852, ...) until an open port is secured.
    """
    from werkzeug.serving import make_server

    ports_to_try = []
    if preferred_port:
        ports_to_try.append(preferred_port)
    ports_to_try.extend(range(58850, 58850 + max_attempts))
    
    seen = set()
    ordered_ports = [p for p in ports_to_try if not (p in seen or seen.add(p))]

    for port in ordered_ports:
        # Check if already listening
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.settimeout(0.15)
                if probe.connect_ex(('127.0.0.1', port)) == 0:
                    continue
        except Exception:
            pass

        try:
            server = make_server(host, port, app, threaded=True)
            return server, port
        except (OSError, socket.error):
            continue

    raise RuntimeError(f"Could not bind Flask backend to any port in range 58850-{58850+max_attempts}")


def start_sync_server(root_dir, port=58855, access_token=''):
    """Optionally start node sync_server.js if Node.js is present."""
    sync_script = os.path.join(root_dir, 'sync_server.js')
    if not os.path.exists(sync_script):
        return None
    try:
        env = os.environ.copy()
        env['SYNC_PORT'] = str(port)
        env['NOTES_SYNC_TOKEN'] = access_token
        proc = subprocess.Popen(
            ['node', sync_script],
            cwd=root_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW
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
            capture_output=True, text=True, timeout=5,
            creationflags=CREATE_NO_WINDOW
        )
        ip = result.stdout.strip()
        if ip and ip.startswith('100.'):
            return ip
    except Exception:
        pass
    return None


def _ensure_tailscale_tray():
    """On Windows, ensure the Tailscale system tray application (tailscale-ipn.exe) is launched."""
    if sys.platform != 'win32':
        return
    ipn_candidates = [
        r"C:\Program Files\Tailscale\tailscale-ipn.exe",
        r"C:\Program Files (x86)\Tailscale\tailscale-ipn.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tailscale", "tailscale-ipn.exe"),
    ]
    for ipn in ipn_candidates:
        if os.path.isfile(ipn):
            try:
                DETACHED = 0x00000008 | 0x00000200
                subprocess.Popen(
                    [ipn],
                    creationflags=DETACHED | CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
            break


def start_tailscale(background=True):
    """
    Attempt to start the Tailscale daemon and bring the device up.
    Runs asynchronously by default so desktop startup is instantaneous.

    Behaviour:
    - If tailscale is not installed → logs clean notice and operates in local Wi-Fi mode.
    - If already connected → ensures tray icon is running, prints the Tailscale IP and returns True.
    - If not running → starts Tailscale daemon in background and opens auth URL if required.
    """
    ts = _find_tailscale_bin()
    if ts is None:
        print("[Desktop] Tailscale not detected locally. Operating in local Wi-Fi / LAN mode.")
        return False

    # Ensure Windows system tray icon is visible
    _ensure_tailscale_tray()

    # Check current status first
    try:
        status = subprocess.run(
            [ts, 'status', '--json'],
            capture_output=True, text=True, timeout=3,
            creationflags=CREATE_NO_WINDOW
        )
        import json
        data = json.loads(status.stdout or '{}')
        backend_state = data.get('BackendState', '')
        if backend_state == 'Running':
            ts_ip = get_tailscale_ip() or 'unknown'
            print(f"[Desktop] [OK] Tailscale connected. Cross-network IP: {ts_ip}")
            return True
    except Exception:
        pass

    # If background mode requested, launch thread
    def _run_tailscale_up():
        print("[Desktop] Bringing up Tailscale for cross-network mesh...")
        try:
            proc = subprocess.Popen(
                [ts, 'up', '--reset', '--accept-routes'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=CREATE_NO_WINDOW
            )
            for line in proc.stdout:
                line = line.strip()
                if line:
                    if line.startswith('https://'):
                        print(f"[Desktop] Tailscale auth required: {line}")
                        webbrowser.open(line)
                    else:
                        print(f"[Desktop]    {line}")
            proc.wait(timeout=120)
            if proc.returncode == 0:
                ts_ip = get_tailscale_ip() or 'unknown'
                print(f"[Desktop] [OK] Tailscale connected. Cross-network IP: {ts_ip}")
        except Exception as e:
            print(f"[Desktop] Tailscale background notice: {e}")

    if background:
        t = threading.Thread(target=_run_tailscale_up, daemon=True)
        t.start()
        return True
    else:
        _run_tailscale_up()
        return True


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

    sep = "-" * 55
    print("\n" + sep)
    print("  Notes Workstation -- Connection Info")
    print(sep)
    print(f"  Local:      http://localhost:{flask_port}")
    for ip in lan_ips:
        print(f"  LAN:        http://{ip}:{flask_port}")
    if ts_ip:
        print(f"  Tailscale:  http://{ts_ip}:{flask_port}  (cross-network active!)")
    else:
        print("  Tailscale:  auto-connecting in background (pass --no-tailscale to skip)")
    print(sep + "\n")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Notes Desktop Application Launcher")
    parser.add_argument('--port', type=int, default=None, help="Flask backend port")
    parser.add_argument('--sync-port', type=int, default=None, help="Yjs P2P Sync WebSocket port")
    parser.add_argument('--dev', action='store_true', help="Point to Vite dev server at http://localhost:5173")
    parser.add_argument('--fullscreen', action='store_true', help="Launch in fullscreen mode")
    parser.add_argument('--browser', action='store_true', help="Force open in default web browser instead of webview")
    parser.add_argument('--tailscale', dest='tailscale', action='store_true', default=True,
                        help="Auto-detect & enable Tailscale on launch for cross-network access (default: enabled)")
    parser.add_argument('--no-tailscale', dest='tailscale', action='store_false',
                        help="Disable automatic Tailscale detection & startup")
    args = parser.parse_args()

    root_dir = os.path.abspath(os.path.dirname(__file__))
    os.chdir(root_dir)

    # Do not attempt to install, start, or authenticate Tailscale. Use it only
    # when the user has already configured the client; LAN remains available.

    # 2. Configure the backend before starting the authenticated sync listener.
    # Windows and VPN software may reserve the conventional port range. Pick an
    # actually bindable port before advertising the node or starting the sync child.
    sync_port = args.sync_port or find_free_port(58855)
    # 3. Import and start Flask app on a guaranteed free port
    from app import create_app
    flask_app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    from app.services.sync_service import sync_service
    sync_service.DEFAULT_PORT = sync_port

    # 4. Start Yjs sync only with the same secret embedded in the local pairing QR.
    sync_proc = start_sync_server(
        root_dir,
        sync_port,
        flask_app.config['PAIRING_ACCESS_TOKEN']
    )
    if sync_proc:
        print(f"[Desktop] Authenticated P2P Yjs WebSocket listener active on port {sync_port}")

    server, flask_port = create_flask_server(flask_app, host='0.0.0.0', preferred_port=args.port or 58850)
    local_check_url = f"http://127.0.0.1:{flask_port}"

    # Inform discovery beacon of actual HTTP port
    try:
        from app.services.sync_service import sync_service
        sync_service.FLASK_PORT = flask_port
    except Exception:
        pass

    flask_thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )
    flask_thread.start()

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
        try:
            webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True
        except Exception:
            pass
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
            print("[Desktop] Server running in background with default browser. Press Ctrl+C to exit.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
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

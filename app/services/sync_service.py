# app/services/sync_service.py
import socket
import os
import hashlib
import time
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from app.database import db
from app.models.models import TailscalePeer, Note
from app.services.hardware_service import hardware_service

DISCOVERY_PORT = 58856

class TailscaleSyncService:
    """
    Zero-Config Tailscale & Local Peer Mesh Engine (LM Studio Nodes style).
    Handles:
    1. Automatic UDP broadcast & listener on port 58856 for zero-URL LAN auto-discovery.
    2. Tailscale detection (MagicDNS + CGNAT 100.x.y.z IP).
    3. One-touch pairing & CRDT delta synchronization.
    4. Hardware specs & services (llama.cpp, GLiNER) discovery & routing across cluster.
    """

    DEFAULT_PORT = 58855
    FLASK_PORT = int(os.environ.get("FLASK_PORT", 58850))

    def __init__(self):
        self._discovered_nodes: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._node_id = self._load_or_create_node_id()
        
        # Local node capabilities & settings
        self._custom_name: Optional[str] = None
        self._llamacpp_enabled: bool = False
        self._llamacpp_local_port: int = 8080
        self._peer_aliases: Dict[str, str] = {}
        self._active_llm_provider: Optional[str] = None

        self._start_discovery_services()

    @staticmethod
    def _load_or_create_node_id() -> str:
        """Keep this device's mesh identity stable across app restarts."""
        identity_dir = Path.home() / ".notes_workstation"
        identity_path = identity_dir / "device_id"
        try:
            identity_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            existing = identity_path.read_text(encoding="ascii").strip()
            if existing.startswith("node-") and len(existing) >= 20:
                return existing
        except (OSError, UnicodeError):
            pass

        node_id = f"node-{uuid.uuid4()}"
        try:
            identity_path.write_text(node_id, encoding="ascii")
            try:
                identity_path.chmod(0o600)
            except OSError:
                pass
        except OSError:
            # Preserve a usable process identity if the profile is read-only.
            pass
        return node_id

    def _start_discovery_services(self):
        """Start background UDP broadcast and listener for zero-config node mesh"""
        self._running = True
        listener_thread = threading.Thread(target=self._udp_listener_loop, daemon=True)
        listener_thread.start()

        beacon_thread = threading.Thread(target=self._udp_beacon_loop, daemon=True)
        beacon_thread.start()

    def _detect_lan_ip(self) -> str:
        """Find local LAN IPv4 address (e.g. 192.168.x.x or 10.x.x.x)"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Connecting to a public address does not send packets but picks the default interface
            s.connect(("8.8.8.8", 80))
            lan_ip = s.getsockname()[0]
            s.close()
            return lan_ip
        except Exception:
            return "127.0.0.1"

    def get_node_id(self) -> str:
        return self._node_id

    def get_node_name(self) -> str:
        return self._custom_name or socket.gethostname()

    def set_node_name(self, name: str):
        if name and name.strip():
            self._custom_name = name.strip()

    def get_llamacpp_config(self) -> Dict[str, Any]:
        return {
            "enabled": self._llamacpp_enabled,
            "local_port": self._llamacpp_local_port,
            "endpoint": f"http://{self._detect_lan_ip()}:{self.FLASK_PORT}/api/nodes/proxy/llm"
        }

    def set_llamacpp_config(self, enabled: bool, local_port: int = 8080):
        self._llamacpp_enabled = bool(enabled)
        if local_port and int(local_port) > 0:
            self._llamacpp_local_port = int(local_port)

    def get_llamacpp_local_port(self) -> int:
        return self._llamacpp_local_port

    def is_llamacpp_enabled(self) -> bool:
        return self._llamacpp_enabled

    def set_peer_alias(self, peer_id: str, alias: str):
        with self._lock:
            self._peer_aliases[str(peer_id)] = alias.strip()

    def get_peer_alias(self, peer_id: str) -> Optional[str]:
        return self._peer_aliases.get(str(peer_id))

    def set_active_llm_provider(self, provider_url: Optional[str]):
        self._active_llm_provider = provider_url.strip() if provider_url else None

    def get_active_llm_provider(self) -> Optional[str]:
        return self._active_llm_provider

    def check_local_llamacpp_health(self) -> Dict[str, Any]:
        """Probe local llama-server port to verify if it is running."""
        port = self._llamacpp_local_port
        url = f"http://127.0.0.1:{port}/health"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    return {"running": True, "status": "ok", "port": port}
        except Exception:
            # Try root endpoint
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1.0) as resp:
                    return {"running": True, "status": "online", "port": port}
            except Exception as e:
                return {"running": False, "status": "unreachable", "port": port, "error": str(e)}

    def _udp_beacon_loop(self):
        """Broadcast presence and capabilities on LAN every 3s so mobile & peers auto-discover this node"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while self._running:
            try:
                lan_ip = self._detect_lan_ip()
                ts_ip = self._detect_tailscale_ip()
                hostname = socket.gethostname()
                display_name = self.get_node_name()

                # Check GLiNER status
                gliner_ready = False
                gliner_device = "cpu"
                gliner_downloading = False
                try:
                    from app.services.gliner_service import gliner_service
                    g_stat = gliner_service.get_status()
                    gliner_ready = g_stat.get("ready", False)
                    gliner_device = g_stat.get("device", "cpu")
                    gliner_downloading = g_stat.get("downloading", False)
                except Exception:
                    pass

                # Polled lightweight hardware specs (cached 30s)
                hw_specs = hardware_service.get_hardware_specs()

                payload = {
                    "type": "NOTES_NODE_ANNOUNCE",
                    "node_id": self._node_id,
                    "name": display_name,
                    "hostname": hostname,
                    "lan_ip": lan_ip,
                    "tailscale_ip": ts_ip,
                    "http_port": self.FLASK_PORT,
                    "sync_port": self.DEFAULT_PORT,
                    "hardware": hw_specs,
                    "services": {
                        "llamacpp": {
                            "enabled": self._llamacpp_enabled,
                            "local_port": self._llamacpp_local_port,
                            "endpoint": f"http://{lan_ip}:{self.FLASK_PORT}/api/nodes/proxy/llm",
                            "tailscale_endpoint": f"http://{ts_ip}:{self.FLASK_PORT}/api/nodes/proxy/llm"
                        },
                        "gliner": {
                            "ready": gliner_ready,
                            "device": gliner_device,
                            "downloading": gliner_downloading,
                            "endpoint": f"http://{lan_ip}:{self.FLASK_PORT}/api/gliner/extract"
                        }
                    },
                    "ts": time.time()
                }
                data = json.dumps(payload).encode("utf-8")
                sock.sendto(data, ("<broadcast>", DISCOVERY_PORT))
            except Exception:
                pass
            time.sleep(3)

    def _udp_listener_loop(self):
        """Listen on DISCOVERY_PORT for announcements from other workstation or mobile nodes"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass

        try:
            sock.bind(("", DISCOVERY_PORT))
        except Exception as e:
            print(f"[Mesh Discovery] Could not bind UDP port {DISCOVERY_PORT}: {e}")
            return

        while self._running:
            try:
                data, addr = sock.recvfrom(4096)
                packet = json.loads(data.decode("utf-8"))
                if packet.get("type") == "NOTES_NODE_ANNOUNCE":
                    node_id = packet.get("node_id")
                    # Ignore own broadcasts
                    if node_id == self._node_id:
                        continue

                    # Record or update discovered node
                    with self._lock:
                        packet["sender_ip"] = addr[0]
                        packet["last_seen"] = time.time()
                        # Apply custom alias if set
                        if node_id in self._peer_aliases:
                            packet["custom_alias"] = self._peer_aliases[node_id]
                        self._discovered_nodes[node_id] = packet
            except Exception:
                time.sleep(0.5)

    def get_discovered_nodes(self) -> List[Dict[str, Any]]:
        """Return all active local nodes discovered within the last 15 seconds"""
        now = time.time()
        active = []
        with self._lock:
            # Purge stale nodes (older than 15 seconds)
            self._discovered_nodes = {
                nid: node for nid, node in self._discovered_nodes.items()
                if now - node.get("last_seen", 0) < 15
            }
            # Decorate with aliases
            for nid, node in self._discovered_nodes.items():
                if nid in self._peer_aliases:
                    node["custom_alias"] = self._peer_aliases[nid]
            active = list(self._discovered_nodes.values())
        return active

    def get_cluster_overview(self) -> Dict[str, Any]:
        """Return complete cluster view: local node, discovered peers, and registered Tailscale peers."""
        lan_ip = self._detect_lan_ip()
        ts_ip = self._detect_tailscale_ip()
        hw_specs = hardware_service.get_hardware_specs()

        # Local GLiNER status
        gliner_stat = {"ready": False, "installed": False, "device": "cpu", "downloading": False}
        try:
            from app.services.gliner_service import gliner_service
            gliner_stat = gliner_service.get_status()
        except Exception:
            pass

        local_node = {
            "node_id": self._node_id,
            "name": self.get_node_name(),
            "hostname": socket.gethostname(),
            "is_local": True,
            "lan_ip": lan_ip,
            "tailscale_ip": ts_ip,
            "http_port": self.FLASK_PORT,
            "sync_port": self.DEFAULT_PORT,
            "hardware": hw_specs,
            "services": {
                "llamacpp": {
                    "enabled": self._llamacpp_enabled,
                    "local_port": self._llamacpp_local_port,
                    "endpoint": f"http://{lan_ip}:{self.FLASK_PORT}/api/nodes/proxy/llm",
                    "tailscale_endpoint": f"http://{ts_ip}:{self.FLASK_PORT}/api/nodes/proxy/llm"
                },
                "gliner": gliner_stat
            },
            "active_llm_provider": self._active_llm_provider
        }

        discovered = self.get_discovered_nodes()

        return {
            "local_node": local_node,
            "discovered_nodes": discovered,
            "paired_peers": self.list_peers(),
            "active_llm_provider": self._active_llm_provider
        }

    def trigger_remote_gliner(self, peer_http_url: str) -> Dict[str, Any]:
        """Send HTTP POST to remote peer to trigger background GLiNER model download."""
        target_url = f"{peer_http_url.rstrip('/')}/api/gliner/download"
        req = urllib.request.Request(
            target_url,
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return {"success": True, "status": resp.status, "message": "GLiNER download triggered on remote peer"}
        except Exception as e:
            return {"success": False, "error": f"Failed to trigger remote GLiNER: {str(e)}"}

    def get_device_info(self) -> Dict[str, Any]:
        hostname = socket.gethostname()
        tailscale_ip = self._detect_tailscale_ip()
        lan_ip = self._detect_lan_ip()
        if lan_ip.startswith("127.") or lan_ip == "0.0.0.0":
            lan_ip = None
        # Do not advertise a guessed MagicDNS name; only advertise routable IPs.
        magic_dns = None
        fingerprint = self._get_or_create_fingerprint()

        return {
            "device_name": self.get_node_name(),
            "hostname": hostname,
            "tailscale_ip": tailscale_ip,
            "lan_ip": lan_ip,
            "magic_dns": magic_dns,
            "http_port": self.FLASK_PORT,
            "port": self.DEFAULT_PORT,
            "fingerprint": fingerprint,
            "hardware": hardware_service.get_hardware_specs(),
            "pairing_payload": {
                "type": "NOTES_PAIR",
                "v": 2,
                "name": self.get_node_name(),
                "lan_url": f"http://{lan_ip}:{self.FLASK_PORT}" if lan_ip else None,
                "tailscale_url": f"http://{tailscale_ip}:{self.FLASK_PORT}" if tailscale_ip else None,
                "lan_ip": lan_ip,
                "tailscale_ip": tailscale_ip,
                "http_port": self.FLASK_PORT,
                "sync_port": self.DEFAULT_PORT,
                "magic_dns": magic_dns,
                "fingerprint": fingerprint
            }
        }

    def register_peer(self, peer_data: Dict[str, Any]) -> TailscalePeer:
        device_name = peer_data.get("device_name") or peer_data.get("name") or "Remote Peer"
        magic_dns = peer_data.get("magic_dns")
        tailscale_ip = peer_data.get("ip") or peer_data.get("tailscale_ip")
        fingerprint = peer_data.get("fingerprint") or "legacy:" + hashlib.sha256(
            f"{magic_dns or ''}|{device_name}".encode("utf-8")
        ).hexdigest()[:32]

        existing = TailscalePeer.query.filter_by(fingerprint=fingerprint).first()
        if existing is None and magic_dns:
            existing = TailscalePeer.query.filter_by(magic_dns=magic_dns).first()

        if existing:
            existing.device_name = device_name
            existing.magic_dns = magic_dns
            if tailscale_ip:
                existing.tailscale_ip = tailscale_ip
            if peer_data.get("port"):
                existing.port = peer_data["port"]
            existing.is_active = True
            existing.last_seen = datetime.now(timezone.utc)
            db.session.commit()
            return existing

        peer = TailscalePeer(
            device_name=device_name,
            magic_dns=magic_dns,
            tailscale_ip=tailscale_ip,
            port=peer_data.get("port", self.DEFAULT_PORT),
            fingerprint=fingerprint,
            is_active=True,
            last_seen=datetime.now(timezone.utc)
        )
        db.session.add(peer)
        db.session.commit()
        return peer

    def list_peers(self) -> List[Dict[str, Any]]:
        peers = TailscalePeer.query.all()
        now = datetime.now(timezone.utc)
        result = []
        for peer in peers:
            last_seen = peer.last_seen
            if last_seen and last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            is_online = bool(last_seen and (now - last_seen).total_seconds() < 90)
            result.append({
                "id": peer.id,
                "device_name": self.get_peer_alias(str(peer.id)) or peer.device_name,
                "tailscale_ip": peer.tailscale_ip,
                "magic_dns": peer.magic_dns,
                "port": peer.port,
                "fingerprint": peer.fingerprint,
                "is_active": is_online,
                "is_online": is_online,
                "last_seen": peer.last_seen.isoformat() if peer.last_seen else None
            })
        return result

    def export_crdt_delta(self, note_id: int) -> Optional[bytes]:
        note = db.session.get(Note, note_id)
        if not note or not note.crdt_state:
            return None
        return note.crdt_state

    def import_crdt_delta(self, note_id: int, binary_delta: bytes) -> bool:
        note = db.session.get(Note, note_id)
        if not note:
            return False
        note.crdt_state = binary_delta
        db.session.commit()
        return True

    def _detect_tailscale_ip(self) -> Optional[str]:
        """Find the real 100.x.y.z Tailscale IP using the CLI or network interfaces."""
        import shutil, subprocess
        # 1. Try tailscale CLI (direct & accurate)
        ts_candidates = [
            shutil.which("tailscale"),
            r"C:\Program Files\Tailscale\tailscale.exe",
            r"C:\Program Files (x86)\Tailscale\tailscale.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tailscale", "tailscale.exe"),
        ]
        for ts_bin in ts_candidates:
            if ts_bin and os.path.isfile(ts_bin):
                try:
                    create_flag = 0x08000000 if sys.platform == "win32" else 0
                    res = subprocess.check_output(
                        [ts_bin, "ip", "-4"],
                        timeout=1.5, text=True, stderr=subprocess.DEVNULL,
                        creationflags=create_flag
                    ).strip()
                    if res and res.startswith("100."):
                        return res
                except Exception:
                    pass

        # 2. Try socket.getaddrinfo fallback
        try:
            addrs = socket.getaddrinfo(socket.gethostname(), None)
            for addr in addrs:
                ip = addr[4][0]
                if ip.startswith("100."):
                    return ip
        except Exception:
            pass

        return None

    def _get_or_create_fingerprint(self) -> str:
        return self._node_id

sync_service = TailscaleSyncService()

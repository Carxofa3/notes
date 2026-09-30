# app/services/sync_service.py
import socket
import os
import hashlib
import time
import json
import threading
from typing import Dict, Any, List, Optional
from app.database import db
from app.models.models import TailscalePeer, Note

DISCOVERY_PORT = 58856

class TailscaleSyncService:
    """
    Zero-Config Tailscale & Local Peer Mesh Engine (LM Studio Nodes style).
    Handles:
    1. Automatic UDP broadcast & listener on port 58856 for zero-URL LAN auto-discovery.
    2. Tailscale detection (MagicDNS + CGNAT 100.x.y.z IP).
    3. One-touch pairing & CRDT delta synchronization.
    """

    DEFAULT_PORT = 58855
    FLASK_PORT = 5000

    def __init__(self):
        self._discovered_nodes: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._node_id = f"node-{socket.gethostname().lower()}-{int(time.time()) % 10000}"
        self._start_discovery_services()

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

    def _udp_beacon_loop(self):
        """Broadcast presence on LAN every 3 seconds so mobile & peers auto-discover this node"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while self._running:
            try:
                lan_ip = self._detect_lan_ip()
                ts_ip = self._detect_tailscale_ip()
                hostname = socket.gethostname()

                # Check if GLiNER is ready
                gliner_ready = False
                try:
                    from app.services.gliner_service import gliner_service
                    gliner_ready = gliner_service.is_ready()
                except Exception:
                    pass

                payload = {
                    "type": "NOTES_NODE_ANNOUNCE",
                    "node_id": self._node_id,
                    "name": hostname,
                    "lan_ip": lan_ip,
                    "tailscale_ip": ts_ip,
                    "http_port": self.FLASK_PORT,
                    "sync_port": self.DEFAULT_PORT,
                    "gliner_ready": gliner_ready,
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
                data, addr = sock.recvfrom(2048)
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
                        self._discovered_nodes[node_id] = packet
            except Exception:
                time.sleep(0.5)

    def get_discovered_nodes(self) -> List[Dict[str, Any]]:
        """Return all active local nodes discovered within the last 15 seconds"""
        now = time.time()
        active = []
        with self._lock:
            # Purge stale nodes
            self._discovered_nodes = {
                nid: node for nid, node in self._discovered_nodes.items()
                if now - node.get("last_seen", 0) < 15
            }
            active = list(self._discovered_nodes.values())
        return active

    def get_device_info(self) -> Dict[str, Any]:
        hostname = socket.gethostname()
        tailscale_ip = self._detect_tailscale_ip()
        lan_ip = self._detect_lan_ip()
        magic_dns = f"{hostname.lower()}.tailnet.ts.net"
        fingerprint = self._get_or_create_fingerprint()

        return {
            "device_name": hostname,
            "tailscale_ip": tailscale_ip,
            "lan_ip": lan_ip,
            "magic_dns": magic_dns,
            "http_port": self.FLASK_PORT,
            "port": self.DEFAULT_PORT,
            "fingerprint": fingerprint,
            "pairing_payload": {
                "v": 1,
                "magic_dns": magic_dns,
                "ip": tailscale_ip,
                "lan_ip": lan_ip,
                "port": self.DEFAULT_PORT,
                "http_port": self.FLASK_PORT,
                "name": hostname,
                "fingerprint": fingerprint,
                "ts": int(time.time())
            }
        }

    def register_peer(self, peer_data: Dict[str, Any]) -> TailscalePeer:
        device_name = peer_data.get("device_name") or peer_data.get("name") or "Remote Peer"
        magic_dns = peer_data.get("magic_dns")
        tailscale_ip = peer_data.get("ip") or peer_data.get("tailscale_ip")
        port = peer_data.get("port", self.DEFAULT_PORT)
        fingerprint = peer_data.get("fingerprint")

        existing = TailscalePeer.query.filter(
            (TailscalePeer.magic_dns == magic_dns) | (TailscalePeer.fingerprint == fingerprint)
        ).first()

        if existing:
            existing.device_name = device_name
            existing.tailscale_ip = tailscale_ip
            existing.port = port
            existing.is_active = True
            db.session.commit()
            return existing

        peer = TailscalePeer(
            device_name=device_name,
            magic_dns=magic_dns,
            tailscale_ip=tailscale_ip,
            port=port,
            fingerprint=fingerprint,
            is_active=True
        )
        db.session.add(peer)
        db.session.commit()
        return peer

    def list_peers(self) -> List[Dict[str, Any]]:
        peers = TailscalePeer.query.all()
        return [{
            "id": p.id,
            "device_name": p.device_name,
            "tailscale_ip": p.tailscale_ip,
            "magic_dns": p.magic_dns,
            "port": p.port,
            "fingerprint": p.fingerprint,
            "is_active": p.is_active,
            "last_seen": p.last_seen.isoformat() if p.last_seen else None
        } for p in peers]

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

    def _detect_tailscale_ip(self) -> str:
        """Find the 100.x.y.z Tailscale CGNAT address if active on the host"""
        try:
            addrs = socket.getaddrinfo(socket.gethostname(), None)
            for addr in addrs:
                ip = addr[4][0]
                if ip.startswith("100."):
                    return ip
        except Exception:
            pass
        return "100.64.0.1"

    def _get_or_create_fingerprint(self) -> str:
        seed = f"{socket.gethostname()}-tailscale-notes-cert"
        return "ed25519:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]

sync_service = TailscaleSyncService()

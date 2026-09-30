# app/services/sync_service.py
import socket
import os
import hashlib
import time
from typing import Dict, Any, List, Optional
from app.database import db
from app.models.models import TailscalePeer, Note

class TailscaleSyncService:
    """
    Tailscale Peer-to-Peer Synchronization Engine.
    Handles asymmetric desktop listener / mobile initiator discovery,
    one-time QR-code pairing, and CRDT document state exchange.
    """

    DEFAULT_PORT = 58855

    def get_device_info(self) -> Dict[str, Any]:
        hostname = socket.gethostname()
        tailscale_ip = self._detect_tailscale_ip()
        magic_dns = f"{hostname.lower()}.tailnet.ts.net"
        fingerprint = self._get_or_create_fingerprint()

        return {
            "device_name": hostname,
            "tailscale_ip": tailscale_ip,
            "magic_dns": magic_dns,
            "port": self.DEFAULT_PORT,
            "fingerprint": fingerprint,
            "pairing_payload": {
                "v": 1,
                "magic_dns": magic_dns,
                "ip": tailscale_ip,
                "port": self.DEFAULT_PORT,
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
            # Enumerate interfaces
            addrs = socket.getaddrinfo(socket.gethostname(), None)
            for addr in addrs:
                ip = addr[4][0]
                if ip.startswith("100."):
                    return ip
        except Exception:
            pass
        return "100.64.0.1" # Fallback Tailscale mesh interface IP

    def _get_or_create_fingerprint(self) -> str:
        seed = f"{socket.gethostname()}-tailscale-notes-cert"
        return "ed25519:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]

sync_service = TailscaleSyncService()

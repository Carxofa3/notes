/**
 * Tailscale P2P Yjs Synchronization Server
 * Persistent listener on 0.0.0.0:58855 for Desktop & Android peer replication.
 */

import { WebSocketServer, WebSocket } from 'ws';
import http from 'http';
import * as Y from 'yjs';
import { timingSafeEqual } from 'crypto';

const PORT = process.env.SYNC_PORT || 58855;
const HOST = '0.0.0.0';

// In-memory document map: roomName -> { doc: Y.Doc, clients: Set<WebSocket> }
const rooms = new Map();

function getOrCreateRoom(roomName) {
  if (!rooms.has(roomName)) {
    const doc = new Y.Doc();
    const clients = new Set();

    doc.on('update', (update, origin) => {
      // Broadcast binary delta to all peers except the origin
      const message = createUpdateMessage(update);
      for (const client of clients) {
        if (client !== origin && client.readyState === WebSocket.OPEN) {
          client.send(message);
        }
      }
    });

    rooms.set(roomName, { doc, clients });
  }
  return rooms.get(roomName);
}

function createUpdateMessage(update) {
  const buf = Buffer.alloc(1 + update.length);
  buf.writeUInt8(1, 0); // message type 1: update delta
  Buffer.from(update).copy(buf, 1);
  return buf;
}

function createSyncStep1Message(doc) {
  const sv = Y.encodeStateVector(doc);
  const buf = Buffer.alloc(1 + sv.length);
  buf.writeUInt8(0, 0); // message type 0: sync step 1 (state vector)
  Buffer.from(sv).copy(buf, 1);
  return buf;
}

const server = http.createServer((req, res) => {
  // Health & Pairing status endpoint
  if (req.url === '/health' || req.url === '/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'active',
      role: 'desktop_tailscale_listener',
      port: PORT,
      active_rooms: rooms.size,
      connected_peers: Array.from(rooms.values()).reduce((acc, r) => acc + r.clients.size, 0),
      timestamp: Date.now()
    }));
    return;
  }
  res.writeHead(404);
  res.end();
});

const expectedToken = Buffer.from(process.env.NOTES_SYNC_TOKEN || '');
const wss = new WebSocketServer({
  server,
  verifyClient: (info, done) => {
    const offered = (info.req.headers['sec-websocket-protocol'] || '')
      .split(',')
      .map((value) => value.trim());
    const suppliedProtocol = offered.find((value) => value.startsWith('notes-auth.')) || '';
    const suppliedToken = Buffer.from(suppliedProtocol.slice('notes-auth.'.length));
    const valid = expectedToken.length > 0
      && suppliedToken.length === expectedToken.length
      && timingSafeEqual(suppliedToken, expectedToken);
    done(valid, valid ? 101 : 401, valid ? 'Paired device' : 'Pairing required');
  },
  handleProtocols: (protocols) => protocols.has('notes') ? 'notes' : false
});

wss.on('connection', (ws, req) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const roomName = url.pathname.replace(/^\/+/, '') || 'global-notes';

  const room = getOrCreateRoom(roomName);
  room.clients.add(ws);

  console.log(`[P2P Sync] Peer connected to room "${roomName}". Total room clients: ${room.clients.size}`);

  // Send current state vector to client so it can compute diff
  ws.send(createSyncStep1Message(room.doc));

  // Also send complete document state update to bring peer up to speed
  const fullState = Y.encodeStateAsUpdate(room.doc);
  if (fullState.length > 0) {
    ws.send(createUpdateMessage(fullState));
  }

  ws.on('message', (data, isBinary) => {
    try {
      const buf = Buffer.from(data);
      if (buf.length === 0) return;
      const messageType = buf.readUInt8(0);
      const payload = buf.subarray(1);

      if (messageType === 0) {
        // Sync Step 1: Received client's state vector -> reply with missing update
        const diff = Y.encodeStateAsUpdate(room.doc, payload);
        if (diff.length > 0) {
          ws.send(createUpdateMessage(diff));
        }
      } else if (messageType === 1) {
        // Update delta: Apply update to server doc with ws as origin
        Y.applyUpdate(room.doc, payload, ws);
      }
    } catch (err) {
      console.error('[P2P Sync] Error processing CRDT delta:', err);
    }
  });

  ws.on('close', () => {
    room.clients.delete(ws);
    console.log(`[P2P Sync] Peer disconnected from room "${roomName}". Remaining: ${room.clients.size}`);
  });

  ws.on('error', (err) => {
    console.error('[P2P Sync] Peer socket error:', err);
  });
});

server.listen(PORT, HOST, () => {
  console.log(`=======================================================`);
  console.log(`  Tailscale P2P Yjs Synchronization Server Running      `);
  console.log(`  Listening on http://${HOST}:${PORT} (0.0.0.0:58855)   `);
  console.log(`=======================================================`);
});

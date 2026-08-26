/**
 * WebRTC Stream Manager
 * 
 * Provides global singleton caching, pooling, and robust fallback for WebRTC MediaStreams.
 * Supports:
 * - Direct AI stream (/{cameraId}/whep)
 * - Raw stream fallback (/raw_{cameraId}/whep)
 * - Auto-retry when stream is starting up
 * - 45s grace period persistence across page navigation and modals
 */

type StreamListener = (stream: MediaStream | null, error: string | null) => void;

interface StreamEntry {
  cameraId: string;
  pc: RTCPeerConnection | null;
  stream: MediaStream | null;
  refCount: number;
  listeners: Set<StreamListener>;
  isConnecting: boolean;
  cleanupTimer: ReturnType<typeof setTimeout> | null;
  retryTimer: ReturnType<typeof setTimeout> | null;
  retryCount: number;
}

class WebRTCStreamManager {
  private entries = new Map<string, StreamEntry>();
  private readonly GRACE_PERIOD_MS = 45000; // 45s stream persistence

  public subscribe(cameraId: string, listener: StreamListener): () => void {
    let entry = this.entries.get(cameraId);

    if (!entry) {
      entry = {
        cameraId,
        pc: null,
        stream: null,
        refCount: 0,
        listeners: new Set(),
        isConnecting: false,
        cleanupTimer: null,
        retryTimer: null,
        retryCount: 0,
      };
      this.entries.set(cameraId, entry);
    }

    if (entry.cleanupTimer) {
      clearTimeout(entry.cleanupTimer);
      entry.cleanupTimer = null;
    }

    entry.refCount++;
    entry.listeners.add(listener);

    // If stream is already live, deliver immediately
    if (entry.stream && entry.stream.active && entry.stream.getVideoTracks().length > 0) {
      listener(entry.stream, null);
    } else if (!entry.isConnecting) {
      this.connect(entry);
    }

    return () => {
      if (!entry) return;
      entry.listeners.delete(listener);
      entry.refCount = Math.max(0, entry.refCount - 1);

      if (entry.refCount === 0 && !entry.cleanupTimer) {
        entry.cleanupTimer = setTimeout(() => {
          this.destroyEntry(cameraId);
        }, this.GRACE_PERIOD_MS);
      }
    };
  }

  private async connect(entry: StreamEntry) {
    if (entry.isConnecting) return;
    entry.isConnecting = true;

    try {
      if (entry.pc) {
        try { entry.pc.close(); } catch (_) {}
      }

      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      });
      entry.pc = pc;

      pc.addTransceiver('video', { direction: 'recvonly' });

      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          entry.stream = event.streams[0];
          entry.retryCount = 0;
          entry.listeners.forEach(l => l(entry.stream, null));
        }
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const host = window.location.hostname;
      const paths = [
        entry.cameraId,
        `raw_${entry.cameraId}`,
        entry.cameraId.toLowerCase(),
        `raw_${entry.cameraId.toLowerCase()}`
      ];

      const whepUrls: string[] = [];
      for (const p of paths) {
        whepUrls.push(`/webrtc-stream/${encodeURIComponent(p)}/whep`);
        whepUrls.push(`http://${host}:8189/${encodeURIComponent(p)}/whep`);
      }

      let response: Response | null = null;
      let lastErr: any = null;

      for (const url of whepUrls) {
        try {
          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/sdp' },
            body: pc.localDescription?.sdp
          });
          if (res.ok) {
            response = res;
            break;
          }
        } catch (e) {
          lastErr = e;
        }
      }

      if (!response || !response.ok) {
        throw new Error(`WHEP endpoint unreachable (${lastErr?.message || 'MediaMTX stream offline'})`);
      }

      const answerSdp = await response.text();
      await pc.setRemoteDescription(new RTCSessionDescription({
        type: 'answer',
        sdp: answerSdp
      }));

    } catch (err: any) {
      console.warn(`WebRTC Stream Manager [${entry.cameraId}]:`, err?.message || err);
      entry.listeners.forEach(l => l(null, err?.message || 'Connecting stream...'));

      // Automatically retry if there are active listeners (stream might still be starting)
      if (entry.listeners.size > 0 && entry.retryCount < 30) {
        entry.retryCount++;
        const delay = Math.min(1000 * Math.pow(1.2, entry.retryCount), 3000);
        entry.retryTimer = setTimeout(() => {
          if (entry.listeners.size > 0) {
            this.connect(entry);
          }
        }, delay);
      }
    } finally {
      entry.isConnecting = false;
    }
  }

  public closeStream(cameraId: string) {
    this.destroyEntry(cameraId);
  }

  private destroyEntry(cameraId: string) {
    const entry = this.entries.get(cameraId);
    if (!entry) return;

    if (entry.cleanupTimer) clearTimeout(entry.cleanupTimer);
    if (entry.retryTimer) clearTimeout(entry.retryTimer);

    if (entry.pc) {
      try { entry.pc.close(); } catch (_) {}
    }

    if (entry.stream) {
      entry.stream.getTracks().forEach(t => {
        try { t.stop(); } catch (_) {}
      });
    }

    this.entries.delete(cameraId);
  }
}

export const webrtcStreamManager = new WebRTCStreamManager();

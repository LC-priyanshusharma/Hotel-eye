#!/usr/bin/env python3
"""
LogicEye WebRTC Stream Pooling & Instant Modal Patch for Jetson Nano.
Eliminates camera reconnections on page navigation and modal open/close.
"""

import os
import sys

BASE_DIR = "/home/user/LogicEye-main"
if not os.path.exists(BASE_DIR):
    if os.path.exists("frontend") and os.path.exists("backend"):
        BASE_DIR = os.getcwd()
    else:
        print(f"Error: Base directory {BASE_DIR} not found.")
        sys.exit(1)

print(f"Applying WebRTC Stream Pool patch to {BASE_DIR}...")

# 1. Create frontend/src/services/webrtcStreamManager.ts
webrtc_manager_code = """type StreamListener = (stream: MediaStream | null, error: string | null) => void;

interface StreamEntry {
  cameraId: string;
  pc: RTCPeerConnection | null;
  stream: MediaStream | null;
  refCount: number;
  listeners: Set<StreamListener>;
  isConnecting: boolean;
  cleanupTimer: ReturnType<typeof setTimeout> | null;
}

class WebRTCStreamManager {
  private entries = new Map<string, StreamEntry>();
  private readonly GRACE_PERIOD_MS = 45000; // Keep stream alive for 45s after unmount

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
      };
      this.entries.set(cameraId, entry);
    }

    if (entry.cleanupTimer) {
      clearTimeout(entry.cleanupTimer);
      entry.cleanupTimer = null;
    }

    entry.refCount++;
    entry.listeners.add(listener);

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
          entry.listeners.forEach(l => l(entry.stream, null));
        }
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const host = window.location.hostname;
      const whepUrls = [
        `/webrtc-stream/${encodeURIComponent(entry.cameraId)}/whep`,
        `http://${host}:8189/${encodeURIComponent(entry.cameraId)}/whep`
      ];

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
        throw new Error(`WHEP endpoint unreachable (${lastErr?.message || 'MediaMTX offline'})`);
      }

      const answerSdp = await response.text();
      await pc.setRemoteDescription(new RTCSessionDescription({
        type: 'answer',
        sdp: answerSdp
      }));

    } catch (err: any) {
      console.warn(`WebRTC Stream Manager [${entry.cameraId}]:`, err?.message || err);
      entry.listeners.forEach(l => l(null, err?.message || 'Connecting stream...'));
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

    if (entry.cleanupTimer) {
      clearTimeout(entry.cleanupTimer);
    }

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
"""
os.makedirs(os.path.join(BASE_DIR, "frontend/src/services"), exist_ok=True)
with open(os.path.join(BASE_DIR, "frontend/src/services/webrtcStreamManager.ts"), "w") as f:
    f.write(webrtc_manager_code)

print("✓ Created frontend/src/services/webrtcStreamManager.ts")

# 2. Update VideoPlaceholder.tsx
video_player_code = """import React, { memo, useEffect, useRef, useState } from 'react'
import { cn } from '@/utils/utils'
import { webrtcStreamManager } from '@/services/webrtcStreamManager'

export interface VideoPlayerProps {
  cameraId: string
  poster?: string
  loading?: boolean
  error?: string
  streamUrl?: string
}

export const VideoPlayer = memo(({ cameraId, poster, loading, error }: VideoPlayerProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hasFirstFrame, setHasFirstFrame] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  useEffect(() => {
    if (loading || error) return;
    setConnectionError(null);

    const unsubscribe = webrtcStreamManager.subscribe(cameraId, (stream, err) => {
      if (err) {
        setConnectionError(err);
        return;
      }

      if (stream && videoRef.current) {
        if (videoRef.current.srcObject !== stream) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
        setHasFirstFrame(true);
        setConnectionError(null);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [cameraId, loading, error]);

  if (error || connectionError) {
    return (
      <div className="w-full h-full relative bg-black/90 flex flex-col items-center justify-center p-4">
        <span className="text-danger font-mono text-xs tracking-widest uppercase text-center">
          {error || connectionError}
        </span>
        <button 
          onClick={() => {
            setConnectionError(null);
            webrtcStreamManager.closeStream(cameraId);
            webrtcStreamManager.subscribe(cameraId, (stream) => {
              if (stream && videoRef.current) {
                videoRef.current.srcObject = stream;
                videoRef.current.play().catch(() => {});
                setHasFirstFrame(true);
              }
            });
          }}
          className="mt-3 px-3 py-1 bg-primary/20 hover:bg-primary/30 border border-primary/40 rounded text-[11px] text-primary transition-colors font-mono"
        >
          Reconnect
        </button>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative bg-black flex items-center justify-center overflow-hidden">
      {poster && !hasFirstFrame && (
        <img 
          src={poster} 
          className="absolute inset-0 w-full h-full object-cover opacity-20" 
          alt={`Poster for ${cameraId}`}
        />
      )}
      
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        onLoadedData={() => setHasFirstFrame(true)}
        onPlaying={() => setHasFirstFrame(true)}
        className={cn(
          "w-full h-full object-cover transition-opacity duration-200",
          hasFirstFrame ? "opacity-100" : "opacity-0"
        )}
      />

      {(!hasFirstFrame || loading) && (
        <div className="absolute inset-0 z-10 bg-black flex flex-col items-center justify-center p-4 pointer-events-none">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
          <span className="text-foreground/60 font-mono text-xs tracking-widest uppercase">
            {loading ? "Initializing Stream..." : "Connecting WebRTC..."}
          </span>
        </div>
      )}
    </div>
  );
});

VideoPlayer.displayName = 'VideoPlayer';
"""
with open(os.path.join(BASE_DIR, "frontend/src/components/camera/VideoPlaceholder.tsx"), "w") as f:
    f.write(video_player_code)

print("✓ Updated frontend/src/components/camera/VideoPlaceholder.tsx")

# 3. Update CameraCard.tsx & LiveCameras/index.tsx
cam_card_path = os.path.join(BASE_DIR, "frontend/src/components/camera/CameraCard.tsx")
if os.path.exists(cam_card_path):
    with open(cam_card_path, "r") as f:
        cc = f.read()
    if "import { webrtcStreamManager } from '@/services/webrtcStreamManager'" not in cc:
        cc = "import { webrtcStreamManager } from '@/services/webrtcStreamManager'\n" + cc
    cc = cc.replace(
        'const endpoint = pipelineStatus === "Stopped" ? "/api/cameras/start" : "/api/cameras/stop"',
        'const isStopping = pipelineStatus !== "Stopped";\n    const endpoint = isStopping ? "/api/cameras/stop" : "/api/cameras/start";\n    if (isStopping) webrtcStreamManager.closeStream(id);'
    )
    with open(cam_card_path, "w") as f:
        f.write(cc)
    print("✓ Updated CameraCard.tsx with stream cleanup on stop.")

live_cam_path = os.path.join(BASE_DIR, "frontend/src/pages/LiveCameras/index.tsx")
if os.path.exists(live_cam_path):
    with open(live_cam_path, "r") as f:
        lc = f.read()
    
    # Replace conditional unmount with overlay grid persistence
    old_grid_block = """          {activeCameraId ? (
            <div className="flex-1 w-full p-4 flex items-center justify-center">
              <div className="w-full h-full max-w-7xl">
                {cameras.filter(c => c.id === activeCameraId).map(cam => (
                  <CameraCard key={cam.id} {...cam} pipelineStatus={pipelineStatuses[cam.id] || "Stopped"} />
                ))}
              </div>
            </div>
          ) : ("""
    
    new_grid_block = """          {activeCameraId && (
            <div className="absolute inset-0 z-20 p-4 flex items-center justify-center bg-background/95 backdrop-blur-sm">
              <div className="w-full h-full max-w-7xl">
                {cameras.filter(c => c.id === activeCameraId).map(cam => (
                  <CameraCard key={`active-${cam.id}`} {...cam} pipelineStatus={pipelineStatuses[cam.id] || "Stopped"} />
                ))}
              </div>
            </div>
          )}

          <div className={cn("w-full h-full", activeCameraId ? "invisible pointer-events-none" : "visible")}>"""
    
    if old_grid_block in lc:
        lc = lc.replace(old_grid_block, new_grid_block)
        lc = lc.replace("          </ResponsiveGridLayout>\n          )}", "          </ResponsiveGridLayout>\n          </div>")
        with open(live_cam_path, "w") as f:
            f.write(lc)
        print("✓ Updated LiveCameras/index.tsx for persistent grid rendering.")

print("\n🚀 WebRTC stream pooling installed! Streams will now remain persistent and transition instantly.")

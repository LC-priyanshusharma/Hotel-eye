import { memo, useEffect, useRef, useState } from 'react'
import { cn } from '@/utils/utils'
import { webrtcStreamManager } from '@/services/webrtcStreamManager'
import { VideoOff, RefreshCw, Signal, Activity } from 'lucide-react'

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
  const [connectionStatus, setConnectionStatus] = useState<string | null>(null);

  useEffect(() => {
    if (loading || error) return;
    setConnectionStatus(null);

    const unsubscribe = webrtcStreamManager.subscribe(cameraId, (stream, err) => {
      if (err) {
        setConnectionStatus(err);
        return;
      }

      if (stream && videoRef.current) {
        if (videoRef.current.srcObject !== stream) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
        setHasFirstFrame(true);
        setConnectionStatus(null);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [cameraId, loading, error]);

  const isOffline = error || connectionStatus;

  return (
    <div className="w-full h-full relative bg-zinc-950 flex items-center justify-center overflow-hidden">
      {/* Poster fallback */}
      {poster && !hasFirstFrame && (
        <img 
          src={poster} 
          className="absolute inset-0 w-full h-full object-contain opacity-10" 
          alt={`Poster for ${cameraId}`}
        />
      )}
      
      {/* Persistent hardware-accelerated video element with true aspect ratio preservation */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        onLoadedData={() => setHasFirstFrame(true)}
        onPlaying={() => setHasFirstFrame(true)}
        className={cn(
          "w-full h-full object-contain transition-opacity duration-300",
          hasFirstFrame && !isOffline ? "opacity-100" : "opacity-0"
        )}
      />

      {/* Standby / Connecting / Offline HUD */}
      {(!hasFirstFrame || isOffline) && (
        <div className="absolute inset-0 z-10 bg-zinc-950/95 flex flex-col items-center justify-center p-4 text-center select-none">
          <div className="relative mb-4 flex items-center justify-center">
            <div className="w-12 h-12 rounded-full border border-primary/30 flex items-center justify-center animate-pulse">
              <Activity className="w-6 h-6 text-primary/70" />
            </div>
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500" />
            </span>
          </div>

          <span className="text-white font-mono text-xs tracking-widest uppercase font-semibold mb-1">
            {loading ? "Initializing Stream..." : isOffline ? "RTSP Stream Standby" : "Connecting WebRTC..."}
          </span>
          <span className="text-muted-foreground/70 font-mono text-[10px] tracking-wider max-w-xs mb-3">
            {isOffline ? "Awaiting camera connection or RTSP stream broadcast" : "Establishing peer connection with MediaMTX"}
          </span>

          <button 
            onClick={() => {
              setConnectionStatus(null);
              webrtcStreamManager.closeStream(cameraId);
              webrtcStreamManager.subscribe(cameraId, (stream) => {
                if (stream && videoRef.current) {
                  videoRef.current.srcObject = stream;
                  videoRef.current.play().catch(() => {});
                  setHasFirstFrame(true);
                }
              });
            }}
            className="flex items-center gap-1.5 px-3 py-1 bg-primary/20 hover:bg-primary/30 border border-primary/40 rounded-lg text-[11px] text-primary transition-all font-mono shadow-sm hover:scale-105"
          >
            <RefreshCw className="w-3 h-3" /> Reconnect
          </button>
        </div>
      )}
    </div>
  );
});

VideoPlayer.displayName = 'VideoPlayer';

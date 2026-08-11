import React, { memo, useEffect, useRef, useState } from 'react'
import { useCameraStateStore } from '@/store/useCameraStateStore'

export interface VideoPlayerProps {
  cameraId: string
  poster?: string
  loading?: boolean
  error?: string
  streamUrl?: string
}

export const VideoPlayer = memo(({ cameraId, poster, loading, error }: VideoPlayerProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isConnecting, setIsConnecting] = useState(true);
  const [hasFirstFrame, setHasFirstFrame] = useState(false);
  const peerConnection = useRef<RTCPeerConnection | null>(null);
  const animFrameId = useRef<number>(0);

  // Drawing Loop for bounding boxes
  useEffect(() => {
    if (!hasFirstFrame || !videoRef.current || !canvasRef.current) return;
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let isActive = true;

    const drawLoop = () => {
      if (!isActive) return;

      // Match canvas resolution to displayed video size
      if (canvas.width !== video.clientWidth || canvas.height !== video.clientHeight) {
        canvas.width = video.clientWidth;
        canvas.height = video.clientHeight;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Get latest detections without triggering React re-renders
      const state = useCameraStateStore.getState().states[cameraId];
      const detections = state?.detections || [];
      
      const videoNativeWidth = video.videoWidth || 1920;
      const videoNativeHeight = video.videoHeight || 1080;
      
      const scaleX = canvas.width / videoNativeWidth;
      const scaleY = canvas.height / videoNativeHeight;

      for (const det of detections) {
        if (!det.bbox || det.bbox.length !== 4) continue;
        const [x1, y1, x2, y2] = det.bbox;
        
        const scaledX = x1 * scaleX;
        const scaledY = y1 * scaleY;
        const scaledW = (x2 - x1) * scaleX;
        const scaledH = (y2 - y1) * scaleY;

        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        ctx.strokeRect(scaledX, scaledY, scaledW, scaledH);
        
        // Optionally draw track ID or class
        ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
        ctx.fillRect(scaledX, scaledY, scaledW, scaledH);
        
        if (det.track_id !== undefined && det.track_id !== null) {
          ctx.fillStyle = '#00ff00';
          ctx.font = 'bold 12px monospace';
          ctx.fillText(`ID: ${det.track_id}`, scaledX, scaledY - 4);
        }
      }

      animFrameId.current = requestAnimationFrame(drawLoop);
    };

    drawLoop();

    return () => {
      isActive = false;
      cancelAnimationFrame(animFrameId.current);
    };
  }, [hasFirstFrame, cameraId]);

  useEffect(() => {
    if (loading || error) return;
    
    setIsConnecting(true);
    let isActive = true;
    
    // We assume MediaMTX is running on the same host but port 8189, or via proxy.
    // For development, assuming MediaMTX is accessible via standard WHEP endpoint.
    const host = window.location.hostname;
    // Note: The camera_id must match the MediaMTX path cleanly.
    // If cameraId has spaces/slashes, it should be encoded or mapped.
    const cleanCameraId = encodeURIComponent(cameraId.replace(/[^a-zA-Z0-9_-]/g, ''));
    const whepUrl = `http://${host}:8189/${cleanCameraId}/whep`;

    const startWebRTC = async () => {
      try {
        const pc = new RTCPeerConnection();
        peerConnection.current = pc;

        pc.addTransceiver('video', { direction: 'recvonly' });
        // Optional: add audio transceiver if needed
        // pc.addTransceiver('audio', { direction: 'recvonly' });

        pc.ontrack = (event) => {
          if (!isActive) return;
          if (videoRef.current) {
            videoRef.current.srcObject = event.streams[0];
            setHasFirstFrame(true);
            setIsConnecting(false);
          }
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const response = await fetch(whepUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/sdp',
          },
          body: offer.sdp,
        });

        if (!response.ok) {
          throw new Error(`MediaMTX WHEP Error: ${response.status} ${response.statusText}`);
        }

        const answerSdp = await response.text();
        await pc.setRemoteDescription(new RTCSessionDescription({
          type: 'answer',
          sdp: answerSdp,
        }));
        
        setRetryCount(0);
      } catch (err) {
        console.error(`WebRTC WHEP error for ${cameraId}:`, err);
        if (isActive) {
          setIsConnecting(true);
          // Exponential backoff
          if (retryCount < 5) {
            const timeout = Math.min(1000 * Math.pow(2, retryCount), 10000);
            setTimeout(() => {
              if (isActive) setRetryCount(prev => prev + 1);
            }, timeout);
          }
        }
      }
    };

    startWebRTC();

    return () => {
      isActive = false;
      if (peerConnection.current) {
        peerConnection.current.close();
        peerConnection.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [cameraId, retryCount, loading, error]);

  if (error) {
    return (
      <div className="w-full h-full relative bg-danger/10 flex flex-col items-center justify-center p-4">
        <span className="text-danger font-bold text-sm tracking-widest text-center">{error}</span>
      </div>
    )
  }

  return (
    <div className="w-full h-full relative bg-black flex items-center justify-center overflow-hidden group/player">
      
      {(loading || (isConnecting && !hasFirstFrame)) && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black animate-pulse">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
          <span className="text-foreground/50 font-mono text-xs tracking-widest uppercase">
            {loading ? "Initializing Stream" : "Connecting WebRTC..."}
          </span>
        </div>
      )}
      {/* Poster fallback when WebSocket permanently fails */}
      {poster && !hasFirstFrame && (
        <img 
          src={poster} 
          className="absolute inset-0 w-full h-full object-cover opacity-30" 
          alt={`Poster for ${cameraId}`}
        />
      )}
      
      {/* Native WebRTC Video Player */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover relative z-0"
      />
      
      {/* Bounding Box Overlay Canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full object-cover z-10 pointer-events-none"
      />
    </div>
  )
})

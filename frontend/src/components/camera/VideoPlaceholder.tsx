import React, { memo, useEffect, useRef, useState } from 'react'

export interface VideoPlayerProps {
  cameraId: string
  poster?: string
  loading?: boolean
  error?: string
  streamUrl?: string
}

export const VideoPlayer = memo(({ cameraId, poster, loading, error }: VideoPlayerProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isConnecting, setIsConnecting] = useState(true);
  const [hasFirstFrame, setHasFirstFrame] = useState(false);
  const peerConnection = useRef<RTCPeerConnection | null>(null);

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
    <div className="w-full h-full relative bg-black flex items-center justify-center overflow-hidden">
      
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
        className="w-full h-full object-cover"
      />
    </div>
  )
})

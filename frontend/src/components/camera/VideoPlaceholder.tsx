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
  const posterImgRef = useRef<HTMLImageElement>(null);
  
  const [retryCount, setRetryCount] = useState(0);
  const [isWsConnecting, setIsWsConnecting] = useState(true);
  const [hasFirstFrame, setHasFirstFrame] = useState(false);

  useEffect(() => {
    if (loading || error) return;
    
    setIsWsConnecting(true);
    let pc: RTCPeerConnection | null = null;
    let isActive = true;

    const connectWebRTC = async () => {
      try {
        pc = new RTCPeerConnection();
        
        pc.addTransceiver('video', { direction: 'recvonly' });
        // Optional: add audio if available
        // pc.addTransceiver('audio', { direction: 'recvonly' });

        pc.ontrack = (event) => {
          if (!isActive) return;
          if (videoRef.current) {
            videoRef.current.srcObject = event.streams[0];
            setIsWsConnecting(false);
          }
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        // MediaMTX WHEP Endpoint
        // Default to Jetson public IP if running on localhost
        let host = window.location.hostname;
        if (host === 'localhost' || host === '127.0.0.1') {
          host = '106.201.231.217';
        }
        const whepUrl = `http://${host}:8189/${encodeURIComponent(cameraId)}/whep`;

        const response = await fetch(whepUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/sdp'
          },
          body: pc.localDescription?.sdp
        });

        if (!response.ok) {
          throw new Error(`WHEP connection failed: ${response.statusText}`);
        }

        const answerSdp = await response.text();
        if (!isActive) return;

        await pc.setRemoteDescription(new RTCSessionDescription({
          type: 'answer',
          sdp: answerSdp
        }));

      } catch (err) {
        console.error(`WebRTC connection error for ${cameraId}:`, err);
        if (isActive) {
          setIsWsConnecting(true);
          // Auto-reconnect
          if (retryCount < 5) {
            const timeout = Math.min(1000 * Math.pow(2, retryCount), 10000);
            setTimeout(() => {
              if (isActive) setRetryCount(prev => prev + 1);
            }, timeout);
          }
        }
      }
    };

    connectWebRTC();

    return () => {
      isActive = false;
      if (pc) {
        pc.close();
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

  if (loading || (isWsConnecting && !hasFirstFrame)) {
    return (
      <div className="w-full h-full relative bg-black flex flex-col items-center justify-center p-4 animate-pulse">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <span className="text-foreground/50 font-mono text-xs tracking-widest uppercase">
          {loading ? "Initializing Stream" : "Connecting WebRTC..."}
        </span>
        
        {/* Hidden video element to capture the first frame behind the loader */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          onPlay={() => setHasFirstFrame(true)}
          className="absolute inset-0 w-full h-full object-cover opacity-0"
        />
      </div>
    )
  }

  return (
    <div className="w-full h-full relative bg-black flex items-center justify-center overflow-hidden">
      {/* Poster fallback */}
      {poster && !hasFirstFrame && (
        <img 
          ref={posterImgRef}
          src={poster} 
          className="absolute inset-0 w-full h-full object-cover opacity-30" 
          alt={`Poster for ${cameraId}`}
        />
      )}
      
      {/* Hardware-accelerated WebRTC video */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        onPlay={() => setHasFirstFrame(true)}
        className="w-full h-full object-cover"
      />
    </div>
  )
})

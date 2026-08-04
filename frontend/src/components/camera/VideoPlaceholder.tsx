import React, { memo, useEffect, useRef, useState } from 'react'

export interface VideoPlayerProps {
  cameraId: string
  poster?: string
  loading?: boolean
  error?: string
  streamUrl?: string
}

export const VideoPlayer = memo(({ cameraId, poster, loading, error }: VideoPlayerProps) => {
  const token = localStorage.getItem('access_token') || '';
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const posterImgRef = useRef<HTMLImageElement>(null);
  
  const [retryCount, setRetryCount] = useState(0);
  const [isWsConnecting, setIsWsConnecting] = useState(true);
  const [hasFirstFrame, setHasFirstFrame] = useState(false);

  useEffect(() => {
    if (loading || error) return;
    
    setIsWsConnecting(true);
    let ws: WebSocket | null = null;
    let isActive = true;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/video/${encodeURIComponent(cameraId)}?token=${encodeURIComponent(token)}`;
    
    ws = new WebSocket(wsUrl);
    ws.binaryType = 'blob';

    ws.onopen = () => {
      setIsWsConnecting(false);
      setRetryCount(0);
    };

    ws.onmessage = (event) => {
      if (!isActive) return;
      if (event.data instanceof Blob && canvasRef.current) {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d', { alpha: false }); // alpha false optimizes performance
        if (!ctx) return;
        
        createImageBitmap(event.data).then(bitmap => {
          if (!isActive) {
            bitmap.close();
            return;
          }
          
          if (!hasFirstFrame) {
            setHasFirstFrame(true);
          }
          
          // Match canvas resolution to video stream resolution
          if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
            canvas.width = bitmap.width;
            canvas.height = bitmap.height;
          }
          
          ctx.drawImage(bitmap, 0, 0);
          bitmap.close(); // Immediately release memory!
        }).catch(err => {
          console.error(`Error decoding video frame for ${cameraId}:`, err);
        });
      }
    };

    ws.onerror = (e) => {
      console.error(`Video WebSocket error for ${cameraId}:`, e);
    };

    ws.onclose = () => {
      setIsWsConnecting(true);
      
      // Auto-reconnect with exponential backoff if dropped
      if (retryCount < 5) {
        const timeout = Math.min(1000 * Math.pow(2, retryCount), 10000);
        setTimeout(() => {
          if (isActive) setRetryCount(prev => prev + 1);
        }, timeout);
      } else {
        if (posterImgRef.current && poster) {
          posterImgRef.current.style.opacity = '0.3';
          posterImgRef.current.style.display = 'block';
          if (canvasRef.current) canvasRef.current.style.display = 'none';
        }
      }
    };

    return () => {
      isActive = false;
      if (ws) {
        ws.close();
      }
    };
  }, [cameraId, token, retryCount, loading, error, poster]);

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
          {loading ? "Initializing Stream" : "Connecting Video WS..."}
        </span>
      </div>
    )
  }

  return (
    <div className="w-full h-full relative bg-black flex items-center justify-center overflow-hidden">
      {/* Poster fallback when WebSocket permanently fails */}
      {poster && (
        <img 
          ref={posterImgRef}
          src={poster} 
          className="absolute inset-0 w-full h-full object-cover" 
          style={{ display: 'none' }}
          alt={`Poster for ${cameraId}`}
        />
      )}
      
      {/* Hardware-accelerated canvas for 60fps JPEG rendering */}
      <canvas
        ref={canvasRef}
        className="w-full h-full object-cover"
        style={{ display: 'block' }}
      />
    </div>
  )
})

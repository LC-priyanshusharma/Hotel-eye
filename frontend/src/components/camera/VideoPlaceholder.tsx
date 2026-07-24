import React, { memo } from 'react'
import { VideoOff } from 'lucide-react'

export interface VideoPlayerProps {
  streamUrl?: string
  cameraId: string
  poster?: string
  loading?: boolean
  error?: boolean
}

export const VideoPlayer = memo(({ cameraId, poster, loading, error }: VideoPlayerProps) => {
  // Use relative path so the Vite proxy handles it and it works over Cloudflare Tunnel
  const streamEndpoint = `/video?camera_id=${encodeURIComponent(cameraId)}`

  if (error) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-black/90 text-muted-foreground gap-2">
        <VideoOff className="w-8 h-8 opacity-50" />
        <span className="text-sm font-medium">No Signal</span>
        <span className="text-xs opacity-50">{cameraId}</span>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-black/90">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const imgRef = React.useRef<HTMLImageElement>(null);

  React.useEffect(() => {
    return () => {
      if (imgRef.current) {
        // Aggressively clear the src so the browser kills the MJPEG stream socket
        // Freeing up the 6-connection limit per domain instantly!
        imgRef.current.src = "";
      }
    }
  }, []);

  return (
    <div className="w-full h-full relative bg-black">
      <img 
        ref={imgRef}
        src={streamEndpoint} 
        alt={`Live Feed ${cameraId}`} 
        className="w-full h-full object-cover"
        onError={(e) => {
          // If the stream is broken, show fallback
          (e.target as HTMLImageElement).src = poster || ''
          ;(e.target as HTMLImageElement).style.opacity = '0.3'
        }}
      />
    </div>
  )
})

VideoPlayer.displayName = 'VideoPlayer'

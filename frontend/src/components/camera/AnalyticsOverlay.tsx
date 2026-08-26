import React, { useEffect, useRef } from 'react';
import { useCameraStateStore } from '@/store/useCameraStateStore';

interface AnalyticsOverlayProps {
  cameraId: string;
}

const CLASS_COLORS: Record<number, string> = {
  0: '#10B981', // Person -> Emerald Green
  1: '#F59E0B', // Bicycle / PPE -> Amber
  2: '#3B82F6', // Car -> Blue
  3: '#8B5CF6', // Motorcycle -> Purple
  5: '#EC4899', // Bus -> Pink
  7: '#06B6D4', // Truck -> Cyan
};

const CLASS_NAMES: Record<number, string> = {
  0: 'Person',
  1: 'Bicycle',
  2: 'Car',
  3: 'Motorcycle',
  5: 'Bus',
  7: 'Truck',
};

export const AnalyticsOverlay: React.FC<AnalyticsOverlayProps> = ({ cameraId }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const telemetry = useCameraStateStore((state) => state.states[cameraId]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const parent = canvas.parentElement;
    if (!parent) return;

    const width = parent.clientWidth;
    const height = parent.clientHeight;

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    ctx.clearRect(0, 0, width, height);

    if (!telemetry) return;

    const detections = telemetry.detections || [];
    const events = telemetry.events || {};

    // 1. DeepStream stream coordinate space is normalized to 1280x720
    const vidW = 1280;
    const vidH = 720;

    // 2. Exact aspect-ratio viewport computation (Matches object-contain perfectly)
    const videoEl = parent.querySelector('video') as HTMLVideoElement | null;
    const rawAspect = (videoEl?.videoWidth && videoEl?.videoHeight)
      ? (videoEl.videoWidth / videoEl.videoHeight)
      : (vidW / vidH);

    const containerAspect = width / (height || 1);

    let renderW = width;
    let renderH = height;
    let offsetX = 0;
    let offsetY = 0;

    if (containerAspect > rawAspect) {
      // Container is wider -> Pillarbox (bars on left and right)
      renderW = height * rawAspect;
      renderH = height;
      offsetX = (width - renderW) / 2;
      offsetY = 0;
    } else {
      // Container is taller -> Letterbox (bars on top and bottom)
      renderW = width;
      renderH = width / rawAspect;
      offsetX = 0;
      offsetY = (height - renderH) / 2;
    }

    const scaleX = renderW / vidW;
    const scaleY = renderH / vidH;

    const mapX = (x: number) => offsetX + x * scaleX;
    const mapY = (y: number) => offsetY + y * scaleY;

    // 3. Render Plugin Custom Drawings ONLY for actively enabled plugins (Fixed coordinates)
    for (const [pluginName, pluginEvents] of Object.entries(events)) {
      if (!Array.isArray(pluginEvents) || pluginEvents.length === 0) continue;

      for (const evt of pluginEvents) {
        const drawings = evt?.metadata?.drawings || [];
        for (const d of drawings) {
          if (d.type === 'line' && d.coords && d.coords.length >= 2) {
            const [[x1, y1], [x2, y2]] = d.coords;
            const sx1 = mapX(x1);
            const sy1 = mapY(y1);
            const sx2 = mapX(x2);
            const sy2 = mapY(y2);

            ctx.save();
            ctx.shadowColor = `rgba(${d.color?.join(',') || '0,240,255'}, 0.8)`;
            ctx.shadowBlur = 6;
            ctx.beginPath();
            ctx.moveTo(sx1, sy1);
            ctx.lineTo(sx2, sy2);
            ctx.strokeStyle = `rgb(${d.color?.join(',') || '0,240,255'})`;
            ctx.lineWidth = (d.thickness || 2) + 0.5;
            ctx.stroke();
            ctx.restore();
          }
        }
      }
    }

    // 4. Render AI Object Bounding Boxes & Tracking IDs
    for (const det of detections) {
      const { bbox, class_id = 0, confidence = 1.0, track_id } = det;
      if (!bbox || bbox.length < 4) continue;

      let [x1, y1, x2, y2] = bbox;
      if (x2 < x1 || y2 < y1) {
        x2 = x1 + x2;
        y2 = y1 + y2;
      }

      const screenX = mapX(x1);
      const screenY = mapY(y1);
      const screenW = (x2 - x1) * scaleX;
      const screenH = (y2 - y1) * scaleY;

      if (screenW <= 0 || screenH <= 0) continue;

      const color = CLASS_COLORS[class_id] || '#10B981';
      const labelName = CLASS_NAMES[class_id] || 'Object';
      const displayConf = Math.min(100, Math.max(50, Math.round(confidence * 100)));
      const labelText = track_id !== undefined && track_id !== null
        ? `${labelName} #${track_id} ${displayConf}%`
        : `${labelName} ${displayConf}%`;

      // Bounding Box Rect
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(screenX, screenY, screenW, screenH);

      // Target Subtle Fill
      ctx.fillStyle = `${color}14`;
      ctx.fillRect(screenX, screenY, screenW, screenH);

      // Label Tag Background
      ctx.font = 'bold 11px Inter, sans-serif';
      const textMetrics = ctx.measureText(labelText);
      const tagHeight = 16;
      const tagWidth = textMetrics.width + 8;
      const tagY = Math.max(offsetY, screenY - tagHeight);

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(screenX, tagY, tagWidth, tagHeight, [3, 3, 0, 0]);
      ctx.fill();

      // Label Text
      ctx.fillStyle = '#000000';
      ctx.fillText(labelText, screenX + 4, tagY + 12);
    }
  }, [telemetry]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none z-10"
    />
  );
};

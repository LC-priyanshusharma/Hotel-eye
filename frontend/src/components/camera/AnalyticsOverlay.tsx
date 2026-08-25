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

    // 1. Determine reference stream coordinate system (Detect 9:16 portrait vs 16:9 landscape)
    let refW = 1280;
    let refH = 720;

    let maxX = 0;
    let maxY = 0;
    for (const d of detections) {
      if (d.bbox && d.bbox.length >= 4) {
        maxX = Math.max(maxX, d.bbox[0], d.bbox[2]);
        maxY = Math.max(maxY, d.bbox[1], d.bbox[3]);
      }
    }

    // Inspect plugin drawings coordinates as well
    for (const [_, pluginEvents] of Object.entries(events)) {
      if (Array.isArray(pluginEvents)) {
        for (const evt of pluginEvents) {
          for (const d of evt?.metadata?.drawings || []) {
            if (d.coords) {
              for (const pt of d.coords) {
                if (Array.isArray(pt) && pt.length >= 2) {
                  maxX = Math.max(maxX, pt[0]);
                  maxY = Math.max(maxY, pt[1]);
                }
              }
            }
          }
        }
      }
    }

    if (maxY > maxX && maxY > 800) {
      // Portrait 9:16 vertical video (e.g. 464x832, 1080x1920, 720x1280)
      refW = maxX > 700 ? 1080 : 464;
      refH = maxY > 1200 ? 1920 : 832;
    } else if (maxX > 1300 || maxY > 750) {
      refW = 1920;
      refH = 1080;
    } else {
      refW = 1280;
      refH = 720;
    }

    // 2. Exact aspect-ratio viewport computation (Accounts for video object-contain pillarbox/letterbox)
    const videoAspect = refW / refH;
    const containerAspect = width / (height || 1);

    let renderW = width;
    let renderH = height;
    let offsetX = 0;
    let offsetY = 0;

    if (containerAspect > videoAspect) {
      // Container is wider -> Pillarbox (bars on left and right)
      renderW = height * videoAspect;
      renderH = height;
      offsetX = (width - renderW) / 2;
      offsetY = 0;
    } else {
      // Container is taller -> Letterbox (bars on top and bottom)
      renderW = width;
      renderH = width / videoAspect;
      offsetX = 0;
      offsetY = (height - renderH) / 2;
    }

    const scaleX = renderW / refW;
    const scaleY = renderH / refH;

    const mapX = (x: number) => offsetX + x * scaleX;
    const mapY = (y: number) => offsetY + y * scaleY;

    // 3. Render Plugin Custom Drawings ONLY for actively enabled plugins in events
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

            // Glow shadow
            ctx.save();
            ctx.shadowColor = `rgba(${d.color?.join(',') || '255,255,0'}, 0.8)`;
            ctx.shadowBlur = 8;
            ctx.beginPath();
            ctx.moveTo(sx1, sy1);
            ctx.lineTo(sx2, sy2);
            ctx.strokeStyle = `rgb(${d.color?.join(',') || '255,255,0'})`;
            ctx.lineWidth = (d.thickness || 2) + 1;
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

      // Skip invalid / off-canvas boxes
      if (screenW <= 0 || screenH <= 0) continue;

      const color = CLASS_COLORS[class_id] || '#10B981';
      const labelName = CLASS_NAMES[class_id] || 'Object';
      const labelText = track_id !== undefined && track_id !== null
        ? `${labelName} #${track_id} ${(confidence * 100).toFixed(0)}%`
        : `${labelName} ${(confidence * 100).toFixed(0)}%`;

      // Bounding Box Rect
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.strokeRect(screenX, screenY, screenW, screenH);

      // Target Glow Fill
      ctx.fillStyle = `${color}18`;
      ctx.fillRect(screenX, screenY, screenW, screenH);

      // Label Tag Background
      ctx.font = 'bold 11px Inter, sans-serif';
      const textMetrics = ctx.measureText(labelText);
      const tagHeight = 18;
      const tagWidth = textMetrics.width + 10;
      const tagY = Math.max(offsetY, screenY - tagHeight);

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(screenX, tagY, tagWidth, tagHeight, [4, 4, 0, 0]);
      ctx.fill();

      // Label Text
      ctx.fillStyle = '#000000';
      ctx.fillText(labelText, screenX + 5, tagY + 13);
    }
  }, [telemetry]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none z-10"
    />
  );
};

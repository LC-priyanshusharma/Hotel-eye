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

    let animFrameId: number;

    const render = () => {
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

      // Estimate reference coordinate space (standard DeepStream / YOLO stream is 1280x720 or 1920x1080)
      let refW = 1280;
      let refH = 720;

      // Detect if coordinates are in 1080p, 720p, or portrait 832x464
      for (const d of detections) {
        if (d.bbox && d.bbox.length >= 4) {
          if (d.bbox[2] > refW || d.bbox[0] > refW) refW = 1920;
          if (d.bbox[3] > refH || d.bbox[1] > refH) refH = 1080;
        }
      }

      const scaleX = width / refW;
      const scaleY = height / refH;

      // 1. Render Plugin Custom Drawings (e.g. Lines, ROI polygons, Door crossings)
      for (const [_, pluginEvents] of Object.entries(events)) {
        if (Array.isArray(pluginEvents)) {
          for (const evt of pluginEvents) {
            const drawings = evt?.metadata?.drawings || [];
            for (const d of drawings) {
              if (d.type === 'line' && d.coords && d.coords.length >= 2) {
                const [[x1, y1], [x2, y2]] = d.coords;
                ctx.beginPath();
                ctx.moveTo(x1 * scaleX, y1 * scaleY);
                ctx.lineTo(x2 * scaleX, y2 * scaleY);
                ctx.strokeStyle = `rgb(${d.color?.join(',') || '255,255,0'})`;
                ctx.lineWidth = (d.thickness || 3);
                ctx.stroke();
              } else if (d.type === 'text' && d.coords && d.text) {
                const [tx, ty] = d.coords;
                ctx.font = 'bold 12px monospace';
                ctx.fillStyle = `rgb(${d.color?.join(',') || '255,255,255'})`;
                ctx.fillText(d.text, tx * scaleX, ty * scaleY);
              }
            }
          }
        }
      }

      // 2. Render AI Object Bounding Boxes & Tracking IDs
      for (const det of detections) {
        const { bbox, class_id = 0, confidence = 1.0, track_id } = det;
        if (!bbox || bbox.length < 4) continue;

        let [x1, y1, x2, y2] = bbox;
        // Check if bbox is [x, y, w, h] vs [x1, y1, x2, y2]
        if (x2 < x1 || y2 < y1) {
          x2 = x1 + x2;
          y2 = y1 + y2;
        }

        const screenX = x1 * scaleX;
        const screenY = y1 * scaleY;
        const screenW = (x2 - x1) * scaleX;
        const screenH = (y2 - y1) * scaleY;

        const color = CLASS_COLORS[class_id] || '#10B981';
        const labelName = CLASS_NAMES[class_id] || 'Object';
        const labelText = track_id !== undefined && track_id !== null
          ? `${labelName} #${track_id} ${(confidence * 100).toFixed(0)}%`
          : `${labelName} ${(confidence * 100).toFixed(0)}%`;

        // Bounding Box Rect
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.strokeRect(screenX, screenY, screenW, screenH);

        // Semi-transparent target glow fill
        ctx.fillStyle = `${color}18`;
        ctx.fillRect(screenX, screenY, screenW, screenH);

        // Label Tag Background
        ctx.font = 'bold 11px Inter, sans-serif';
        const textMetrics = ctx.measureText(labelText);
        const tagHeight = 18;
        const tagWidth = textMetrics.width + 10;
        const tagY = Math.max(0, screenY - tagHeight);

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.roundRect(screenX, tagY, tagWidth, tagHeight, [4, 4, 0, 0]);
        ctx.fill();

        // Label Text
        ctx.fillStyle = '#000000';
        ctx.fillText(labelText, screenX + 5, tagY + 13);
      }
    };

    render();
  }, [telemetry]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none z-10"
    />
  );
};

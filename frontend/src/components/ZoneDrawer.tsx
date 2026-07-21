import React, { useState, useRef, useEffect } from 'react';
import { Trash2, CheckCircle2, RotateCcw } from 'lucide-react';

interface Point {
  x: number;
  y: number;
}

interface ZoneDrawerProps {
  streamUrl: string;
  points: Point[];
  onChange: (points: Point[]) => void;
  title: string;
  nativeWidth?: number;
  nativeHeight?: number;
}

export function ZoneDrawer({ streamUrl, points, onChange, title, nativeWidth = 1920, nativeHeight = 1080 }: ZoneDrawerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [localPoints, setLocalPoints] = useState<Point[]>(points || []);

  // Update local if props change (unless user is currently editing)
  useEffect(() => {
    setLocalPoints(points || []);
  }, [points]);

  const handleImageClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Convert to native coordinates
    const scaleX = nativeWidth / rect.width;
    const scaleY = nativeHeight / rect.height;
    
    const nativeX = Math.round(x * scaleX);
    const nativeY = Math.round(y * scaleY);
    
    setLocalPoints([...localPoints, { x: nativeX, y: nativeY }]);
  };

  const handleClear = () => {
    setLocalPoints([]);
    onChange([]);
  };

  const handleSave = () => {
    onChange(localPoints);
  };

  const handleUndo = () => {
    setLocalPoints(localPoints.slice(0, -1));
  };

  // Convert native points to container coordinates for SVG rendering
  const renderPoints = () => {
    if (!containerRef.current) return [];
    const rect = containerRef.current.getBoundingClientRect();
    
    if (rect.width === 0) return []; // not mounted fully
    
    const scaleX = rect.width / nativeWidth;
    const scaleY = rect.height / nativeHeight;
    
    return localPoints.map(p => ({
      x: p.x * scaleX,
      y: p.y * scaleY
    }));
  };

  const svgPoints = renderPoints();
  const polyString = svgPoints.map(p => `${p.x},${p.y}`).join(' ');

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-white">{title}</h3>
        <div className="flex gap-2">
          <button onClick={handleUndo} disabled={localPoints.length === 0} className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded text-xs flex items-center gap-1 transition-colors disabled:opacity-50">
            <RotateCcw className="w-3 h-3" /> Undo
          </button>
          <button onClick={handleClear} disabled={localPoints.length === 0} className="px-3 py-1.5 bg-danger/20 hover:bg-danger/30 text-danger rounded text-xs flex items-center gap-1 transition-colors disabled:opacity-50">
            <Trash2 className="w-3 h-3" /> Clear
          </button>
          <button onClick={handleSave} className="px-3 py-1.5 bg-primary hover:bg-primary/90 text-primary-foreground rounded text-xs flex items-center gap-1 transition-colors">
            <CheckCircle2 className="w-3 h-3" /> Apply Area
          </button>
        </div>
      </div>
      
      <div 
        className="relative rounded-lg overflow-hidden border-2 border-white/10 bg-black/50 aspect-video group"
        ref={containerRef}
      >
        <img 
          src={streamUrl} 
          alt="Live Stream" 
          className="w-full h-full object-cover cursor-crosshair opacity-80 group-hover:opacity-100 transition-opacity"
          onClick={handleImageClick}
          draggable={false}
        />
        
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {svgPoints.length > 1 && (
            <polygon 
              points={polyString} 
              fill="rgba(59, 130, 246, 0.3)" 
              stroke="rgba(59, 130, 246, 0.8)" 
              strokeWidth="2"
              strokeDasharray={svgPoints.length > 2 ? "none" : "5,5"}
            />
          )}
          {svgPoints.map((p, i) => (
            <circle 
              key={i} 
              cx={p.x} 
              cy={p.y} 
              r="4" 
              fill="white" 
              stroke="rgba(59, 130, 246, 1)" 
              strokeWidth="2" 
            />
          ))}
          {/* Draw closing dashed line if we have at least 3 points */}
          {svgPoints.length > 2 && (
            <line 
              x1={svgPoints[svgPoints.length - 1].x} 
              y1={svgPoints[svgPoints.length - 1].y} 
              x2={svgPoints[0].x} 
              y2={svgPoints[0].y} 
              stroke="rgba(59, 130, 246, 0.5)" 
              strokeWidth="2" 
              strokeDasharray="5,5" 
            />
          )}
        </svg>
      </div>
      <p className="text-xs text-muted-foreground">
        Click on the video to add boundary points. Apply to update the configuration. (Native resolution: {nativeWidth}x{nativeHeight})
      </p>
    </div>
  );
}

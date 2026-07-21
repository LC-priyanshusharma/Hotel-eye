import { create } from 'zustand'

interface CameraState {
  timestamp: number
  events: any
  fps: number
}

interface CameraStateStore {
  states: Record<string, CameraState>
  isConnected: boolean
  connect: () => void
  disconnect: () => void
}

let ws: WebSocket | null = null;

export const useCameraStateStore = create<CameraStateStore>((set, get) => ({
  states: {},
  isConnected: false,
  connect: () => {
    if (ws) return;
    
    console.log("Connecting to WebSocket...");
    ws = new WebSocket('ws://localhost:8000/ws/events');
    
    ws.onopen = () => {
      console.log("WebSocket connected");
      set({ isConnected: true });
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        set({ states: data });
      } catch (e) {
        console.error("Failed to parse websocket message", e);
      }
    };
    
    ws.onclose = () => {
      console.log("WebSocket disconnected");
      set({ isConnected: false });
      ws = null;
      // Try to reconnect after 3 seconds
      setTimeout(() => get().connect(), 3000);
    };
    
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  },
  disconnect: () => {
    if (ws) {
      ws.close();
      ws = null;
    }
  }
}))

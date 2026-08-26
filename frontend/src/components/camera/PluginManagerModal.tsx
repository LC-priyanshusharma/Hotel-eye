import { memo, useState, useEffect } from 'react'
import { X, Activity, Cpu, Zap, Box, Hash } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/api/api'
import { cn } from '@/utils/utils'
import { useCameraStateStore } from '@/store/useCameraStateStore'

const PLUGIN_METRICS: Record<string, any> = {
  "VisitorPlugin": { cost: "Medium", cpu: "8%", gpu: "15%", latency: "+20ms", mem: "100MB", version: "v2.0" },
  "PPEDetectionPlugin": { cost: "High", cpu: "15%", gpu: "30%", latency: "+35ms", mem: "180MB", version: "v1.5" },
  "FireDetectionPlugin": { cost: "Medium", cpu: "5%", gpu: "10%", latency: "+10ms", mem: "60MB", version: "v1.0" },
  "ANPRPlugin": { cost: "High", cpu: "12%", gpu: "25%", latency: "+40ms", mem: "150MB", version: "v2.1" },
  "ParkingAnalyticsPlugin": { cost: "Low", cpu: "3%", gpu: "5%", latency: "+5ms", mem: "20MB", version: "v1.0" },
  "IntrusionDetectionPlugin": { cost: "Medium", cpu: "6%", gpu: "10%", latency: "+12ms", mem: "45MB", version: "v1.4" },
  "PeopleCountingPlugin": { cost: "Low", cpu: "2%", gpu: "5%", latency: "+4ms", mem: "15MB", version: "v1.2" },
  "AttendanceDetectionPlugin": { cost: "Medium", cpu: "8%", gpu: "15%", latency: "+25ms", mem: "80MB", version: "v3.0" },
  "CartonCountingPlugin": { cost: "Low", cpu: "0.5%", gpu: "1%", latency: "+1ms", mem: "5MB", version: "v1.0" },
  "RestrictionZonePlugin": { cost: "Low", cpu: "1%", gpu: "2%", latency: "+2ms", mem: "10MB", version: "v1.0" },
};

export const PluginManagerModal = memo(({ cameraId, isOpen, onClose }: { cameraId: string, isOpen: boolean, onClose: () => void }) => {
  const [allowedPlugins, setAllowedPlugins] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen) return;
    setIsLoading(true);
    api.get(`/api/config?t=${Date.now()}`)
      .then(res => res.data)
      .then(data => {
        const plugins = data?.CAMERA_PLUGINS?.[cameraId];
        if (plugins && Array.isArray(plugins)) {
          setAllowedPlugins(plugins);
        } else {
          // By default all discovered plugins are running
          setAllowedPlugins(Object.keys(PLUGIN_METRICS));
        }
      })
      .catch(err => {
        console.error("Failed to fetch config plugins:", err);
        setAllowedPlugins(Object.keys(PLUGIN_METRICS));
      })
      .finally(() => setIsLoading(false));
  }, [cameraId, isOpen]);

  const togglePlugin = (pluginName: string) => {
    let newPlugins = [...allowedPlugins];
    if (newPlugins.includes(pluginName)) {
      newPlugins = newPlugins.filter(p => p !== pluginName);
    } else {
      newPlugins.push(pluginName);
    }
    
    setAllowedPlugins(newPlugins);
    
    // Instant 0ms visual update in local Zustand store
    useCameraStateStore.getState().setCameraPlugins(cameraId, newPlugins);

    api.post('/api/config', {
      updates: { CAMERA_PLUGINS: { [cameraId]: newPlugins } }
    }).catch(err => {
      console.error("Failed to persist plugin update:", err);
    });
  };

  if (!isOpen) return null;

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-background/60 backdrop-blur-sm" onClick={onClose}>
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        onClick={e => e.stopPropagation()}
        className="w-full max-w-2xl bg-slate-900/95 border border-foreground/10 shadow-2xl rounded-2xl overflow-hidden flex flex-col max-h-[90%]"
      >
        <div className="p-4 border-b border-foreground/10 flex justify-between items-center bg-background/40">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" />
              Dynamic Plugin Manager
            </h2>
            <p className="text-xs text-foreground/50">Hot-swap AI models without interrupting streams</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-foreground/10 rounded-full transition-colors text-foreground/70">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="overflow-y-auto p-4 flex flex-col gap-3">
          {Object.entries(PLUGIN_METRICS).map(([plugin, metrics]) => {
            const active = allowedPlugins.includes(plugin);
            const displayName = plugin.replace('Plugin', '');
            
            return (
              <div key={plugin} className={cn(
                "p-3 rounded-xl border transition-all duration-300 flex flex-col gap-3",
                active ? "bg-primary/5 border-primary/30" : "bg-background/40 border-foreground/5 opacity-60 hover:opacity-100"
              )}>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    {/* iOS style toggle */}
                    <button 
                      onClick={() => togglePlugin(plugin)}
                      className={cn(
                        "w-10 h-5 rounded-full relative transition-colors duration-300 ease-in-out",
                        active ? "bg-primary" : "bg-foreground/20"
                      )}
                    >
                      <div className={cn(
                        "w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform duration-300 ease-in-out shadow-sm",
                        active ? "translate-x-5" : "translate-x-0.5"
                      )} />
                    </button>
                    <div>
                      <div className="text-sm font-bold text-white flex items-center gap-2">
                        {displayName}
                        {active ? (
                          <span className="px-1.5 py-0.5 rounded text-[9px] bg-success/20 text-success uppercase tracking-widest font-bold">Running</span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded text-[9px] bg-foreground/10 text-foreground/50 uppercase tracking-widest font-bold">Stopped</span>
                        )}
                      </div>
                      <div className="text-xs text-foreground/50">{metrics.version}</div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4 text-xs font-mono">
                    <div className="flex flex-col items-end">
                      <span className="text-foreground/40 text-[9px] tracking-widest uppercase">Cost</span>
                      <span className={cn(
                        metrics.cost === "High" ? "text-danger" : metrics.cost === "Medium" ? "text-warning" : "text-success"
                      )}>{metrics.cost}</span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-2 border-t border-foreground/5 pt-3 mt-1">
                  <div className="flex items-center gap-2 text-foreground/70">
                    <Cpu className="w-3.5 h-3.5 text-foreground/40" />
                    <span className="text-[10px]">{metrics.cpu}</span>
                  </div>
                  <div className="flex items-center gap-2 text-foreground/70">
                    <Box className="w-3.5 h-3.5 text-foreground/40" />
                    <span className="text-[10px]">{metrics.gpu}</span>
                  </div>
                  <div className="flex items-center gap-2 text-foreground/70">
                    <Activity className="w-3.5 h-3.5 text-foreground/40" />
                    <span className="text-[10px]">{metrics.latency}</span>
                  </div>
                  <div className="flex items-center gap-2 text-foreground/70">
                    <Hash className="w-3.5 h-3.5 text-foreground/40" />
                    <span className="text-[10px]">{metrics.mem}</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </motion.div>
    </div>
  );
});
PluginManagerModal.displayName = 'PluginManagerModal';

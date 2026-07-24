import React, { useState, useRef, useCallback } from 'react';
import { Camera, Check, RefreshCcw, ChevronRight, CheckCircle2 } from 'lucide-react';
import axios from 'axios';

export const VisitorRegistration = () => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({ name: '', email: '' });
  const [photos, setPhotos] = useState({ front: '', left: '', right: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const searchParams = new URLSearchParams(window.location.search);
  const roleParam = searchParams.get('role');
  const role = roleParam && roleParam.toLowerCase() === 'employee' ? 'EMPLOYEE' : 'VISITOR';
  
  const [isSuccess, setIsSuccess] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 640 } } 
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error("Error accessing camera:", err);
      alert("Please allow camera access to register.");
    }
  }, []);

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
      tracks.forEach(track => track.stop());
    }
  };

  const capturePhoto = (angle: 'front' | 'left' | 'right') => {
    if (videoRef.current && canvasRef.current) {
      const context = canvasRef.current.getContext('2d');
      if (context) {
        canvasRef.current.width = videoRef.current.videoWidth;
        canvasRef.current.height = videoRef.current.videoHeight;
        context.drawImage(videoRef.current, 0, 0);
        const base64 = canvasRef.current.toDataURL('image/jpeg');
        setPhotos(prev => ({ ...prev, [angle]: base64 }));
      }
    }
  };

  const submitRegistration = async () => {
    setIsSubmitting(true);
    try {
      // NOTE: Uses relative path to rely on proxy, or full path if needed.
      // But since they might access this via a public cloudflare URL, using relative is safer
      // Wait, API is on port 8000 and Cloudflare tunnel will expose frontend on 5173.
      // Wait! If cloudflared exposes 5173, the API request to localhost:8000 will fail on their phone!
      // I should configure vite proxy to forward /api to 8000.
      await axios.post('/api/plugins/visitor/register', {
        name: formData.name,
        email: formData.email,
        role: role,
        photo_front: photos.front,
        photo_left: photos.left,
        photo_right: photos.right
      });
      setIsSuccess(true);
      stopCamera();
    } catch (error) {
      console.error("Registration failed:", error);
      alert("Failed to register. Make sure your face is visible in all 3 photos.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-6 text-center">
        <div className="bg-gradient-to-br from-indigo-500/20 to-purple-600/20 p-8 rounded-full mb-8 shadow-[0_0_50px_rgba(99,102,241,0.3)]">
          <CheckCircle2 className="w-24 h-24 text-indigo-400" />
        </div>
        <h1 className="text-4xl font-extrabold text-white mb-4 bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">Registration Complete!</h1>
        <p className="text-zinc-400 text-lg max-w-sm">
          You can now proceed to the entrance. The LogicEye cameras will recognize you automatically.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white flex flex-col max-w-md mx-auto relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/30 blur-[100px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/30 blur-[100px] rounded-full pointer-events-none" />

      <div className="p-8 z-10 flex-1 flex flex-col">
        <div className="mb-10 text-center">
          <h1 className="text-3xl font-extrabold mb-2 tracking-tight">Welcome to LogicEye</h1>
          <p className="text-zinc-400 font-medium">
            {role === 'EMPLOYEE' ? 'Employee Self-Registration' : 'Visitor Self-Registration'}
          </p>
        </div>

        {step === 1 && (
          <div className="space-y-6 flex-1 flex flex-col justify-center">
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 p-6 rounded-3xl shadow-xl">
              <div className="mb-6">
                <label className="block text-sm font-semibold mb-2 text-indigo-200">Full Name</label>
                <input 
                  type="text" 
                  className="w-full bg-black/50 border border-white/10 rounded-2xl px-5 py-4 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 transition-all text-white placeholder-white/30"
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. John Doe"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold mb-2 text-indigo-200">Email Address (Optional)</label>
                <input 
                  type="email" 
                  className="w-full bg-black/50 border border-white/10 rounded-2xl px-5 py-4 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 transition-all text-white placeholder-white/30"
                  value={formData.email}
                  onChange={e => setFormData({ ...formData, email: e.target.value })}
                  placeholder="john@example.com"
                />
              </div>
            </div>
            <button 
              disabled={!formData.name}
              onClick={() => { setStep(2); startCamera(); }}
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white py-4 rounded-2xl font-bold flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 transition-all active:scale-[0.98]"
            >
              Continue to Face Scan <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        )}

        {[2, 3, 4].includes(step) && (
          <div className="flex flex-col items-center flex-1 justify-center">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-2">Face Capture</h2>
              <p className="text-indigo-300">Step {step - 1} of 3</p>
            </div>
            
            <div className="relative w-full aspect-square bg-black/50 rounded-full overflow-hidden mb-8 border-4 border-indigo-500/50 shadow-[0_0_30px_rgba(99,102,241,0.2)]">
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted 
                className="w-full h-full object-cover transform scale-x-[-1]" 
              />
              <canvas ref={canvasRef} className="hidden" />
              
              <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-end pb-8">
                <span className="bg-black/70 backdrop-blur-md px-6 py-3 rounded-full text-sm font-bold text-white shadow-xl border border-white/10">
                  {step === 2 && "Look Straight Ahead"}
                  {step === 3 && "Turn Head Slightly Left"}
                  {step === 4 && "Turn Head Slightly Right"}
                </span>
              </div>
            </div>

            <button 
              onClick={() => {
                if (step === 2) capturePhoto('front');
                if (step === 3) capturePhoto('left');
                if (step === 4) capturePhoto('right');
                
                if (step < 4) {
                  setStep(step + 1);
                } else {
                  submitRegistration();
                }
              }}
              disabled={isSubmitting}
              className="w-20 h-20 bg-white text-indigo-600 rounded-full flex items-center justify-center active:scale-95 transition-all shadow-[0_0_30px_rgba(255,255,255,0.3)] hover:scale-105"
            >
              {isSubmitting ? (
                <RefreshCcw className="w-8 h-8 animate-spin" />
              ) : (
                <Camera className="w-8 h-8" />
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default VisitorRegistration;

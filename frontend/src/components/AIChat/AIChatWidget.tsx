import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Mic, MicOff, Volume2, VolumeX, Activity, AlertCircle, Fingerprint } from 'lucide-react';
import { api } from '../../api/api';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/utils/utils';

interface Message {
  text: string;
  isBot: boolean;
  isPartial?: boolean;
  isError?: boolean;
}

type VoiceState = "IDLE" | "LISTENING" | "TRANSCRIBING" | "WAITING_FOR_RESPONSE" | "SPEAKING" | "ERROR";

const AIChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { text: "Hello! I'm LogicEye AI. How can I help you analyze the camera data today?", isBot: true }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // FSM Voice State
  const [voiceState, setVoiceState] = useState<VoiceState>("IDLE");
  const [speakerEnabled, setSpeakerEnabled] = useState(true);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, voiceState]);

  useEffect(() => {
    // Initialize Web Speech API
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';
      
      recognition.onstart = () => {
        transitionTo("LISTENING");
      };
      
      recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        
        if (finalTranscript) {
          setInput(finalTranscript);
        } else if (interimTranscript) {
          setInput(interimTranscript);
        }
      };
      
      recognition.onerror = (event: any) => {
        console.error("Speech Recognition Error:", event.error);
        if (event.error !== 'aborted') {
          transitionTo("ERROR", `Microphone error: ${event.error}`);
        }
      };
      
      recognition.onend = () => {
        if (voiceState === "LISTENING") {
           // If it ends naturally, send the message
           transitionTo("IDLE");
           if (input.trim()) {
              // We need to use a ref or pass the current input. 
              // To avoid stale closures, we'll trigger a custom event or just let the user press send.
              // For a better experience, we can auto-send if there's final text.
           }
        } else {
           transitionTo("IDLE");
        }
      };
      
      recognitionRef.current = recognition;
    }
    
    return () => {
      forceCleanup();
    };
  }, []);

  const transitionTo = (newState: VoiceState, errorMsg?: string) => {
    setVoiceState(newState);
    
    if (errorMsg) {
      setMessages(prev => [...prev, { text: `[System]: ${errorMsg}`, isBot: true, isError: true }]);
    }
    
    if (newState === "IDLE" || newState === "ERROR") {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
      setIsLoading(false);
    }
  };

  const forceCleanup = () => {
    transitionTo("IDLE");
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  };

  const playTTS = (text: string) => {
    if (!speakerEnabled || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    
    utterance.onstart = () => transitionTo("SPEAKING");
    utterance.onend = () => transitionTo("IDLE");
    utterance.onerror = () => transitionTo("IDLE");
    
    window.speechSynthesis.speak(utterance);
  };

  const toggleListening = () => {
    if (!recognitionRef.current) {
      transitionTo("ERROR", "Web Speech API is not supported in this browser.");
      return;
    }
    
    if (voiceState === "LISTENING") {
      recognitionRef.current.stop();
      transitionTo("IDLE");
      if (input.trim()) {
         handleSend(input);
      }
    } else {
      setInput(''); // Clear input before starting
      try {
        recognitionRef.current.start();
      } catch (e) {
        console.error(e);
      }
    }
  };

  const handleSend = async (textToSend?: string) => {
    const messageText = typeof textToSend === 'string' ? textToSend.trim() : input.trim();
    if (!messageText) return;

    setMessages(prev => [...prev, { text: messageText, isBot: false }]);
    setInput('');
    setIsLoading(true);
    transitionTo("WAITING_FOR_RESPONSE");

    try {
      const res = await api.post('/api/chat', { message: messageText, camera_id: "global" });
      const botResponse = res.data.response;
      setMessages(prev => [...prev, { text: botResponse, isBot: true }]);
      
      if (speakerEnabled) {
        playTTS(botResponse);
      } else {
        transitionTo("IDLE");
      }
    } catch (error: any) {
      setMessages(prev => [...prev, { text: "The AI service is temporarily unavailable. Please try again later.", isBot: true, isError: true }]);
      transitionTo("ERROR");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  const getStatusBadge = () => {
    switch (voiceState) {
      case "LISTENING":
        return <><Activity size={14} className="animate-pulse" /> Listening (Web Speech API)...</>;
      case "TRANSCRIBING":
      case "WAITING_FOR_RESPONSE":
        return <><div className="animate-spin h-3 w-3 border-2 border-blue-500 rounded-full border-t-transparent"></div> Processing...</>;
      case "SPEAKING":
        return <><Volume2 size={14} className="animate-bounce" /> Speaking...</>;
      case "ERROR":
        return <><AlertCircle size={14} className="text-red-500" /> <span className="text-red-500">Error Occurred</span></>;
      default:
        return null;
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 font-sans">
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="glass-pro rounded-3xl shadow-[0_0_50px_rgba(0,112,243,0.15)] w-80 sm:w-96 flex flex-col overflow-hidden h-[600px] mb-4 border border-white/10"
          >
            <div className="p-5 border-b border-white/10 bg-black/40 flex justify-between items-center relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-primary/20 rounded-full blur-[40px] -mr-10 -mt-10 pointer-events-none" />
              <div className="flex items-center gap-3 relative z-10">
                <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/50 flex items-center justify-center shadow-[0_0_15px_rgba(0,112,243,0.3)]">
                  <Fingerprint className="text-primary w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-black text-sm text-white tracking-wide">LogicEye Core</h3>
                  <span className="text-[10px] text-success font-bold tracking-widest uppercase flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse glow-success" /> Online
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 relative z-10">
                <button onClick={() => setSpeakerEnabled(!speakerEnabled)} className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors border border-white/10 text-muted-foreground hover:text-white" title="Toggle Voice Response">
                  {speakerEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
                </button>
                <button onClick={() => setIsOpen(false)} className="p-2 bg-white/5 hover:bg-danger/20 hover:text-danger hover:border-danger/30 rounded-lg transition-colors border border-white/10 text-muted-foreground">
                  <X size={16} />
                </button>
              </div>
            </div>


            <div className="flex-1 p-5 overflow-y-auto custom-scrollbar flex flex-col gap-4 relative">
              <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
              
              {messages.map((msg, idx) => (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={idx} 
                  className={`flex ${msg.isBot ? 'justify-start' : 'justify-end'} relative z-10`}
                >
                  {msg.isBot && (
                    <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/50 flex items-center justify-center shrink-0 mr-2 mt-auto mb-1">
                      <Fingerprint className="w-3 h-3 text-primary" />
                    </div>
                  )}
                  <div className={cn(
                    "max-w-[80%] rounded-2xl p-3 text-sm shadow-md",
                    msg.isBot 
                      ? (msg.isError ? 'bg-danger/10 text-danger border border-danger/30 rounded-bl-sm' : 'glass-panel border-white/10 text-white/90 rounded-bl-sm')
                      : 'bg-primary text-white rounded-br-sm glow-primary',
                    msg.isPartial ? 'opacity-70 italic' : ''
                  )}>
                    {msg.text}
                  </div>
                </motion.div>
              ))}
              
              {(isLoading || voiceState === "WAITING_FOR_RESPONSE") && (
                <div className="flex justify-start relative z-10">
                  <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/50 flex items-center justify-center shrink-0 mr-2 mt-auto mb-1">
                    <Fingerprint className="w-3 h-3 text-primary animate-pulse" />
                  </div>
                  <div className="glass-panel border-white/10 text-white rounded-2xl rounded-bl-sm p-4 text-sm flex gap-1.5 items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"></span>
                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce delay-75"></span>
                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce delay-150"></span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

          {voiceState !== "IDLE" && (
            <div className="bg-black/60 border-t border-white/5 px-4 py-2 flex items-center gap-3 justify-center text-[10px] font-bold tracking-widest uppercase text-primary glow-primary">
               {getStatusBadge()}
            </div>
          )}

          <div className="p-4 bg-black/40 border-t border-white/10 backdrop-blur-md">
            <div className="relative flex items-center gap-3">
              <button 
                onClick={toggleListening}
                className={cn(
                  "p-3 rounded-xl transition-all duration-300 shadow-lg flex shrink-0 items-center justify-center",
                  voiceState === "LISTENING" || voiceState === "TRANSCRIBING"
                  ? 'bg-danger/20 text-danger border border-danger/50 glow-danger animate-pulse' 
                  : 'bg-white/5 text-muted-foreground border border-white/10 hover:bg-white/10 hover:text-white'
                )}
                title={voiceState === "LISTENING" ? "Stop Listening" : "Start Voice Mode"}
              >
                {voiceState === "LISTENING" || voiceState === "TRANSCRIBING" ? <MicOff size={18} /> : <Mic size={18} />}
              </button>
              
              <div className="relative flex-1">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Query LogicEye Core..."
                  disabled={voiceState !== "IDLE" && voiceState !== "ERROR"}
                  className="w-full bg-black/50 text-white border border-white/10 rounded-xl pl-4 pr-12 py-3 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 disabled:opacity-50 transition-all placeholder-white/30"
                />
                <button 
                  onClick={() => handleSend()}
                  disabled={!input.trim() || isLoading || (voiceState !== "IDLE" && voiceState !== "ERROR")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 bg-primary text-white p-1.5 rounded-lg hover:bg-primary/80 disabled:bg-white/5 disabled:text-white/20 transition-all"
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </div>
        </motion.div>
        )}
      </AnimatePresence>
      
      {!isOpen && (
        <motion.button 
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setIsOpen(true)}
          className="bg-primary text-white p-4 rounded-full shadow-[0_0_30px_rgba(0,112,243,0.4)] flex items-center justify-center group relative border border-primary/50"
        >
          <Fingerprint size={24} className="group-hover:animate-pulse" />
          <span className="absolute -top-1 -right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
            <span className="relative inline-flex rounded-full h-4 w-4 bg-accent border-2 border-background"></span>
          </span>
        </motion.button>
      )}
    </div>
  );
};

export default AIChatWidget;

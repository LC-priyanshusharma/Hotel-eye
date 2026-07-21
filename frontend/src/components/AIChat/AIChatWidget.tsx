import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send } from 'lucide-react';
import { api } from '../../api/api';

interface Message {
  text: string;
  isBot: boolean;
}

const AIChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { text: "Hello! I'm LogicEye AI. How can I help you analyze the camera data today?", isBot: true }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { text: userMsg, isBot: false }]);
    setInput('');
    setIsLoading(true);

    try {
      // Send request to the backend LangGraph endpoint
      const res = await api.post('/api/chat', { message: userMsg, camera_id: "global" });
      const botResponse = res.data.response;
      setMessages(prev => [...prev, { text: botResponse, isBot: true }]);
    } catch (error: any) {
      console.error("Chat error:", error);
      
      let errorMsg = "Sorry, I encountered an error communicating with the server.";
      if (error.response) {
        errorMsg += ` Server responded with status ${error.response.status}. ${error.response.data?.detail || ''}`;
      } else if (error.message) {
        errorMsg += ` ${error.message}`;
      }
      
      setMessages(prev => [...prev, { text: errorMsg, isBot: true }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {isOpen ? (
        <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-2xl w-80 sm:w-96 flex flex-col overflow-hidden transition-all duration-300 ease-in-out h-[500px]">
          {/* Header */}
          <div className="bg-blue-600 p-4 flex justify-between items-center text-white">
            <div className="flex items-center gap-2">
              <MessageSquare size={20} />
              <h3 className="font-semibold text-sm">LogicEye AI Assistant</h3>
            </div>
            <button onClick={() => setIsOpen(false)} className="hover:text-gray-200 transition-colors">
              <X size={20} />
            </button>
          </div>

          {/* Chat Body */}
          <div className="flex-1 p-4 overflow-y-auto bg-slate-900/50 space-y-4">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.isBot ? 'justify-start' : 'justify-end'}`}>
                <div className={`max-w-[85%] rounded-xl p-3 text-sm ${
                  msg.isBot 
                    ? 'bg-slate-700 text-slate-100 rounded-tl-none' 
                    : 'bg-blue-600 text-white rounded-tr-none'
                }`}>
                  {msg.text}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-700 text-slate-100 rounded-xl rounded-tl-none p-3 text-sm flex gap-1">
                  <span className="animate-bounce">●</span>
                  <span className="animate-bounce delay-100">●</span>
                  <span className="animate-bounce delay-200">●</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-3 bg-slate-800 border-t border-slate-700">
            <div className="relative flex items-center">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask about camera events..."
                className="w-full bg-slate-900 text-slate-100 border border-slate-700 rounded-full pl-4 pr-10 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
              <button 
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="absolute right-2 text-blue-500 hover:text-blue-400 disabled:text-slate-500 p-1"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button 
          onClick={() => setIsOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-full shadow-xl transition-all duration-300 hover:scale-110 flex items-center justify-center group relative"
        >
          <MessageSquare size={24} />
          <span className="absolute -top-1 -right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
          </span>
        </button>
      )}
    </div>
  );
};

export default AIChatWidget;

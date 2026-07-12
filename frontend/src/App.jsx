import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send } from 'lucide-react';

export default function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [tenant, setTenant] = useState('Tenant_A');
  const [messages, setMessages] = useState([
    { role: 'system', text: 'Welcome to Cortex Copilot. Select your tenant and ask anything.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': tenant,
        },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'assistant', text: data.response }]);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        { role: 'system', text: `Error: ${error.message || 'Failed to connect to backend'}` }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9fa] relative overflow-hidden">
      {/* Dashboard / Main UI Content */}
      <div className="p-8">
        <h1 className="text-3xl font-bold text-slate-800">Cortex Copilot Dashboard</h1>
        <p className="text-slate-500 mt-2">Industrial Telemetry & Intelligence Gateway</p>
      </div>

      {/* Floating Trigger Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 bg-[#10b981] hover:bg-[#0d9488] text-white p-4 rounded-full shadow-lg transition-transform duration-200 active:scale-95 flex items-center justify-center z-50"
        >
          <MessageSquare className="w-6 h-6" />
        </button>
      )}

      {/* Sliding Sidebar Container */}
      <div
        className={`fixed top-0 right-0 h-full w-96 bg-white shadow-2xl flex flex-col transition-transform duration-300 z-50 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Sidebar Header */}
        <div className="bg-[#0f172a] text-white p-3 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-[#10b981]" />
            <select
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
              className="bg-[#1e293b] text-white border border-slate-700 rounded px-2 py-1 text-sm focus:outline-none focus:border-[#10b981]"
            >
              <option value="Tenant_A">Tenant A</option>
              <option value="Tenant_B">Tenant B</option>
            </select>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="hover:bg-slate-800 p-1 rounded text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Message List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3 flex flex-col">
          {messages.map((msg, index) => {
            let bubbleStyle = '';
            if (msg.role === 'user') {
              bubbleStyle = 'bg-slate-100 text-slate-800 self-end ml-auto';
            } else if (msg.role === 'system') {
              bubbleStyle = 'bg-yellow-50 border border-yellow-200 text-yellow-800 text-xs text-center mx-auto w-full';
            } else {
              bubbleStyle = 'bg-[#ecfdf5] border border-[#10b981] text-slate-800 self-start mr-auto';
            }

            return (
              <div
                key={index}
                className={`p-3 rounded-lg max-w-[85%] text-sm whitespace-pre-wrap ${bubbleStyle}`}
              >
                {msg.text}
              </div>
            );
          })}
          {isLoading && (
            <div className="bg-[#ecfdf5] border border-[#10b981] text-slate-800 self-start mr-auto p-3 rounded-lg max-w-[85%] text-sm flex items-center gap-2">
              <span className="w-2 h-2 bg-[#10b981] rounded-full animate-bounce"></span>
              <span className="w-2 h-2 bg-[#10b981] rounded-full animate-bounce [animation-delay:0.2s]"></span>
              <span className="w-2 h-2 bg-[#10b981] rounded-full animate-bounce [animation-delay:0.4s]"></span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="p-3 border-t border-slate-200 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            placeholder="Type your message..."
            className="flex-1 border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#10b981]"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-[#10b981] hover:bg-[#0d9488] disabled:bg-slate-300 text-white px-3 py-2 rounded flex items-center justify-center transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}

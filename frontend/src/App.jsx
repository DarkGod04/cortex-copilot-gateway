import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send } from 'lucide-react';

export default function App() {
  const [tenant, setTenant] = useState('Tenant_A');
  const [messages, setMessages] = useState([
    { role: 'system', text: 'Welcome to Cortex Copilot. Select your tenant and ask anything.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [insights, setInsights] = useState([]);
  const [insightError, setInsightError] = useState(null);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    setMessages([]); 
    setInsights([]); 
    setInsightError(null);
    
    const fetchInsights = async () => {
      if (!tenant) return;
      const encodedTenant = encodeURIComponent(tenant);
      const url = `http://127.0.0.1:8000/api/insights?tenant_id=${encodedTenant}`;
      
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error("Failed to fetch insights");
        }
        const data = await response.json();
        
        if (!data.insights || data.insights.length === 0) {
          setInsightError("Telemetry data unavailable for this tenant.");
          setInsights([]);
        } else {
          setInsightError(null);
          setInsights(data.insights);
        }
      } catch (error) {
        setInsightError("Telemetry data unavailable for this tenant.");
        setInsights([]);
      }
    };
    fetchInsights();
  }, [tenant]);

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

  const getCardStyle = (type) => {
    switch (type) {
      case 'danger':
        return {
          background: '#fee2e2',
          color: '#991b1b',
          borderLeft: '4px solid #ef4444',
        };
      case 'warning':
        return {
          background: '#fef3c7',
          color: '#92400e',
          borderLeft: '4px solid #f59e0b',
        };
      case 'success':
        return {
          background: '#dcfce7',
          color: '#166534',
          borderLeft: '4px solid #22c55e',
        };
      default:
        return {};
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', padding: '2rem' }} className="min-h-screen bg-[#f8f9fa] relative overflow-y-auto">

      {/* Dashboard Title Header */}
      <div style={{ width: '100%', maxWidth: '1200px', margin: '0 auto' }} className="mb-6">
        <h1 className="text-3xl font-bold text-slate-800">Cortex Copilot Dashboard</h1>
        <p className="text-slate-500 mt-2">Industrial Telemetry & Intelligence Gateway</p>
      </div>

      {/* First Child: This Week's Insights Panel (horizontal flex row) */}
      <div style={{ width: '100%', maxWidth: '1200px', margin: '0 auto' }} className="mb-6 bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h2 className="text-lg font-bold text-slate-800 mb-4">This Week's Insights</h2>
        <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem', flexWrap: 'wrap' }}>
          {insightError ? (
            <div className="p-4 rounded-lg bg-slate-100 text-slate-500 border border-slate-200 text-sm w-full text-center">
              Data unavailable.
            </div>
          ) : insights.length === 0 ? (
            <div className="p-4 rounded-lg bg-slate-50 text-slate-400 border border-slate-200 border-dashed text-sm w-full text-center">
              Loading insights...
            </div>
          ) : (
            insights.map((insight, index) => (
              <div
                key={index}
                style={{ ...getCardStyle(insight.type), flex: '1 1 250px' }}
                className="p-4 rounded-lg shadow-sm flex flex-col gap-1 transition-all duration-200 hover:shadow-md"
              >
                <div className="font-bold text-sm md:text-base">{insight.title}</div>
                <div className="text-xs md:text-sm opacity-90">{insight.description}</div>
                <div className="text-xs font-semibold mt-2">
                  Financial Impact: ₹{insight.impact_inr.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Second Child: Chat Window Container (fixed or minHeight 500px) */}
      <div style={{ width: '100%', maxWidth: '1200px', margin: '0 auto', minHeight: '550px' }} className="flex-1 bg-white border border-slate-200 rounded-xl shadow-sm flex flex-col overflow-hidden mb-6">
        {/* Chat Header */}
        <div className="bg-[#0f172a] text-white p-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-[#10b981]" />
            <span className="font-semibold text-sm md:text-base">Interactive AI Copilot</span>
            <select
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
              className="ml-3 bg-[#1e293b] text-white border border-slate-700 rounded px-2 py-1 text-sm focus:outline-none focus:border-[#10b981]"
            >
              <option value="Tenant_A">Tenant A</option>
              <option value="Tenant_B">Tenant B</option>
            </select>
          </div>
        </div>

        {/* Message List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 flex flex-col bg-slate-50">
          {messages.map((msg, index) => {
            let bubbleStyle = '';
            if (msg.role === 'user') {
              bubbleStyle = 'bg-slate-200 text-slate-800 self-end ml-auto';
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
        <form onSubmit={handleSubmit} className="p-4 border-t border-slate-200 flex gap-2 bg-white">
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
            className="bg-[#10b981] hover:bg-[#0d9488] disabled:bg-slate-300 text-white px-4 py-2 rounded flex items-center justify-center transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

    </div>
  );
}

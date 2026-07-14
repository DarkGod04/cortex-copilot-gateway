import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, Bell } from 'lucide-react';

function ChatChart({ data }) {
  if (!data || data.length === 0) return null;
  
  // Find max value to scale appropriately
  const maxDemand = Math.max(...data.map(d => d.Demand || 0), 10);
  const minDemand = Math.min(...data.map(d => d.Demand || 0), 0);
  
  const width = 500;
  const height = 150;
  const padding = 30;
  
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;
  
  const points = data.map((d, index) => {
    const x = padding + (index / (data.length - 1)) * chartWidth;
    const y = padding + chartHeight - ((d.Demand - minDemand) / (maxDemand - minDemand || 1)) * chartHeight;
    return { x, y, label: d.label, val: d.Demand };
  });
  
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const areaPath = points.length > 0 
    ? `${linePath} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`
    : '';
    
  return (
    <div className="mt-3 p-3 bg-slate-900 border border-slate-700 rounded-lg max-w-full shadow-inner">
      <div className="text-xs font-semibold text-slate-300 mb-2">Demand Trend (kVA)</div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
        <defs>
          <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
          </linearGradient>
        </defs>
        
        {/* Grid Lines */}
        <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="#334155" strokeDasharray="3,3" />
        <line x1={padding} y1={padding + chartHeight / 2} x2={width - padding} y2={padding + chartHeight / 2} stroke="#334155" strokeDasharray="3,3" />
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#475569" />
        
        {/* Area & Line */}
        <path d={areaPath} fill="url(#chartGradient)" />
        <path d={linePath} fill="none" stroke="#10b981" strokeWidth="2.5" />
        
        {/* Data Nodes */}
        {points.map((p, i) => (
          <circle 
            key={i} 
            cx={p.x} 
            cy={p.y} 
            r="3.5" 
            fill="#10b981" 
            stroke="#ffffff" 
            strokeWidth="1.5" 
          />
        ))}
        
        {/* Y Axis Labels */}
        <text x={padding - 5} y={padding + 4} fill="#94a3b8" fontSize="10" textAnchor="end">{Math.round(maxDemand)}</text>
        <text x={padding - 5} y={height - padding + 4} fill="#94a3b8" fontSize="10" textAnchor="end">{Math.round(minDemand)}</text>
        
        {/* X Axis Labels */}
        {data.length > 0 && (
          <>
            <text x={padding} y={height - 10} fill="#94a3b8" fontSize="10" textAnchor="start">{data[0].label}</text>
            {data.length > 2 && (
              <text x={width / 2} y={height - 10} fill="#94a3b8" fontSize="10" textAnchor="middle">{data[Math.floor(data.length / 2)].label}</text>
            )}
            <text x={width - padding} y={height - 10} fill="#94a3b8" fontSize="10" textAnchor="end">{data[data.length - 1].label}</text>
          </>
        )}
      </svg>
    </div>
  );
}

export default function App() {
  const [tenant, setTenant] = useState('Tenant_A');
  const [messages, setMessages] = useState([
    { role: 'system', text: 'Welcome to Cortex Copilot. Select your tenant and ask anything.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [insights, setInsights] = useState([]);
  const [insightError, setInsightError] = useState(null);
  const [suggestedPrompts, setSuggestedPrompts] = useState([]);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch insights and suggested prompts
  useEffect(() => {
    setMessages([]); 
    setInsights([]); 
    setInsightError(null);
    setSuggestedPrompts([]);
    
    const fetchInsights = async () => {
      if (!tenant) return;
      const encodedTenant = encodeURIComponent(tenant);
      const url = `/api/insights?tenant_id=${encodedTenant}`;
      
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error("Failed to fetch insights");
        }
        const data = await response.json();
        
        if (!data.insights || data.insights.length === 0) {
          setInsightError("Telemetry data unavailable for this tenant.");
          setInsights([]);
          setSuggestedPrompts([]);
        } else {
          setInsightError(null);
          setInsights(data.insights);
          setSuggestedPrompts(data.suggested_prompts || []);
        }
      } catch (error) {
        setInsightError("Telemetry data unavailable for this tenant.");
        setInsights([]);
        setSuggestedPrompts([]);
      }
    };
    fetchInsights();
  }, [tenant]);

  // Alert WebSocket Connection
  useEffect(() => {
    if (!tenant) return;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/alerts/${tenant}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const alertData = JSON.parse(event.data);
        if (alertData.type === "alert") {
          setMessages((prev) => [
            ...prev, 
            { 
              role: 'system', 
              text: alertData.description,
              isAlert: true
            }
          ]);
        }
      } catch (err) {
        console.error("Error reading WebSocket alert:", err);
      }
    };
    
    return () => {
      ws.close();
    };
  }, [tenant]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: userMessage }]);
    setIsLoading(true);

    await getChatResponse(userMessage);
  };

  const handleSuggestedClick = async (promptText) => {
    if (isLoading) return;
    setMessages((prev) => [...prev, { role: 'user', text: promptText }]);
    setIsLoading(true);

    await getChatResponse(promptText);
  };

  const getChatResponse = async (queryText) => {
    try {
      const response = await fetch("/api/chat", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': tenant,
        },
        body: JSON.stringify({ message: queryText }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setMessages((prev) => [
        ...prev, 
        { 
          role: 'assistant', 
          text: data.response,
          timeseries_data: data.timeseries_data
        }
      ]);
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

      {/* First Child: This Week's Insights Panel */}
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

      {/* Second Child: Chat Window Container */}
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
              bubbleStyle = msg.isAlert 
                ? 'bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold px-4 py-2.5 mx-auto w-full rounded-md shadow-sm flex items-center gap-2'
                : 'bg-yellow-50 border border-yellow-200 text-yellow-800 text-xs text-center mx-auto w-full';
            } else {
              bubbleStyle = 'bg-[#ecfdf5] border border-[#10b981] text-slate-800 self-start mr-auto';
            }

            return (
              <div
                key={index}
                className={`p-3 rounded-lg max-w-[85%] text-sm whitespace-pre-wrap ${bubbleStyle}`}
              >
                {msg.isAlert && <Bell className="w-4 h-4 text-rose-600 shrink-0 inline mr-1 animate-bounce" />}
                {msg.text}
                {msg.timeseries_data && msg.timeseries_data.length > 0 && (
                  <ChatChart data={msg.timeseries_data} />
                )}
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

        {/* Dynamic Suggested Prompts */}
        {suggestedPrompts.length > 0 && !isLoading && (
          <div className="flex flex-wrap gap-2 px-4 py-2.5 bg-slate-100 border-t border-slate-200">
            {suggestedPrompts.map((promptText, i) => (
              <button
                key={i}
                type="button"
                onClick={() => handleSuggestedClick(promptText)}
                className="text-xs bg-white text-slate-700 border border-slate-200 hover:border-[#10b981] hover:text-[#10b981] rounded-full px-3 py-1.5 cursor-pointer transition-all duration-150 shadow-sm"
              >
                {promptText}
              </button>
            ))}
          </div>
        )}

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
            className="bg-[#10b981] hover:bg-[#0d9488] disabled:bg-slate-300 text-white px-4 py-2 rounded flex items-center justify-center transition-colors cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

    </div>
  );
}

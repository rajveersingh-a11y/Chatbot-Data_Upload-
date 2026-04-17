import React, { useState } from 'react';
import { Upload, FileSpreadsheet, Send, Database, AlertCircle, Bot, User, Loader2 } from 'lucide-react';
import { uploadFile, getDatasetSummary, sendChatMessage } from './services/api';

// --- Sub-components ---

const LoadingSpinner = () => (
  <div className="flex items-center justify-center p-4">
    <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
  </div>
);

const ErrorBanner = ({ message }: { message: string }) => (
  <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4 flex items-center gap-3">
    <AlertCircle className="text-red-500 w-5 h-5" />
    <span className="text-red-700 text-sm font-medium">{message}</span>
  </div>
);

const MessageBubble = ({ sender, text, model }: { sender: 'user' | 'ai', text: string, model?: string }) => (
  <div className={`flex flex-col mb-4 ${sender === 'user' ? 'items-end' : 'items-start'}`}>
    <div className={`flex items-center gap-2 mb-1 px-1`}>
      {sender === 'ai' ? <Bot size={14} className="text-blue-500" /> : <User size={14} className="text-gray-500" />}
      <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
        {sender === 'ai' ? (model || 'Gemini AI') : 'You'}
      </span>
    </div>
    <div className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${
      sender === 'user' 
        ? 'bg-blue-600 text-white rounded-tr-none' 
        : 'bg-white border border-gray-100 text-gray-800 rounded-tl-none'
    }`}>
      <p className="text-sm whitespace-pre-wrap leading-relaxed">{text}</p>
    </div>
  </div>
);

// --- Main App Component ---

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [datasetInfo, setDatasetInfo] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{sender: 'user' | 'ai', text: string, model?: string}>>([]);
  const [query, setQuery] = useState('');

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setLoading(true);
    setError(null);
    try {
      const uploadRes = await uploadFile(selectedFile);
      setDatasetInfo(uploadRes);
      
      const summaryRes = await getDatasetSummary(uploadRes.dataset_id);
      setSummary(summaryRes);
      setFile(selectedFile);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to process file.");
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !datasetInfo) return;

    const userMsg = query;
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setQuery('');
    setChatLoading(true);
    setError(null);

    try {
      const res = await sendChatMessage(datasetInfo.dataset_id, userMsg);
      setMessages(prev => [...prev, { sender: 'ai', text: res.answer, model: res.model_used }]);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Chat service error.");
      setMessages(prev => [...prev, { 
        sender: 'ai', 
        text: "The dataset was loaded, but AI analysis is temporarily unavailable." 
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <Database className="text-white w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">DataChat <span className="text-blue-600">MVP</span></h1>
        </div>
        {summary && (
          <div className="hidden md:flex items-center gap-4 text-sm font-medium">
             <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full border border-blue-100 flex items-center gap-2">
                <FileSpreadsheet size={14} /> {datasetInfo.filename}
             </span>
             <span className="text-gray-400">|</span>
             <span className="text-gray-500">{summary.shape[0]} Rows • {summary.shape[1]} Columns</span>
          </div>
        )}
      </header>

      <main className="flex-1 flex flex-col md:flex-row gap-0 max-w-[1600px] mx-auto w-full p-4 md:p-6 overflow-hidden">
        
        {/* Left Sidebar: Upload & Summary */}
        <div className="w-full md:w-1/3 lg:w-1/4 flex flex-col gap-6 pr-0 md:pr-6 mb-6 md:mb-0 overflow-y-auto">
          
          {/* Upload Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Upload size={18} className="text-blue-500" /> Upload Dataset
            </h2>
            <div className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center hover:border-blue-400 transition-colors bg-gray-50 group cursor-pointer relative">
              <input 
                type="file" 
                className="absolute inset-0 opacity-0 cursor-pointer" 
                onChange={handleUpload} 
                accept=".csv,.xlsx,.xls"
                disabled={loading}
              />
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                  <FileSpreadsheet className="text-blue-500" />
                </div>
                <div className="text-sm font-medium text-gray-600">
                  {file ? file.name : 'Choose CSV or Excel'}
                </div>
                <div className="text-xs text-gray-400">Max 20MB</div>
              </div>
            </div>
          </div>

          {/* Summary Card */}
          {summary && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Database size={18} className="text-green-500" /> Dataset Summary
              </h2>
              <div className="space-y-4">
                <div>
                  <h3 className="text-xs font-bold text-gray-400 uppercase mb-2">Columns</h3>
                  <div className="flex flex-wrap gap-2">
                    {summary.columns.map((col: string) => (
                      <span key={col} className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-[11px] font-mono border border-gray-200">
                        {col}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 pt-2 border-t border-gray-100">
                  <div>
                    <div className="text-xl font-bold text-gray-900">{summary.shape[0]}</div>
                    <div className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">Rows</div>
                  </div>
                  <div>
                    <div className="text-xl font-bold text-gray-900">{summary.shape[1]}</div>
                    <div className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">Columns</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {error && <ErrorBanner message={error} />}
          {loading && <LoadingSpinner />}
        </div>

        {/* Right Section: Chat */}
        <div className="flex-1 bg-white rounded-2xl shadow-sm border border-gray-200 flex flex-col overflow-hidden relative">
          
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-2 bg-[#f9fafc]">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-12 opacity-40">
                <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mb-4">
                  <Bot size={40} className="text-blue-500" />
                </div>
                <h3 className="text-lg font-bold text-gray-900">AI Data Assistant</h3>
                <p className="text-sm text-gray-600 max-w-xs mx-auto mt-2">
                  {summary 
                    ? "Ask me anything about your dataset! Examples: 'summarize this data', 'how many rows have nulls?', 'what is the average of column X?'" 
                    : "Upload a file to start chatting with your data."}
                </p>
              </div>
            ) : (
              messages.map((m, i) => (
                <MessageBubble key={i} sender={m.sender} text={m.text} model={m.model} />
              ))
            )}
            {chatLoading && (
              <div className="flex items-center gap-2 p-4 text-blue-500 justify-center">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span className="text-xs font-semibold uppercase tracking-widest italic">Gemini is thinking...</span>
              </div>
            )}
          </div>

          {/* Chat Input */}
          <div className="p-6 border-t border-gray-100 bg-white">
            <form onSubmit={handleSendMessage} className="relative group">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={datasetInfo ? "Ask a question about the data..." : "Upload a file first..."}
                disabled={!datasetInfo || chatLoading}
                className="w-full pl-6 pr-14 py-4 bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-gray-800 shadow-inner disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button 
                type="submit"
                disabled={!datasetInfo || chatLoading || !query.trim()}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:bg-gray-300 transition-colors shadow-md active:scale-95"
              >
                <Send size={20} />
              </button>
            </form>
          </div>
        </div>
      </main>

      {/* Footer Info */}
      <footer className="px-6 py-3 border-t border-gray-200 text-center text-xs text-gray-400 bg-white">
        Simple Data Chatbot MVP • Built with FastAPI, React & Gemini 1.5/2.0+
      </footer>
    </div>
  );
}

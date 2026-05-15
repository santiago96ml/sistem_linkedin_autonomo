import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Monitor, Send, MousePointer, Keyboard, RefreshCw, Power, AlertCircle, ShieldCheck } from 'lucide-react';
import { useOrchestrator } from '../../hooks/useOrchestrator';

export const CommandCenterView = () => {
  const { API_URL } = useOrchestrator();
  const [accounts, setAccounts] = useState<any[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [streamImage, setStreamImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    fetchAccounts();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const fetchAccounts = async () => {
    try {
      const res = await fetch(`${API_URL}/accounts/`);
      const data = await res.json();
      setAccounts(data.filter((a: any) => a.status === 'active'));
    } catch (err) {
      console.error('Error fetching accounts:', err);
    }
  };

  const startLiveSession = async (accountId: number) => {
    setLoading(true);
    setSelectedAccountId(accountId);
    try {
      const url = `${API_URL}/accounts/${accountId}/live`;
      console.log('Initiating live session at:', url);
      const res = await fetch(url, { method: 'POST' });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(`Failed to start session: ${errorData.detail || res.statusText}`);
      }
      connectWebSocket(accountId);
    } catch (err) {
      console.error('Error starting live session:', err);
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = (accountId: number) => {
    if (wsRef.current) wsRef.current.close();
    
    // Dynamically derive WS URL from API_URL, ensuring no trailing slashes
    const baseUrl = API_URL.replace(/^http/, 'ws').replace(/\/$/, '');
    const wsUrl = `${baseUrl}/ws/live/${accountId}`;
    console.log('Connecting to WS:', wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WS Connected');
      setIsLive(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'stream') {
        setStreamImage(`data:image/jpeg;base64,${data.image}`);
      }
    };

    ws.onclose = () => {
      console.log('WS Closed');
      setIsLive(false);
    };

    wsRef.current = ws;
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!wsRef.current || !isLive) return;
    
    // Relay keypress
    wsRef.current.send(JSON.stringify({ type: 'press', key: e.key }));
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500" onKeyDown={handleKeyDown} tabIndex={0}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Terminal className="w-8 h-8 text-indigo-500" />
            Command Center
          </h2>
          <p className="text-slate-400 mt-1">Control remoto e interacción directa con navegadores persistentes.</p>
        </div>

        <div className="flex items-center gap-3">
          <select 
            onChange={(e) => startLiveSession(Number(e.target.value))}
            className="bg-slate-900 border border-slate-800 text-slate-300 text-sm rounded-xl px-4 py-2 focus:ring-2 focus:ring-indigo-500/50 outline-none transition-all"
          >
            <option value="">Seleccionar cuenta para operar...</option>
            {accounts.map(acc => (
              <option key={acc.id} value={acc.id}>{acc.name} ({acc.email})</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Remote Viewport */}
        <div className="lg:col-span-3 space-y-4">
          <div className="relative aspect-video bg-slate-950 rounded-3xl border border-slate-800 overflow-hidden group">
            {streamImage ? (
              <div className="relative w-full h-full">
                <img 
                  src={streamImage} 
                  alt="Live Stream" 
                  className="w-full h-full object-contain cursor-crosshair"
                  onClick={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const x = ((e.clientX - rect.left) / rect.width) * 1280;
                    const y = ((e.clientY - rect.top) / rect.height) * 720;
                    wsRef.current?.send(JSON.stringify({ type: 'click', x: Math.round(x), y: Math.round(y) }));
                  }}
                />
                <div className="absolute top-6 left-6 flex items-center gap-3 px-4 py-2 bg-black/60 backdrop-blur-xl rounded-2xl border border-white/10">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
                  <span className="text-xs font-bold text-white uppercase tracking-[0.2em]">Live Identity Feed</span>
                </div>
              </div>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-slate-600">
                {loading ? (
                  <>
                    <RefreshCw className="w-12 h-12 animate-spin text-indigo-500" />
                    <p className="text-slate-400 font-medium">Iniciando sesión persistente...</p>
                  </>
                ) : (
                  <>
                    <Monitor className="w-16 h-16 opacity-20" />
                    <p className="text-sm font-medium">Selecciona una identidad para tomar el control</p>
                  </>
                )}
              </div>
            )}
          </div>
          
          <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-2xl flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
                <MousePointer className="w-4 h-4 text-indigo-400" />
                Click Directo habilitado
              </div>
              <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
                <Keyboard className="w-4 h-4 text-indigo-400" />
                Relay de Teclado activo
              </div>
            </div>
            <div className="flex items-center gap-2">
               <ShieldCheck className="w-4 h-4 text-emerald-500" />
               <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Secure Tunnel</span>
            </div>
          </div>
        </div>

        {/* Sidebar / Stats */}
        <div className="space-y-6">
          <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-3xl space-y-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
              <Power className="w-4 h-4 text-indigo-500" />
              Estado de Sesión
            </h3>
            
            <div className="space-y-3">
               <div className="flex justify-between items-center p-3 bg-slate-950 rounded-xl border border-white/5">
                 <span className="text-xs text-slate-500">Conectividad WS</span>
                 <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${isLive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                   {isLive ? 'ESTABLE' : 'OFFLINE'}
                 </span>
               </div>
               <div className="flex justify-between items-center p-3 bg-slate-950 rounded-xl border border-white/5">
                 <span className="text-xs text-slate-500">Latencia</span>
                 <span className="text-[10px] font-bold text-indigo-400">~150ms</span>
               </div>
               <div className="flex justify-between items-center p-3 bg-slate-950 rounded-xl border border-white/5">
                 <span className="text-xs text-slate-500">Stream FPS</span>
                 <span className="text-[10px] font-bold text-indigo-400">2 FPS</span>
               </div>
            </div>
          </div>

          <div className="p-6 bg-indigo-500/10 border border-indigo-500/20 rounded-3xl space-y-3">
             <div className="flex items-center gap-2 text-indigo-400">
               <AlertCircle className="w-5 h-5" />
               <span className="text-xs font-bold uppercase tracking-wider">Modo Comando</span>
             </div>
             <p className="text-xs text-slate-400 leading-relaxed">
               Estás interactuando directamente con el navegador del bot. Las acciones realizadas aquí son definitivas y afectan la reputación de la cuenta.
             </p>
          </div>
        </div>
      </div>
    </div>
  );
};

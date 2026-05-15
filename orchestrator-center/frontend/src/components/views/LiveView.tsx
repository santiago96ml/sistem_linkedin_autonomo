'use client';

import React, { useState, useEffect } from 'react';
import { Monitor, RefreshCw, Camera, AlertCircle } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const LiveView = () => {
  const [timestamp, setTimestamp] = useState(Date.now());
  const [accounts, setAccounts] = useState<any[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAccounts();
    const interval = setInterval(() => {
      setTimestamp(Date.now());
    }, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchAccounts = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/accounts/`);
      const data = await res.json();
      setAccounts(data.filter((a: any) => a.status === 'active'));
    } catch (err) {
      console.error('Error fetching accounts:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredAccounts = selectedAccountId === 'all' 
    ? accounts 
    : accounts.filter(a => a.id.toString() === selectedAccountId);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Monitor className="w-8 h-8 text-indigo-500" />
            Live View
          </h2>
          <p className="text-slate-400 mt-1">Monitoreo visual vinculado a identidades reales.</p>
        </div>

        <select 
          value={selectedAccountId}
          onChange={(e) => setSelectedAccountId(e.target.value)}
          className="bg-slate-900 border border-slate-800 text-slate-300 text-sm rounded-xl px-4 py-2 focus:ring-2 focus:ring-indigo-500/50 outline-none transition-all"
        >
          <option value="all">Ver todas las cuentas</option>
          {accounts.map(acc => (
            <option key={acc.id} value={acc.id}>{acc.name}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {loading ? (
           <div className="col-span-full py-20 flex flex-col items-center gap-4">
             <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
             <p className="text-slate-500">Localizando cámaras de los bots...</p>
           </div>
        ) : filteredAccounts.length === 0 ? (
          <div className="col-span-full p-12 border-2 border-dashed border-slate-800 rounded-3xl text-center">
            <AlertCircle className="w-12 h-12 text-slate-700 mx-auto mb-4" />
            <h3 className="text-white font-semibold">No hay sesiones activas</h3>
            <p className="text-slate-500">Inicia sesión con una cuenta para ver su actividad en vivo.</p>
          </div>
        ) : (
          filteredAccounts.map((acc) => (
            <div key={acc.id} className="rounded-3xl border border-slate-800 bg-slate-900/50 overflow-hidden group relative">
              <div className="aspect-video bg-slate-950 flex items-center justify-center relative">
                <img 
                  src={`${API_URL}/static/screenshots/account_${acc.id}.png?t=${timestamp}`}
                  alt={`Bot View ${acc.name}`}
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = 'https://placehold.co/600x400/020617/475569?text=Bot+Idle';
                  }}
                />
                <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1 bg-black/60 backdrop-blur-md rounded-full border border-white/10">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[10px] font-bold text-white uppercase tracking-widest">{acc.name} - LIVE</span>
                </div>
              </div>
              <div className="p-4 border-t border-slate-800 flex items-center justify-between">
                 <div className="flex items-center gap-2 text-xs text-slate-500">
                   <Camera className="w-3 h-3" />
                   <span>Identidad: {acc.email}</span>
                 </div>
                 <button 
                   onClick={() => setTimestamp(Date.now())}
                   className="p-2 hover:bg-white/5 rounded-lg transition-colors text-slate-400"
                 >
                   <RefreshCw className="w-4 h-4" />
                 </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

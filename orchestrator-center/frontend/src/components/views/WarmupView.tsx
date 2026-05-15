'use client';

import React, { useState, useEffect } from 'react';
import { Flame, Shield, TrendingUp, Settings, User, AlertCircle, CheckCircle2, Languages, Ban, MessageSquareQuote } from 'lucide-react';

interface WarmupStatus {
  account_id: number;
  name: string;
  profile_pic_url?: string;
  current_day: number;
  total_days: number;
  current_level: number;
  daily_actions: number;
  max_actions: number;
  health_percentage: number;
  is_warming_up: number;
}

interface WarmupConfig {
  niche: string;
  personality: string;
  languages: string;
  forbidden_topics: string;
  tone_modifiers: string;
  total_days: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const WarmupView = () => {
  const [accounts, setAccounts] = useState<WarmupStatus[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<number | null>(null);
  const [config, setConfig] = useState<WarmupConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      console.log('Fetching warmup status from:', `${API_URL}/warmup/status`);
      const res = await fetch(`${API_URL}/warmup/status`);
      
      if (!res.ok) {
        const errorBody = await res.text();
        console.error(`Error ${res.status}:`, errorBody);
        throw new Error(`Error ${res.status} en el servidor`);
      }

      const data = await res.json();
      if (Array.isArray(data)) {
        setAccounts(data);
        setError(null);
      } else {
        console.warn('Unexpected warmup status payload, expected array:', data);
        setError('Formato de datos inválido.');
        setAccounts([]);
      }
      setLoading(false);
    } catch (err: any) {
      console.error('Detailed fetch error:', err);
      setError(err.message || 'No se pudo conectar con el servidor.');
      setLoading(false);
    }
  };

  const fetchConfig = async (accountId: number) => {
    setSelectedAccount(accountId);
    try {
      const res = await fetch(`${API_URL}/warmup/config/${accountId}`);
      const data = await res.json();
      setConfig(data);
    } catch (err) {
      console.error('Error fetching config:', err);
    }
  };

  const saveConfig = async () => {
    if (!selectedAccount || !config) return;
    setSaving(true);
    try {
      await fetch(`${API_URL}/warmup/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...config, account_id: selectedAccount })
      });
      fetchStatus(); // Refresh to update total_days in list
      alert('Configuration saved successfully!');
    } catch (err) {
      console.error('Error saving config:', err);
    } finally {
      setSaving(false);
    }
  };

  const toggleWarmup = async (accountId: number) => {
    try {
      const res = await fetch(`${API_URL}/accounts/${accountId}/warmup/toggle`, { method: 'PUT' });
      if (res.ok) fetchStatus();
    } catch (err) {
      console.error('Error toggling warmup:', err);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <Flame className="w-8 h-8 text-orange-500 animate-pulse" />
            Warmup Lab
          </h2>
          <p className="text-slate-400 mt-1">Gestión de calentamiento y salud de identidades.</p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-3 animate-in fade-in slide-in-from-top-4 duration-300">
          <AlertCircle className="w-5 h-5" />
          <p className="font-medium">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {accounts.map((acc) => (
          <div 
            key={acc.account_id}
            className={`relative group overflow-hidden rounded-2xl border transition-all duration-300 cursor-pointer ${
              selectedAccount === acc.account_id 
                ? 'border-orange-500 bg-orange-500/5 ring-1 ring-orange-500/50' 
                : 'border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900/80'
            }`}
            onClick={() => fetchConfig(acc.account_id)}
          >
            <div className="p-6 space-y-4">
              <div className="flex items-center gap-4">
                <div className="relative">
                  {acc.profile_pic_url ? (
                    <img 
                      src={acc.profile_pic_url} 
                      alt={acc.name} 
                      className="w-14 h-14 rounded-full border-2 border-orange-500/30 object-cover"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-slate-800 border-2 border-slate-700 flex items-center justify-center">
                      <User className="w-6 h-6 text-slate-500" />
                    </div>
                  )}
                  <div className="absolute -bottom-1 -right-1 bg-green-500 rounded-full p-1 border-2 border-slate-900">
                    <Shield className="w-3 h-3 text-white" />
                  </div>
                </div>
                <div>
                  <h3 className="font-semibold text-lg text-white">{acc.name}</h3>
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/20">
                    Level {acc.current_level}
                  </span>
                </div>
              </div>

              {/* Progress Circle & Day */}
              <div className="flex items-center justify-between pt-2">
                <div className="space-y-1">
                  <p className="text-xs text-slate-500 uppercase tracking-wider font-bold">Progreso del Ciclo</p>
                  <p className="text-2xl font-black text-white">Día {acc.current_day}<span className="text-slate-600">/{acc.total_days}</span></p>
                </div>
                <div className="h-12 w-12 rounded-full border-4 border-slate-800 border-t-orange-500 flex items-center justify-center">
                  <span className="text-[10px] font-bold">{Math.round((acc.current_day/acc.total_days)*100)}%</span>
                </div>
              </div>

              {/* Health Bar (Action Limit) */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400 flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" /> Salud de Actividad
                  </span>
                  <span className="text-white font-mono">{acc.daily_actions}/150</span>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-1000 ${
                      acc.health_percentage > 80 ? 'bg-red-500' : 
                      acc.health_percentage > 50 ? 'bg-orange-500' : 'bg-emerald-500'
                    }`}
                    style={{ width: `${acc.health_percentage}%` }}
                  />
                </div>
              </div>
            </div>
            
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <Settings className="w-4 h-4 text-slate-600" />
            </div>
          </div>
        ))}
      </div>

      {selectedAccount && config && (
        <div className="mt-8 rounded-3xl border border-slate-800 bg-slate-900/80 backdrop-blur-xl p-8 space-y-8 animate-in slide-in-from-bottom-4 duration-500">
          <div className="flex items-center justify-between border-b border-slate-800 pb-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-orange-500/10 border border-orange-500/20 text-orange-500">
                <Settings className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white">Configuración de Inteligencia</h3>
                <p className="text-slate-400 text-sm">Personaliza el comportamiento humano para {accounts.find(a => a.account_id === selectedAccount)?.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 mr-4 bg-slate-950 px-4 py-2 rounded-xl border border-slate-800">
                <span className="text-xs font-bold text-slate-500">ESTADO:</span>
                <button 
                  onClick={(e) => { e.stopPropagation(); toggleWarmup(selectedAccount); }}
                  className={`text-[10px] font-black px-3 py-1 rounded-full transition-all ${
                    accounts.find(a => a.account_id === selectedAccount)?.is_warming_up === 1
                      ? 'bg-orange-500 text-white shadow-[0_0_12px_rgba(249,115,22,0.4)]'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {accounts.find(a => a.account_id === selectedAccount)?.is_warming_up === 1 ? 'ACTIVO' : 'PAUSADO'}
                </button>
              </div>
              <button 
                onClick={saveConfig}
                disabled={saving}
                className="px-6 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:bg-slate-700 text-white rounded-xl font-bold transition-all flex items-center gap-2"
              >
                {saving ? 'Guardando...' : <><CheckCircle2 className="w-4 h-4" /> Guardar Cambios</>}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <label className="text-sm font-bold text-slate-400 uppercase flex items-center gap-2">
                <TrendingUp className="w-4 h-4" /> Rubro / Industria
              </label>
              <input 
                type="text"
                value={config.niche || ''}
                onChange={(e) => setConfig({...config, niche: e.target.value})}
                placeholder="Ej: Consultoría IT, Real Estate, Marketing..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-orange-500 outline-none transition-all"
              />
            </div>
            <div className="space-y-4">
              <label className="text-sm font-bold text-slate-400 uppercase flex items-center gap-2">
                <Languages className="w-4 h-4" /> Idiomas Operativos
              </label>
              <input 
                type="text"
                value={config.languages || ''}
                onChange={(e) => setConfig({...config, languages: e.target.value})}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-orange-500 outline-none transition-all"
              />
            </div>
            <div className="col-span-full space-y-4">
              <label className="text-sm font-bold text-slate-400 uppercase flex items-center gap-2">
                <MessageSquareQuote className="w-4 h-4" /> Personalidad y Tono (AI Prompt)
              </label>
              <textarea 
                rows={4}
                value={config.personality || ''}
                onChange={(e) => setConfig({...config, personality: e.target.value})}
                placeholder="Define el estilo: Senior, formal, usa muchos emojis, experto en tecnología..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-white focus:border-orange-500 outline-none transition-all"
              />
            </div>
            <div className="col-span-full space-y-4">
              <label className="text-sm font-bold text-slate-400 uppercase flex items-center gap-2 text-red-400">
                <Ban className="w-4 h-4" /> Temas Prohibidos
              </label>
              <input 
                type="text"
                value={config.forbidden_topics || ''}
                onChange={(e) => setConfig({...config, forbidden_topics: e.target.value})}
                placeholder="Política, ventas agresivas, cripto..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-red-500 outline-none transition-all"
              />
            </div>
            
            <div className="col-span-full border-t border-slate-800 pt-6">
               <label className="text-sm font-bold text-slate-400 uppercase flex items-center gap-2">
                <Settings className="w-4 h-4" /> Duración Total del Calentamiento (Días)
              </label>
              <div className="mt-4 flex items-center gap-4">
                <input 
                  type="number"
                  value={config.total_days || 120}
                  onChange={(e) => setConfig({...config, total_days: parseInt(e.target.value)})}
                  className="w-32 bg-slate-950 border border-slate-800 rounded-xl p-3 text-white focus:border-orange-500 outline-none transition-all"
                />
                <p className="text-xs text-slate-500">
                  Por defecto son 120 días. Para cuentas antiguas (como Franco), puedes reducirlo a 15-30 días.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="w-12 h-12 border-4 border-orange-500/20 border-t-orange-500 rounded-full animate-spin" />
          <p className="text-slate-500 font-medium">Sincronizando con el laboratorio...</p>
        </div>
      )}
    </div>
  );
};


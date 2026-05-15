"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Globe, Plus, Trash2, Power, PowerOff, RefreshCw, Server,
  CheckCircle, XCircle, AlertTriangle, Loader2, MapPin,
  Wifi, WifiOff, ExternalLink
} from 'lucide-react';

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

interface Proxy {
  id: number;
  name: string | null;
  host: string;
  port: number;
  protocol: string;
  country: string | null;
  city: string | null;
  is_active: boolean;
  is_online: boolean;
  last_health_check: string | null;
  assigned_account_id: number | null;
  created_at: string | null;
}

interface Account {
  id: number;
  name: string;
  email: string;
}

interface ProxyStats {
  total: number;
  active: number;
  online: number;
  assigned: number;
  by_country: Record<string, number>;
}

export function ProxiesView() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [stats, setStats] = useState<ProxyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [healthRunning, setHealthRunning] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

  // Form state
  const [formHost, setFormHost] = useState('');
  const [formPort, setFormPort] = useState('1080');
  const [formCountry, setFormCountry] = useState('');
  const [formCity, setFormCity] = useState('');
  const [formName, setFormName] = useState('');
  const [formUser, setFormUser] = useState('');
  const [formPass, setFormPass] = useState('');
  const [formProtocol, setFormProtocol] = useState('socks5');

  const fetchData = useCallback(async () => {
    try {
      const [pRes, sRes, aRes] = await Promise.all([
        fetch(`${API_URL}/proxies/`),
        fetch(`${API_URL}/proxies/stats`),
        fetch(`${API_URL}/accounts/`),
      ]);
      if (pRes.ok) setProxies(await pRes.json());
      if (sRes.ok) setStats(await sRes.json());
      if (aRes.ok) setAccounts(await aRes.json());
    } catch (e) {
      console.error('Failed to fetch proxy data', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleAdd = async () => {
    if (!formHost || !formPort) return;
    try {
      const body: any = { host: formHost, port: parseInt(formPort), protocol: formProtocol };
      if (formName) body.name = formName;
      if (formCountry) body.country = formCountry.toUpperCase();
      if (formCity) body.city = formCity;
      if (formUser) body.username = formUser;
      if (formPass) body.password = formPass;

      const res = await fetch(`${API_URL}/proxies/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        setShowAddForm(false);
        setFormHost(''); setFormPort('1080'); setFormCountry(''); setFormCity('');
        setFormName(''); setFormUser(''); setFormPass('');
        fetchData();
      } else {
        const err = await res.json();
        alert('Error: ' + (err.detail || 'Unknown'));
      }
    } catch (e: any) {
      alert('Error: ' + e.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Eliminar este proxy?')) return;
    try {
      await fetch(`${API_URL}/proxies/${id}`, { method: 'DELETE' });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const handleAssign = async (proxyId: number, accountId: number) => {
    try {
      const res = await fetch(`${API_URL}/proxies/${proxyId}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id: accountId }),
      });
      if (res.ok) fetchData();
      else alert('Error: ' + ((await res.json()).detail || ''));
    } catch (e: any) { alert('Error: ' + e.message); }
  };

  const handleUnassign = async (proxyId: number) => {
    try {
      await fetch(`${API_URL}/proxies/${proxyId}/unassign`, { method: 'POST' });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const handleHealthCheck = async () => {
    setHealthRunning(true);
    try {
      const res = await fetch(`${API_URL}/proxies/health-check`, { method: 'POST' });
      const data = await res.json();
      alert(`Health check: ${data.online}/${data.total} proxies online`);
      fetchData();
    } catch (e: any) {
      alert('Error: ' + e.message);
    } finally {
      setHealthRunning(false);
    }
  };

  const getCountryFlag = (country: string | null) => {
    if (!country) return null;
    const flags: Record<string, string> = {
      'BR': '🇧🇷', 'AR': '🇦🇷', 'US': '🇺🇸', 'GB': '🇬🇧',
      'DE': '🇩🇪', 'FR': '🇫🇷', 'ES': '🇪🇸', 'IT': '🇮🇹',
      'MX': '🇲🇽', 'CO': '🇨🇴', 'CL': '🇨🇱', 'PE': '🇵🇪',
      'PT': '🇵🇹', 'CA': '🇨🇦', 'AU': '🇦🇺', 'JP': '🇯🇵',
    };
    return flags[country] || '🌍';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={32} className="text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-medium text-slate-200 flex items-center gap-2">
          <div className="w-1.5 h-6 bg-indigo-500 rounded-full"></div>
          Proxy Pool
        </h3>
        <div className="flex items-center gap-3">
          <button
            onClick={handleHealthCheck}
            disabled={healthRunning}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 border border-white/5 text-slate-300 text-xs font-medium hover:bg-slate-700/50 transition-all disabled:opacity-50"
          >
            {healthRunning ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Health Check
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-sm font-medium hover:bg-indigo-500/20 transition-all"
          >
            <Plus size={16} />
            Añadir Proxy
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-xl border border-white/5 bg-slate-900/40 p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Total</p>
            <p className="text-2xl font-bold text-slate-200 mt-1">{stats.total}</p>
          </div>
          <div className="rounded-xl border border-white/5 bg-slate-900/40 p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Activos</p>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{stats.active}</p>
          </div>
          <div className="rounded-xl border border-white/5 bg-slate-900/40 p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Online</p>
            <p className="text-2xl font-bold text-indigo-400 mt-1">{stats.online}</p>
          </div>
          <div className="rounded-xl border border-white/5 bg-slate-900/40 p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Asignados</p>
            <p className="text-2xl font-bold text-amber-400 mt-1">{stats.assigned}</p>
          </div>
          {Object.keys(stats.by_country).length > 0 && (
            <div className="col-span-full rounded-xl border border-white/5 bg-slate-900/40 p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Por País</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(stats.by_country).map(([country, count]) => (
                  <span key={country} className="px-3 py-1 rounded-full bg-slate-800/50 text-xs text-slate-300 border border-white/5">
                    {getCountryFlag(country)} {country} ×{count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add Form Modal */}
      {showAddForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-md" onClick={() => setShowAddForm(false)}></div>
          <div className="relative w-full max-w-md bg-slate-900 border border-white/10 rounded-2xl shadow-2xl p-6 space-y-4">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <Globe size={18} className="text-indigo-400" />
              Añadir Proxy
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="text-xs font-medium text-slate-400">Nombre (opcional)</label>
                <input value={formName} onChange={e => setFormName(e.target.value)}
                  placeholder="Oracle São Paulo" className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400">Host/IP</label>
                <input value={formHost} onChange={e => setFormHost(e.target.value)}
                  placeholder="192.168.1.1" className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400">Puerto</label>
                <input value={formPort} onChange={e => setFormPort(e.target.value)}
                  placeholder="1080" className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400">País (ISO)</label>
                <input value={formCountry} onChange={e => setFormCountry(e.target.value.toUpperCase())}
                  placeholder="BR" maxLength={2} className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400">Ciudad</label>
                <input value={formCity} onChange={e => setFormCity(e.target.value)}
                  placeholder="São Paulo" className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400">Usuario (opcional)</label>
                <input value={formUser} onChange={e => setFormUser(e.target.value)}
                  placeholder="proxy" className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-400">Contraseña (opcional)</label>
                <input value={formPass} onChange={e => setFormPass(e.target.value)}
                  type="password" placeholder="••••••" className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500" />
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button onClick={() => setShowAddForm(false)}
                className="flex-1 py-2 rounded-lg bg-slate-800 text-slate-300 text-sm hover:bg-slate-700 transition-colors">
                Cancelar
              </button>
              <button onClick={handleAdd}
                className="flex-1 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium transition-all shadow-[0_0_15px_rgba(99,102,241,0.3)]">
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Proxy Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {proxies.length === 0 ? (
          <div className="col-span-full py-16 flex flex-col items-center border border-dashed border-white/5 rounded-xl bg-slate-900/20">
            <Server size={48} className="text-slate-800 mb-4" />
            <p className="text-slate-400 text-sm font-medium">No hay proxies configurados.</p>
            <p className="text-xs text-slate-500 mt-1">Añadí un proxy SOCKS5 desde un VPS Oracle o cualquier servidor.</p>
            <button onClick={() => setShowAddForm(true)}
              className="mt-4 text-xs text-indigo-400 hover:text-indigo-300 underline underline-offset-4">
              Añadir primer proxy
            </button>
          </div>
        ) : proxies.map(proxy => {
          const isOnline = proxy.is_online;
          const isAssigned = proxy.assigned_account_id !== null;
          const assignedAccount = accounts.find(a => a.id === proxy.assigned_account_id);

          return (
            <div key={proxy.id} className={`group relative rounded-xl border ${
              isOnline ? 'border-emerald-500/20' : proxy.is_active ? 'border-white/5' : 'border-rose-500/20'
            } bg-slate-900/40 backdrop-blur-sm p-5 hover:bg-slate-900/60 transition-all shadow-lg`}>
              
              <div className="flex justify-between items-start mb-3">
                <div className="flex gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    isOnline ? 'bg-emerald-500/20' : 'bg-slate-800'
                  }`}>
                    {isOnline ? <Wifi size={20} className="text-emerald-400" /> : <WifiOff size={20} className="text-slate-500" />}
                  </div>
                  <div>
                    <h4 className="font-medium text-slate-100 text-sm">{proxy.name || proxy.host}</h4>
                    <p className="text-xs text-slate-500 mt-0.5 font-mono">{proxy.short_url}</p>
                  </div>
                </div>
                <button onClick={() => handleDelete(proxy.id)}
                  className="text-slate-500 hover:text-rose-400 p-1 rounded hover:bg-rose-500/10 transition-all opacity-0 group-hover:opacity-100">
                  <Trash2 size={14} />
                </button>
              </div>

              <div className="space-y-2 text-xs">
                {proxy.country && (
                  <div className="flex items-center gap-2 text-slate-400">
                    <MapPin size={12} />
                    <span>{getCountryFlag(proxy.country)} {proxy.country}{proxy.city ? ` - ${proxy.city}` : ''}</span>
                  </div>
                )}
                <div className="flex items-center gap-2 text-slate-400">
                  <Server size={12} />
                  <span>{proxy.protocol.toUpperCase()} :{proxy.port}</span>
                </div>
                <div className="flex items-center gap-2">
                  {isOnline ? (
                    <span className="flex items-center gap-1.5 text-emerald-400"><CheckCircle size={12} /> Online</span>
                  ) : (
                    <span className="flex items-center gap-1.5 text-slate-500"><XCircle size={12} /> Offline</span>
                  )}
                  <span className={`flex items-center gap-1.5 ${isAssigned ? 'text-amber-400' : 'text-slate-500'}`}>
                    <ExternalLink size={12} />
                    {isAssigned ? `Cuenta #${proxy.assigned_account_id}` : 'Sin asignar'}
                  </span>
                </div>
              </div>

              {isAssigned && assignedAccount && (
                <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-2">
                  <div className="w-5 h-5 rounded-full bg-indigo-500/20 flex items-center justify-center text-[10px] font-bold text-indigo-300 uppercase">
                    {assignedAccount.name.charAt(0)}
                  </div>
                  <span className="text-xs text-slate-400 flex-1 truncate">{assignedAccount.name}</span>
                  <button onClick={() => handleUnassign(proxy.id)}
                    className="text-[10px] text-rose-400/60 hover:text-rose-400">
                    Desasignar
                  </button>
                </div>
              )}

              {!isAssigned && accounts.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/5">
                  <select
                    onChange={e => { if (e.target.value) handleAssign(proxy.id, parseInt(e.target.value)); }}
                    value=""
                    className="w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">Asignar a cuenta...</option>
                    {accounts.filter(a => a.status === 'active').map(a => (
                      <option key={a.id} value={a.id}>#{a.id} {a.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

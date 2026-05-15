"use client";

import React, { useState, useEffect } from 'react';
import { X, Loader2, CheckCircle2, AlertTriangle, ThumbsUp, MessageSquare, UserPlus } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Account {
  id: number;
  name: string;
  email: string;
  status: string;
}

interface TestResult {
  account_id: number;
  account_name: string;
  mission_id: number | null;
  status: string;
  duration_ms: number;
}

const MISSION_TYPES = [
  { value: 'comment', label: 'Comentario', icon: MessageSquare },
  { value: 'reaction', label: 'Reacción', icon: ThumbsUp },
  { value: 'follow', label: 'Follow', icon: UserPlus },
] as const;

export function ConcurrentTestModal({ triggerClassName }: { triggerClassName?: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountIds, setSelectedAccountIds] = useState<Set<number>>(new Set());
  const [missionType, setMissionType] = useState<string>('comment');
  const [postUrl, setPostUrl] = useState('');
  const [concurrency, setConcurrency] = useState(3);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<TestResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setError(null);
    setResults([]);
    fetch(`${API_URL}/accounts/`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setAccounts(data.filter((a: Account) => a.status === 'active'));
        }
      })
      .catch(() => setError('No se pudieron cargar las cuentas.'));
  }, [isOpen]);

  const toggleAccount = (id: number) => {
    setSelectedAccountIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSubmit = async () => {
    if (selectedAccountIds.size === 0 || !postUrl) return;
    setIsLoading(true);
    setError(null);
    setResults([]);

    try {
      const res = await fetch(`${API_URL}/test/concurrent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_ids: Array.from(selectedAccountIds),
          mission_type: missionType,
          post_url: postUrl,
          concurrency,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setResults(data.results || []);
    } catch (e: any) {
      setError(e.message || 'Error de conexión al backend.');
    } finally {
      setIsLoading(false);
    }
  };

  const resultColor = (status: string) => {
    if (status === '200' || status === 'success') return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    if (status === 'ALREADY_LIKED' || status === 'ALREADY') return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
    return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
  };

  const missionIcon = () => {
    const mt = MISSION_TYPES.find(t => t.value === missionType);
    if (!mt) return <ThumbsUp size={14} />;
    const Icon = mt.icon;
    return <Icon size={14} />;
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className={triggerClassName}
      >
        🧪 Test de Concurrencia
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-md" onClick={() => setIsOpen(false)} />
      <div className="relative w-full max-w-2xl bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
          <h3 className="font-semibold text-white flex items-center gap-2">
            🧪 Test de Concurrencia
          </h3>
          <button onClick={() => setIsOpen(false)} className="text-slate-500 hover:text-slate-300 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto custom-scrollbar space-y-5">
          {/* Accounts Multi-select */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 block">
              Cuentas ({selectedAccountIds.size} seleccionadas)
            </label>
            <div className="max-h-36 overflow-y-auto space-y-1.5 pr-1 custom-scrollbar">
              {accounts.length === 0 && (
                <p className="text-slate-500 text-xs italic py-3 text-center">No hay cuentas activas disponibles</p>
              )}
              {accounts.map(acc => (
                <label
                  key={acc.id}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg border cursor-pointer transition-all ${
                    selectedAccountIds.has(acc.id)
                      ? 'border-indigo-500/40 bg-indigo-500/10'
                      : 'border-white/5 bg-white/[0.02] hover:bg-white/5'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedAccountIds.has(acc.id)}
                    onChange={() => toggleAccount(acc.id)}
                    className="accent-indigo-500"
                  />
                  <div className="flex flex-col min-w-0">
                    <span className="text-sm text-slate-200 truncate">{acc.name}</span>
                    <span className="text-[10px] text-slate-500 truncate">{acc.email}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Mission Type Dropdown */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">Tipo de Misión</label>
            <div className="flex gap-2">
              {MISSION_TYPES.map(mt => {
                const Icon = mt.icon;
                return (
                  <button
                    key={mt.value}
                    type="button"
                    onClick={() => setMissionType(mt.value)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                      missionType === mt.value
                        ? 'border-indigo-500/50 bg-indigo-500/10 text-indigo-300 shadow-[0_0_12px_rgba(99,102,241,0.2)]'
                        : 'border-white/5 bg-white/[0.02] text-slate-500 hover:bg-white/5 hover:text-slate-300'
                    }`}
                  >
                    <Icon size={14} />
                    {mt.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Post URL */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">URL del Post</label>
            <input
              type="text"
              value={postUrl}
              onChange={e => setPostUrl(e.target.value)}
              placeholder="https://www.linkedin.com/posts/..."
              className="w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all"
            />
          </div>

          {/* Concurrency Slider */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex justify-between">
              <span>Nivel de Concurrencia</span>
              <span className="text-indigo-400 font-mono">{concurrency}</span>
            </label>
            <input
              type="range"
              min={1}
              max={10}
              value={concurrency}
              onChange={e => setConcurrency(parseInt(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
            <div className="flex justify-between text-[10px] text-slate-600 mt-1">
              <span>1 (secuencial)</span>
              <span>10 (máximo paralelo)</span>
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={isLoading || selectedAccountIds.size === 0 || !postUrl}
            className="w-full py-3 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm transition-all shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] flex items-center justify-center gap-2"
          >
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : null}
            {isLoading ? 'LANZANDO TEST...' : '🚀 Lanzar Test'}
          </button>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-rose-500/20 bg-rose-500/5 text-sm text-rose-400">
              <AlertTriangle size={16} />
              {error}
            </div>
          )}

          {/* Results Table */}
          {results.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-400" />
                Resultados ({results.length})
              </h4>
              <div className="rounded-xl border border-white/5 bg-slate-900/40 overflow-hidden shadow-xl">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-white/[0.02] border-b border-white/5">
                    <tr>
                      <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-slate-500">Cuenta</th>
                      <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-slate-500">Mission ID</th>
                      <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-slate-500">Resultado</th>
                      <th className="px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-slate-500">Duración</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {results.map((r, idx) => (
                      <tr key={idx} className="hover:bg-white/[0.01] transition-colors">
                        <td className="px-4 py-3 text-sm text-slate-200">{r.account_name}</td>
                        <td className="px-4 py-3 text-sm font-mono text-slate-500">
                          {r.mission_id ? `#${r.mission_id}` : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[11px] font-bold uppercase tracking-wider ${resultColor(r.status)}`}>
                            {r.status === '200' || r.status === 'success' ? <CheckCircle2 size={11} /> :
                             r.status === 'ALREADY_LIKED' || r.status === 'ALREADY' ? <AlertTriangle size={11} /> :
                             <X size={11} />}
                            {r.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-400">{r.duration_ms}ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

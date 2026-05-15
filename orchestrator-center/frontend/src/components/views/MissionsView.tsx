import React, { useState } from 'react';
import { TerminalSquare, Play, History, CheckCircle2, XCircle, Loader2, MessageSquare, ThumbsUp, Users, User, Sparkles, Type, Clock, ChevronDown, ChevronUp } from 'lucide-react';
import { Account, Mission, LogEntry } from '../../hooks/useOrchestrator';
import { ConcurrentTestModal } from '../ConcurrentTestModal';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface MissionsViewProps {
  accounts: Account[];
  missions: Mission[];
  logs?: LogEntry[];
  onLaunchMission: (accountId: number, tasks: any[]) => Promise<void>;
}

type AccountMode = 'single' | 'multi' | 'all';
type CommentMode = 'literal' | 'ai';

export function MissionsView({ accounts, missions, logs = [], onLaunchMission }: MissionsViewProps) {
  const [accountMode, setAccountMode] = useState<AccountMode>('single');
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [selectedAccounts, setSelectedAccounts] = useState<Set<number>>(new Set());
  const [postUrl, setPostUrl] = useState('');
  const [commentText, setCommentText] = useState('');
  const [commentMode, setCommentMode] = useState<CommentMode>('literal');
  const [isLaunching, setIsLaunching] = useState(false);
  const [enableLike, setEnableLike] = useState(true);
  const [enableComment, setEnableComment] = useState(true);
  const [expandedMission, setExpandedMission] = useState<number | null>(null);
  const [delayMin, setDelayMin] = useState(30);
  const [delayMax, setDelayMax] = useState(90);

  const activeAccounts = accounts.filter(a => a.status === 'active');

  const toggleAccount = (id: number) => {
    setSelectedAccounts(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const getTargetAccountIds = (): number[] => {
    if (accountMode === 'all') return activeAccounts.map(a => a.id);
    if (accountMode === 'multi') return Array.from(selectedAccounts);
    return selectedAccount ? [parseInt(selectedAccount)] : [];
  };

  const isMultiAccount = accountMode !== 'single';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!postUrl) return;
    if (!enableLike && !enableComment) return;
    if (enableComment && !commentText) return;

    const accountIds = getTargetAccountIds();
    if (accountIds.length === 0) return;

    setIsLaunching(true);
    const tasks: any[] = [];
    if (enableLike) tasks.push({ type: 'reaction', payload: { url: postUrl, reaction_type: 'LIKE' } });
    if (enableComment && commentText) tasks.push({ type: 'comment', payload: { url: postUrl, text: commentText } });

    try {
      if (!isMultiAccount) {
        await onLaunchMission(accountIds[0], tasks);
      } else {
        // Bulk endpoint
        const res = await fetch(`${API_URL}/missions/bulk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            account_ids: accountMode === 'all' ? [] : accountIds,
            tasks,
            comment_mode: commentMode,
            delay_min: delayMin,
            delay_max: delayMax,
          }),
        });
        if (!res.ok) {
          const err = await res.json();
          alert(`Error: ${err.detail}`);
          return;
        }
      }
      setPostUrl('');
      setCommentText('');
    } finally {
      setIsLaunching(false);
    }
  };

  const launchLabel = () => {
    const actions = [enableLike && 'Like', enableComment && 'Comment'].filter(Boolean).join(' + ');
    const n = getTargetAccountIds().length;
    if (accountMode === 'all') return `EJECUTAR EN TODAS (${activeAccounts.length}) · ${actions}`;
    if (accountMode === 'multi') return `EJECUTAR EN ${n} CUENTA${n !== 1 ? 'S' : ''} · ${actions}`;
    return `EJECUTAR MISIÓN · ${actions}`;
  };

  const canSubmit = !isLaunching && postUrl && (enableLike || enableComment) && (!enableComment || commentText) && getTargetAccountIds().length > 0;

  return (
    <div suppressHydrationWarning className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-500">

      {/* ── New Mission Form ── */}
      <section className="rounded-xl border border-white/5 bg-slate-900/40 p-6 backdrop-blur-sm shadow-xl">
        <h3 className="text-lg font-medium text-slate-200 flex items-center gap-2 mb-6">
          <Play className="text-indigo-500" size={18} />
          Lanzar Nueva Misión
        </h3>

        <div className="flex justify-end mb-4">
          <ConcurrentTestModal triggerClassName="px-4 py-2 rounded-lg bg-gradient-to-r from-violet-500 to-indigo-600 hover:from-violet-600 hover:to-indigo-700 text-white font-medium text-xs shadow-[0_0_15px_rgba(99,102,241,0.3)] hover:shadow-[0_0_25px_rgba(99,102,241,0.5)] transition-all" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">

          {/* ── Row 1: Account Mode Tabs ── */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 block">Modo de Cuentas</label>
            <div className="flex gap-2">
              {(['single', 'multi', 'all'] as AccountMode[]).map(m => {
                const icons = { single: User, multi: Users, all: Users };
                const labels = { single: 'Una Cuenta', multi: 'Múltiples', all: 'Todas' };
                const Icon = icons[m];
                return (
                  <button key={m} type="button" onClick={() => setAccountMode(m)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                      accountMode === m
                        ? 'border-indigo-500/50 bg-indigo-500/10 text-indigo-300 shadow-[0_0_12px_rgba(99,102,241,0.2)]'
                        : 'border-white/5 bg-white/[0.02] text-slate-500 hover:bg-white/5 hover:text-slate-300'
                    }`}
                  >
                    <Icon size={14} />
                    {labels[m]}
                  </button>
                );
              })}
            </div>
          </div>

          {/* ── Row 2: Account Selector ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              {accountMode === 'single' && (
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">Identidad</label>
                  <select
                    value={selectedAccount}
                    onChange={e => setSelectedAccount(e.target.value)}
                    className="w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all appearance-none"
                  >
                    <option value="">Selecciona una cuenta...</option>
                    {activeAccounts.map(acc => (
                      <option key={acc.id} value={acc.id}>{acc.name} ({acc.email})</option>
                    ))}
                  </select>
                </div>
              )}

              {accountMode === 'multi' && (
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">
                    Seleccionar Cuentas ({selectedAccounts.size} seleccionadas)
                  </label>
                  <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1 custom-scrollbar">
                    {activeAccounts.map(acc => (
                      <label key={acc.id} className={`flex items-center gap-3 px-3 py-2 rounded-lg border cursor-pointer transition-all ${
                        selectedAccounts.has(acc.id)
                          ? 'border-indigo-500/40 bg-indigo-500/10'
                          : 'border-white/5 bg-white/[0.02] hover:bg-white/5'
                      }`}>
                        <input
                          type="checkbox"
                          checked={selectedAccounts.has(acc.id)}
                          onChange={() => toggleAccount(acc.id)}
                          className="accent-indigo-500"
                        />
                        <div className="flex flex-col min-w-0">
                          <span className="text-sm text-slate-200 truncate">{acc.name}</span>
                          <span className="text-[10px] text-slate-500 truncate">{acc.email}</span>
                        </div>
                      </label>
                    ))}
                    {activeAccounts.length === 0 && (
                      <p className="text-slate-500 text-xs italic py-4 text-center">No hay cuentas activas</p>
                    )}
                  </div>
                </div>
              )}

              {accountMode === 'all' && (
                <div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5">
                  <Users className="text-emerald-400 shrink-0" size={16} />
                  <div>
                    <p className="text-sm font-medium text-emerald-300">{activeAccounts.length} cuentas activas en cola</p>
                    <p className="text-[11px] text-slate-500">Se ejecutarán secuencialmente con delays humanos</p>
                  </div>
                </div>
              )}

              {/* URL */}
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

              {/* Action Toggles */}
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 block">Acciones</label>
                <div className="flex gap-3">
                  <button type="button" onClick={() => setEnableLike(!enableLike)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                      enableLike
                        ? 'border-blue-500/40 bg-blue-500/10 text-blue-400 shadow-[0_0_12px_rgba(59,130,246,0.15)]'
                        : 'border-white/5 bg-white/[0.02] text-slate-500 hover:bg-white/5'
                    }`}
                  >
                    <ThumbsUp size={16} />Like
                  </button>
                  <button type="button" onClick={() => setEnableComment(!enableComment)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                      enableComment
                        ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.15)]'
                        : 'border-white/5 bg-white/[0.02] text-slate-500 hover:bg-white/5'
                    }`}
                  >
                    <MessageSquare size={16} />Comentar
                  </button>
                </div>
              </div>
            </div>

            {/* ── Right Column: Comment + Options ── */}
            <div className="space-y-4 flex flex-col">
              {enableComment ? (
                <>
                  {/* Comment Mode Toggle */}
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 block">Modo de Comentario</label>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => setCommentMode('literal')}
                        className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium transition-all ${
                          commentMode === 'literal'
                            ? 'border-slate-400/40 bg-slate-400/10 text-slate-300'
                            : 'border-white/5 bg-white/[0.02] text-slate-500 hover:bg-white/5'
                        }`}
                      >
                        <Type size={13} />
                        Literal
                      </button>
                      <button type="button" onClick={() => setCommentMode('ai')}
                        className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium transition-all ${
                          commentMode === 'ai'
                            ? 'border-violet-500/40 bg-violet-500/10 text-violet-300 shadow-[0_0_12px_rgba(139,92,246,0.2)]'
                            : 'border-white/5 bg-white/[0.02] text-slate-500 hover:bg-white/5'
                        }`}
                      >
                        <Sparkles size={13} />
                        IA Única
                      </button>
                    </div>
                    {commentMode === 'ai' && (
                      <p className="text-[11px] text-violet-400/80 mt-1.5 flex items-center gap-1">
                        <Sparkles size={10} />
                        Cada cuenta recibirá una variante única que expresa la misma idea
                      </p>
                    )}
                  </div>

                  <div className="flex-1">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">
                      Comentario {commentMode === 'ai' ? '(Base — se reinterpretará)' : '(Exacto)'}
                    </label>
                    <textarea
                      value={commentText}
                      onChange={e => setCommentText(e.target.value)}
                      placeholder="Escribe el comentario..."
                      className={`w-full h-[90px] bg-[#020617] border rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none transition-all resize-none ${
                        commentMode === 'ai' ? 'border-violet-500/20 focus:border-violet-500' : 'border-white/10 focus:border-indigo-500'
                      }`}
                    />
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-slate-600 text-sm italic border border-dashed border-white/5 rounded-lg">
                  Solo se enviará el Like
                </div>
              )}

              {/* Delay Config (only for multi/all) */}
              {isMultiAccount && (
                <div className="rounded-lg border border-amber-500/10 bg-amber-500/5 p-3 space-y-2">
                  <div className="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase tracking-wider">
                    <Clock size={12} />
                    Delay Humano Entre Cuentas
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex-1">
                      <label className="text-[10px] text-slate-500 mb-1 block">Mínimo (seg)</label>
                      <input
                        type="number" min={5} max={300} value={delayMin}
                        onChange={e => setDelayMin(parseInt(e.target.value) || 30)}
                        className="w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                      />
                    </div>
                    <div className="text-slate-600 mt-4">—</div>
                    <div className="flex-1">
                      <label className="text-[10px] text-slate-500 mb-1 block">Máximo (seg)</label>
                      <input
                        type="number" min={5} max={600} value={delayMax}
                        onChange={e => setDelayMax(parseInt(e.target.value) || 90)}
                        className="w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                      />
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-500">Cada cuenta esperará un tiempo aleatorio entre {delayMin}s y {delayMax}s para parecer humana</p>
                </div>
              )}

              <button
                type="submit"
                disabled={!canSubmit}
                className="w-full py-3 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm transition-all shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] flex items-center justify-center gap-2"
              >
                {isLaunching ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} />}
                {isLaunching ? 'ENVIANDO A COLA...' : launchLabel()}
              </button>
            </div>
          </div>
        </form>
      </section>

      {/* ── Mission History ── */}
      <section>
        <h3 className="text-lg font-medium text-slate-200 flex items-center gap-2 mb-6">
          <History className="text-indigo-500" size={18} />
          Historial de Misiones
        </h3>

        <div className="rounded-xl border border-white/5 bg-slate-900/40 overflow-hidden shadow-xl">
          <table className="w-full text-left border-collapse">
            <thead className="bg-white/[0.02] border-b border-white/5">
              <tr>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">ID</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Agente</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Origen</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Tareas</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Estado</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Fecha</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {missions.length > 0 ? missions.map(m => (
                <React.Fragment key={m.id}>
                  <tr className="hover:bg-white/[0.01] transition-colors group">
                    <td className="px-6 py-4 text-sm font-mono text-slate-500">#{m.id}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-slate-800 border border-white/5 flex items-center justify-center text-[10px] font-bold text-indigo-400 uppercase">
                          {accounts.find(a => a.id === m.account_id)?.name.charAt(0) || '?'}
                        </div>
                        <span className="text-sm text-slate-200">
                          {accounts.find(a => a.id === m.account_id)?.name || 'Unknown'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <SourceBadge source={m.source} />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1.5">
                        {m.tasks?.map((t: any, idx: number) => (
                          <span key={idx} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            t.type === 'reaction' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                            t.type === 'comment' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                            'bg-slate-700/50 text-slate-400 border border-white/5'
                          }`}>
                            {t.type === 'reaction' ? <ThumbsUp size={10} /> : <MessageSquare size={10} />}
                            {t.type}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4"><StatusBadge status={m.status} /></td>
                    <td className="px-6 py-4 text-xs text-slate-400">{new Date(m.created_at).toLocaleString()}</td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => setExpandedMission(expandedMission === m.id ? null : m.id)}
                        className={`text-xs font-medium transition-all flex items-center gap-1 ${
                          expandedMission === m.id ? 'text-indigo-300' : 'text-indigo-400 opacity-0 group-hover:opacity-100'
                        }`}
                      >
                        {expandedMission === m.id ? <><ChevronUp size={12} />Ocultar</> : <><ChevronDown size={12} />Ver Logs</>}
                      </button>
                    </td>
                  </tr>
                  {expandedMission === m.id && (
                    <tr>
                      <td colSpan={7} className="px-6 py-4 bg-slate-950/50 border-t border-white/5">
                        <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
                          <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">Logs del Sistema (últimos)</div>
                          {logs.length > 0 ? logs.map((log) => (
                            <div key={log.id} className={`flex items-start gap-3 text-xs px-3 py-2 rounded-lg ${
                              log.type === 'error' ? 'bg-rose-500/5 border border-rose-500/10' :
                              log.type === 'success' ? 'bg-emerald-500/5 border border-emerald-500/10' :
                              log.type === 'warning' ? 'bg-amber-500/5 border border-amber-500/10' :
                              'bg-white/[0.01] border border-white/5'
                            }`}>
                              <span className={`text-[10px] font-bold uppercase w-16 shrink-0 ${
                                log.type === 'error' ? 'text-rose-400' :
                                log.type === 'success' ? 'text-emerald-400' :
                                log.type === 'warning' ? 'text-amber-400' :
                                'text-slate-500'
                              }`}>{log.type}</span>
                              <span className="text-slate-300 flex-1">{log.msg}</span>
                              <span className="text-slate-600 text-[10px] shrink-0">{log.time}</span>
                            </div>
                          )) : (
                            <div className="text-slate-600 text-xs italic py-2">No hay logs disponibles.</div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )) : (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-500 text-sm italic">
                    No se han registrado misiones aún.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}



function SourceBadge({ source }: { source?: string }) {
  const configs: any = {
    manual: { label: 'Manual', color: 'text-slate-400 bg-slate-500/10 border-slate-500/20', icon: '👤' },
    autopilot: { label: 'AutoPilot', color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20', icon: '🤖' },
    autopilot_notification: { label: 'Notificación', color: 'text-violet-400 bg-violet-500/10 border-violet-500/20', icon: '🔔' },
    concurrent_test: { label: 'Test', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20', icon: '🧪' },
  };
  const key = (source || 'manual') as keyof typeof configs;
  const config = configs[key] || configs.manual;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider ${config.color}`}>
      <span className="text-[11px]">{config.icon}</span>
      {config.label}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const configs: any = {
    pending: { label: 'Pendiente', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20', icon: Loader2 },
    running: { label: 'Ejecutando', color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20', icon: Loader2 },
    completed: { label: 'Completada', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', icon: CheckCircle2 },
    failed: { label: 'Fallida', color: 'text-rose-400 bg-rose-500/10 border-rose-500/20', icon: XCircle },
  };
  const config = configs[status] || configs.pending;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-bold uppercase tracking-wider ${config.color}`}>
      <Icon size={12} className={status === 'running' || status === 'pending' ? 'animate-spin' : ''} />
      {config.label}
    </span>
  );
}

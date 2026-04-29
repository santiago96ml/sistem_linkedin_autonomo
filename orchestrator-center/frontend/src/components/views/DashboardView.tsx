import React from 'react';
import { ChevronRight, Loader2 } from 'lucide-react';
import { LogEntry, Stats } from '../../hooks/useOrchestrator';

interface DashboardViewProps {
  logs: LogEntry[];
  stats: Stats;
}

export function DashboardView({ logs, stats }: DashboardViewProps) {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Stats Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard 
          label="Misiones Activas" 
          value={stats.active_missions} 
          sub="Ejecutándose ahora" 
          color="indigo" 
        />
        <StatCard 
          label="Tasa de Éxito" 
          value={`${stats.success_rate}%`} 
          sub="Últimas 24h" 
          color="emerald" 
        />
        <StatCard 
          label="Estado Sistema" 
          value={stats.system_status.toUpperCase()} 
          sub="Cloud Latency: 42ms" 
          color={stats.system_status === 'nominal' ? 'emerald' : 'rose'} 
        />
      </div>

      {/* Real-time Logs Terminal */}
      <section className="pb-8">
        <h3 className="text-lg font-medium text-slate-200 flex items-center gap-2 mb-6">
          <ChevronRight className="text-indigo-500" />
          Real-time Telemetry
        </h3>
        
        <div className="relative rounded-xl border border-white/10 bg-[#020617] shadow-2xl overflow-hidden group">
          <div className="h-10 bg-slate-900/80 border-b border-white/10 flex items-center px-4 justify-between">
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-rose-500/20 border border-rose-500/50"></div>
              <div className="w-3 h-3 rounded-full bg-amber-500/20 border border-amber-500/50"></div>
              <div className="w-3 h-3 rounded-full bg-emerald-500/20 border border-emerald-500/50"></div>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              LIVE STREAM
            </div>
          </div>

          <div className="p-5 font-mono text-[13px] leading-relaxed h-[400px] overflow-y-auto custom-scrollbar">
            {logs.length > 0 ? logs.map((log) => (
              <div key={log.id} className="flex gap-3 mb-1.5 hover:bg-white/[0.02] px-2 py-0.5 rounded transition-colors">
                <span className="text-slate-600">[{log.time}]</span>
                <span className={`
                  ${log.type === 'info' ? 'text-slate-400' : ''}
                  ${log.type === 'warning' ? 'text-amber-400 drop-shadow-[0_0_2px_rgba(251,191,36,0.8)]' : ''}
                  ${log.type === 'success' ? 'text-emerald-400 drop-shadow-[0_0_2px_rgba(52,211,153,0.8)]' : ''}
                  ${log.type === 'error' ? 'text-rose-400 drop-shadow-[0_0_2px_rgba(244,63,94,0.8)]' : ''}
                `}>
                  [{log.source}]
                </span>
                <span className="text-slate-300">{log.msg}</span>
              </div>
            )) : (
              <div className="text-slate-600 italic">No logs available.</div>
            )}
            <div className="flex gap-3 px-2 py-0.5 animate-pulse mt-2">
              <Loader2 size={14} className="text-indigo-400 animate-spin mt-0.5" />
              <span className="text-slate-500 italic">Listening for events...</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value, sub, color }: { label: string, value: any, sub: string, color: string }) {
  const colorMap: any = {
    indigo: 'from-indigo-500/20 to-indigo-500/5 text-indigo-400 border-indigo-500/20',
    emerald: 'from-emerald-500/20 to-emerald-500/5 text-emerald-400 border-emerald-500/20',
    rose: 'from-rose-500/20 to-rose-500/5 text-rose-400 border-rose-500/20',
  };

  return (
    <div className={`rounded-xl border bg-gradient-to-br ${colorMap[color]} p-6 backdrop-blur-sm shadow-lg`}>
      <p className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-1">{label}</p>
      <h4 className="text-3xl font-bold text-white mb-1">{value}</h4>
      <p className="text-[11px] text-slate-400">{sub}</p>
    </div>
  );
}

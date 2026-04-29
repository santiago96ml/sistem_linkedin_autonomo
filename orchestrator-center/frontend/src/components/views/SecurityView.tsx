import React from 'react';
import { Shield, Lock, AlertTriangle, Eye, Activity } from 'lucide-react';
import { LogEntry, Stats } from '../../hooks/useOrchestrator';

interface SecurityViewProps {
  logs: LogEntry[];
  stats: Stats;
}

export function SecurityView({ logs, stats }: SecurityViewProps) {
  // Filter security-related logs
  const securityLogs = logs.filter(l => 
    l.msg.toLowerCase().includes('auth') || 
    l.msg.toLowerCase().includes('identity') || 
    l.msg.toLowerCase().includes('security') ||
    l.type === 'error' ||
    l.type === 'warning'
  );

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-top-4 duration-500">
      
      {/* Security Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-xl border border-white/5 bg-slate-900/40 p-6 flex items-start gap-4">
          <div className="w-12 h-12 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
            <Shield className="text-indigo-400" />
          </div>
          <div>
            <h4 className="text-white font-medium">Session Protection</h4>
            <p className="text-xs text-slate-400 mt-1">Todas las sesiones de Playwright están aisladas y encriptadas localmente.</p>
            <div className="mt-3 flex items-center gap-2 text-[10px] font-bold text-emerald-400 uppercase tracking-widest">
              <Lock size={12} />
              Active AES-256
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-white/5 bg-slate-900/40 p-6 flex items-start gap-4">
          <div className="w-12 h-12 rounded-lg bg-amber-500/10 flex items-center justify-center border border-amber-500/20">
            <Activity className="text-amber-400" />
          </div>
          <div>
            <h4 className="text-white font-medium">System Integrity</h4>
            <p className="text-xs text-slate-400 mt-1">El orquestador monitoriza bloqueos y retos 2FA en tiempo real.</p>
            <div className="mt-3 flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              <Eye size={12} />
              Stealth Mode Enabled
            </div>
          </div>
        </div>
      </div>

      {/* Security Event Log */}
      <section>
        <h3 className="text-lg font-medium text-slate-200 flex items-center gap-2 mb-6">
          <AlertTriangle className="text-amber-500" size={18} />
          Security Events
        </h3>
        
        <div className="rounded-xl border border-white/5 bg-slate-900/40 divide-y divide-white/5 shadow-xl">
          {securityLogs.length > 0 ? securityLogs.map(log => (
            <div key={log.id} className="p-4 flex items-center justify-between hover:bg-white/[0.01] transition-colors">
              <div className="flex items-center gap-4">
                <div className={`w-2 h-2 rounded-full ${
                  log.type === 'error' ? 'bg-rose-500' : 'bg-amber-500'
                }`}></div>
                <div>
                  <p className="text-sm text-slate-200">{log.msg}</p>
                  <p className="text-[10px] text-slate-500 uppercase font-bold mt-0.5">{log.source} • {log.time}</p>
                </div>
              </div>
              <button className="px-3 py-1 text-[10px] font-bold text-slate-400 border border-white/10 rounded hover:bg-white/5 transition-all uppercase tracking-widest">
                Detail
              </button>
            </div>
          )) : (
            <div className="p-12 text-center text-slate-500 text-sm italic">
              No se han detectado eventos de seguridad críticos.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

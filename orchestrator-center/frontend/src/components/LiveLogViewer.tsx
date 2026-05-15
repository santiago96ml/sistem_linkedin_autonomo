"use client";

import React from 'react';
import { Terminal, Wifi, WifiOff, Loader2 } from 'lucide-react';
import { useMissionLogs, LogEntry } from '@/hooks/useMissionLogs';

interface LiveLogViewerProps {
  missionId: number;
  height?: string;
  className?: string;
}

const levelColors: Record<string, string> = {
  info: 'text-slate-300', success: 'text-emerald-400',
  warning: 'text-amber-400', error: 'text-rose-400',
};

function LogLine({ entry }: { entry: LogEntry }) {
  const time = entry.timestamp
    ? new Date(entry.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '--:--:--';
  return (
    <div className={`flex gap-3 px-3 py-0.5 text-[13px] leading-6 font-mono ${levelColors[entry.level] || 'text-slate-300'}`}>
      <span className="text-slate-600 w-16 shrink-0">[{time}]</span>
      <span className="w-14 shrink-0 text-[10px] uppercase tracking-wider font-semibold opacity-60">{entry.level}</span>
      <span className="break-words">{entry.message}</span>
    </div>
  );
}

export function LiveLogViewer({ missionId, height = '300px', className = '' }: LiveLogViewerProps) {
  const { logs, connected, error } = useMissionLogs(missionId);
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = React.useState(true);

  React.useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  return (
    <div className={`rounded-xl border border-white/5 bg-slate-950 overflow-hidden ${className}`}>
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-slate-900/50">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-indigo-400" />
          <span className="text-xs font-medium text-slate-400">Mission Logs</span>
          <span className="text-[10px] text-slate-600">#{missionId}</span>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <span className="flex items-center gap-1 text-[10px] text-emerald-400"><Wifi size={10} /> Live</span>
          ) : error ? (
            <span className="flex items-center gap-1 text-[10px] text-rose-400"><WifiOff size={10} /> Error</span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] text-amber-400"><Loader2 size={10} className="animate-spin" /> Connecting</span>
          )}
          <span className="text-[10px] text-slate-600">{logs.length} lines</span>
        </div>
      </div>
      <div ref={scrollRef} className="overflow-y-auto font-mono" style={{ height }}
        onScroll={(e) => { const el = e.currentTarget; setAutoScroll(el.scrollHeight - el.scrollTop - el.clientHeight < 50); }}>
        {logs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-600"><span className="text-xs">Waiting for logs...</span></div>
        ) : (
          logs.map((entry, i) => <LogLine key={i} entry={entry} />)
        )}
      </div>
    </div>
  );
}

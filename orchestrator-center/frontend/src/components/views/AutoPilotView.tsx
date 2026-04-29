import React, { useState } from 'react';
import { Target, Plus, Play, Pause, Trash2, Clock, Key, AlignLeft, ShieldCheck, Zap } from 'lucide-react';
import { TargetProfile } from '../../hooks/useOrchestrator';

interface AutoPilotViewProps {
  targets: TargetProfile[];
  onAddTarget: (data: Omit<TargetProfile, 'id' | 'status'>) => Promise<void>;
  onToggleTarget: (id: number) => Promise<void>;
  onDeleteTarget: (id: number) => Promise<void>;
}

export function AutoPilotView({ targets, onAddTarget, onToggleTarget, onDeleteTarget }: AutoPilotViewProps) {
  const [url, setUrl] = useState('');
  const [start, setStart] = useState('09:00');
  const [end, setEnd] = useState('18:00');
  const [keywords, setKeywords] = useState('IA, Inteligencia Artificial, automatización');
  const [baseComment, setBaseComment] = useState('¡Excelente aporte sobre este tema tan clave hoy en día!');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;
    
    await onAddTarget({
      linkedin_url: url,
      schedule_start: start,
      schedule_end: end,
      cta_keywords: keywords,
      comment_base: baseComment
    });
    
    setUrl('');
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-500">
      
      {/* Informational Header */}
      <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-6 shadow-lg relative overflow-hidden">
        <div className="absolute -right-10 -top-10 text-blue-500/10">
          <Zap size={150} />
        </div>
        <h3 className="text-xl font-bold text-blue-400 flex items-center gap-2 mb-3">
          <ShieldCheck size={24} />
          Agente de Monitoreo Autónomo
        </h3>
        <p className="text-slate-300 text-sm max-w-3xl leading-relaxed">
          El Piloto Automático revisará periódicamente los perfiles configurados dentro de su horario activo. 
          Si detecta una publicación nueva que contenga las <strong>Palabras Clave (CTAs)</strong>, activará 
          automáticamente a todas las cuentas disponibles para dar Like y comentar usando IA basada en tu mensaje original.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Form Column */}
        <div className="lg:col-span-1">
          <section className="rounded-xl border border-white/5 bg-slate-900/40 p-6 backdrop-blur-sm shadow-xl sticky top-6">
            <h3 className="text-lg font-medium text-slate-200 flex items-center gap-2 mb-6">
              <Plus className="text-indigo-500" size={18} />
              Añadir Objetivo
            </h3>
            
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block flex items-center gap-1.5">
                  <Target size={14} /> URL del Perfil
                </label>
                <input 
                  type="text" 
                  value={url} onChange={e => setUrl(e.target.value)} required
                  placeholder="https://www.linkedin.com/in/..." 
                  className="w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block flex items-center gap-1.5">
                    <Clock size={14} /> Inicio
                  </label>
                  <input 
                    type="time" 
                    value={start} onChange={e => setStart(e.target.value)} required
                    className="w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block flex items-center gap-1.5">
                    <Clock size={14} /> Fin
                  </label>
                  <input 
                    type="time" 
                    value={end} onChange={e => setEnd(e.target.value)} required
                    className="w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block flex items-center gap-1.5">
                  <Key size={14} /> CTAs (Separados por coma)
                </label>
                <input 
                  type="text" 
                  value={keywords} onChange={e => setKeywords(e.target.value)}
                  placeholder="ej: IA, curso, gratis" 
                  className="w-full bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all"
                />
                <p className="text-[10px] text-slate-500 mt-1 text-right">Dejar vacío para actuar en TODOS los posts</p>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block flex items-center gap-1.5">
                  <AlignLeft size={14} /> Comentario Base (IA)
                </label>
                <textarea 
                  value={baseComment} onChange={e => setBaseComment(e.target.value)}
                  placeholder="Comentario que la IA usará como base para variar..." 
                  className="w-full h-24 bg-[#020617] border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all resize-none"
                />
              </div>

              <button 
                type="submit"
                disabled={!url}
                className="w-full py-2.5 rounded-lg bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 border border-indigo-500/30 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-sm transition-all"
              >
                AÑADIR AL MONITOR
              </button>
            </form>
          </section>
        </div>

        {/* List Column */}
        <div className="lg:col-span-2">
          <section className="space-y-4">
            <h3 className="text-lg font-medium text-slate-200 flex items-center gap-2 mb-2">
              <Target className="text-indigo-500" size={18} />
              Perfiles en Monitoreo ({targets.length})
            </h3>

            {targets.length === 0 ? (
              <div className="rounded-xl border border-dashed border-white/10 p-12 text-center text-slate-500 text-sm">
                No hay perfiles configurados en el Piloto Automático.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {targets.map(target => (
                  <div key={target.id} className="rounded-xl border border-white/5 bg-slate-900/60 p-5 shadow-lg group relative overflow-hidden transition-all hover:bg-slate-900/80">
                    {/* Status Indicator line */}
                    <div className={`absolute left-0 top-0 bottom-0 w-1 ${target.status === 'active' ? 'bg-emerald-500' : 'bg-slate-600'}`}></div>
                    
                    <div className="flex justify-between items-start pl-2">
                      <div className="min-w-0 pr-4">
                        <div className="flex items-center gap-3 mb-1">
                          <h4 className="text-sm font-bold text-slate-200 truncate" title={target.linkedin_url}>
                            {target.linkedin_url.split('/in/')[1]?.replace('/', '') || target.linkedin_url}
                          </h4>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                            target.status === 'active' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' : 'border-slate-500/20 bg-slate-500/10 text-slate-400'
                          }`}>
                            {target.status}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 truncate">{target.linkedin_url}</p>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button 
                          onClick={() => onToggleTarget(target.id)}
                          className={`w-8 h-8 rounded-lg border flex items-center justify-center transition-all ${
                            target.status === 'active' ? 'border-amber-500/20 text-amber-400 hover:bg-amber-500/10' : 'border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10'
                          }`}
                          title={target.status === 'active' ? "Pausar" : "Reanudar"}
                        >
                          {target.status === 'active' ? <Pause size={14} /> : <Play size={14} />}
                        </button>
                        <button 
                          onClick={() => onDeleteTarget(target.id)}
                          className="w-8 h-8 rounded-lg border border-rose-500/20 text-rose-400 hover:bg-rose-500/10 flex items-center justify-center transition-all"
                          title="Eliminar"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-2 gap-4 pl-2">
                      <div>
                        <p className="text-[10px] font-bold uppercase text-slate-500 mb-0.5 flex items-center gap-1"><Clock size={10}/> Horario</p>
                        <p className="text-xs text-slate-300">{target.schedule_start} — {target.schedule_end}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase text-slate-500 mb-0.5 flex items-center gap-1"><Key size={10}/> Keywords (CTAs)</p>
                        <p className="text-xs text-slate-300 truncate" title={target.cta_keywords || 'Todos'}>
                          {target.cta_keywords || <span className="italic text-slate-500">Cualquier post</span>}
                        </p>
                      </div>
                    </div>
                    
                    <div className="mt-3 pl-2">
                      <p className="text-[10px] font-bold uppercase text-slate-500 mb-0.5 flex items-center gap-1"><AlignLeft size={10}/> Comentario (Base)</p>
                      <p className="text-xs text-slate-400 italic bg-black/20 p-2 rounded-lg border border-white/5 line-clamp-2" title={target.comment_base || ''}>
                        "{target.comment_base}"
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

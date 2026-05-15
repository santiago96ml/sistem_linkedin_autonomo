import React, { useState } from 'react';
import { Users, MoreVertical, Server, Plus, Trash2, AlertTriangle } from 'lucide-react';
import { Account } from '../../hooks/useOrchestrator';

interface AccountsViewProps {
  accounts: Account[];
  onOpenWizard: () => void;
  onDeleteAccount: (id: number) => Promise<void>;
  onRefresh: () => void;
}

export function AccountsView({ accounts, onOpenWizard, onDeleteAccount, onRefresh }: AccountsViewProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);

  const handleDelete = async (id: number) => {
    await onDeleteAccount(id);
    setShowDeleteConfirm(null);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-medium text-slate-200 flex items-center gap-2">
          <div className="w-1.5 h-6 bg-indigo-500 rounded-full"></div>
          Linked Identities
        </h3>
        <div className="flex items-center gap-3">
          <button 
            onClick={onOpenWizard}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-sm font-medium hover:bg-indigo-500/20 transition-all shadow-[0_0_15px_rgba(99,102,241,0.1)]"
          >
            <Plus size={16} />
            Vincular Nueva
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {accounts.length > 0 ? accounts.map((acc) => (
          <div key={acc.id} className="group relative rounded-xl border border-white/5 bg-slate-900/40 backdrop-blur-sm p-5 hover:border-indigo-500/30 transition-all hover:bg-slate-900/60 shadow-lg overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl pointer-events-none"></div>
            
            {/* Delete Confirmation Overlay */}
            {showDeleteConfirm === acc.id && (
              <div className="absolute inset-0 z-20 bg-slate-950/90 backdrop-blur-sm flex flex-col items-center justify-center p-4 text-center animate-in fade-in duration-300">
                <AlertTriangle className="text-rose-500 mb-2" size={24} />
                <p className="text-xs font-bold text-slate-200 mb-1 uppercase">¿Eliminar cuenta?</p>
                <p className="text-[10px] text-slate-400 mb-4 px-4">Esta acción eliminará permanentemente la sesión y el historial asociado.</p>
                <div className="flex gap-2 w-full px-4">
                  <button 
                    onClick={() => setShowDeleteConfirm(null)}
                    className="flex-1 py-1.5 rounded bg-slate-800 text-slate-300 text-[10px] font-bold hover:bg-slate-700 transition-colors"
                  >
                    CANCELAR
                  </button>
                  <button 
                    onClick={() => handleDelete(acc.id)}
                    className="flex-1 py-1.5 rounded bg-rose-500 text-white text-[10px] font-bold hover:bg-rose-600 transition-colors shadow-[0_0_10px_rgba(244,63,94,0.3)]"
                  >
                    ELIMINAR
                  </button>
                </div>
              </div>
            )}

            <div className="flex justify-between items-start mb-4 relative z-10">
              <div className="flex gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-900 to-slate-800 border border-indigo-500/20 flex items-center justify-center font-bold text-indigo-300 shadow-inner uppercase">
                  {acc.name.charAt(0)}
                </div>
                <div>
                  <h4 className="font-medium text-slate-100 text-sm">{acc.name}</h4>
                  <p className="text-xs text-slate-400 mt-0.5">{acc.email}</p>
                </div>
              </div>
              <button 
                onClick={() => setShowDeleteConfirm(acc.id)}
                className="text-slate-500 hover:text-rose-400 p-1 rounded hover:bg-rose-500/10 transition-all opacity-0 group-hover:opacity-100"
              >
                <Trash2 size={16} />
              </button>
            </div>

            <div className="space-y-3 relative z-10">
              <div>
                <div className="flex justify-between text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1.5">
                  <span>Tasks Done</span>
                  <span className="text-indigo-400">{acc.tasks || 0}</span>
                </div>
                <div className="w-full bg-slate-800/50 rounded-full h-1.5 border border-white/5 overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-indigo-500 to-purple-500 h-1.5 rounded-full" 
                    style={{ width: `${Math.min((acc.tasks || 0) * 20, 100)}%` }}
                  ></div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-white/5">
                <div className="flex items-center gap-1.5 text-xs text-slate-400">
                  <Server size={12} />
                  {acc.proxy || 'US-East-1'}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Status</span>
                  <div className="relative flex h-2 w-2">
                    {acc.status === 'active' ? (
                      <>
                        <span className="animate-pulse absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-40"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,1)]"></span>
                      </>
                    ) : (
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500 shadow-[0_0_5px_rgba(244,63,94,1)]"></span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )) : (
          <div className="col-span-full py-20 flex flex-col items-center justify-center border border-dashed border-white/5 rounded-xl bg-slate-900/20">
            <Users size={48} className="text-slate-800 mb-4" />
            <p className="text-slate-400 text-sm font-medium">No hay identidades vinculadas.</p>
            <button 
              onClick={onOpenWizard}
              className="mt-4 text-xs text-indigo-400 hover:text-indigo-300 underline underline-offset-4"
            >
              Comenzar vinculación ahora
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

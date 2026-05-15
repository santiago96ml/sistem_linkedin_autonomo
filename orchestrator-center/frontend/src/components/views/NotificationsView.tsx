'use client';

import React, { useState, useEffect } from 'react';
import { Bell, ExternalLink, Clock, User, CheckCircle2, RefreshCcw } from 'lucide-react';

interface Notification {
  id: number;
  account_id: number;
  text: string;
  link: string;
  time_ago: string;
  timestamp: string;
  is_unread: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const NotificationsView = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchAccounts();
    fetchNotifications();
  }, [selectedAccountId]);

  const fetchAccounts = async () => {
    try {
      const res = await fetch(`${API_URL}/accounts/`);
      const data = await res.json();
      setAccounts(data);
    } catch (err) {
      console.error('Error fetching accounts:', err);
    }
  };

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const url = selectedAccountId === 'all' 
        ? `${API_URL}/notifications/` 
        : `${API_URL}/notifications/?account_id=${selectedAccountId}`;
      const res = await fetch(url);
      const data = await res.json();
      setNotifications(data);
    } catch (err) {
      console.error('Error fetching notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  const getAccountName = (id: number) => {
    const acc = accounts.find(a => a.id === id);
    return acc ? acc.name : `Cuenta ${id}`;
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Bell className="w-8 h-8 text-indigo-500" />
            Interacciones Recientes
          </h2>
          <p className="text-slate-400 mt-1">Monitoreo de actividad cronológico y filtrado.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <select 
            value={selectedAccountId}
            onChange={(e) => setSelectedAccountId(e.target.value)}
            className="bg-slate-900 border border-slate-800 text-slate-300 text-sm rounded-xl px-4 py-2 focus:ring-2 focus:ring-indigo-500/50 outline-none transition-all"
          >
            <option value="all">Todas las cuentas</option>
            {accounts.map(acc => (
              <option key={acc.id} value={acc.id}>{acc.name}</option>
            ))}
          </select>

          <button 
            onClick={fetchNotifications}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-sm font-medium transition-all"
          >
            <RefreshCcw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Sincronizar
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
            <p className="text-slate-500 font-medium">Filtrando interacciones...</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="p-12 border-2 border-dashed border-slate-800 rounded-3xl text-center space-y-4">
            <div className="w-16 h-16 bg-slate-900 rounded-full flex items-center justify-center mx-auto">
              <Bell className="w-8 h-8 text-slate-700" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-300">Sin interacciones para este filtro</h3>
              <p className="text-slate-500">No se encontraron notificaciones recientes para esta selección.</p>
            </div>
          </div>
        ) : (
          notifications.map((notif) => (
            <div 
              key={notif.id}
              className={`p-5 rounded-2xl border bg-slate-900/50 backdrop-blur-sm flex items-start gap-4 transition-all hover:bg-slate-900/80 group ${
                notif.is_unread ? 'border-indigo-500/30 ring-1 ring-indigo-500/10' : 'border-slate-800'
              }`}
            >
              <div className={`p-3 rounded-xl ${notif.is_unread ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-800 text-slate-500'}`}>
                <User className="w-5 h-5" />
              </div>
              
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                   <div className="flex items-center gap-2">
                     <span className="text-[10px] font-black uppercase tracking-widest text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">
                       {getAccountName(notif.account_id)}
                     </span>
                     <span className="text-[10px] font-medium uppercase tracking-widest text-slate-500">LinkedIn Event</span>
                   </div>
                   <span className="flex items-center gap-1 text-xs text-slate-500">
                     <Clock className="w-3 h-3" />
                     {notif.time_ago || 'Recientemente'}
                   </span>
                </div>
                <p className="text-slate-200 font-medium leading-relaxed">
                  {notif.text}
                </p>
                {notif.link && (
                  <a 
                    href={notif.link} 
                    target="_blank" 
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-bold mt-2 pt-2 border-t border-white/5 w-full transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Ver en LinkedIn
                  </a>
                )}
              </div>

              {notif.is_unread === 1 && (
                <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.8)] mt-2" />
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

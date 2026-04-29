"use client";

import React, { useState } from 'react';
import { 
  Activity, Users, Zap, Shield, Plus, 
  TerminalSquare, CheckCircle2, ChevronRight, 
  Loader2, KeyRound, Lock, Search, Target
} from 'lucide-react';

import { useOrchestrator } from '@/hooks/useOrchestrator';
import { DashboardView } from '@/components/views/DashboardView';
import { AccountsView } from '@/components/views/AccountsView';
import { MissionsView } from '@/components/views/MissionsView';
import { SecurityView } from '@/components/views/SecurityView';
import { AutoPilotView } from '@/components/views/AutoPilotView';

// --- CUSTOM STYLES FOR ANIMATIONS ---
const styles = `
  @keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
  .animate-shimmer {
    animation: shimmer 2.5s infinite linear;
  }
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.1);
  }
`;

export default function CommandHub() {
  const { 
    accounts, missions, logs, stats, targets,
    refresh, deleteAccount, 
    addTargetProfile, toggleTargetProfile, deleteTargetProfile,
    API_URL 
  } = useOrchestrator();
  
  const [activeTab, setActiveTab] = useState('orchestrator');
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState('choice'); // choice -> manual -> loading -> 2fa -> success
  
  // Form States
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [twoFACode, setTwoFACode] = useState("");

  // --- WIZARD HANDLERS ---
  const handleStartLogin = async () => {
    setWizardStep('loading');
    try {
      const res = await fetch(`${API_URL}/accounts/login/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      
      if (data.status === '2fa_required') {
        setWizardStep('2fa');
      } else if (data.status === 'success') {
        setWizardStep('success');
        setTimeout(() => { 
          setIsWizardOpen(false); 
          setWizardStep('choice');
          refresh();
        }, 2500);
      } else {
        setWizardStep('manual');
        alert("Error: Revisa tus credenciales.");
      }
    } catch (e) {
      setWizardStep('manual');
      alert("Error de conexión.");
    }
  };

  const handleVerify2FA = async () => {
    setWizardStep('loading');
    try {
      const res = await fetch(`${API_URL}/accounts/login/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code: twoFACode })
      });
      const data = await res.json();
      
      if (data.status === 'success') {
        setWizardStep('success');
        setTimeout(() => { 
          setIsWizardOpen(false); 
          setWizardStep('choice');
          refresh();
        }, 2500);
      } else {
        setWizardStep('2fa');
        alert("Código incorrecto.");
      }
    } catch (e) {
      setWizardStep('2fa');
      alert("Error de verificación.");
    }
  };

  const handleLaunchMission = async (accountId: number, tasks: any[]) => {
    try {
      const res = await fetch(`${API_URL}/missions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id: accountId, tasks })
      });
      if (res.ok) {
        // Immediate refresh to show "running" state
        refresh();
        // Then poll again after 5s and 15s so completed missions appear
        setTimeout(() => refresh(), 5000);
        setTimeout(() => refresh(), 15000);
      } else {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        alert(`Error: ${err.detail}`);
      }
    } catch (e) {
      console.error("Failed to launch mission", e);
      alert("Error de conexión al backend.");
    }
  };

  const closeWizard = () => {
    setIsWizardOpen(false);
    setTimeout(() => setWizardStep('choice'), 300);
  };

  const SidebarItem = ({ icon: Icon, label, id, isActive }: any) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300 ${
        isActive 
          ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-[inset_0_0_20px_rgba(99,102,241,0.05)]' 
          : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
      }`}
    >
      <Icon size={20} className={isActive ? 'drop-shadow-[0_0_8px_rgba(99,102,241,0.8)]' : ''} />
      <span className="font-medium text-sm tracking-wide">{label}</span>
      {isActive && <ChevronRight size={16} className="ml-auto opacity-50" />}
    </button>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30 flex overflow-hidden relative">
      <style>{styles}</style>

      {/* --- BACKGROUND DYNAMIC LIGHTING --- */}
      <div className="absolute top-[-20%] left-[-10%] w-[50vw] h-[50vw] bg-indigo-600/15 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[60vw] h-[60vw] bg-purple-700/10 rounded-full blur-[150px] pointer-events-none" />

      {/* --- SIDEBAR --- */}
      <aside className="w-64 flex-shrink-0 border-r border-white/5 bg-slate-950/50 backdrop-blur-2xl flex flex-col z-20 relative shadow-[4px_0_24px_rgba(0,0,0,0.2)]">
        <div className="h-16 flex items-center px-6 border-b border-white/5 bg-gradient-to-b from-white/[0.02] to-transparent">
          <div className="flex items-center gap-3">
            <Zap className="text-indigo-500 drop-shadow-[0_0_12px_rgba(99,102,241,0.6)]" size={24} />
            <h1 className="font-bold tracking-wider text-sm bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">
              INTELLIGENCE HUB
            </h1>
          </div>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-2">
          <SidebarItem icon={Activity} label="Orchestrator" id="orchestrator" isActive={activeTab === 'orchestrator'} />
          <SidebarItem icon={Users} label="Accounts" id="accounts" isActive={activeTab === 'accounts'} />
          <SidebarItem icon={TerminalSquare} label="Missions" id="missions" isActive={activeTab === 'missions'} />
          <SidebarItem icon={Target} label="Piloto Automático" id="autopilot" isActive={activeTab === 'autopilot'} />
          <SidebarItem icon={Shield} label="Security" id="security" isActive={activeTab === 'security'} />
        </nav>

        <div className="p-4 border-t border-white/5 bg-slate-900/30">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="relative flex h-3 w-3">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-20 ${stats.system_status === 'nominal' ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
              <span className={`relative inline-flex rounded-full h-3 w-3 shadow-[0_0_8px_rgba(16,185,129,0.8)] ${stats.system_status === 'nominal' ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-300">SYSTEM STATUS</p>
              <p className={`text-[11px] tracking-wider ${stats.system_status === 'nominal' ? 'text-emerald-400/80' : 'text-rose-400/80'}`}>
                {stats.system_status === 'nominal' ? 'All Systems Nominal' : 'Connection Error'}
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* --- MAIN CONTENT --- */}
      <main className="flex-1 flex flex-col relative z-10 h-screen overflow-hidden">
        
        {/* Top Header */}
        <header className="h-24 px-8 flex items-center justify-between border-b border-white/5 bg-slate-950/30 backdrop-blur-md">
          <div>
            <h2 className="text-2xl font-semibold text-white tracking-tight flex items-center gap-3">
              {activeTab === 'orchestrator' ? 'Command Center' : 
               activeTab === 'accounts' ? 'Account Registry' : 
               activeTab === 'missions' ? 'Mission Control' : 
               activeTab === 'autopilot' ? 'Piloto Automático' : 'Security Audit'}
            </h2>
            <div className="flex items-center gap-6 mt-2 text-sm text-slate-400">
              <span className="flex items-center gap-2">
                <Users size={14} className="text-indigo-400" />
                <strong className="text-slate-200">{stats.total_identities}</strong> Identities Linked
              </span>
              <span className="flex items-center gap-2">
                <Activity size={14} className="text-purple-400" />
                <strong className="text-slate-200">{stats.active_missions}</strong> Active Missions
              </span>
            </div>
          </div>

          <button 
            onClick={() => setIsWizardOpen(true)}
            className="group relative px-5 py-2.5 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 font-medium text-sm text-white shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] transition-all overflow-hidden"
          >
            <div className="absolute inset-0 bg-white/20 group-hover:bg-transparent transition-colors duration-300"></div>
            <div className="flex items-center gap-2 relative z-10">
              <Plus size={16} />
              Añadir Cuenta
            </div>
          </button>
        </header>

        {/* Scrollable Content View Switcher */}
        <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
          {activeTab === 'orchestrator' && <DashboardView logs={logs} stats={stats} />}
          {activeTab === 'accounts' && <AccountsView accounts={accounts} onOpenWizard={() => setIsWizardOpen(true)} onDeleteAccount={deleteAccount} />}
          {activeTab === 'missions' && <MissionsView accounts={accounts} missions={missions} logs={logs} onLaunchMission={handleLaunchMission} />}
          {activeTab === 'autopilot' && <AutoPilotView targets={targets} onAddTarget={addTargetProfile} onToggleTarget={toggleTargetProfile} onDeleteTarget={deleteTargetProfile} />}
          {activeTab === 'security' && <SecurityView logs={logs} stats={stats} />}
        </div>
      </main>

      {/* --- WIZARD ONBOARDING OVERLAY --- */}
      {isWizardOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-md" onClick={closeWizard}></div>
          <div className="relative w-full max-w-lg bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <Users size={18} className="text-indigo-400" />
                Vincular Nueva Identidad
              </h3>
              <div className="flex gap-1">
                {[1, 2, 3].map(i => (
                  <div key={i} className={`h-1.5 w-6 rounded-full transition-colors ${
                    (wizardStep === 'choice' && i === 1) || 
                    (wizardStep === 'manual' && i === 2) || 
                    (['loading', '2fa', 'success'].includes(wizardStep) && i === 3) 
                      ? 'bg-indigo-500' : 'bg-slate-800'
                  }`} />
                ))}
              </div>
            </div>

            <div className="p-8 flex-1 min-h-[300px] flex flex-col justify-center">
              {wizardStep === 'choice' && (
                <div className="space-y-4">
                  <p className="text-sm text-slate-400 mb-6 text-center">Selecciona el método de autenticación para vincular la cuenta de forma segura.</p>
                  <button onClick={() => setWizardStep('manual')} className="w-full flex items-center gap-4 p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-indigo-500/10 hover:border-indigo-500/30 transition-all text-left group">
                    <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                      <KeyRound size={20} className="text-indigo-400" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-200">Credenciales Manuales</h4>
                      <p className="text-xs text-slate-500 mt-1">Usuario, contraseña y proxy personalizado</p>
                    </div>
                  </button>
                  <button className="w-full flex items-center gap-4 p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-slate-800 transition-all text-left opacity-50 cursor-not-allowed">
                    <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center">
                      <Search size={20} className="text-slate-400" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-200">Importar Cookies (Próximamente)</h4>
                      <p className="text-xs text-slate-500 mt-1">Sincronización via storageState.json</p>
                    </div>
                  </button>
                </div>
              )}

              {wizardStep === 'manual' && (
                <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                  <div>
                    <label className="text-xs font-medium text-slate-400 ml-1">Email / Identificador</label>
                    <input type="text" value={email} onChange={e => setEmail(e.target.value)} placeholder="agente@dominio.com" className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-400 ml-1">Contraseña</label>
                    <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all" />
                  </div>
                  <div className="pt-4">
                    <button onClick={handleStartLogin} className="w-full py-2.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white font-medium text-sm transition-colors shadow-[0_0_15px_rgba(99,102,241,0.4)]">
                      Conectar Identidad
                    </button>
                  </div>
                </div>
              )}

              {wizardStep === 'loading' && (
                <div className="flex flex-col items-center justify-center space-y-4 py-8">
                  <Loader2 size={48} className="text-indigo-500 animate-spin" />
                  <p className="text-sm font-medium text-slate-300 animate-pulse">Estableciendo túnel seguro...</p>
                </div>
              )}

              {wizardStep === '2fa' && (
                <div className="space-y-6 text-center">
                  <Lock size={28} className="text-amber-400 mx-auto" />
                  <div>
                    <h4 className="text-lg font-medium text-slate-200">Verificación Requerida</h4>
                    <p className="text-xs text-slate-400 mt-2">Ingresa el código enviado a tu dispositivo.</p>
                  </div>
                  <input type="text" value={twoFACode} onChange={e => setTwoFACode(e.target.value)} placeholder="CÓDIGO 2FA" className="w-full bg-[#020617] border border-white/10 rounded-lg text-center text-lg text-white focus:border-amber-500 tracking-[0.5em] font-bold py-3" />
                  <button onClick={handleVerify2FA} className="w-full py-2.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-amber-950 font-bold text-sm transition-colors shadow-[0_0_15px_rgba(245,158,11,0.3)]">
                    Verificar
                  </button>
                </div>
              )}

              {wizardStep === 'success' && (
                <div className="flex flex-col items-center justify-center space-y-4 py-8">
                  <CheckCircle2 size={40} className="text-emerald-400" />
                  <h4 className="text-xl font-semibold text-emerald-400">Conexión Exitosa</h4>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

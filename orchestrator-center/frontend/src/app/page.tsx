"use client";

import React, { useState } from 'react';
import { 
  Activity, Users, Zap, Shield, Plus, 
  TerminalSquare, CheckCircle2, ChevronRight, 
  Loader2, KeyRound, Lock, Search, Target, Flame, Bell, Monitor, Terminal, Globe,
  Cookie, X, Upload, ClipboardPaste, AlertTriangle, CheckCircle
} from 'lucide-react';

import { useRouter } from 'next/navigation';
import { useOrchestrator } from '@/hooks/useOrchestrator';
import { DashboardView } from '@/components/views/DashboardView';
import { AccountsView } from '@/components/views/AccountsView';
import { MissionsView } from '@/components/views/MissionsView';
import { SecurityView } from '@/components/views/SecurityView';
import { AutoPilotView } from '@/components/views/AutoPilotView';
import { WarmupView } from '@/components/views/WarmupView';
import { NotificationsView } from '@/components/views/NotificationsView';
import { LiveView } from '@/components/views/LiveView';
import { CommandCenterView } from '@/components/views/CommandCenterView';
import { ProxiesView } from '@/components/views/ProxiesView';


export default function CommandHub() {
  const router = useRouter();
  const { 
    accounts, missions, logs, stats, targets, autopilotStatus,
    refresh, deleteAccount, 
    addTargetProfile, toggleTargetProfile, deleteTargetProfile,
    API_URL 
  } = useOrchestrator();
  
  const [activeTab, setActiveTab] = useState('orchestrator');
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState('choice'); // choice -> manual -> loading -> 2fa -> success
  const [mounted, setMounted] = React.useState(false);

  // Form States — Credenciales manuales
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [twoFACode, setTwoFACode] = useState("");

  // Form States — Cookies
  const [cookieJson, setCookieJson] = useState("");
  const [cookieAccountName, setCookieAccountName] = useState("");
  const [cookieValidating, setCookieValidating] = useState(false);
  const [cookieImporting, setCookieImporting] = useState(false);
  const [cookieValidation, setCookieValidation] = useState<{valid: boolean; name?: string; error?: string; detected_country?: string} | null>(null);
  const [cookieResult, setCookieResult] = useState<{status: string; detail?: string} | null>(null);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  // --- WIZARD HANDLERS: CREDENCIALES MANUALES ---
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

  // --- WIZARD HANDLERS: COOKIES ---
  const handleValidateCookies = async () => {
    setCookieValidating(true);
    setCookieValidation(null);
    setCookieResult(null);
    let cookies;
    try {
      cookies = JSON.parse(cookieJson);
      if (!Array.isArray(cookies) || cookies.length === 0) {
        setCookieValidation({ valid: false, error: 'El JSON debe ser un array de cookies no vacío' });
        setCookieValidating(false);
        return;
      }
    } catch {
      setCookieValidation({ valid: false, error: 'JSON inválido. Verifica el formato.' });
      setCookieValidating(false);
      return;
    }
    try {
      const res = await fetch(`${API_URL}/accounts/cookies/validate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookies }),
      });
      const data = await res.json();
      setCookieValidation(data);
      if (data.valid && data.name && !cookieAccountName) {
        setCookieAccountName(data.name);
      }
    } catch (e: any) {
      setCookieValidation({ valid: false, error: `Error de conexión: ${e.message}` });
    } finally {
      setCookieValidating(false);
    }
  };

  const handleImportCookies = async () => {
    setCookieImporting(true);
    setCookieResult(null);
    let cookies;
    try { cookies = JSON.parse(cookieJson); } catch { setCookieResult({ status: 'error', detail: 'JSON inválido' }); setCookieImporting(false); return; }
    try {
      const res = await fetch(`${API_URL}/accounts/cookies`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookies, name: cookieAccountName || undefined }),
      });
      const data = await res.json();
      setCookieResult(data);
      if (data.status === 'success') {
        setTimeout(() => {
          setIsWizardOpen(false);
          setWizardStep('choice');
          setCookieJson(''); setCookieAccountName(''); setCookieValidation(null); setCookieResult(null);
          refresh();
        }, 2000);
      }
    } catch (e: any) {
      setCookieResult({ status: 'error', detail: `Error: ${e.message}` });
    } finally {
      setCookieImporting(false);
    }
  };

  const resetWizard = () => {
    setIsWizardOpen(false);
    setTimeout(() => {
      setWizardStep('choice');
      setEmail(''); setPassword(''); setTwoFACode('');
      setCookieJson(''); setCookieAccountName(''); setCookieValidation(null); setCookieResult(null);
    }, 300);
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
    setTimeout(() => {
      setWizardStep('choice');
      setEmail(''); setPassword(''); setTwoFACode('');
      setCookieJson(''); setCookieAccountName(''); setCookieValidation(null); setCookieResult(null);
    }, 300);
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

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30 flex overflow-hidden relative">

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
          <SidebarItem icon={Activity} label="Dashboard" id="orchestrator" isActive={activeTab === 'orchestrator'} />
          <SidebarItem icon={Terminal} label="Command Center" id="command" isActive={activeTab === 'command'} />
          <SidebarItem icon={Users} label="Accounts" id="accounts" isActive={activeTab === 'accounts'} />
          <SidebarItem icon={Flame} label="Warmup Lab" id="warmup" isActive={activeTab === 'warmup'} />
          <SidebarItem icon={TerminalSquare} label="Missions" id="missions" isActive={activeTab === 'missions'} />
          <SidebarItem icon={Target} label="Piloto Automático" id="autopilot" isActive={activeTab === 'autopilot'} />
          <SidebarItem icon={Bell} label="Interacciones" id="notifications" isActive={activeTab === 'notifications'} />
          <SidebarItem icon={Monitor} label="Live View" id="live" isActive={activeTab === 'live'} />
          <SidebarItem icon={Globe} label="Proxies" id="proxies" isActive={activeTab === 'proxies'} />
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
        
        <header className="h-24 px-8 flex items-center justify-between border-b border-white/5 bg-slate-950/30 backdrop-blur-md">
          <div>
            <h2 className="text-2xl font-semibold text-white tracking-tight flex items-center gap-3">
              {activeTab === 'orchestrator' ? 'Dashboard' : 
               activeTab === 'command' ? 'Command Center' :
               activeTab === 'accounts' ? 'Account Registry' : 
               activeTab === 'missions' ? 'Mission Control' : 
               activeTab === 'autopilot' ? 'Piloto Automático' : 
               activeTab === 'proxies' ? 'Proxy Pool' : 'Security Audit'}
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
            onClick={() => setActiveTab('accounts')}
            className="group relative px-5 py-2.5 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 font-medium text-sm text-white shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] transition-all overflow-hidden"
          >
            <div className="absolute inset-0 bg-white/20 group-hover:bg-transparent transition-colors duration-300"></div>
            <div className="flex items-center gap-2 relative z-10">
              <Users size={16} />
              Ir a Account Registry
            </div>
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
          {activeTab === 'orchestrator' && <DashboardView logs={logs} stats={stats} />}
          {activeTab === 'command' && <CommandCenterView />}
          {activeTab === 'accounts' && <AccountsView accounts={accounts} onOpenWizard={() => setIsWizardOpen(true)} onDeleteAccount={deleteAccount} onRefresh={refresh} />}
          {activeTab === 'warmup' && <WarmupView />}
          {activeTab === 'missions' && <MissionsView accounts={accounts} missions={missions} logs={logs} onLaunchMission={handleLaunchMission} />}
          {activeTab === 'autopilot' && <AutoPilotView targets={targets} status={autopilotStatus} onAddTarget={addTargetProfile} onToggleTarget={toggleTargetProfile} onDeleteTarget={deleteTargetProfile} />}
          {activeTab === 'notifications' && <NotificationsView />}
          {activeTab === 'live' && <LiveView />}
          {activeTab === 'proxies' && <ProxiesView />}
          {activeTab === 'security' && <SecurityView logs={logs} stats={stats} />}
        </div>
      </main>

      {/* --- WIZARD ONBOARDING OVERLAY (CONSOLIDATED) --- */}
      {isWizardOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-md" onClick={closeWizard}></div>
          <div className="relative w-full max-w-lg bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-white/[0.02] shrink-0">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <Users size={18} className="text-indigo-400" />
                Vincular Nueva Identidad
              </h3>
              <button onClick={closeWizard} className="text-slate-500 hover:text-slate-300 transition-colors p-1">
                <X size={18} />
              </button>
            </div>

            <div className="p-6 overflow-y-auto custom-scrollbar flex-1 min-h-[300px] flex flex-col justify-center">
              {/* --- CHOICE: TWO OPTIONS --- */}
              {wizardStep === 'choice' && (
                <div className="space-y-4">
                  <p className="text-sm text-slate-400 mb-6 text-center">
                    Selecciona el método para vincular tu cuenta de LinkedIn.
                  </p>
                  <button
                    onClick={() => setWizardStep('manual')}
                    className="w-full flex items-center gap-4 p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-indigo-500/10 hover:border-indigo-500/30 transition-all text-left group"
                  >
                    <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                      <KeyRound size={20} className="text-indigo-400" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-200">Inicio de Sesión Manual</h4>
                      <p className="text-xs text-slate-500 mt-1">Usuario, contraseña y código 2FA si es necesario</p>
                    </div>
                  </button>
                  <button
                    onClick={() => setWizardStep('cookie')}
                    className="w-full flex items-center gap-4 p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-amber-500/10 hover:border-amber-500/30 transition-all text-left group"
                  >
                    <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                      <Cookie size={20} className="text-amber-400" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-200">Importar Cookies</h4>
                      <p className="text-xs text-slate-500 mt-1">Pega el JSON exportado desde tu extensión de Chrome</p>
                    </div>
                  </button>
                  <button
                    onClick={closeWizard}
                    className="w-full py-2 text-xs text-slate-500 hover:text-slate-300 transition-colors text-center"
                  >
                    Cancelar
                  </button>
                </div>
              )}

              {/* --- MANUAL LOGIN: CREDENTIALS --- */}
              {wizardStep === 'manual' && (
                <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                  <button onClick={() => setWizardStep('choice')} className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 mb-2">
                    ← Volver
                  </button>
                  <div>
                    <label className="text-xs font-medium text-slate-400 ml-1">Email / Identificador</label>
                    <input type="text" value={email} onChange={e => setEmail(e.target.value)} placeholder="agente@dominio.com" className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-400 ml-1">Contraseña</label>
                    <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all" />
                  </div>
                  <div className="pt-2">
                    <button onClick={handleStartLogin} className="w-full py-2.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white font-medium text-sm transition-colors shadow-[0_0_15px_rgba(99,102,241,0.4)]">
                      Iniciar Sesión
                    </button>
                  </div>
                </div>
              )}

              {/* --- COOKIE IMPORT --- */}
              {wizardStep === 'cookie' && (
                <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                  <button onClick={() => { setWizardStep('choice'); setCookieValidation(null); setCookieResult(null); }} className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 mb-2">
                    ← Volver
                  </button>

                  <div className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/5 text-xs text-slate-300 space-y-1.5">
                    <p className="font-medium text-amber-300 flex items-center gap-1.5">
                      <ClipboardPaste size={14} />
                      Cómo obtener las cookies:
                    </p>
                    <ol className="text-[11px] text-slate-400 ml-4 list-decimal space-y-0.5">
                      <li>Instala una extensión exportadora de cookies (ej: <span className="text-amber-400">Get cookies.txt</span> o <span className="text-amber-400">EditThisCookie</span>)</li>
                      <li>Ve a <span className="text-slate-300">linkedin.com</span> y asegúrate de estar logueado</li>
                      <li>Exporta las cookies como JSON</li>
                      <li>Pega el JSON abajo y valida</li>
                    </ol>
                  </div>

                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">
                      Cookies (JSON)
                    </label>
                    <textarea
                      value={cookieJson}
                      onChange={e => { setCookieJson(e.target.value); setCookieValidation(null); setCookieResult(null); }}
                      placeholder='[{&quot;domain&quot;: &quot;.www.linkedin.com&quot;, &quot;name&quot;: &quot;li_at&quot;, &quot;value&quot;: &quot;...&quot;}, ...]'
                      rows={6}
                      className="w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-amber-500 transition-all resize-none"
                      spellCheck={false}
                    />
                  </div>

                  <button
                    onClick={handleValidateCookies}
                    disabled={cookieValidating || !cookieJson.trim()}
                    className="w-full py-2.5 rounded-lg bg-amber-500 hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed text-amber-950 font-bold text-sm transition-all shadow-[0_0_15px_rgba(245,158,11,0.3)] flex items-center justify-center gap-2"
                  >
                    {cookieValidating ? <Loader2 size={18} className="animate-spin" /> : <Upload size={16} />}
                    {cookieValidating ? 'VALIDANDO...' : 'Validar Cookies'}
                  </button>

                  {cookieValidation && (
                    <div className={`p-4 rounded-xl border ${
                      cookieValidation.valid ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-rose-500/20 bg-rose-500/5'
                    }`}>
                      <div className="flex items-start gap-3">
                        {cookieValidation.valid ? <CheckCircle size={20} className="text-emerald-400 mt-0.5 shrink-0" />
                          : <AlertTriangle size={20} className="text-rose-400 mt-0.5 shrink-0" />}
                        <div className="min-w-0">
                          <p className={`text-sm font-medium ${cookieValidation.valid ? 'text-emerald-300' : 'text-rose-300'}`}>
                            {cookieValidation.valid ? 'Cookies válidas' : 'Cookies inválidas'}
                          </p>
                          {cookieValidation.name && (
                            <p className="text-xs text-slate-400 mt-1">Cuenta: <span className="text-slate-200 font-medium">{cookieValidation.name}</span></p>
                          )}
                          {cookieValidation.detected_country && (
                            <p className="text-xs text-slate-400 mt-1">País detectado: <span className="text-amber-300 font-medium">{cookieValidation.detected_country}</span></p>
                          )}
                          {cookieValidation.error && <p className="text-xs text-slate-400 mt-1">{cookieValidation.error}</p>}
                        </div>
                      </div>
                    </div>
                  )}

                  {cookieValidation?.valid && (
                    <>
                      <div>
                        <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 block">
                          Nombre de la cuenta (opcional)
                        </label>
                        <input type="text" value={cookieAccountName} onChange={e => setCookieAccountName(e.target.value)}
                          placeholder={cookieValidation.name || 'Mi Cuenta LinkedIn'}
                          className="w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500 transition-all" />
                      </div>
                      {!cookieResult && (
                        <button onClick={handleImportCookies} disabled={cookieImporting}
                          className="w-full py-3 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)] flex items-center justify-center gap-2">
                          {cookieImporting ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle size={18} />}
                          {cookieImporting ? 'IMPORTANDO...' : 'Guardar Cuenta'}
                        </button>
                      )}
                      {cookieResult && (
                        <div className={`p-4 rounded-xl border ${
                          cookieResult.status === 'success' ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-rose-500/20 bg-rose-500/5'
                        }`}>
                          <div className="flex items-start gap-3">
                            {cookieResult.status === 'success' ? <CheckCircle size={20} className="text-emerald-400 mt-0.5 shrink-0" />
                              : <AlertTriangle size={20} className="text-rose-400 mt-0.5 shrink-0" />}
                            <div>
                              <p className={`text-sm font-medium ${cookieResult.status === 'success' ? 'text-emerald-300' : 'text-rose-300'}`}>
                                {cookieResult.status === 'success' ? 'Cuenta importada exitosamente' : 'Error al importar'}
                              </p>
                              {cookieResult.detail && <p className="text-xs text-slate-400 mt-1">{cookieResult.detail}</p>}
                            </div>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* --- LOADING --- */}
              {wizardStep === 'loading' && (
                <div className="flex flex-col items-center justify-center space-y-4 py-8">
                  <Loader2 size={48} className="text-indigo-500 animate-spin" />
                  <p className="text-sm font-medium text-slate-300 animate-pulse">Estableciendo túnel seguro...</p>
                </div>
              )}

              {/* --- 2FA --- */}
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

              {/* --- SUCCESS --- */}
              {wizardStep === 'success' && (
                <div className="flex flex-col items-center justify-center space-y-4 py-8">
                  <CheckCircle2 size={40} className="text-emerald-400" />
                  <h4 className="text-xl font-semibold text-emerald-400">Conexión Exitosa</h4>
                  <p className="text-sm text-slate-400">La cuenta se vinculó correctamente.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

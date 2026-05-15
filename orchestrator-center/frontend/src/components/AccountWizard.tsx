"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, CheckCircle2, Mail, KeyRound, AlertTriangle } from 'lucide-react';
import { LiveLogViewer } from '@/components/LiveLogViewer';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface AccountWizardProps {
  onComplete?: () => void;
  onCancel?: () => void;
}

export function AccountWizard({ onComplete, onCancel }: AccountWizardProps) {
  const router = useRouter();
  const [step, setStep] = useState<'credentials' | 'loading' | 'success' | '2fa_email' | '2fa_app' | 'error'>('credentials');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [proxyUrl, setProxyUrl] = useState('');
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [codeSentTo, setCodeSentTo] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  const handleStartLogin = async () => {
    setStep('loading');
    setErrorMessage('');
    try {
      const res = await fetch(`${API_URL}/wizard/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, proxy_url: proxyUrl || undefined }),
      });
      const data = await res.json();
      if (!res.ok) { setStep('error'); setErrorMessage(data.detail || 'Error'); return; }
      
      setSessionId(data.session_id);
      
      const pollStatus = async () => {
        for (let i = 0; i < 30; i++) {
          await new Promise(r => setTimeout(r, 2000));
          try {
            const sr = await fetch(`${API_URL}/wizard/status/${data.session_id}`);
            const sd = await sr.json();
            if (sd.status === 'success') { setStep('success'); return; }
            if (sd.status === '2fa_email') { setStep('2fa_email'); setCodeSentTo(sd.two_fa_destination); return; }
            if (sd.status === '2fa_app') { setStep('2fa_app'); return; }
            if (sd.status === 'failed' || sd.status === 'expired') { setStep('error'); setErrorMessage('Sesión expirada.'); return; }
          } catch { /* continue */ }
        }
        setStep('error'); setErrorMessage('Tiempo de espera agotado.');
      };
      pollStatus();
    } catch (e: any) { setStep('error'); setErrorMessage(`Error: ${e.message}`); }
  };

  return (
    <div className="w-full max-w-lg mx-auto">
      <div className="flex justify-center gap-2 mb-8">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-1.5 w-12 rounded-full transition-colors bg-indigo-500" />
        ))}
      </div>

      {step === 'credentials' && (
        <div className="rounded-xl border border-white/5 bg-slate-900/40 p-8 space-y-4">
          <h3 className="text-lg font-semibold text-white text-center">Vincular Nueva Cuenta LinkedIn</h3>
          <p className="text-sm text-slate-400 text-center">Ingresa las credenciales</p>
          <div>
            <label className="text-xs font-medium text-slate-400 ml-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="usuario@email.com"
              className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-400 ml-1">Contraseña</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1 w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-all" />
          </div>
          <details className="text-xs text-slate-500">
            <summary className="cursor-pointer hover:text-slate-300">Proxy (opcional)</summary>
            <input type="text" value={proxyUrl} onChange={e => setProxyUrl(e.target.value)}
              placeholder="http://proxy:8080"
              className="mt-2 w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500" />
          </details>
          <button onClick={handleStartLogin}
            className="w-full py-2.5 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-medium text-sm shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] transition-all">
            Iniciar Sesión
          </button>
          {onCancel && <button onClick={onCancel} className="w-full py-2 text-xs text-slate-500 hover:text-slate-300">Cancelar</button>}
        </div>
      )}

      {step === 'loading' && (
        <div className="flex flex-col items-center py-8 space-y-4">
          <Loader2 size={48} className="text-indigo-500 animate-spin" />
          <p className="text-sm font-medium text-slate-300 animate-pulse">Iniciando sesión en LinkedIn...</p>
          {sessionId && (
            <div className="w-full mt-4">
              <LiveLogViewer missionId={sessionId} height="200px" />
            </div>
          )}
        </div>
      )}

      {step === '2fa_email' && (
        <div className="rounded-xl border border-white/5 bg-slate-900/40 p-8 space-y-6 text-center">
          <div className="w-16 h-16 rounded-full bg-amber-500/20 flex items-center justify-center mx-auto">
            <Mail size={28} className="text-amber-400" />
          </div>
          <h3 className="text-lg font-medium text-slate-200">Código de Verificación</h3>
          <p className="text-sm text-slate-400">Te enviamos un código a:</p>
          <p className="text-base font-bold text-indigo-400 bg-indigo-500/10 px-4 py-2 rounded-lg inline-block">{codeSentTo || 'correo@email.com'}</p>
          <TwoFACodeInput onVerify={async (code) => {
            setStep('loading');
            try {
              const res = await fetch(`${API_URL}/wizard/verify`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, code }),
              });
              const data = await res.json();
              if (data.status === 'success') setStep('success');
              else { setStep('2fa_email'); setErrorMessage('Código incorrecto.'); }
            } catch { setStep('2fa_email'); setErrorMessage('Error de verificación.'); }
          }} />
        </div>
      )}

      {step === '2fa_app' && (
        <div className="rounded-xl border border-white/5 bg-slate-900/40 p-8 space-y-6 text-center">
          <div className="w-16 h-16 rounded-full bg-purple-500/20 flex items-center justify-center mx-auto">
            <KeyRound size={28} className="text-purple-400" />
          </div>
          <h3 className="text-lg font-medium text-slate-200">Verificación de Dos Pasos</h3>
          <p className="text-sm text-slate-400">Código de tu app de autenticación:</p>
          <TwoFACodeInput onVerify={async (code) => {
            setStep('loading');
            try {
              const res = await fetch(`${API_URL}/wizard/verify`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, code }),
              });
              const data = await res.json();
              if (data.status === 'success') setStep('success');
              else { setStep('2fa_app'); setErrorMessage('Código incorrecto.'); }
            } catch { setStep('2fa_app'); }
          }} />
        </div>
      )}

      {step === 'success' && (
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <CheckCircle2 size={48} className="text-emerald-400" />
          <h3 className="text-xl font-semibold text-emerald-400">Cuenta Registrada</h3>
          <p className="text-sm text-slate-400">La cuenta {email} se vinculó exitosamente.</p>
          <div className="flex gap-3 pt-4">
            <button onClick={() => { setStep('credentials'); setEmail(''); setPassword(''); setSessionId(null); }}
              className="px-6 py-2 rounded-lg bg-slate-800 text-slate-300 text-sm hover:bg-slate-700">Registrar Otra</button>
            <button onClick={() => router.push('/')}
              className="px-6 py-2 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-sm shadow-[0_0_20px_rgba(99,102,241,0.3)]">Ir al Dashboard</button>
          </div>
        </div>
      )}

      {step === 'error' && (
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <AlertTriangle size={48} className="text-rose-400" />
          <h3 className="text-lg font-semibold text-rose-400">Error</h3>
          <p className="text-sm text-slate-400">{errorMessage}</p>
          <button onClick={() => setStep('credentials')}
            className="px-6 py-2 rounded-lg bg-slate-800 text-slate-300 text-sm hover:bg-slate-700">Intentar de Nuevo</button>
        </div>
      )}
    </div>
  );
}

function TwoFACodeInput({ onVerify }: { onVerify: (code: string) => Promise<void> }) {
  const [code, setCode] = useState('');
  return (
    <div className="space-y-4">
      <input type="text" value={code} onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
        placeholder="000000" maxLength={6} autoFocus
        className="w-full bg-[#020617] border border-white/10 rounded-lg text-center text-2xl text-white focus:border-amber-500 tracking-[0.5em] font-bold py-4" />
      <button onClick={() => onVerify(code)} disabled={code.length < 6}
        className="w-full py-2.5 rounded-lg bg-amber-500 hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed text-amber-950 font-bold text-sm shadow-[0_0_15px_rgba(245,158,11,0.3)]">
        Verificar
      </button>
    </div>
  );
}

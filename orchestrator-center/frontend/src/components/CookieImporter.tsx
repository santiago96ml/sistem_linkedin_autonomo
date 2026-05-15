"use client";

import React, { useState } from 'react';
import { X, Loader2, CheckCircle2, AlertTriangle, ClipboardPaste, Cookie, Upload } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface CookieImporterProps {
  onComplete: () => void;
  trigger?: React.ReactNode;
}

export function CookieImporter({ onComplete, trigger }: CookieImporterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [cookieJson, setCookieJson] = useState('');
  const [name, setName] = useState('');
  const [validating, setValidating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    name?: string;
    error?: string;
  } | null>(null);
  const [importResult, setImportResult] = useState<{
    status: string;
    account_id?: number;
    detail?: string;
  } | null>(null);

  const handleValidate = async () => {
    setValidating(true);
    setValidationResult(null);
    setImportResult(null);

    // Parse JSON
    let cookies;
    try {
      cookies = JSON.parse(cookieJson);
      if (!Array.isArray(cookies)) {
        setValidationResult({ valid: false, error: 'El JSON debe ser un array de cookies' });
        setValidating(false);
        return;
      }
      if (cookies.length === 0) {
        setValidationResult({ valid: false, error: 'El array de cookies está vacío' });
        setValidating(false);
        return;
      }
    } catch {
      setValidationResult({ valid: false, error: 'JSON inválido. Verificá el formato.' });
      setValidating(false);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/accounts/cookies/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookies }),
      });
      const data = await res.json();
      setValidationResult(data);
      if (data.valid && data.name && !name) {
        setName(data.name);
      }
    } catch (e: any) {
      setValidationResult({ valid: false, error: `Error de conexión: ${e.message}` });
    } finally {
      setValidating(false);
    }
  };

  const handleImport = async () => {
    setImporting(true);
    setImportResult(null);

    let cookies;
    try {
      cookies = JSON.parse(cookieJson);
    } catch {
      setImportResult({ status: 'error', detail: 'JSON inválido' });
      setImporting(false);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/accounts/cookies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cookies,
          name: name || undefined,
        }),
      });
      const data = await res.json();
      setImportResult(data);
      if (data.status === 'success') {
        setTimeout(() => {
          setIsOpen(false);
          setCookieJson('');
          setName('');
          setValidationResult(null);
          setImportResult(null);
          onComplete();
        }, 2000);
      }
    } catch (e: any) {
      setImportResult({ status: 'error', detail: `Error de conexión: ${e.message}` });
    } finally {
      setImporting(false);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setCookieJson('');
    setName('');
    setValidationResult(null);
    setImportResult(null);
  };

  return (
    <>
      {trigger ? (
        <div onClick={() => setIsOpen(true)}>{trigger}</div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm font-medium hover:bg-amber-500/20 transition-all"
        >
          <Cookie size={16} />
          Importar Cookies
        </button>
      )}

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-md" onClick={handleClose} />
          <div className="relative w-full max-w-2xl bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Header */}
            <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <Cookie size={20} className="text-amber-400" />
                Importar Cookies de LinkedIn
              </h3>
              <button onClick={handleClose} className="text-slate-500 hover:text-slate-300 transition-colors">
                <X size={18} />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 overflow-y-auto custom-scrollbar space-y-5">
              {/* Instructions */}
              <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 text-sm text-slate-300 space-y-2">
                <p className="font-medium text-indigo-300 flex items-center gap-2">
                  <ClipboardPaste size={16} />
                  Cómo obtener las cookies:
                </p>
                <ol className="text-xs text-slate-400 space-y-1 ml-5 list-decimal">
                  <li>Instalá una extensión exportadora de cookies (ej: <span className="text-indigo-400">Get cookies.txt</span> o <span className="text-indigo-400">EditThisCookie</span>)</li>
                  <li>Andá a <span className="text-slate-300">linkedin.com</span> y asegurate de estar logueado</li>
                  <li>Exportá las cookies como JSON</li>
                  <li>Copiá el JSON y pegalo abajo</li>
                </ol>
              </div>

              {/* JSON Input */}
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 block">
                  Cookies (JSON)
                </label>
                <textarea
                  value={cookieJson}
                  onChange={(e) => {
                    setCookieJson(e.target.value);
                    setValidationResult(null);
                    setImportResult(null);
                  }}
                  placeholder='[{&quot;domain&quot;: &quot;.www.linkedin.com&quot;, &quot;name&quot;: &quot;li_at&quot;, &quot;value&quot;: &quot;...&quot;}, ...]'
                  rows={8}
                  className="w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-amber-500 transition-all resize-none"
                  spellCheck={false}
                />
              </div>

              {/* Validate Button */}
              <button
                onClick={handleValidate}
                disabled={validating || !cookieJson.trim()}
                className="w-full py-2.5 rounded-lg bg-amber-500 hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed text-amber-950 font-bold text-sm transition-all shadow-[0_0_15px_rgba(245,158,11,0.3)] flex items-center justify-center gap-2"
              >
                {validating ? <Loader2 size={18} className="animate-spin" /> : <Upload size={16} />}
                {validating ? 'VALIDANDO...' : 'Validar Cookies'}
              </button>

              {/* Validation Result */}
              {validationResult && (
                <div className={`p-4 rounded-xl border ${
                  validationResult.valid
                    ? 'border-emerald-500/20 bg-emerald-500/5'
                    : 'border-rose-500/20 bg-rose-500/5'
                }`}>
                  <div className="flex items-start gap-3">
                    {validationResult.valid ? (
                      <CheckCircle2 size={20} className="text-emerald-400 mt-0.5 shrink-0" />
                    ) : (
                      <AlertTriangle size={20} className="text-rose-400 mt-0.5 shrink-0" />
                    )}
                    <div className="min-w-0">
                      <p className={`text-sm font-medium ${validationResult.valid ? 'text-emerald-300' : 'text-rose-300'}`}>
                        {validationResult.valid ? 'Cookies válidas' : 'Cookies inválidas'}
                      </p>
                      {validationResult.name && (
                        <p className="text-xs text-slate-400 mt-1">
                          Cuenta detectada: <span className="text-slate-200 font-medium">{validationResult.name}</span>
                        </p>
                      )}
                      {validationResult.error && (
                        <p className="text-xs text-slate-400 mt-1">{validationResult.error}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Name Input (shown after successful validation) */}
              {validationResult?.valid && (
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 block">
                    Nombre de la cuenta (opcional)
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={validationResult.name || 'Mi Cuenta LinkedIn'}
                    className="w-full bg-[#020617] border border-white/10 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500 transition-all"
                  />
                </div>
              )}

              {/* Import Button */}
              {validationResult?.valid && !importResult && (
                <button
                  onClick={handleImport}
                  disabled={importing}
                  className="w-full py-3 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)] flex items-center justify-center gap-2"
                >
                  {importing ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
                  {importing ? 'IMPORTANDO...' : 'Guardar Cuenta'}
                </button>
              )}

              {/* Import Result */}
              {importResult && (
                <div className={`p-4 rounded-xl border ${
                  importResult.status === 'success'
                    ? 'border-emerald-500/20 bg-emerald-500/5'
                    : 'border-rose-500/20 bg-rose-500/5'
                }`}>
                  <div className="flex items-start gap-3">
                    {importResult.status === 'success' ? (
                      <CheckCircle2 size={20} className="text-emerald-400 mt-0.5 shrink-0" />
                    ) : (
                      <AlertTriangle size={20} className="text-rose-400 mt-0.5 shrink-0" />
                    )}
                    <div>
                      <p className={`text-sm font-medium ${importResult.status === 'success' ? 'text-emerald-300' : 'text-rose-300'}`}>
                        {importResult.status === 'success' ? 'Cuenta importada exitosamente' : 'Error al importar'}
                      </p>
                      {importResult.detail && (
                        <p className="text-xs text-slate-400 mt-1">{importResult.detail}</p>
                      )}
                      {importResult.account_id && (
                        <p className="text-xs text-slate-500 mt-1">Account ID: #{importResult.account_id}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

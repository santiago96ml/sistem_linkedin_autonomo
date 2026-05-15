"use client";

import { AccountWizard } from '@/components/AccountWizard';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';

export default function WizardPage() {
  const router = useRouter();
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
      <button onClick={() => router.push('/')} className="self-start mb-4 flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200">
        <ArrowLeft size={16} /> Volver al Dashboard
      </button>
      <AccountWizard onComplete={() => router.push('/')} onCancel={() => router.push('/')} />
    </div>
  );
}

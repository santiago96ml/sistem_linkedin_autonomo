import { useState, useEffect, useCallback } from 'react';

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export interface Account {
  id: number;
  name: string;
  email: string;
  status: string;
  proxy?: string;
  tasks?: number;
}

export interface Mission {
  id: number;
  account_id: number;
  status: string;
  source?: string;
  target_profile_id?: number;
  created_at: string;
  tasks: any[];
}

export interface LogEntry {
  id: number;
  time: string;
  source: string;
  msg: string;
  type: 'info' | 'warning' | 'success' | 'error';
}

export interface Stats {
  total_identities: number;
  active_missions: number;
  success_rate: number;
  system_status: string;
}

export interface TargetProfile {
  id: number;
  linkedin_url: string;
  status: string;
  schedule_start: string;
  schedule_end: string;
  cta_keywords?: string;
  comment_base?: string;
}

export interface AutoPilotStatus {
  status: string;            // "starting" | "running" | "cooldown" | "error"
  failures: number;
  cooldown_remaining: number;
  last_autopilot_cycle: string | null;
  last_notifications_cycle: string | null;
  last_error: string | null;
  started_at: string | null;
  targets_active: number;
  total_cycles_run: number;
}

export function useOrchestrator() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [targets, setTargets] = useState<TargetProfile[]>([]);
  const [autopilotStatus, setAutopilotStatus] = useState<AutoPilotStatus | null>(null);
  const [stats, setStats] = useState<Stats>({
    total_identities: 0,
    active_missions: 0,
    success_rate: 100,
    system_status: 'nominal'
  });

  const fetchData = useCallback(async () => {
    try {
      const [accRes, missRes, logRes, statsRes, targetsRes, apStatusRes] = await Promise.allSettled([
        fetch(`${API_URL}/accounts/`),
        fetch(`${API_URL}/missions/`),
        fetch(`${API_URL}/logs/`),
        fetch(`${API_URL}/stats`),
        fetch(`${API_URL}/autopilot/targets`),
        fetch(`${API_URL}/autopilot/status`)
      ]);

      const safeJson = async (res: PromiseSettledResult<Response>) => {
        if (res.status === 'fulfilled' && res.value.ok) {
          try { return await res.value.json(); } catch { return null; }
        }
        return null;
      };

      const [accData, missData, logData, statsData, targetsData, apStatusData] = await Promise.all([
        safeJson(accRes),
        safeJson(missRes),
        safeJson(logRes),
        safeJson(statsRes),
        safeJson(targetsRes),
        safeJson(apStatusRes),
      ]);

      if (accData) setAccounts(accData);
      if (missData) setMissions(missData);
      if (statsData) setStats(statsData);
      if (targetsData) setTargets(targetsData);
      if (apStatusData) setAutopilotStatus(apStatusData);

      if (logData) {
        // Map backend logs to frontend format
        const validTypes = ['info', 'warning', 'success', 'error'];
        const formattedLogs = logData.map((l: any) => ({
          id: l.id,
          time: new Date(l.timestamp).toLocaleTimeString(),
          source: 'System',
          msg: l.message || '(sin mensaje)',
          type: validTypes.includes(l.level) ? l.level as any : 'info'
        }));
        setLogs(formattedLogs);
      }

      // Mark offline only if ALL fetches failed
      const allFailed = [accRes, missRes, logRes, statsRes].every(r => r.status === 'rejected');
      if (allFailed) {
        setStats(prev => ({ ...prev, system_status: 'offline' }));
      }

    } catch (e) {
      console.error("Unexpected error in fetchData:", e);
      setStats(prev => ({ ...prev, system_status: 'offline' }));
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const deleteAccount = async (id: number) => {
    try {
      const res = await fetch(`${API_URL}/accounts/${id}`, { method: 'DELETE' });
      if (res.ok) fetchData();
    } catch (e) { console.error("Failed to delete account", e); }
  };

  const addTargetProfile = async (data: Omit<TargetProfile, 'id' | 'status'>) => {
    try {
      const res = await fetch(`${API_URL}/autopilot/targets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (res.ok) fetchData();
      else alert('Error: ' + (await res.json()).detail);
    } catch (e) { console.error("Failed to add target", e); }
  };

  const deleteTargetProfile = async (id: number) => {
    try {
      const res = await fetch(`${API_URL}/autopilot/targets/${id}`, { method: 'DELETE' });
      if (res.ok) fetchData();
    } catch (e) { console.error("Failed to delete target", e); }
  };

  const toggleTargetProfile = async (id: number) => {
    try {
      const res = await fetch(`${API_URL}/autopilot/targets/${id}/toggle`, { method: 'PUT' });
      if (res.ok) fetchData();
    } catch (e) { console.error("Failed to toggle target", e); }
  };

  return {
    accounts,
    missions,
    logs,
    stats,
    targets,
    autopilotStatus,
    refresh: fetchData,
    deleteAccount,
    addTargetProfile,
    deleteTargetProfile,
    toggleTargetProfile,
    API_URL
  };
}

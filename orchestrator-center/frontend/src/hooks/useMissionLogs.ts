"use client";

import { useState, useEffect, useRef, useCallback } from 'react';

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'success' | 'warning' | 'error';
  message: string;
  type?: string;
}

interface UseMissionLogsReturn {
  logs: LogEntry[];
  connected: boolean;
  error: string | null;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
const MAX_LOG_LINES = 500;

export function useMissionLogs(missionId: number | null): UseMissionLogsReturn {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const maxRetries = 10;

  const connect = useCallback(() => {
    if (missionId === null) return;
    const ws = new WebSocket(`${WS_URL}/ws/logs/${missionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setError(null);
      retriesRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'heartbeat') return;
        setLogs(prev => {
          const next = [...prev, { ...data, timestamp: data.timestamp || new Date().toISOString() }];
          return next.length > MAX_LOG_LINES ? next.slice(next.length - MAX_LOG_LINES) : next;
        });
      } catch (e) { /* ignore */ }
    };

    ws.onclose = () => {
      setConnected(false);
      if (retriesRef.current < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retriesRef.current), 30000);
        retriesRef.current++;
        setTimeout(connect, delay);
      } else {
        setError('Connection lost. Max retries exceeded.');
      }
    };

    ws.onerror = () => { setError('WebSocket connection error'); ws.close(); };
  }, [missionId]);

  useEffect(() => {
    setLogs([]); setError(null);
    connect();
    return () => { if (wsRef.current) { wsRef.current.close(); wsRef.current = null; } };
  }, [connect]);

  return { logs, connected, error };
}

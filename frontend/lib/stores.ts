"use client";

import { create } from "zustand";

type SystemState = {
  connected: boolean;
  capabilities: any | null;
  setConnected: (connected: boolean) => void;
  setCapabilities: (capabilities: any | null) => void;
};

type AnalysisState = {
  taskId: string;
  sessionId: string;
  status: "idle" | "running" | "cancelling" | "completed" | "failed" | "cancelled";
  running: boolean;
  setTask: (taskId: string, sessionId: string) => void;
  setStatus: (status: AnalysisState["status"]) => void;
  setRunning: (running: boolean) => void;
};

type SessionState = {
  currentSessionData: any | null;
  historySessions: any[];
  setCurrentSessionData: (data: any | null) => void;
  setHistorySessions: (sessions: any[]) => void;
};

export const useSystemStore = create<SystemState>((set) => ({
  connected: false,
  capabilities: null,
  setConnected: (connected) => set({ connected }),
  setCapabilities: (capabilities) => set({ capabilities })
}));

export const useAnalysisStore = create<AnalysisState>((set) => ({
  taskId: "",
  sessionId: "",
  status: "idle",
  running: false,
  setTask: (taskId, sessionId) => set({ taskId, sessionId }),
  setStatus: (status) =>
    set({
      status,
      running: status === "running" || status === "cancelling"
    }),
  setRunning: (running) => set({ running })
}));

export const useSessionStore = create<SessionState>((set) => ({
  currentSessionData: null,
  historySessions: [],
  setCurrentSessionData: (currentSessionData) => set({ currentSessionData }),
  setHistorySessions: (historySessions) => set({ historySessions })
}));


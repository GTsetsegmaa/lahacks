"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

interface DemoContextValue {
  isDemoMode: boolean;
  toggle: () => void;
}

const DemoContext = createContext<DemoContextValue>({
  isDemoMode: false,
  toggle: () => {},
});

export function DemoProvider({ children }: { children: React.ReactNode }) {
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    try {
      setIsDemoMode(localStorage.getItem("supplymind_demo_mode") === "true");
    } catch {}
  }, []);

  const toggle = useCallback(() => {
    setIsDemoMode((prev) => {
      const next = !prev;
      try { localStorage.setItem("supplymind_demo_mode", String(next)); } catch {}
      return next;
    });
  }, []);

  return (
    <DemoContext.Provider value={{ isDemoMode, toggle }}>
      {children}
    </DemoContext.Provider>
  );
}

export function useDemoMode() {
  return useContext(DemoContext);
}

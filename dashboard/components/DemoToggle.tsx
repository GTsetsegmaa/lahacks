"use client";

import { useDemoMode } from "@/contexts/DemoContext";
import { cn } from "@/lib/utils";
import { Mic, MicOff } from "lucide-react";

export function DemoToggle() {
  const { isDemoMode, toggle } = useDemoMode();

  return (
    <button
      onClick={toggle}
      title={isDemoMode ? "Demo Mode ON — click to disable" : "Enable Demo Mode"}
      className={cn(
        "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-all",
        isDemoMode
          ? "bg-blue-950 text-blue-300 ring-1 ring-blue-700 hover:bg-blue-900"
          : "bg-gray-900 text-gray-600 ring-1 ring-gray-800 hover:text-gray-400"
      )}
    >
      {isDemoMode ? <Mic size={11} /> : <MicOff size={11} />}
      Demo
    </button>
  );
}

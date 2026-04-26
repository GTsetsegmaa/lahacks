"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Play, Pause, RotateCcw, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { SavingsCounter } from "@/components/SavingsCounter";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Script beats ──────────────────────────────────────────────────────────
// startsAt: seconds into the presentation
const BEATS = [
  {
    startsAt: 0,
    title: "Introduce SupplyMind",
    cue: "0:00 — Open on Overview page",
    notes: [
      "Diamond Foods ships $400M of snack products a year — nuts, seeds, dried fruit.",
      "They run on a push supply chain: procurement teams make buy/hold decisions manually, once a week, from spreadsheets.",
      "That works fine in steady state. It breaks the moment demand spikes, a fuel surcharge hits, or lots start expiring.",
      "SupplyMind is a five-agent AI system that monitors all of that in real time and surfaces decisions — not just data.",
      "It runs entirely on this ASUS Ascent GX10. No cloud. No latency. The agents are live right now.",
    ],
    accent: "text-blue-400",
    border: "border-blue-900/50",
    bg: "bg-blue-950/10",
  },
  {
    startsAt: 30,
    title: "Show the empty Activity Log",
    cue: "0:30 — Navigate to Activity Log",
    notes: [
      "This is the Activity Log — every agent decision streams here in real time via SSE.",
      "Right now it's empty because no cascade has fired. This is the clean state.",
      "I'm going to click Run Demo. Watch the agents fire one by one.",
      "Each one is running Gemma 3 locally on the GX10 NPU for reasoning — you can see the inference badge.",
      "Click Run Demo now →",
    ],
    accent: "text-gray-300",
    border: "border-gray-800",
    bg: "bg-gray-900/20",
    action: "CLICK RUN DEMO",
  },
  {
    startsAt: 60,
    title: "Walk through the agents",
    cue: "1:00 — Agents firing (3 s each)",
    notes: [
      "Market Intelligence fires first — it's spotted an 18% fuel surcharge spike on the Gulf Coast-Midwest truck lane. That's the signal that triggers the whole cascade.",
      "Demand Planning: SKU-4471, Holiday Mixed Nuts, is running at 340% of its 90-day baseline. Week 47 seasonal index is 2.40 — that's the Thanksgiving peak — plus a 120% promo lift.",
      "Inventory Manager: three SKUs are under 5 days of supply at this demand rate. SKU-4471 hits zero in 2.1 days without an emergency order.",
      "Shipment Analyst: two open POs are routing to the same DC by truck at $3,540 each. The agent recommends switching both to intermodal.",
      "Coordinator synthesises everything into a single action brief — which is what ASI:One would return to a buyer asking 'what do I need to do this week?'",
    ],
    accent: "text-yellow-400",
    border: "border-yellow-900/50",
    bg: "bg-yellow-950/10",
  },
  {
    startsAt: 150,
    title: "Highlight the savings",
    cue: "2:30 — Point to the Overview KPI cards",
    notes: [
      "The number that matters: $3,421 in freight savings, identified and quantified automatically.",
      "That's from two shipments, Gulf Coast to Midwest, switched from truck to intermodal. Two-day transit extension, which is fine given the lead time available.",
      "Over a full year of operations, this kind of signal fires weekly. The compounding effect is material.",
      "And all of that inference — the market signal detection, the demand spike classification, the consolidation math — ran on the GX10 NPU. No API keys. No network calls. Zero cloud egress.",
    ],
    accent: "text-emerald-400",
    border: "border-emerald-900/50",
    bg: "bg-emerald-950/10",
    showSavings: true,
  },
  {
    startsAt: 180,
    title: "Close — differentiators",
    cue: "3:00 — Navigate to Overview or keep on Activity",
    notes: [
      "Three things make SupplyMind different from a dashboard.",
      "First: agent boundaries. Each agent owns exactly one domain and communicates through the coordinator. No cross-wiring. You can swap out the freight agent without touching demand planning.",
      "Second: Fetch.ai Agentverse. The coordinator is registered on the marketplace. Any ASI:One user can chat with it — 'What's my biggest supply chain risk this week?' — and get a synthesis answer.",
      "Third: GX10 deployment. The full system, five agents plus the backend, runs in 3 GB of RAM. Fits on a single edge device. Buyers at a warehouse can run this without cloud infrastructure.",
      "Thank you.",
    ],
    accent: "text-purple-400",
    border: "border-purple-900/50",
    bg: "bg-purple-950/10",
  },
] as const;

type Beat = (typeof BEATS)[number];

// ─── Helpers ──────────────────────────────────────────────────────────────

function fmt(s: number) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function beatIndexAt(elapsed: number) {
  let idx = 0;
  for (let i = 0; i < BEATS.length; i++) {
    if (elapsed >= BEATS[i].startsAt) idx = i;
  }
  return idx;
}

// ─── Page ─────────────────────────────────────────────────────────────────

export default function ScriptPage() {
  const [elapsed, setElapsed]       = useState(0);
  const [running, setRunning]       = useState(false);
  const [demoFiring, setDemoFiring] = useState(false);
  const [manualBeat, setManualBeat] = useState<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const totalDuration = 210; // 3:30

  const currentBeatIdx = manualBeat ?? beatIndexAt(elapsed);
  const beat = BEATS[currentBeatIdx] as Beat;
  const nextBeat = BEATS[currentBeatIdx + 1] as Beat | undefined;

  // ── Timer ──────────────────────────────────────────────────────────────
  const startTimer = useCallback(() => {
    setRunning(true);
    setManualBeat(null);
    intervalRef.current = setInterval(() => {
      setElapsed((s) => {
        if (s >= totalDuration) {
          clearInterval(intervalRef.current!);
          setRunning(false);
          return totalDuration;
        }
        return s + 1;
      });
    }, 1000);
  }, []);

  const pauseTimer = useCallback(() => {
    setRunning(false);
    if (intervalRef.current) clearInterval(intervalRef.current);
  }, []);

  const resetTimer = useCallback(() => {
    pauseTimer();
    setElapsed(0);
    setManualBeat(null);
  }, [pauseTimer]);

  useEffect(() => () => { if (intervalRef.current) clearInterval(intervalRef.current); }, []);

  // Auto-clear manualBeat override when timer catches up
  useEffect(() => {
    if (manualBeat !== null && beatIndexAt(elapsed) === manualBeat) {
      setManualBeat(null);
    }
  }, [elapsed, manualBeat]);

  // ── Demo trigger ───────────────────────────────────────────────────────
  async function fireDemo() {
    setDemoFiring(true);
    try {
      await fetch(`${API_URL}/api/trigger/demo`, { method: "POST" });
    } finally {
      setDemoFiring(false);
    }
  }

  const progress = Math.min((elapsed / totalDuration) * 100, 100);

  return (
    <div className="fixed inset-0 z-[100] flex flex-col overflow-hidden bg-[#0a0a0a] text-gray-100">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-gray-800 px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold tracking-tight">
            Supply<span className="text-blue-400">Mind</span>
            <span className="ml-2 text-xs font-normal text-gray-500">· Demo Script</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Timer display */}
          <span className="w-12 text-center font-mono text-lg font-semibold tabular-nums text-white">
            {fmt(elapsed)}
          </span>

          {/* Controls */}
          <button
            onClick={resetTimer}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-800 text-gray-500 hover:bg-gray-900 hover:text-gray-300"
          >
            <RotateCcw size={13} />
          </button>
          <button
            onClick={running ? pauseTimer : startTimer}
            disabled={elapsed >= totalDuration}
            className={cn(
              "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-40",
              running
                ? "border-gray-700 bg-gray-800 text-gray-200"
                : "border-blue-700 bg-blue-950 text-blue-200 hover:bg-blue-900"
            )}
          >
            {running ? <Pause size={13} /> : <Play size={13} />}
            {running ? "Pause" : "Start"}
          </button>

          <div className="mx-1 h-5 w-px bg-gray-800" />

          {/* Run Demo shortcut */}
          <button
            onClick={fireDemo}
            disabled={demoFiring}
            className="flex items-center gap-1.5 rounded-lg border border-emerald-800 bg-emerald-950 px-3 py-1.5 text-sm font-medium text-emerald-300 transition-colors hover:bg-emerald-900 disabled:opacity-50"
          >
            <Zap size={13} />
            {demoFiring ? "Firing…" : "Fire Cascade"}
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-0.5 bg-gray-900">
        <div
          className="h-full bg-blue-600 transition-all duration-1000"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Beat pills */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-gray-900 px-6 py-2">
        {BEATS.map((b, i) => (
          <button
            key={i}
            onClick={() => setManualBeat(i)}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs transition-colors",
              i === currentBeatIdx
                ? "bg-gray-800 text-white"
                : "text-gray-600 hover:text-gray-400"
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", i === currentBeatIdx ? "bg-blue-400" : "bg-gray-700")} />
            {fmt(b.startsAt)} {b.title}
          </button>
        ))}
      </div>

      {/* Main body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Speaker notes — main column */}
        <div className={cn("flex flex-1 flex-col overflow-y-auto border-r border-gray-800 p-8 transition-colors", beat.bg)}>
          <div className="mb-1 flex items-center gap-2">
            <span className={cn("text-xs font-medium", beat.accent)}>{beat.cue}</span>
            {"action" in beat && (
              <span className="rounded bg-yellow-900/60 px-2 py-0.5 text-xs font-bold text-yellow-300">
                {beat.action}
              </span>
            )}
          </div>

          <h2 className={cn("mb-6 text-2xl font-bold", beat.accent)}>{beat.title}</h2>

          <ol className="flex flex-col gap-5">
            {beat.notes.map((note, i) => (
              <li key={i} className="flex gap-4">
                <span className={cn("mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold", beat.accent, beat.border, "border")}>
                  {i + 1}
                </span>
                <p className="text-lg leading-relaxed text-gray-100">{note}</p>
              </li>
            ))}
          </ol>

          {"showSavings" in beat && beat.showSavings && (
            <div className="mt-8 inline-flex flex-col items-center rounded-2xl border border-emerald-800/50 bg-emerald-950/40 px-8 py-6">
              <span className="mb-1 text-xs font-medium text-emerald-600 uppercase tracking-widest">Total Freight Savings</span>
              <SavingsCounter
                target={3421}
                duration={1500}
                className="text-5xl font-bold tabular-nums text-emerald-400"
              />
              <span className="mt-1 text-sm text-emerald-700">Gulf Coast consolidation · 2 shipments · Week 47</span>
            </div>
          )}
        </div>

        {/* Right sidebar — next beat + nav */}
        <div className="flex w-72 shrink-0 flex-col gap-4 overflow-y-auto p-5">
          {/* Beat navigation */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setManualBeat(Math.max(0, currentBeatIdx - 1))}
              disabled={currentBeatIdx === 0}
              className="flex items-center gap-1 rounded-lg border border-gray-800 px-3 py-1.5 text-xs text-gray-400 hover:bg-gray-900 disabled:opacity-30"
            >
              <ChevronLeft size={13} /> Prev
            </button>
            <span className="text-xs text-gray-600">
              {currentBeatIdx + 1} / {BEATS.length}
            </span>
            <button
              onClick={() => setManualBeat(Math.min(BEATS.length - 1, currentBeatIdx + 1))}
              disabled={currentBeatIdx === BEATS.length - 1}
              className="flex items-center gap-1 rounded-lg border border-gray-800 px-3 py-1.5 text-xs text-gray-400 hover:bg-gray-900 disabled:opacity-30"
            >
              Next <ChevronRight size={13} />
            </button>
          </div>

          {/* Next beat preview */}
          {nextBeat && (
            <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-4">
              <p className="mb-2 text-xs font-medium text-gray-500">
                Up next · {fmt(nextBeat.startsAt)}
              </p>
              <p className="text-sm font-medium text-gray-300">{nextBeat.title}</p>
              <p className="mt-1 text-xs text-gray-600">{nextBeat.cue}</p>
              <ul className="mt-3 flex flex-col gap-1.5">
                {nextBeat.notes.slice(0, 2).map((n, i) => (
                  <li key={i} className="text-xs text-gray-500 leading-relaxed line-clamp-2">
                    · {n}
                  </li>
                ))}
                {nextBeat.notes.length > 2 && (
                  <li className="text-xs text-gray-700">+{nextBeat.notes.length - 2} more…</li>
                )}
              </ul>
            </div>
          )}

          {/* Time to next beat */}
          {nextBeat && (
            <div className="rounded-lg border border-gray-800 bg-gray-900/20 px-4 py-3 text-center">
              <p className="text-xs text-gray-600">Time to next beat</p>
              <p className="text-xl font-semibold tabular-nums text-white">
                {fmt(Math.max(0, nextBeat.startsAt - elapsed))}
              </p>
            </div>
          )}

          {/* Dashboard links */}
          <div className="mt-auto flex flex-col gap-1.5">
            <p className="text-xs font-medium text-gray-600 mb-1">Dashboard</p>
            {(["/", "/activity", "/plan"] as const).map((href) => (
              <a
                key={href}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg border border-gray-800 px-3 py-2 text-xs text-gray-400 hover:bg-gray-900 hover:text-gray-200 transition-colors"
              >
                {href === "/" ? "Overview" : href.slice(1).replace(/^\w/, c => c.toUpperCase())} ↗
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

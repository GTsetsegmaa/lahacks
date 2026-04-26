"use client";

import { useEffect, useRef, useState } from "react";

interface SavingsCounterProps {
  target: number;
  duration?: number; // ms, default 1500
  prefix?: string;
  className?: string;
}

export function SavingsCounter({
  target,
  duration = 1500,
  prefix = "$",
  className,
}: SavingsCounterProps) {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number | null>(null);
  const prevTarget = useRef(0);

  useEffect(() => {
    if (target === prevTarget.current) return;
    prevTarget.current = target;

    if (target === 0) { setValue(0); return; }

    const startValue = value;
    const delta = target - startValue;
    const startTime = performance.now();

    const step = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(startValue + eased * delta));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step);
      }
    };

    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(step);

    return () => { if (rafRef.current !== null) cancelAnimationFrame(rafRef.current); };
  }, [target, duration]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <span className={className}>
      {prefix}{value.toLocaleString()}
    </span>
  );
}

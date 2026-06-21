import { useEffect, useState } from "react";
import { CheckIcon, Spinner } from "./icons";

// One phase of a streamed turn. `doneMs` is null while the phase is still
// running (the timer ticks live); once the next phase or the final event
// arrives it is frozen to the measured duration.
export interface Step {
  key: string;
  label: string;
  startedAt: number;
  doneMs: number | null;
}

function fmt(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export function StepTimeline({ steps, totalMs }: { steps: Step[]; totalMs: number | null }) {
  const running = steps.some((s) => s.doneMs === null);
  const [now, setNow] = useState(() => performance.now());

  // While a phase is active, re-render a few times a second so its counter ticks.
  useEffect(() => {
    if (!running) return;
    const t = window.setInterval(() => setNow(performance.now()), 60);
    return () => window.clearInterval(t);
  }, [running]);

  if (steps.length === 0) return null;

  return (
    <div className="mb-3 rounded-xl border border-edge bg-panel/60 p-2.5">
      <ul className="flex flex-col gap-1.5">
        {steps.map((s, i) => {
          const done = s.doneMs !== null;
          const elapsed = s.doneMs ?? now - s.startedAt;
          return (
            <li key={i} className="flex items-center gap-2.5 text-sm">
              <span
                className={`grid h-5 w-5 place-items-center rounded-full ${
                  done ? "text-emerald-400" : "text-accent-2"
                }`}
              >
                {done ? <CheckIcon width={14} height={14} /> : <Spinner width={14} height={14} />}
              </span>
              <span className={`flex-1 ${done ? "text-fog" : "text-white"}`}>{s.label}</span>
              <span className={`tabular-nums text-xs ${done ? "text-fog-2" : "text-accent-2"}`}>
                {fmt(elapsed)}
              </span>
            </li>
          );
        })}
      </ul>
      {totalMs !== null && (
        <div className="mt-2 border-t border-edge pt-2 text-right text-xs text-fog-2">
          Total <span className="tabular-nums text-fog">{fmt(totalMs)}</span>{" "}
          <span className="text-fog-2">(server)</span>
        </div>
      )}
    </div>
  );
}

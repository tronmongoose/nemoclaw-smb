/** The global DEMO/LIVE switch. Amber when LIVE (the one warm-blooded element). */

import { useLive } from "./LiveContext";

export function LiveToggle() {
  const { live, setLive } = useLive();

  return (
    <div className="flex items-center gap-2 font-mono text-xs">
      <button
        onClick={() => setLive(false)}
        aria-pressed={!live}
        className={[
          "px-3 py-1 rounded border transition-colors",
          !live
            ? "bg-slate-800 border-slate-600 text-slate-200"
            : "bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300",
        ].join(" ")}
      >
        DEMO
      </button>
      <button
        onClick={() => setLive(true)}
        aria-pressed={live}
        className={[
          "px-3 py-1 rounded border transition-colors",
          live
            ? "bg-amber-950 border-amber-600 text-amber-300"
            : "bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300",
        ].join(" ")}
      >
        LIVE
      </button>
    </div>
  );
}

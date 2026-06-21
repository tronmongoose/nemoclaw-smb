/** The global DEMO/LIVE switch. Amber + heartbeat when LIVE (the one warm element). */

import { useLive } from "./LiveContext";
import { cn } from "../../lib/utils";

export function LiveToggle() {
  const { live, setLive } = useLive();

  return (
    <div className="inline-flex items-center rounded-[var(--radius)] border border-border bg-card/60 p-0.5 font-mono text-xs">
      <button
        onClick={() => setLive(false)}
        aria-pressed={!live}
        className={cn(
          "rounded-[var(--radius)] px-3 py-1 transition-colors",
          !live ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
        )}
      >
        DEMO
      </button>
      <button
        onClick={() => setLive(true)}
        aria-pressed={live}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-[var(--radius)] px-3 py-1 transition-colors",
          live
            ? "bg-[hsl(var(--primary)/0.15)] text-primary"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        {live && <span className="h-1.5 w-1.5 rounded-full bg-primary animate-heartbeat" />}
        LIVE
      </button>
    </div>
  );
}

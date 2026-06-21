/** STR experience shell: editorial chrome + a Story / Explore switch.
 *
 * Story  -> the guided narrative (StrStory), built for screen-recording.
 * Explore -> free tab navigation over the four acts (StrNav + act views).
 * Wraps everything in LiveProvider so every act threads the LIVE/DEMO toggle.
 */

import { useState } from "react";
import { ErrorBoundary } from "../ErrorBoundary";
import { cn } from "../../lib/utils";
import { LiveProvider } from "./LiveContext";
import { LiveToggle } from "./LiveToggle";
import { StrNav, StrTab } from "./StrNav";
import { StrStory } from "./StrStory";
import { Act1View } from "./Act1View";
import { Act2View } from "./Act2View";
import { Act3View } from "./Act3View";
import { AuditPanel } from "./AuditPanel";

type Mode = "story" | "explore";

export function StrView({ onLegacy }: { onLegacy?: () => void }) {
  const [mode, setMode] = useState<Mode>("story");
  const [tab, setTab] = useState<StrTab>("owner");

  return (
    <LiveProvider>
      <div className="min-h-screen">
        <header className="border-b border-border">
          <div className="mx-auto flex max-w-5xl flex-wrap items-end justify-between gap-4 px-6 py-5">
            <div className="flex flex-col">
              <span className="font-mono text-[0.7rem] uppercase tracking-[0.28em] text-muted-foreground">
                NemoClaw
              </span>
              <span className="font-serif text-xl font-semibold leading-tight text-foreground">
                Short-term rental operations, governed.
              </span>
            </div>
            <div className="flex items-center gap-4">
              <ModeSwitch mode={mode} onChange={setMode} />
              <LiveToggle />
            </div>
          </div>
        </header>

        <main className="px-6 py-10">
          {mode === "story" ? (
            <StrStory />
          ) : (
            <div className="mx-auto flex max-w-4xl flex-col gap-8">
              <StrNav tab={tab} onChange={setTab} />
              <ErrorBoundary label={tab}>
                {tab === "owner" && <Act1View />}
                {tab === "management" && <Act2View />}
                {tab === "platform" && <Act3View />}
                {tab === "audit" && <AuditPanel />}
              </ErrorBoundary>
            </div>
          )}
        </main>

        {onLegacy && (
          <footer className="border-t border-border px-6 py-4">
            <div className="mx-auto max-w-5xl">
              <button
                onClick={onLegacy}
                className="font-mono text-[0.7rem] uppercase tracking-[0.2em] text-muted-foreground/60 transition-colors hover:text-muted-foreground"
              >
                Legacy demos
              </button>
            </div>
          </footer>
        )}
      </div>
    </LiveProvider>
  );
}

function ModeSwitch({ mode, onChange }: { mode: Mode; onChange: (m: Mode) => void }) {
  const opt = (m: Mode, label: string) => (
    <button
      onClick={() => onChange(m)}
      aria-pressed={mode === m}
      className={cn(
        "rounded-[var(--radius)] px-3 py-1 font-mono text-xs uppercase tracking-widest transition-colors",
        mode === m ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </button>
  );
  return (
    <div className="inline-flex items-center rounded-[var(--radius)] border border-border bg-card/60 p-0.5">
      {opt("story", "Story")}
      {opt("explore", "Explore")}
    </div>
  );
}

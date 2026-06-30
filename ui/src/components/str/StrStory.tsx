/** Guided narrative: a stepped walkthrough of the three acts for the demo video.
 *
 * Intro -> Act I (Owner) -> Act II (Management) -> Act III (Platform) -> Close.
 * Each act step frames the real act view with a serif narrative intro. Reuses the
 * same act components as the explorer, so what the viewer sees is the real system.
 */

import { useState, ReactNode } from "react";
import { ErrorBoundary } from "../ErrorBoundary";
import { Button } from "@/components/ui/button";
import { cn } from "../../lib/utils";
import { Rule } from "./shared";
import { Act1View } from "./Act1View";
import { Act2View } from "./Act2View";
import { Act3View } from "./Act3View";

interface Step {
  key: string;
  kicker?: string;
  title: string;
  dek: string;
  body?: ReactNode;
}

const STEPS: Step[] = [
  {
    key: "intro",
    title: "Sweet Clementine by the Sea",
    dek:
      "One beach cottage in Oceanside. Three roles in the short-term rental economy. One governed agent that earns the right to act.",
  },
  {
    key: "owner",
    title: "The Owner",
    dek:
      "You are the owner. Your management company sends a monthly statement. The agent reads the ledger before you do, and catches a fee that does not match the contract.",
    body: <Act1View />,
  },
  {
    key: "management",
    title: "The Management Company",
    dek:
      "Now you run the company. Five properties, three owners, a cleaning crew. Every checkout issues a single-use card under a scoped identity, then settles at month end.",
    body: <Act2View />,
  },
  {
    key: "platform",
    title: "The Platform",
    dek:
      "Now you are the platform. Other AI agents pay you per call for a price and for an audit of how machine-readable a listing is. The audit is the product.",
    body: <Act3View />,
  },
  {
    key: "close",
    title: "This is Agent Engine Optimization",
    dek:
      "Search is becoming machine to machine. A listing an AI booking agent cannot parse is a listing that does not get booked. The agent that audits for that, and earns per call to do it, is the business.",
  },
];

export function StrStory() {
  const [i, setI] = useState(0);
  const step = STEPS[i];
  const atStart = i === 0;
  const atEnd = i === STEPS.length - 1;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8">
      <header className="flex flex-col gap-3">
        {step.kicker && (
          <span className="font-mono text-[0.7rem] uppercase tracking-[0.28em] text-primary">
            {step.kicker}
          </span>
        )}
        <h2 className="font-serif text-3xl font-semibold leading-tight text-foreground md:text-4xl">
          {step.title}
        </h2>
        <p
          className={cn(
            "max-w-prose font-serif text-lg leading-relaxed text-muted-foreground",
            (atStart || atEnd) && "drop-cap",
          )}
        >
          {step.dek}
        </p>
      </header>

      {step.body && (
        <>
          <Rule />
          <ErrorBoundary label={step.title}>{step.body}</ErrorBoundary>
        </>
      )}

      {atEnd && <Colophon />}

      <Rule />
      <nav className="flex items-center justify-between">
        <Button
          variant="ghost"
          disabled={atStart}
          onClick={() => setI((n) => Math.max(0, n - 1))}
          className="font-mono text-xs uppercase tracking-widest disabled:opacity-30"
        >
          Back
        </Button>

        <div className="flex items-center gap-2">
          {STEPS.map((s, n) => (
            <button
              key={s.key}
              aria-label={`Go to ${s.title}`}
              onClick={() => setI(n)}
              className={cn(
                "h-1.5 rounded-full transition-all",
                n === i ? "w-6 bg-primary" : "w-1.5 bg-border hover:bg-muted-foreground",
              )}
            />
          ))}
        </div>

        {atEnd ? (
          <Button
            onClick={() => setI(0)}
            className="font-mono text-xs uppercase tracking-widest"
          >
            Restart
          </Button>
        ) : (
          <Button
            onClick={() => setI((n) => Math.min(STEPS.length - 1, n + 1))}
            className="font-mono text-xs uppercase tracking-widest"
          >
            {atStart ? "Begin" : "Next"}
          </Button>
        )}
      </nav>
    </div>
  );
}

function Colophon() {
  return (
    <div className="flex flex-col gap-3 border-t border-border pt-6 font-mono text-xs text-muted-foreground">
      <span className="uppercase tracking-[0.22em] text-muted-foreground/70">Colophon</span>
      <p className="leading-relaxed">
        Governed by C1 identity (Baton grant-matching, scoped non-human
        identities). Reasoning by Hermes on Nous Portal and Nemotron on NVIDIA NIM.
        Payments by Stripe, in demo mode. Every action is written to a hash-chained
        audit log. Flip LIVE to watch a real model call land.
      </p>
    </div>
  );
}

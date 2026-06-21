/** Per-portal "explain the stack" overlay: shows which sponsor plugs into THIS portal,
 *  with live + historical call counts drawn from /str/interactions. */

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "../../../lib/utils";
import type { StrInteractionsResponse, StrSegment } from "../../../types";
import { SectionLabel } from "../shared";
import {
  opMatchesCell,
  PORTAL_LABELS,
  SPONSOR_MAP,
  type SponsorRow,
  type SponsorCell,
} from "./sponsorMap";
import { usePoll } from "../../../hooks/usePoll";

// ---------------------------------------------------------------------------
// Counts helper
// ---------------------------------------------------------------------------

interface CellCounts {
  total: number;
  live: number;
}

/** Tally how many interactions belong to a given sponsor cell. */
function cellCounts(
  entries: StrInteractionsResponse["entries"],
  sponsor: string,
  cell: SponsorCell,
): CellCounts {
  const matching = entries.filter(
    (e) => e.sponsor === sponsor && opMatchesCell(e.op, cell),
  );
  return {
    total: matching.length,
    live: matching.filter((e) => e.mode === "live").length,
  };
}

// ---------------------------------------------------------------------------
// SponsorCallout
// ---------------------------------------------------------------------------

/** Card for one sponsor that is active in the current portal. */
function SponsorCallout({
  row,
  cell,
  counts,
}: {
  row: SponsorRow;
  cell: SponsorCell;
  counts: CellCounts;
}) {
  return (
    <div className="rounded-[var(--radius)] border border-border bg-card p-4 flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-serif text-base font-semibold text-foreground">
          {row.sponsor}
        </span>
        <span className="font-mono text-[0.65rem] uppercase tracking-widest text-muted-foreground">
          {row.kind}
        </span>
      </div>
      <p className="font-mono text-xs text-primary">{cell.capability}</p>
      <p className="text-xs text-muted-foreground">{cell.problem}</p>
      <div className="mt-auto flex items-center gap-2 pt-2 border-t border-border">
        {counts.live > 0 && (
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
        )}
        <span className="font-mono text-xs text-muted-foreground">
          {counts.total} calls
          {counts.live > 0 && (
            <span className="ml-1 text-primary">({counts.live} live)</span>
          )}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panel (rendered only when open so the poll hook is only alive when open)
// ---------------------------------------------------------------------------

/** The dialog panel content, including its own data fetch. */
function OverlayPanel({
  segment,
  onClose,
  panelRef,
}: {
  segment: StrSegment;
  onClose: () => void;
  panelRef: React.RefObject<HTMLDivElement>;
}) {
  const { data } = usePoll<StrInteractionsResponse>(
    `/str/interactions?segment=${segment}`,
    5000,
  );

  const entries = data?.entries ?? [];
  const activeRows = SPONSOR_MAP.filter((r) => r.byPortal[segment]);
  const inactiveRows = SPONSOR_MAP.filter((r) => !r.byPortal[segment]);
  const portalLabel = PORTAL_LABELS[segment];

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-label={`Tech stack for the ${portalLabel} portal`}
      tabIndex={-1}
      className={cn(
        "relative z-50 mx-auto my-auto w-full max-w-2xl max-h-[85vh] overflow-y-auto",
        "rounded-[var(--radius)] border border-border bg-background p-6 shadow-lg",
        "flex flex-col gap-5",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-serif text-xl font-semibold text-foreground">
            The stack, in this portal
          </h2>
          <p className="font-mono text-xs text-muted-foreground mt-0.5">
            {portalLabel} portal
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onClose}
          aria-label="Close stack overlay"
        >
          Hide
        </Button>
      </div>

      <SectionLabel>Active sponsors</SectionLabel>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {activeRows.map((row) => {
          const cell = row.byPortal[segment]!;
          return (
            <SponsorCallout
              key={row.id}
              row={row}
              cell={cell}
              counts={cellCounts(entries, row.sponsor, cell)}
            />
          );
        })}
      </div>

      {inactiveRows.length > 0 && (
        <p className="font-mono text-[0.7rem] text-muted-foreground/60">
          Not used in this portal:{" "}
          {inactiveRows.map((r) => r.sponsor).join(", ")}
        </p>
      )}

      <p className="border-t border-border pt-3 font-mono text-[0.65rem] text-muted-foreground/70">
        Every action here is governed by ConductorOne and written to a
        hash-chained audit log.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public export
// ---------------------------------------------------------------------------

/** Toggle button + full-viewport overlay for the sponsor tech layer. */
export function StackOverlay({ segment }: { segment: StrSegment }): JSX.Element {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Move focus into the panel when opened.
  useEffect(() => {
    if (open) panelRef.current?.focus();
  }, [open]);

  // Close on Escape.
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        {open ? "Hide the stack" : "Show the stack"}
      </Button>

      {open && (
        // Scrim: bg-black/50 reads as a neutral dim on both light and dark themes.
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpen(false);
          }}
        >
          <OverlayPanel
            segment={segment}
            onClose={() => setOpen(false)}
            panelRef={panelRef as React.RefObject<HTMLDivElement>}
          />
        </div>
      )}
    </>
  );
}

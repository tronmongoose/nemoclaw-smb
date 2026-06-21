/** Audit: hash-chain proof. Polls /str/audit; new entries flash in as they land. */

import { useEffect, useRef } from "react";
import { usePoll } from "../../hooks/usePoll";
import { StrAuditEntry, StrAuditResponse } from "../../types";
import { useLive, liveParam } from "./LiveContext";
import { centsToUSD, EmptyState, SectionLabel, Rule } from "./shared";
import {
  Table, TableHeader, TableHead, TableBody, TableRow, TableCell,
} from "@/components/ui/table";
import {
  Tooltip, TooltipTrigger, TooltipContent, TooltipProvider,
} from "@/components/ui/tooltip";
import { cn } from "../../lib/utils";

function fmtTs(ts: string | undefined): string {
  if (!ts) return "";
  try {
    const d = new Date(ts);
    return d.toISOString().replace("T", " ").slice(0, 19) + "Z";
  } catch {
    return ts;
  }
}

function HashChain({ prev, entry }: { prev: string | undefined; entry: string | undefined }) {
  if (!entry) return <span className="text-muted-foreground/40 font-mono text-xs">--</span>;
  const prevTrunc = prev ? prev.slice(0, 8) + "..." : "genesis";
  const entryTrunc = entry.slice(0, 8) + "...";
  const fullLabel = prev ? `${prev} -> ${entry}` : `genesis -> ${entry}`;
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className="cursor-default font-mono text-xs text-muted-foreground hover:text-foreground transition-colors"
            aria-label={fullLabel}
          >
            <span className="text-muted-foreground/50">{prevTrunc}</span>
            <span className="mx-1 text-border">-&gt;</span>
            <span className="text-primary/70">{entryTrunc}</span>
          </span>
        </TooltipTrigger>
        <TooltipContent className="font-mono text-xs max-w-xs break-all">
          {fullLabel}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function AuditRow({ entry, isNew }: { entry: StrAuditEntry; isNew: boolean }) {
  const label =
    entry.event === "mpp_earn"
      ? `earn / ${entry.service ?? ""}`
      : entry.action ?? entry.event ?? "entry";
  const amount = typeof entry.amount_cents === "number" ? centsToUSD(entry.amount_cents) : "";
  const actor = typeof entry.actor === "string" ? entry.actor : (entry.token_id as string | undefined) ?? "";
  const decision = typeof entry.decision === "string" ? entry.decision : "";

  return (
    <TableRow className={cn("border-b border-border/50", isNew && "animate-flash")}>
      <TableCell className="w-10 font-mono text-xs text-muted-foreground/60 pr-1">
        {entry.seq ?? ""}
      </TableCell>
      <TableCell className="font-mono text-xs text-muted-foreground/70 whitespace-nowrap">
        {fmtTs(entry.ts)}
      </TableCell>
      <TableCell className="font-mono text-xs text-foreground">{label}</TableCell>
      <TableCell className="font-mono text-xs text-muted-foreground">{actor}</TableCell>
      <TableCell className="font-mono text-xs text-muted-foreground">{decision}</TableCell>
      <TableCell className="font-mono text-xs text-right text-foreground tabular-nums">
        {amount}
      </TableCell>
      <TableCell className="text-left">
        <HashChain prev={entry.prev_hash} entry={entry.entry_hash} />
      </TableCell>
    </TableRow>
  );
}

export function AuditPanel() {
  const { live } = useLive();
  const url = `/str/audit?limit=50${liveParam(live).replace("?", "&")}`;
  const { data } = usePoll<StrAuditResponse>(url, 2_000);

  const entries = data?.entries ?? [];
  const prevMaxSeq = useRef(-1);
  const firstLoad = useRef(true);
  const maxSeq = entries.reduce((m, e) => Math.max(m, e.seq ?? -1), -1);
  const threshold = firstLoad.current ? Infinity : prevMaxSeq.current;
  useEffect(() => {
    if (entries.length > 0) {
      firstLoad.current = false;
      prevMaxSeq.current = maxSeq;
    }
  }, [maxSeq, entries.length]);
  const verifyOk = data?.verify?.ok ?? null;
  const verifyMsg = data?.verify?.message;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-0.5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-serif text-xl font-semibold text-foreground">The Audit Trail</h2>
            <p className="font-mono text-xs text-muted-foreground mt-0.5">
              Tamper-evident. Every act writes here.
            </p>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0 pt-0.5">
            {verifyOk === null ? (
              <span className="font-mono text-xs px-2 py-1 rounded border border-border text-muted-foreground/50">
                VERIFYING...
              </span>
            ) : (
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-[var(--radius)] border px-2 py-1 font-mono text-xs",
                  verifyOk ? "border-verified text-verified" : "border-destructive text-destructive",
                )}
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    verifyOk ? "bg-verified animate-heartbeat" : "bg-destructive",
                  )}
                />
                {verifyOk ? "CHAIN VERIFIED" : "CHAIN FAULT"}
              </span>
            )}
          </div>
        </div>
      </div>

      <Rule />

      <div className="flex items-center justify-between">
        <SectionLabel>Hash chain ({data?.count ?? 0} entries)</SectionLabel>
        {verifyMsg && (
          <span className="font-mono text-[0.65rem] text-muted-foreground/50">{verifyMsg}</span>
        )}
      </div>

      {entries.length === 0 ? (
        <EmptyState hint="GET /str/audit" />
      ) : (
        <div className="border border-border rounded-[var(--radius)] overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-b border-border hover:bg-transparent">
                <TableHead className="font-mono text-[0.65rem] uppercase tracking-widest text-muted-foreground/60 w-10 pr-1">#</TableHead>
                <TableHead className="font-mono text-[0.65rem] uppercase tracking-widest text-muted-foreground/60">Time</TableHead>
                <TableHead className="font-mono text-[0.65rem] uppercase tracking-widest text-muted-foreground/60">Event / Service</TableHead>
                <TableHead className="font-mono text-[0.65rem] uppercase tracking-widest text-muted-foreground/60">Actor</TableHead>
                <TableHead className="font-mono text-[0.65rem] uppercase tracking-widest text-muted-foreground/60">Decision</TableHead>
                <TableHead className="font-mono text-[0.65rem] uppercase tracking-widest text-muted-foreground/60 text-right">Amount</TableHead>
                <TableHead className="font-mono text-[0.65rem] uppercase tracking-widest text-muted-foreground/60">Hash linkage</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((e, i) => (
                <AuditRow
                  key={`${e.entry_hash ?? i}`}
                  entry={e}
                  isNew={(e.seq ?? -1) > threshold}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

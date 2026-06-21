/** Live verification grid: each sponsor pillar with its status, detail, skills, and a
 *  Verify-live button that probes the real integration. The cross-cutting matrix above
 *  carries the visual; this is the proof that each sponsor is actually live. */

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import type { IntegrationStatusResponse, IntegrationVerify } from "../../types";
import { StatusPill, ElapsedCounter, EmptyState, Plate } from "./shared";
import { Button } from "@/components/ui/button";

function statusOk(status: string): boolean {
  return status === "REAL" || status === "LIVE-OK" || status === "LIVE-CAPABLE";
}

interface VerifyState {
  pending: boolean;
  result: IntegrationVerify | null;
}

export function StackGraph() {
  const [data, setData] = useState<IntegrationStatusResponse | null | undefined>(undefined);
  // nodeStatuses: mutable status overrides from live-verify results
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, string>>({});
  const [verifyStates, setVerifyStates] = useState<Record<string, VerifyState>>({});

  useEffect(() => {
    apiFetch<IntegrationStatusResponse>("/integrations/status").then((res) => setData(res ?? null));
  }, []);

  const handleVerify = useCallback(async (id: string) => {
    setVerifyStates((prev) => ({ ...prev, [id]: { pending: true, result: null } }));
    const result = await apiFetch<IntegrationVerify>(`/integrations/verify?pillar=${id}`);
    setVerifyStates((prev) => ({ ...prev, [id]: { pending: false, result: result ?? null } }));
    if (result) setNodeStatuses((prev) => ({ ...prev, [id]: result.status }));
  }, []);

  if (data === undefined) return null;
  if (data === null) return <EmptyState hint="Integration status unavailable" />;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {data.pillars.map((pillar) => {
        const currentStatus = nodeStatuses[pillar.id] ?? pillar.status;
        const vs = verifyStates[pillar.id];
        const verifyResult = vs?.result ?? null;

        return (
          <Plate key={pillar.id} className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-medium text-foreground">{pillar.label}</span>
                {pillar.vendor && (
                  <span className="font-mono text-xs text-muted-foreground">{pillar.vendor}</span>
                )}
                <StatusPill ok={statusOk(currentStatus)} label={currentStatus} />
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleVerify(pillar.id)}
                disabled={vs?.pending ?? false}
                aria-label={`Verify live ${pillar.label}`}
              >
                Verify live
              </Button>
            </div>

            {pillar.detail && (
              <p className="font-mono text-xs text-muted-foreground">{pillar.detail}</p>
            )}

            {vs?.pending && <ElapsedCounter running={true} label={`Verifying ${pillar.label}`} />}
            {verifyResult && !vs?.pending && (
              <span className="font-mono text-xs text-verified">
                {verifyResult.status} {verifyResult.latency_ms}ms, {verifyResult.detail}
              </span>
            )}

            {pillar.skills && pillar.skills.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {pillar.skills.map((skill) => (
                  <span
                    key={skill}
                    className="rounded-[var(--radius)] border border-border bg-background px-1.5 py-0.5 font-mono text-[0.65rem] text-muted-foreground"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            )}
          </Plate>
        );
      })}
    </div>
  );
}

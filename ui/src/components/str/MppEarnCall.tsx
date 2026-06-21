/** MPP HTTP-402 earn-call demonstrator.
 *
 * Renders the real pay-per-call loop on /str/act3/aeo-audit: first WITHOUT a
 * token (server returns 402 + the stripe-mpp WWW-Authenticate header), then
 * WITH mpp_tok_demo (server returns 200 and the audit result). The shared
 * apiFetch wrapper collapses non-2xx to null, so this component talks to fetch
 * directly to capture the 402 status and header. Threads the live param through.
 */

import { useState } from "react";
import { liveParam, useLive } from "./LiveContext";
import { SectionLabel } from "./shared";
import { Button } from "@/components/ui/button";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

const AEO_BODY = {
  listing_text: "Sweet Clementine by the Sea. Pet-friendly home. We only accept dogs.",
  amenities_list: ["wifi", "parking"],
  existing_schema: {},
  listing_url: "https://www.airbnb.com/rooms/838634728141757030",
};

interface CallResult {
  status: number;
  wwwAuth: string | null;
  ok: boolean;
}

async function callAeo(token: string | null, live: boolean): Promise<CallResult | null> {
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${BASE}/str/act3/aeo-audit${liveParam(live)}`, {
      method: "POST",
      headers,
      body: JSON.stringify(AEO_BODY),
    });
    return { status: res.status, wwwAuth: res.headers.get("www-authenticate"), ok: res.ok };
  } catch {
    return null;
  }
}

export function MppEarnCall() {
  const { live } = useLive();
  const [unpaid, setUnpaid] = useState<CallResult | null>(null);
  const [paid, setPaid] = useState<CallResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setUnpaid(await callAeo(null, live));
    setPaid(await callAeo("mpp_tok_demo", live));
    setBusy(false);
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <SectionLabel>MPP earn loop (402 then 200)</SectionLabel>
        <Button
          variant="outline"
          disabled={busy}
          onClick={() => void run()}
          className="font-mono text-xs"
        >
          {busy ? "Calling..." : "Run earn call"}
        </Button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <CallCard title="No token" result={unpaid} expect={402} />
        <CallCard title="mpp_tok_demo" result={paid} expect={200} />
      </div>
    </section>
  );
}

function CallCard({ title, result, expect }: { title: string; result: CallResult | null; expect: number }) {
  const match = result?.status === expect;
  return (
    <div className="rounded-[var(--radius)] border border-border bg-card/60 p-4 flex flex-col gap-2 font-mono text-xs">
      <span className="text-muted-foreground">{title}</span>
      {!result ? (
        <span className="text-muted-foreground/50">not yet called</span>
      ) : (
        <>
          <span
            className={[
              "self-start rounded-[var(--radius)] border px-2 py-1",
              match
                ? expect === 402
                  ? "border-primary bg-[hsl(var(--primary)/0.1)] text-primary"
                  : "border-verified bg-[hsl(var(--verified)/0.08)] text-verified"
                : "border-destructive bg-[hsl(var(--destructive)/0.08)] text-destructive",
            ].join(" ")}
          >
            HTTP {result.status}
          </span>
          {result.wwwAuth && (
            <span className="text-muted-foreground/70 break-all leading-relaxed">
              {result.wwwAuth}
            </span>
          )}
        </>
      )}
    </div>
  );
}

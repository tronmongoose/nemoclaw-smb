/** STR-specific API helpers that the shared lib/api wrapper cannot express.
 *
 * The AEO endpoint enforces the real HTTP-402 paywall: it returns 200 only when
 * an MPP bearer token is presented. The shared apiPost sends no Authorization
 * header, so the AEO call needs a header-aware post. Fails soft to null on any
 * non-2xx (including the 402) or transport error, matching apiFetch semantics.
 */

import { StrAeoResponse, StrGuestCommsResponse } from "../../types";
import { liveParam } from "./LiveContext";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

// The demo MPP token that satisfies the AEO 402 gate (matches mpp_tok_demo).
const MPP_TOKEN = "mpp_tok_demo";

const AEO_BODY = {
  listing_text: "Sweet Clementine by the Sea. Pet-friendly home. We only accept dogs.",
  amenities_list: ["wifi", "parking"],
  existing_schema: {},
  listing_url: "https://www.airbnb.com/rooms/838634728141757030",
};

/** POST the AEO audit with the MPP bearer token. Returns null on 402/error. */
export async function postAeoAudit(live: boolean): Promise<StrAeoResponse | null> {
  try {
    const res = await fetch(`${BASE}/str/act3/aeo-audit${liveParam(live)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${MPP_TOKEN}` },
      body: JSON.stringify(AEO_BODY),
    });
    if (!res.ok) return null;
    return (await res.json()) as StrAeoResponse;
  } catch {
    return null;
  }
}

const GUEST_COMMS_BODY = {
  guest_context:
    "Hi! Booking Fri-Sun for 2. Any chance of early check-in, and is the place good for an anniversary trip?",
  property_id: "prop-001",
  inquiry_type: "pre-booking",
};

/** POST the guest-comms call with the MPP bearer token. Returns null on 402/error. */
export async function postGuestComms(live: boolean): Promise<StrGuestCommsResponse | null> {
  try {
    const res = await fetch(`${BASE}/str/act3/guest-comms${liveParam(live)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${MPP_TOKEN}` },
      body: JSON.stringify(GUEST_COMMS_BODY),
    });
    if (!res.ok) return null;
    return (await res.json()) as StrGuestCommsResponse;
  } catch {
    return null;
  }
}

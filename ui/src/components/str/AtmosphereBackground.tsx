/** Portal atmosphere. Three stacked fixed layers cross-fade as the portal changes,
 *  so the page temperature shifts warm -> cool -> electric. The beach (one rental)
 *  gives way to a cool operations floor, then to the dark technical swarm: the
 *  transition itself communicates scale. Owner photo: Mark Neal on Unsplash.
 *  prefers-reduced-motion disables the fades and the drift (handled in index.css). */

import type { PortalView } from "../../types";

export function AtmosphereBackground({ portal }: { portal: PortalView }) {
  const isOwner = portal === "owner";
  const isFirm = portal === "firm";
  const isDark = portal === "agent" || portal === "stack";

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* Owner: the Oceanside pier at golden hour, a slow drift. The single rental. */}
      <div
        className={`absolute inset-0 transition-opacity duration-700 ${isOwner ? "opacity-100" : "opacity-0"}`}
      >
        <div
          className="animate-drift absolute inset-0 bg-cover bg-center opacity-40"
          style={{ backgroundImage: "url(/oceanside.jpg)" }}
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(to bottom, hsl(40 48% 96% / 0.20) 0%, hsl(40 42% 95% / 0.55) 42%, hsl(40 42% 94% / 0.86) 100%)",
          }}
        />
        {/* faint sand grain, felt not seen */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
          }}
        />
      </div>

      {/* Company: a cool operations floor. No photo, just cool light. */}
      <div
        className={`absolute inset-0 transition-opacity duration-700 ${isFirm ? "opacity-100" : "opacity-0"}`}
        style={{
          background:
            "linear-gradient(160deg, hsl(205 44% 95%) 0%, hsl(195 40% 94%) 55%, hsl(205 30% 92%) 100%)",
        }}
      />

      {/* Swarm + tech layer: dark command center, faint technical grid + electric vignette. */}
      <div
        className={`absolute inset-0 transition-opacity duration-700 ${isDark ? "opacity-100" : "opacity-0"}`}
      >
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(120% 80% at 50% -10%, hsl(205 40% 16%) 0%, hsl(215 32% 9%) 58%, hsl(220 34% 6%) 100%)",
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.10]"
          style={{
            backgroundImage:
              "linear-gradient(hsl(186 80% 60% / 0.5) 1px, transparent 1px), linear-gradient(90deg, hsl(186 80% 60% / 0.5) 1px, transparent 1px)",
            backgroundSize: "44px 44px",
          }}
        />
      </div>
    </div>
  );
}

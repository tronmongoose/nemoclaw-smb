/** Portal atmosphere. Three stacked fixed layers cross-fade as the portal changes, so
 *  the page temperature shifts warm-light -> cool-dark -> electric-dark. Owner keeps the
 *  Oceanside pier (the one beach house); Company is a cool operations console; Swarm is a
 *  dark command center. The photo receding into abstraction tells the scale story.
 *  Owner photo: Mark Neal on Unsplash. prefers-reduced-motion disables the drift (index.css). */

import type { PortalView } from "../../types";

export function AtmosphereBackground({ portal }: { portal: PortalView }) {
  const isOwner = portal === "owner";
  const isFirm = portal === "firm";
  const isSwarm = portal === "agent" || portal === "stack";

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* Owner: the Oceanside pier at golden hour, subtle behind a warm scrim, slow drift. */}
      <div
        className={`absolute inset-0 transition-opacity duration-700 ${isOwner ? "opacity-100" : "opacity-0"}`}
      >
        <div
          className="animate-drift absolute inset-0 bg-cover bg-center opacity-[0.34]"
          style={{
            backgroundImage: "url(/oceanside.jpg)",
            filter: "saturate(0.62) brightness(1.02) contrast(0.92)",
          }}
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(to bottom, hsl(38 44% 93% / 0.30) 0%, hsl(36 38% 92% / 0.62) 44%, hsl(35 33% 91% / 0.90) 100%)",
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
          }}
        />
      </div>

      {/* Company: a cool, dark operations console. Faint blue grid, no photo. */}
      <div
        className={`absolute inset-0 transition-opacity duration-700 ${isFirm ? "opacity-100" : "opacity-0"}`}
      >
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(120% 90% at 50% -8%, hsl(212 30% 18%) 0%, hsl(214 28% 13%) 56%, hsl(216 30% 10%) 100%)",
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              "linear-gradient(hsl(202 82% 66% / 0.5) 1px, transparent 1px), linear-gradient(90deg, hsl(202 82% 66% / 0.5) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
      </div>

      {/* Swarm + tech layer: dark command center, electric vignette + cyan grid. */}
      <div
        className={`absolute inset-0 transition-opacity duration-700 ${isSwarm ? "opacity-100" : "opacity-0"}`}
      >
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(120% 85% at 50% -10%, hsl(220 45% 14%) 0%, hsl(230 35% 6%) 58%, hsl(232 40% 4%) 100%)",
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.10]"
          style={{
            backgroundImage:
              "linear-gradient(hsl(188 95% 60% / 0.5) 1px, transparent 1px), linear-gradient(90deg, hsl(188 95% 60% / 0.5) 1px, transparent 1px)",
            backgroundSize: "44px 44px",
          }}
        />
      </div>
    </div>
  );
}

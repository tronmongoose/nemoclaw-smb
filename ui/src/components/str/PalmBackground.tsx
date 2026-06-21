/** Calm beach atmosphere: the Oceanside pier at golden hour, palms lining the rail,
 *  with a slow drift. A light scrim keeps the page calm and readable.
 *  Photo: Mark Neal on Unsplash (free for commercial use). Fixed, behind all content. */

export function PalmBackground() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div
        className="animate-drift absolute inset-0 bg-cover bg-center opacity-40"
        style={{ backgroundImage: "url(/oceanside.jpg)" }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(to bottom, hsl(200 48% 96% / 0.20) 0%, hsl(195 42% 96% / 0.55) 42%, hsl(40 42% 95% / 0.82) 100%)",
        }}
      />
    </div>
  );
}

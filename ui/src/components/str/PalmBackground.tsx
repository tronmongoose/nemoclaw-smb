/** Calm beach atmosphere: a palm whose fronds sway lightly in the breeze.
 *  The one signature motion. Fixed, low-opacity, behind all content. */

export function PalmBackground() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <svg
        className="absolute -bottom-12 -right-6 h-[82vh] w-auto text-primary opacity-[0.12]"
        viewBox="0 0 220 300"
        fill="none"
        preserveAspectRatio="xMaxYMax meet"
      >
        {/* trunk: a gentle lean toward the sea */}
        <path
          d="M150 300 C140 232 142 176 150 128 C153 110 158 98 166 90"
          stroke="currentColor"
          strokeWidth="7"
          strokeLinecap="round"
          fill="none"
        />
        {/* crown of fronds, swaying as one */}
        <g className="animate-palm-sway" style={{ transformOrigin: "166px 88px" }}>
          <path d="M166 88 C128 70 92 64 56 78" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" fill="none" />
          <path d="M166 88 C132 56 96 40 60 38" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" fill="none" />
          <path d="M166 88 C150 50 132 22 104 8" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" fill="none" />
          <path d="M166 88 C176 48 178 18 168 -4" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" fill="none" />
          <path d="M166 88 C198 56 222 36 250 30" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" fill="none" />
          <path d="M166 88 C204 74 236 70 268 80" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" fill="none" />
          <path d="M166 88 C200 96 230 108 252 130" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" fill="none" />
          {/* coconuts */}
          <circle cx="162" cy="96" r="4" fill="currentColor" />
          <circle cx="172" cy="98" r="4" fill="currentColor" />
        </g>
      </svg>
    </div>
  );
}

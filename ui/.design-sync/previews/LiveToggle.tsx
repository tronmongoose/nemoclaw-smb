import { LiveToggle } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Default state: component initialises in DEMO mode via LiveContext default. */
export function LiveToggleDefault() {
  return (
    <Frame>
      <p className="font-mono text-xs text-muted-foreground">Mode selector - starts in DEMO</p>
      <LiveToggle />
    </Frame>
  );
}

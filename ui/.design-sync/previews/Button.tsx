import { Button } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", padding: 28 }}
  >
    {children}
  </div>
);

export const Variants = () => (
  <Frame>
    <Button>Approve correction</Button>
    <Button variant="outline">Run pricing ($0.25)</Button>
    <Button variant="secondary">Explore</Button>
    <Button variant="ghost">Back</Button>
    <Button variant="destructive">Deny</Button>
  </Frame>
);

export const Sizes = () => (
  <Frame>
    <Button size="sm">Small</Button>
    <Button>Default</Button>
    <Button size="lg">Run AEO audit ($1.00)</Button>
  </Frame>
);

export const Disabled = () => (
  <Frame>
    <Button disabled>Approving...</Button>
  </Frame>
);

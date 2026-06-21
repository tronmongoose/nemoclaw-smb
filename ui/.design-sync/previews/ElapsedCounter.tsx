import { ElapsedCounter } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

export function DefaultLabel() {
  return (
    <Frame>
      <ElapsedCounter running={true} />
    </Frame>
  );
}

export function NemotronUltra() {
  return (
    <Frame>
      <ElapsedCounter running={true} label="Calling Nemotron Ultra" />
    </Frame>
  );
}

export function AeoAnalysis() {
  return (
    <Frame>
      <ElapsedCounter running={true} label="AEO audit - prop-001" />
    </Frame>
  );
}

export function HashChainVerify() {
  return (
    <Frame>
      <ElapsedCounter running={true} label="Verifying hash chain" />
    </Frame>
  );
}

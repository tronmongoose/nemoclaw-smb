import {
  Tooltip,
  TooltipProvider,
  TooltipTrigger,
  TooltipContent,
} from "nemoclaw-smb-ui";
import { Button } from "nemoclaw-smb-ui";
import { SectionLabel, StatusPill, KV } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Payout action button with tooltip explaining fee schedule */
export function PayoutTooltip() {
  return (
    <Frame>
      <SectionLabel>Tooltip -- Payout Action</SectionLabel>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button size="sm">Release $2,511.80</Button>
          </TooltipTrigger>
          <TooltipContent>
            Net after 18% platform fee + $145 cleaning. Clears in 2 business days.
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </Frame>
  );
}

/** AEO score badge -- hover explains what AEO means */
export function AEOScoreTooltip() {
  return (
    <Frame>
      <SectionLabel>Tooltip -- AEO Score</SectionLabel>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="outline" size="sm" className="font-mono text-primary">
              AEO 73
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">
            AI Experience Optimization score. Target 85+ for top search placement.
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </Frame>
  );
}

/** Hash-chain status pill -- hover shows last verified timestamp */
export function HashChainStatusTooltip() {
  return (
    <Frame>
      <SectionLabel>Tooltip -- Hash-Chain Status</SectionLabel>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="cursor-default">
              <StatusPill ok={true} label="VALID" />
            </span>
          </TooltipTrigger>
          <TooltipContent>
            1,204 entries verified. Last full scan 2026-06-21 06:30. No gaps.
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </Frame>
  );
}

/** LIVE/DEMO toggle tooltip -- hover explains what LIVE mode costs */
export function LiveModeTooltip() {
  return (
    <Frame>
      <SectionLabel>Tooltip -- LIVE Mode Warning</SectionLabel>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="font-mono text-xs text-primary border border-primary/40 bg-[hsl(var(--primary)/0.08)] px-3"
            >
              <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-primary inline-block" />
              LIVE
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            Calls Nemotron Ultra. Latency 30-90s. Use DEMO for quick iteration.
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </Frame>
  );
}

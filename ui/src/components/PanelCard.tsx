/** Reusable dark panel card shell with a title bar. */

import { ReactNode } from "react";

interface PanelCardProps {
  title: string;
  children: ReactNode;
  className?: string;
}

export function PanelCard({ title, children, className = "" }: PanelCardProps) {
  return (
    <div className={`flex flex-col bg-slate-900 border border-slate-800 rounded-lg overflow-hidden ${className}`}>
      <div className="px-4 py-2 border-b border-slate-800 bg-slate-950">
        <h2 className="text-xs font-mono font-semibold uppercase tracking-widest text-cyan-500">
          {title}
        </h2>
      </div>
      <div className="flex-1 overflow-auto p-4">{children}</div>
    </div>
  );
}

/** Error boundary: a render crash in one view shows a message instead of blanking the app. */

import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
  label?: string;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error): void {
    console.error("View crashed:", error);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="flex flex-col gap-2 p-6 font-mono text-sm text-red-400 bg-slate-900 border border-red-900 rounded-lg">
          <span className="text-red-300">{this.props.label ?? "View"} failed to render</span>
          <span className="text-slate-400 break-all">{this.state.error.message}</span>
          <span className="text-slate-600 text-xs">Open the browser console for the full stack.</span>
        </div>
      );
    }
    return this.props.children;
  }
}

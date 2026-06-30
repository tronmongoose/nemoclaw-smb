/** Global test setup: extend expect with jest-dom matchers and shim browser APIs absent from jsdom. */

import { vi } from "vitest";
import "@testing-library/jest-dom";

// react-force-graph-2d needs a real canvas (absent in jsdom). Stub it globally so any
// component embedding SegmentNodeGraph (e.g. Act2View's portfolio graph) renders in tests.
vi.mock("react-force-graph-2d", () => ({ default: () => null }));

// ResizeObserver is used by recharts (Tremor) and react-force-graph-2d.
// jsdom does not implement it; provide a no-op shim.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).ResizeObserver = ResizeObserverStub;

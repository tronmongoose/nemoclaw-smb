/** Global test setup: extend expect with jest-dom matchers and shim browser APIs absent from jsdom. */

import "@testing-library/jest-dom";

// ResizeObserver is used by recharts (Tremor) and react-force-graph-2d.
// jsdom does not implement it; provide a no-op shim.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).ResizeObserver = ResizeObserverStub;

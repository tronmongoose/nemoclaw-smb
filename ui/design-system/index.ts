// Curated design-system entry for claude.ai/design (via /design-sync).
// Re-exports only the reusable, presentational slice of the NemoClaw STR UI:
// the shadcn primitives + the editorial vocabulary. The app itself never imports
// this file; it exists so the converter bundles the slice, never the app screens.

export * from "../src/components/ui/button";
export * from "../src/components/ui/card";
export * from "../src/components/ui/badge";
export * from "../src/components/ui/table";
export * from "../src/components/ui/tabs";
export * from "../src/components/ui/separator";
export * from "../src/components/ui/tooltip";
export * from "../src/components/ui/skeleton";
export * from "../src/components/ui/dialog";
export * from "../src/components/ui/progress";
export * from "../src/components/ui/accordion";
export * from "../src/components/str/shared";
export * from "../src/components/str/ProvenanceBadge";
export * from "../src/components/str/LiveToggle";

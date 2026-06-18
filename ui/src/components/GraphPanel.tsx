/** Graph panel wrapper: measures container and passes dimensions to KnowledgeGraph. */

import { useRef, useEffect, useState } from "react";
import { KnowledgeGraph } from "./KnowledgeGraph";

export function GraphPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 400, height: 350 });

  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      const e = entries[0];
      if (e) {
        setDims({
          width: Math.floor(e.contentRect.width),
          height: Math.floor(e.contentRect.height),
        });
      }
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  return (
    <div ref={containerRef} className="w-full h-full min-h-[350px]">
      <KnowledgeGraph width={dims.width} height={dims.height} />
    </div>
  );
}

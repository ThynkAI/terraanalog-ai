import { Suspense } from "react";
import type { Metadata } from "next";
import { PlanetExplorer } from "@/components/PlanetExplorer";

export const metadata: Metadata = { title: "Moon Reference Explorer" };

export default function Page() {
  return (
    <Suspense fallback={<p className="text-lunar-300">Loading…</p>}>
      <PlanetExplorer body="moon" />
    </Suspense>
  );
}

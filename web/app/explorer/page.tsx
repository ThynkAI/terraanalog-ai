import { Suspense } from "react";
import type { Metadata } from "next";
import ExplorerClient from "./ExplorerClient";

export const metadata: Metadata = { title: "Earth Analog Explorer" };

export default function Page() {
  return (
    <Suspense fallback={<p className="text-lunar-300">Loading explorer…</p>}>
      <ExplorerClient />
    </Suspense>
  );
}

import { Suspense } from "react";
import type { Metadata } from "next";
import CompareClient from "./CompareClient";

export const metadata: Metadata = { title: "Site Comparison Laboratory" };

export default function Page() {
  return (
    <Suspense fallback={<p className="text-lunar-300">Loading lab…</p>}>
      <CompareClient />
    </Suspense>
  );
}

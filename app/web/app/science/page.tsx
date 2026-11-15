import { Suspense } from "react";
import type { Metadata } from "next";
import ScienceClient from "./ScienceClient";
export const metadata: Metadata = { title: "Scientific Case Studies", description: "Source-reviewed Earth–Moon–Mars case studies, matched-scale regional measurements, benchmark comparisons and assumption stress tests." };
export default function Page() { return <Suspense fallback={<p>Loading scientific cases…</p>}><ScienceClient /></Suspense>; }

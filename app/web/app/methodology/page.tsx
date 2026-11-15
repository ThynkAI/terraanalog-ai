import type { Metadata } from "next";
import MethodologyClient from "./MethodologyClient";
export const metadata: Metadata = { title: "Scientific Methodology" };
export default function Page() {
  return <MethodologyClient />;
}

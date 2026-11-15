import type { Metadata } from "next";
import DataClient from "./DataClient";
export const metadata: Metadata = { title: "Data Sources and Provenance" };
export default function Page() {
  return <DataClient />;
}

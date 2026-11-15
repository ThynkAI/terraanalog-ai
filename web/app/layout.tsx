import type { Metadata, Viewport } from "next";
import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: { default: "TerraAnalog AI — Earth as a Testbed for Moon and Mars", template: "%s · TerraAnalog AI" },
  description: "Interactive decision-support platform ranking terrestrial analog sites for lunar and Martian mission testing.",
  icons: { icon: "/favicon.svg" },
};
export const viewport: Viewport = { themeColor: "#070b16", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans text-lunar-100 antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { Toaster } from "@/components/ui/Toaster";

export const metadata: Metadata = {
  title: "Trading212 Bot — signals & local execution",
  description:
    "Web portal for subscription and licensing, Windows desktop executor for Trading212. Broker API keys stay on your device.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full flex flex-col bg-slate-950 text-slate-50">
        <SiteHeader />
        <div className="flex flex-1 flex-col">{children}</div>
        <SiteFooter />
        <Toaster />
      </body>
    </html>
  );
}

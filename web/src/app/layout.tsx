import type { Metadata } from "next";
import "./globals.css";
import { PageBackdrop } from "@/components/PageBackdrop";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { Toaster } from "@/components/ui/Toaster";
import { fontMono, fontSans } from "@/lib/fonts";

export const metadata: Metadata = {
  title: "SwiftTrade — signals & local execution",
  description:
    "Web portal for subscription and licensing, Windows desktop executor for Trading212. Broker API keys stay on your device.",
  icons: {
    // Prefer Next.js icon routes (`src/app/icon.png`, `src/app/apple-icon.png`) for broad browser support.
    icon: [{ url: "/icon.png", type: "image/png" }],
    apple: [{ url: "/apple-icon.png", type: "image/png" }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark h-full antialiased ${fontSans.variable} ${fontMono.variable}`}>
      <body className="flex min-h-full flex-col bg-background font-sans text-foreground">
        <PageBackdrop />
        <SiteHeader />
        <div className="flex flex-1 flex-col">{children}</div>
        <SiteFooter />
        <Toaster />
      </body>
    </html>
  );
}

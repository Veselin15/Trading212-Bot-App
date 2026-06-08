import type { Metadata } from "next";
import "./globals.css";
import { PageBackdrop } from "@/components/PageBackdrop";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { Toaster } from "@/components/ui/Toaster";
import { fontMono, fontSans } from "@/lib/fonts";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://swifttrade.app";
const siteTitle = "SwiftTrade — EU investing on Trading212";
const siteDescription =
  "Web portal for subscription and licensing, plus a Windows desktop executor for Trading212. Signals target EU-listed stocks only, and your broker API keys never leave your device.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: siteTitle,
    template: "%s · SwiftTrade",
  },
  description: siteDescription,
  applicationName: "SwiftTrade",
  keywords: [
    "Trading212 bot",
    "EU stocks",
    "automated trading",
    "trading signals",
    "algorithmic trading",
    "EU investing",
    "no US withholding tax",
  ],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: "SwiftTrade",
    title: siteTitle,
    description: siteDescription,
    url: siteUrl,
    images: [{ url: "/logo_text.png", width: 240, height: 96, alt: "SwiftTrade" }],
  },
  twitter: {
    card: "summary_large_image",
    title: siteTitle,
    description: siteDescription,
    images: ["/logo_text.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
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

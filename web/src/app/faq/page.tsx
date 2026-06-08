import type { Metadata } from "next";
import { FaqClient } from "./FaqClient";

export const metadata: Metadata = {
  title: "FAQ — Trading212 Bot Questions",
  description:
    "Answers to common questions about SwiftTrade: how the Trading212 bot works, where API keys are stored, EU stock strategy, signal delivery, and subscription plans.",
  keywords: [
    "Trading212 bot FAQ",
    "Trading212 automation questions",
    "EU stock bot how it works",
    "Trading212 API key safety",
    "automated EU trading help",
  ],
  alternates: { canonical: "/faq" },
  openGraph: {
    title: "FAQ — Trading212 Bot Questions · SwiftTrade",
    description:
      "Everything you need to know about SwiftTrade's Trading212 bot: security, EU signals, strategy, and plans.",
    url: "/faq",
  },
};

const FAQ_JSONLD = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Where are my Trading212 API keys stored?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Your API keys are stored locally on your PC, encrypted by the desktop app. They are never uploaded to SwiftTrade's servers. All Trading212 API calls happen directly from your desktop to Trading212.",
      },
    },
    {
      "@type": "Question",
      name: "How do signals reach the desktop app without exposing my keys?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Signals are published to Supabase Realtime channels — these contain trade instructions only, no broker credentials. Your desktop app subscribes to these channels and your API key never travels through SwiftTrade's infrastructure.",
      },
    },
    {
      "@type": "Question",
      name: "What is the difference between paper trading and live execution?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Paper trading shows you what trades would be executed without placing real orders — perfect for testing your setup risk-free. Live execution places real orders on your Trading212 account. You can switch between modes inside the desktop app at any time.",
      },
    },
    {
      "@type": "Question",
      name: "Which markets does SwiftTrade support?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "SwiftTrade focuses on European stocks listed on major EU exchanges such as XETRA (Germany), Euronext Paris, and others. Strategies are optimised for long-only investing in EU-listed stocks and account for withholding tax structures.",
      },
    },
    {
      "@type": "Question",
      name: "How quickly do signals arrive after they are published?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Signal delivery via Supabase Realtime typically arrives in under 200 ms. The desktop app processes and submits orders to Trading212 immediately on receipt. Total round-trip latency from signal publish to order placement is generally well under one second.",
      },
    },
    {
      "@type": "Question",
      name: "What happens if I cancel my subscription?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Your access and desktop license key are deactivated immediately on cancellation. The desktop app will stop receiving live signals. You can re-subscribe at any time to restore access.",
      },
    },
    {
      "@type": "Question",
      name: "Is there a free trial?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. SwiftTrade offers a 14-day free trial with no credit card required. Trial users receive a license key automatically and can paper-trade with the full signal feed.",
      },
    },
  ],
};

export default function FaqPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(FAQ_JSONLD) }}
      />
      <FaqClient />
    </>
  );
}

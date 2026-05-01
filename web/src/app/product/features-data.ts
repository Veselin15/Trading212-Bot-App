import type { LucideIcon } from "lucide-react";
import { Activity, Globe2, KeyRound, Layers, Lock, ShieldCheck, Workflow } from "lucide-react";

export type ProductFeature = {
  Icon: LucideIcon;
  title: string;
  body: string;
};

export const PRODUCT_FEATURES: ProductFeature[] = [
  {
    Icon: Workflow,
    title: "Signal → execute architecture",
    body: "Signals are published to Supabase. Your desktop executor subscribes in real-time and places orders locally.",
  },
  {
    Icon: Lock,
    title: "No broker keys on the website",
    body: "Your Trading212 API key is entered only inside the desktop app and stored encrypted on your machine.",
  },
  {
    Icon: ShieldCheck,
    title: "Subscription gating + RLS",
    body: "Supabase Row Level Security limits access to the feed to active subscribers. The portal manages licensing.",
  },
  {
    Icon: Globe2,
    title: "EU Börse–oriented universe",
    body: "The strategy is designed mainly around European exchanges and listings. Stock selection favours names where dividend withholding and similar tax-like frictions are minimal — not tax advice; rules depend on your residency.",
  },
  {
    Icon: Layers,
    title: "Strategy stack (high level)",
    body: "Two-timeframe approach: a higher timeframe defines regime; a lower timeframe times entries and exits.",
  },
  {
    Icon: Activity,
    title: "Risk controls",
    body: "Stop-loss and protective logic are enforced by the executor. Capital preservation is treated as a first-class goal.",
  },
  {
    Icon: KeyRound,
    title: "License-based desktop access",
    body: "A per-user license key unlocks the executor. Pro users get download access plus the live feed.",
  },
];

export const PRODUCT_SETUP_STEPS = [
  {
    step: "Step 1",
    title: "Create your portal account",
    body: "Sign up and verify email. Subscribe to Pro if needed.",
  },
  {
    step: "Step 2",
    title: "Download the executor",
    body: "Pro users can download the Windows desktop installer.",
  },
  {
    step: "Step 3",
    title: "Connect Trading212 locally",
    body: "Paste your Trading212 API key into the desktop app and choose paper/auto mode.",
  },
] as const;

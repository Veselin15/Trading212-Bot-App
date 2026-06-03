"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Lock, MessageCircle, BarChart2, Zap } from "lucide-react";

import { Container } from "@/components/ui/Container";
import { SectionLabel } from "@/components/ui/SectionLabel";
import { ButtonLink } from "@/components/ui/Button";

const EASE = [0.22, 1, 0.36, 1] as const;

type Faq = { question: string; answer: string };
type Group = { label: string; icon: typeof Lock; color: string; iconCls: string; faqs: Faq[] };

const GROUPS: Group[] = [
  {
    label: "Security & Privacy",
    icon: Lock,
    color: "border-amber-500/25 bg-amber-500/[0.07]",
    iconCls: "border-amber-500/30 bg-amber-500/15 text-amber-400",
    faqs: [
      {
        question: "Where are my Trading212 API keys stored?",
        answer:
          "Your API keys are stored locally on your PC, encrypted by the desktop app. They are NEVER uploaded to our servers or the web portal. All Trading212 API calls happen directly from your desktop to Trading212 — the portal has no visibility into your broker credentials.",
      },
      {
        question: "How do signals reach the desktop app without exposing my keys?",
        answer:
          "Signals are published to Supabase Realtime channels — these contain trade instructions only, no broker credentials. Your desktop app subscribes to these channels and receives signals instantly. Your subscription tier controls channel access via row-level security (RLS). The API key never needs to travel through our infrastructure.",
      },
    ],
  },
  {
    label: "Platform & Signals",
    icon: Zap,
    color: "border-emerald-500/25 bg-emerald-500/[0.07]",
    iconCls: "border-emerald-500/30 bg-emerald-500/15 text-emerald-400",
    faqs: [
      {
        question: "How does subscription gating work?",
        answer:
          "Your subscription status (Free, Pro, Enterprise) is stored in Supabase. Row-level security policies check your tier before allowing access to live signal channels. Free users see historical data only; Pro users get live signals and a desktop app license key for execution.",
      },
      {
        question: "What's the difference between paper trading and live execution?",
        answer:
          "Paper trading (monitoring mode) shows you what trades WOULD be executed without placing real orders — perfect for testing your setup and evaluating signal quality risk-free. Live execution mode places real orders on your Trading212 account. You can switch between modes inside the desktop app at any time.",
      },
      {
        question: "How quickly do signals arrive after they're published?",
        answer:
          "Signal delivery via Supabase Realtime typically arrives in under 200ms. The desktop app processes and submits orders to Trading212 immediately on receipt. Total round-trip latency from signal publish to order placement is generally well under one second, depending on your network.",
      },
    ],
  },
  {
    label: "Strategy & Markets",
    icon: BarChart2,
    color: "border-sky-500/25 bg-sky-500/[0.07]",
    iconCls: "border-sky-500/30 bg-sky-500/15 text-sky-400",
    faqs: [
      {
        question: "Which markets are supported?",
        answer:
          "We focus on European stocks listed on major EU exchanges. Our strategies consider withholding tax rates and are optimised for long-only investing in the EU equity universe. The strategy avoids markets with punitive withholding structures that erode dividend returns.",
      },
      {
        question: "Is there a performance guarantee?",
        answer:
          "No. Past backtested results — including the CAGR and Sharpe ratio figures shown — do not guarantee future returns. Trading involves substantial risk. Market conditions change, and strategies that worked historically may underperform going forward. Only invest capital you can afford to lose, and consult a financial professional before making investment decisions.",
      },
    ],
  },
  {
    label: "Support & Help",
    icon: MessageCircle,
    color: "border-slate-500/20 bg-white/[0.03]",
    iconCls: "border-white/[0.12] bg-white/[0.06] text-slate-400",
    faqs: [
      {
        question: "What happens if I cancel my Pro subscription?",
        answer:
          "Your Pro access and desktop license key are deactivated immediately on cancellation. The desktop app will stop receiving live signals. You can re-subscribe at any time to get a new license key and restore access. Historical data remains visible on the free plan.",
      },
      {
        question: "Can I use the desktop app on multiple machines?",
        answer:
          "Currently, one active license key is issued per Pro subscription. The key is tied to your account and can be regenerated from the dashboard at any time. Concurrent multi-machine activation is an Enterprise feature — email legal@swifttrade.app if you need this.",
      },
    ],
  },
];

function FaqItem({ faq, isOpen, onToggle }: { faq: Faq; isOpen: boolean; onToggle: () => void }) {
  return (
    <div className={`overflow-hidden rounded-2xl border transition-colors duration-200 ${isOpen ? "border-white/[0.12] bg-white/[0.04]" : "border-white/[0.07] bg-[#060609]/80 hover:border-white/[0.1]"}`}>
      <button
        type="button"
        className="flex w-full items-start justify-between gap-4 px-5 py-4 text-left"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <span className={`text-sm font-semibold leading-snug transition-colors duration-200 ${isOpen ? "text-white" : "text-slate-200"}`}>
          {faq.question}
        </span>
        <motion.div
          className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-white/[0.1] bg-white/[0.05] text-slate-400"
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.25, ease: EASE }}
        >
          <ChevronDown className="h-3 w-3" />
        </motion.div>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ height: { duration: 0.28, ease: EASE }, opacity: { duration: 0.2 } }}
          >
            <div className="border-t border-white/[0.06] px-5 pb-5 pt-4">
              <p className="text-sm leading-relaxed text-slate-400">{faq.answer}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function FaqGroup({ group }: { group: Group }) {
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  const toggle = (i: number) => setOpenIdx(openIdx === i ? null : i);

  return (
    <div className={`rounded-2xl border p-5 ${group.color}`}>
      <div className="mb-4 flex items-center gap-3">
        <div className={`flex h-8 w-8 items-center justify-center rounded-xl border ${group.iconCls}`}>
          <group.icon className="h-4 w-4" strokeWidth={1.75} />
        </div>
        <span className="text-sm font-bold text-slate-200">{group.label}</span>
        <span className="ml-auto rounded-full border border-white/[0.08] bg-white/[0.04] px-2 py-0.5 text-[0.65rem] text-slate-500">
          {group.faqs.length}
        </span>
      </div>

      <div className="space-y-2">
        {group.faqs.map((faq, i) => (
          <FaqItem
            key={faq.question}
            faq={faq}
            isOpen={openIdx === i}
            onToggle={() => toggle(i)}
          />
        ))}
      </div>
    </div>
  );
}

export function FaqClient() {
  return (
    <main>
      {/* ── Hero ── */}
      <section className="relative border-b border-white/[0.06] pb-16 pt-16 lg:pb-20 lg:pt-20">
        <div
          className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[800px] -translate-x-1/2 rounded-full opacity-50 blur-3xl"
          style={{ background: "radial-gradient(ellipse at center, rgba(16,185,129,0.12) 0%, transparent 70%)" }}
          aria-hidden
        />
        <Container>
          <div className="mx-auto max-w-2xl text-center">
            <SectionLabel className="mb-4 justify-center">FAQ</SectionLabel>
            <h1 className="mb-4 text-balance text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              Frequently asked questions
            </h1>
            <p className="text-base leading-relaxed text-slate-400 sm:text-lg">
              Everything you need to know about security, signals, the strategy, and how the platform works.
            </p>
          </div>
        </Container>
      </section>

      {/* ── FAQ groups ── */}
      <section className="py-16 lg:py-20">
        <Container>
          <div className="mx-auto max-w-3xl space-y-4">
            {GROUPS.map((group) => (
              <FaqGroup key={group.label} group={group} />
            ))}
          </div>

          {/* Still have questions */}
          <div className="mx-auto mt-12 max-w-3xl rounded-2xl border border-white/[0.07] bg-[#060609]/80 p-6 text-center">
            <p className="mb-1 text-sm font-semibold text-slate-200">Still have questions?</p>
            <p className="mb-4 text-sm text-slate-500">
              Email us at{" "}
              <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                legal@swifttrade.app
              </a>{" "}
              or check the product overview.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <ButtonLink href="/product" variant="secondary" className="h-10 px-4 text-sm">
                Product overview
              </ButtonLink>
              <ButtonLink href="/pricing" variant="secondary" className="h-10 px-4 text-sm">
                Pricing
              </ButtonLink>
            </div>
          </div>
        </Container>
      </section>
    </main>
  );
}

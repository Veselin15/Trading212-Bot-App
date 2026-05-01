import { Card } from "@/components/ui/Card";
import { Container } from "@/components/ui/Container";
import { RevealOnScroll } from "@/components/home/RevealOnScroll";

const faqs = [
  {
    question: "How do signals reach the desktop app?",
    answer:
      "Signals are published to Supabase Realtime channels. Your desktop app subscribes to these channels and receives signals instantly. Your subscription tier controls which channels you can access via row-level security (RLS).",
  },
  {
    question: "Where are my Trading212 API keys stored?",
    answer:
      "Your API keys are stored locally on your PC, encrypted by the desktop app. They are NEVER uploaded to our servers or the web portal. All Trading212 API calls happen directly from your desktop to Trading212.",
  },
  {
    question: "How does subscription gating work?",
    answer:
      "Your subscription status (Free, Pro, Enterprise) is stored in Supabase. Row-level security policies check your tier before allowing access to live signals. Free users see historical data only; Pro users get live signals and desktop app licenses.",
  },
  {
    question: "What's the difference between monitoring and automation?",
    answer:
      "Monitoring mode (paper trading) shows you what trades WOULD be executed without actually placing orders. Automation mode executes real trades on your Trading212 account. We recommend starting with monitoring to verify signal quality.",
  },
  {
    question: "Which markets are supported?",
    answer:
      "We focus on European stocks listed on major EU exchanges. Our strategies consider tax withholding rates and are optimized for long-only investing in the EU equity universe.",
  },
  {
    question: "Is there a performance guarantee?",
    answer:
      "No. Past backtested results do not guarantee future returns. Trading involves substantial risk. Market conditions change, and strategies that worked historically may underperform in the future. Only invest capital you can afford to lose.",
  },
];

export default function FaqPage() {
  return (
    <main>
      <Container className="py-20">
        <div className="mx-auto max-w-3xl">
          <RevealOnScroll className="mb-12 text-center">
            <h1 className="mb-4 text-5xl">Frequently Asked Questions</h1>
            <p className="text-lg text-slate-400">Common questions about setup, security, and how the system works</p>
          </RevealOnScroll>

          <div className="space-y-6">
            {faqs.map((faq) => (
              <RevealOnScroll key={faq.question}>
                <Card className="border-slate-800/70 bg-white/5 p-6">
                  <h3 className="mb-3 text-lg">{faq.question}</h3>
                  <p className="text-slate-400">{faq.answer}</p>
                </Card>
              </RevealOnScroll>
            ))}
          </div>
        </div>
      </Container>
    </main>
  );
}


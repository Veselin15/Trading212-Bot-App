import type { Metadata } from "next";
import Link from "next/link";

import { Container } from "@/components/ui/Container";
import {
  LegalDocHeader,
  LegalDocLayout,
  LegalInfoBox,
  LegalList,
  LegalSection,
  LegalWarningBox,
} from "@/components/legal/LegalDoc";

export const metadata: Metadata = {
  title: "Risk Disclosure — SwiftTrade",
  description:
    "Mandatory risk warnings for SwiftTrade automated trading software. Read before enabling live order execution.",
};

const EFFECTIVE = "3 June 2026";

export default function RiskPage() {
  return (
    <LegalDocLayout>
      <LegalDocHeader
        title="Risk Disclosure"
        subtitle="Important warnings you must read and understand before using live execution."
        effectiveDate={EFFECTIVE}
      />

      <section className="py-14 lg:py-18">
        <Container>
          <div className="mx-auto max-w-3xl">

            <LegalWarningBox>
              <strong>READ THIS DOCUMENT IN FULL.</strong> By clicking &ldquo;Connect&rdquo; in the desktop
              application, or by enabling live order execution, you confirm that you have read and understood
              all risk warnings set out below. Automated trading involves substantial risk of financial loss.
              You can lose more money than you expect.
            </LegalWarningBox>

            <div className="mt-8">
              <LegalSection num={1} heading="Nature of the Service">
                <p>
                  SwiftTrade is a <strong className="text-slate-200">software tool</strong> that automates the
                  placement of orders on your Trading212 brokerage account. It is not:
                </p>
                <LegalList
                  items={[
                    "A licensed investment firm or financial institution.",
                    "A regulated investment adviser or portfolio manager.",
                    "An authorised firm under the Markets in Financial Instruments Directive II (MiFID II), the UK FCA, or any other financial regulatory regime.",
                    "A provider of financial advice, investment recommendations, or personalised investment guidance.",
                  ]}
                />
                <p>
                  SwiftTrade provides a technical execution layer only. All trading decisions are encoded in a
                  pre-computed, fully automated strategy. You retain full legal and financial responsibility for
                  your Trading212 account and all orders placed through it.
                </p>
                <LegalInfoBox>
                  Before using any automated trading tool, check with your national financial regulator whether
                  you require any authorisation or must meet any suitability criteria. In the EU, retail
                  investors should be familiar with the requirements of MiFID II and the PRIIPs Regulation.
                </LegalInfoBox>
              </LegalSection>

              <LegalSection num={2} heading="Investment and Capital Risk">
                <LegalWarningBox>
                  <strong>Trading in financial instruments, including equities, involves a high risk of losing
                  money rapidly. The value of investments can fall as well as rise. You may lose all of the
                  money you invest. Past performance is not a reliable indicator of future results.</strong>
                </LegalWarningBox>
                <p>Specific risks include, but are not limited to:</p>
                <LegalList
                  items={[
                    "Market risk: equity prices can decline significantly due to economic, political, or company-specific events.",
                    "Liquidity risk: positions may not be executable at expected prices during periods of low market liquidity.",
                    "Concentration risk: the strategy holds a limited number of EU equity positions; a single adverse event can disproportionately affect performance.",
                    "Currency risk: if your account is denominated in a currency different from the securities traded, exchange-rate movements may affect returns.",
                    "Dividend risk: the strategy considers dividend income; dividends are not guaranteed and can be reduced or cancelled at any time.",
                    "Withholding tax risk: tax treatment of dividends varies by country and personal circumstances; changes in tax law may affect returns.",
                  ]}
                />
                <p>
                  <strong className="text-slate-200">Only invest capital you can afford to lose entirely.</strong>{" "}
                  Do not invest funds needed for essential living expenses, savings targets, or debt repayment.
                </p>
              </LegalSection>

              <LegalSection num={3} heading="No Guarantee of Performance">
                <p>
                  SwiftTrade makes <strong className="text-slate-200">no representation or warranty</strong>{" "}
                  that the Service will generate profits, preserve capital, or achieve any particular investment
                  outcome.
                </p>
                <p>
                  Historical and backtested performance figures displayed on this website — including, without
                  limitation, CAGR, Sharpe ratio, maximum drawdown, and win rate statistics — are provided for
                  informational purposes only. They represent the results of a model tested on historical data
                  and do not constitute a guarantee, promise, or prediction of future performance.
                </p>
                <LegalList
                  items={[
                    "Backtests are simulations run on historical data. They cannot account for conditions that have not yet occurred.",
                    "Live results will differ from backtests due to real-world factors including order slippage, bid-ask spreads, partial fills, and Trading212 platform constraints.",
                    "Market regimes change. A strategy that performed well in the historical period tested may underperform or lose money in different market conditions.",
                    "Strategy parameters may be adjusted over time, which may affect future performance relative to historical figures.",
                  ]}
                />
              </LegalSection>

              <LegalSection num={4} heading="Technology and Execution Risks">
                <p>
                  The automated execution of orders depends on multiple technology layers, each of which can fail:
                </p>
                <LegalList
                  items={[
                    "Internet connectivity: your desktop computer must maintain a stable internet connection. Disconnections may result in missed signals.",
                    "Signal server availability: SwiftTrade's signal infrastructure may experience outages. During an outage, no signals will be delivered and no orders will be placed.",
                    "Trading212 API availability: Trading212 may experience downtime or impose API rate limits, preventing order placement.",
                    "Order rejection: Trading212 may reject orders due to insufficient funds, instrument restrictions, market hours, or API errors.",
                    "Software bugs: the Desktop App or backend may contain bugs that cause unexpected behaviour.",
                    "Latency: signal delivery and order placement involve unavoidable latency. During fast-moving markets, executed prices may differ significantly from signal prices.",
                    "Windows environment: antivirus software, OS updates, or resource constraints on your computer may interfere with the Desktop App.",
                  ]}
                />
                <p>
                  SwiftTrade is not liable for trading losses or missed opportunities resulting from any of these
                  technology risks. See the{" "}
                  <Link href="/legal/terms" className="text-emerald-400 hover:underline">Terms of Service</Link>{" "}
                  for the full limitation of liability.
                </p>
              </LegalSection>

              <LegalSection num={5} heading="Not Financial Advice">
                <p>
                  Nothing on this website, in the desktop application, in any communication from SwiftTrade, or
                  in the signals delivered by the Service constitutes:
                </p>
                <LegalList
                  items={[
                    "Investment advice or a recommendation to buy or sell any financial instrument.",
                    "A personal recommendation tailored to your financial situation, risk tolerance, or investment objectives.",
                    "Tax advice.",
                    "Legal advice.",
                  ]}
                />
                <p>
                  Before investing, you should carefully consider whether automated trading is appropriate for
                  your personal circumstances, financial situation, and risk appetite.{" "}
                  <strong className="text-slate-200">
                    If in doubt, seek independent financial advice from a qualified professional authorised in
                    your jurisdiction.
                  </strong>
                </p>
              </LegalSection>

              <LegalSection num={6} heading="Regulatory Status">
                <p>
                  SwiftTrade is not authorised or regulated by the European Securities and Markets Authority
                  (ESMA), the Bulgarian Financial Supervision Commission (FSC), the UK Financial Conduct
                  Authority (FCA), or any other financial regulatory body in any jurisdiction.
                </p>
                <p>
                  The use of automated trading software may be subject to regulation in your country of
                  residence. You are solely responsible for ensuring that your use of the Service complies with
                  all applicable laws and regulations in your jurisdiction, including any rules applicable to
                  retail investors under MiFID II or equivalent national law.
                </p>
                <p>
                  Trading212 is an independent, separately regulated broker. SwiftTrade has no affiliation with
                  Trading212 and does not act on behalf of Trading212. Your account with Trading212 is governed
                  solely by Trading212&rsquo;s own regulatory status and client agreements.
                </p>
              </LegalSection>

              <LegalSection num={7} heading="Live Execution — Additional Warnings">
                <LegalWarningBox>
                  Enabling &ldquo;Real trades&rdquo; mode in the Desktop App will cause the software to place
                  real orders with real money in your Trading212 invest/ISA account. These orders are live and
                  binding. Losses incurred are real. SwiftTrade cannot reverse or cancel orders once submitted
                  to Trading212.
                </LegalWarningBox>
                <p>Before enabling live execution, ensure you have:</p>
                <LegalList
                  items={[
                    "Tested the application in paper (demo) mode and verified it behaves as expected.",
                    "Reviewed the maximum position size and concurrent position limits for your subscription tier.",
                    "Confirmed that sufficient funds are available in your Trading212 account.",
                    "Verified that your Trading212 API key has the correct permissions for the account type (invest/ISA).",
                    "Read and understood the full Terms of Service and this Risk Disclosure.",
                  ]}
                />
              </LegalSection>

              <LegalSection num={8} heading="Tax Considerations">
                <p>
                  Trading in financial instruments may give rise to tax obligations, including capital gains tax,
                  income tax on dividends, and withholding tax. Tax rules vary by jurisdiction and individual
                  circumstances. SwiftTrade does not provide tax advice.
                </p>
                <p>
                  You are solely responsible for reporting and paying any taxes arising from your trading
                  activity. Consult a qualified tax adviser in your country before engaging in automated trading.
                </p>
              </LegalSection>

              <LegalSection num={9} heading="Your Responsibility">
                <p>
                  By using the Service, you confirm that:
                </p>
                <LegalList
                  items={[
                    "You are at least 18 years of age.",
                    "You have read and understood this Risk Disclosure in its entirety.",
                    "You understand that you may lose money, up to and including your entire investment.",
                    "You are investing only capital you can afford to lose.",
                    "You are solely responsible for your Trading212 account, all orders placed thereon, and all resulting financial outcomes.",
                    "You have considered whether automated trading is suitable for your personal circumstances.",
                    "You will monitor the Desktop App and your Trading212 account regularly and are not relying on SwiftTrade to manage your account for you.",
                  ]}
                />
              </LegalSection>

              <LegalSection num={10} heading="Contact">
                <p>
                  For questions about this Risk Disclosure:{" "}
                  <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                    legal@swifttrade.app
                  </a>
                </p>
                <LegalInfoBox>
                  Related documents:{" "}
                  <Link href="/legal/terms" className="text-sky-300 hover:underline">Terms of Service</Link>
                  {" · "}
                  <Link href="/legal/privacy" className="text-sky-300 hover:underline">Privacy Policy</Link>
                </LegalInfoBox>
              </LegalSection>
            </div>

          </div>
        </Container>
      </section>
    </LegalDocLayout>
  );
}

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
  title: "Terms of Service — SwiftTrade",
  description:
    "The binding agreement between you and SwiftTrade governing access to the platform, subscriptions, desktop app, and signal service.",
};

const EFFECTIVE = "3 June 2026";

export default function TermsPage() {
  return (
    <LegalDocLayout>
      <LegalDocHeader
        title="Terms of Service"
        subtitle="Please read these terms carefully before using SwiftTrade."
        effectiveDate={EFFECTIVE}
      />

      <section className="py-14 lg:py-18">
        <Container>
          <div className="mx-auto max-w-3xl">

            <LegalSection num={1} heading="Acceptance of Terms">
              <p>
                By creating an account, downloading the desktop application, or otherwise accessing or using any part
                of the SwiftTrade service (&ldquo;Service&rdquo;), you (&ldquo;User&rdquo; or &ldquo;you&rdquo;)
                agree to be bound by these Terms of Service (&ldquo;Terms&rdquo;) and all policies incorporated by
                reference, including the{" "}
                <Link href="/legal/privacy" className="text-emerald-400 hover:underline">Privacy Policy</Link> and{" "}
                <Link href="/legal/risk" className="text-emerald-400 hover:underline">Risk Disclosure</Link>.
              </p>
              <p>
                If you do not agree with any part of these Terms, you must not use the Service. By clicking
                &ldquo;Connect&rdquo; in the desktop application or completing checkout, you confirm that you have
                read, understood, and agreed to these Terms in their entirety.
              </p>
              <p>
                You must be at least 18 years of age and legally capable of entering into a binding contract in your
                jurisdiction to use this Service.
              </p>
            </LegalSection>

            <LegalSection num={2} heading="Description of Service">
              <p>
                SwiftTrade provides software tooling that can automate order execution on a user&rsquo;s
                Trading212 brokerage account. The Service consists of:
              </p>
              <LegalList
                items={[
                  "A web portal for account management, subscription billing, and license key issuance.",
                  "A Windows desktop application (“Desktop App”) that receives trading signals and places orders on your Trading212 account using API keys stored locally on your device.",
                  "A signal delivery service that transmits trade instructions to connected Desktop App instances based on a pre-computed strategy.",
                ]}
              />
              <LegalWarningBox>
                SwiftTrade is a software tool, not a licensed investment firm, investment adviser, broker, or
                portfolio manager. It does not provide investment advice, financial recommendations, or regulated
                financial services. You retain full control of and responsibility for your Trading212 account at all
                times.
              </LegalWarningBox>
              <p>
                The Service is intended for use exclusively with Trading212 practice (demo) and/or invest/ISA
                accounts on EU-listed equities. Use with other brokers or markets is not supported.
              </p>
            </LegalSection>

            <LegalSection num={3} heading="Accounts and Registration">
              <p>
                To access the Service you must register an account using a valid email address. You are responsible
                for:
              </p>
              <LegalList
                items={[
                  "Keeping your password and account credentials confidential.",
                  "All activity that occurs under your account, whether or not authorised by you.",
                  "Notifying us immediately at legal@swifttrade.app if you suspect unauthorised access.",
                ]}
              />
              <p>
                You may not create more than one account per person. Creating multiple accounts to abuse the free
                trial or circumvent access restrictions is a material breach of these Terms and will result in
                immediate termination of all associated accounts.
              </p>
            </LegalSection>

            <LegalSection num={4} heading="Subscriptions and Billing">
              <p>
                The Service offers the following subscription tiers, billed monthly through Stripe:
              </p>
              <LegalList
                items={[
                  "Free Trial — 14 days at no charge; paper (demo) mode only; full signal feed; no payment details required.",
                  "Starter — €19 per month; live and paper execution; core signal feed; up to 3 concurrent positions.",
                  "Pro — €49 per month; live and paper execution; full signal feed; up to 10 concurrent positions.",
                ]}
              />
              <p>
                Prices are displayed inclusive of any applicable taxes where required by law. Subscription fees are
                charged in advance on the monthly anniversary of your subscription start date. All charges are
                non-refundable except as expressly stated in Section 5.
              </p>
              <p>
                Payments are processed by Stripe, Inc. By subscribing, you authorise Stripe to charge your selected
                payment method on a recurring basis until you cancel. SwiftTrade does not store your payment card
                details.
              </p>
              <p>
                We reserve the right to change subscription pricing with 30 days&rsquo; prior written notice to
                your registered email address. Continued use of the Service after the notice period constitutes
                acceptance of the new pricing.
              </p>
            </LegalSection>

            <LegalSection num={5} heading="Cancellation and Right of Withdrawal">
              <p>
                <strong className="text-slate-200">Cancellation.</strong> You may cancel your subscription at any
                time via the account dashboard. Cancellation takes effect at the end of the current billing period;
                you will retain access until that date.
              </p>
              <p>
                <strong className="text-slate-200">EU / EEA consumers &mdash; 14-day right of withdrawal.</strong>{" "}
                If you are a consumer in the European Union or European Economic Area, you have the right to
                withdraw from a new subscription contract within 14 days of purchase without giving a reason
                (&ldquo;Cooling-Off Period&rdquo;), under Directive 2011/83/EU (Consumer Rights Directive).
              </p>
              <p>
                However, by completing checkout and activating your subscription you expressly request that we
                begin providing the Service immediately, and you acknowledge that you will lose your right of
                withdrawal once the Service has been fully performed. Because signal delivery begins immediately
                upon subscription activation, the right of withdrawal is waived upon first connection of the
                desktop application to the signal server during the Cooling-Off Period.
              </p>
              <p>
                If you wish to exercise your right of withdrawal before first using the signal service, contact{" "}
                <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                  legal@swifttrade.app
                </a>{" "}
                within 14 days of purchase. A full refund will be issued within 14 days of receipt of your
                withdrawal notice.
              </p>
              <p>
                <strong className="text-slate-200">No other refunds.</strong> Except for the statutory
                withdrawal right above, all subscription fees are non-refundable. Partial-month cancellations are
                not refunded.
              </p>
            </LegalSection>

            <LegalSection num={6} heading="License to Use the Service">
              <p>
                Subject to your compliance with these Terms and payment of applicable fees, SwiftTrade grants you
                a limited, non-exclusive, non-transferable, non-sublicensable, revocable licence to:
              </p>
              <LegalList
                items={[
                  "Access and use the web portal for personal, non-commercial account management.",
                  "Install and run the Desktop App on a single Windows computer that you own or control.",
                  "Receive trading signals through the Service for use with your own Trading212 account.",
                ]}
              />
              <p>
                The license key issued to your account is for your sole use. You may not share, sell, transfer, or
                sublicense it to any third party. One license key is active per subscription at any time.
              </p>
            </LegalSection>

            <LegalSection num={7} heading="Desktop Application">
              <p>
                The Desktop App is distributed as a Windows executable. By downloading and running it you agree
                that:
              </p>
              <LegalList
                items={[
                  "You are running the application on hardware you own or are authorised to use.",
                  "The app will store your Trading212 API keys encrypted on that device. These keys never leave your computer and are never transmitted to SwiftTrade servers.",
                  "You are solely responsible for keeping your device secure and for any orders placed using your Trading212 API keys.",
                  "You will not reverse-engineer, decompile, disassemble, or modify the Desktop App.",
                  "You will not redistribute, sell, rent, lease, or otherwise transfer the Desktop App or any component thereof.",
                ]}
              />
              <p>
                The Desktop App connects to the SwiftTrade signal server via WebSocket. You are responsible for
                maintaining a reliable internet connection. SwiftTrade is not liable for missed signals or
                unexecuted orders due to connectivity issues on your end.
              </p>
            </LegalSection>

            <LegalSection num={8} heading="Acceptable Use">
              <p>You agree not to use the Service to:</p>
              <LegalList
                items={[
                  "Violate any applicable law, regulation, or third-party agreement, including Trading212’s terms of service.",
                  "Attempt to gain unauthorised access to SwiftTrade systems, servers, or databases.",
                  "Probe, scan, or test the vulnerability of any system or network.",
                  "Interfere with or disrupt the integrity or performance of the Service.",
                  "Use automated scripts or bots against the web portal (other than the Desktop App as intended).",
                  "Create accounts for the purpose of obtaining multiple free trials.",
                  "Use the Service for market manipulation or any activity that is illegal under applicable financial law.",
                ]}
              />
            </LegalSection>

            <LegalSection num={9} heading="Trading212 and Third-Party Services">
              <p>
                SwiftTrade is an independent software product. It is not affiliated with, endorsed by, or
                authorised by Trading212 Markets Ltd or any of its affiliates.
              </p>
              <p>
                Your use of Trading212 is governed solely by Trading212&rsquo;s own terms and conditions. You
                are responsible for complying with Trading212&rsquo;s API usage policies, and for ensuring that
                automated trading is permitted under your account agreement with Trading212.
              </p>
              <p>
                The Service also uses Supabase (authentication and database) and Stripe (payments). Your
                interactions with these third parties are governed by their respective terms and privacy policies.
                SwiftTrade is not responsible for the acts or omissions of these providers.
              </p>
            </LegalSection>

            <LegalSection num={10} heading="Disclaimer of Warranties">
              <LegalWarningBox>
                THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE&rdquo; WITHOUT WARRANTIES
                OF ANY KIND, EITHER EXPRESS OR IMPLIED. TO THE FULLEST EXTENT PERMITTED BY LAW, SWIFTTRADE
                DISCLAIMS ALL WARRANTIES INCLUDING, WITHOUT LIMITATION, IMPLIED WARRANTIES OF MERCHANTABILITY,
                FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT, AND ACCURACY.
              </LegalWarningBox>
              <p>
                SwiftTrade does not warrant that: (a) the Service will be uninterrupted, error-free, or available
                at any particular time; (b) any signal will result in a profitable trade; (c) the Desktop App
                will execute orders within any specified latency; or (d) the strategy underlying the signals will
                perform in the future as it has in backtests.
              </p>
              <p>
                Nothing in these Terms excludes or limits liability that cannot be excluded or limited under
                applicable law, including liability for death or personal injury caused by negligence, or for fraud.
              </p>
            </LegalSection>

            <LegalSection num={11} heading="Limitation of Liability">
              <p>
                To the maximum extent permitted by applicable law, SwiftTrade and its directors, employees,
                agents, and licensors shall not be liable for:
              </p>
              <LegalList
                items={[
                  "Any loss of profits, revenue, or data.",
                  "Any indirect, incidental, special, consequential, or punitive damages.",
                  "Trading losses arising from signals received through the Service.",
                  "Losses arising from connectivity failures, latency, or order rejection by Trading212.",
                  "Losses arising from bugs, downtime, or discontinuation of the Service.",
                ]}
              />
              <p>
                In any event, SwiftTrade&rsquo;s total aggregate liability to you arising out of or in connection
                with these Terms shall not exceed the total subscription fees paid by you to SwiftTrade in the
                three (3) calendar months immediately preceding the event giving rise to the claim.
              </p>
            </LegalSection>

            <LegalSection num={12} heading="Intellectual Property">
              <p>
                All content, software, trademarks, logos, and intellectual property forming part of the Service are
                owned by or licensed to SwiftTrade and are protected by applicable intellectual property law. You
                receive no ownership rights in any part of the Service.
              </p>
              <p>
                Strategy signals delivered through the Service are proprietary outputs of SwiftTrade&rsquo;s
                trading models. You may use signals solely to execute trades on your own Trading212 account. You
                may not copy, distribute, publish, or commercially exploit signal data.
              </p>
            </LegalSection>

            <LegalSection num={13} heading="Termination">
              <p>
                SwiftTrade may suspend or terminate your access to the Service immediately and without notice if:
              </p>
              <LegalList
                items={[
                  "You breach any material provision of these Terms.",
                  "You create multiple accounts to abuse the free trial.",
                  "We receive a valid legal order requiring us to do so.",
                  "Continued provision of the Service to you would expose SwiftTrade to legal or regulatory risk.",
                ]}
              />
              <p>
                Upon termination, your license to use the Service and Desktop App is revoked. You may delete your
                account data at any time by contacting{" "}
                <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                  legal@swifttrade.app
                </a>.
              </p>
            </LegalSection>

            <LegalSection num={14} heading="Governing Law and Disputes">
              <p>
                These Terms and any dispute arising out of or in connection with them shall be governed by and
                construed in accordance with the laws of the Republic of Bulgaria, without regard to conflict of
                law principles.
              </p>
              <p>
                Subject to any mandatory consumer protection rights you may have under the law of your country of
                residence, any dispute shall be subject to the exclusive jurisdiction of the competent courts of
                Bulgaria.
              </p>
              <p>
                If you are a consumer in the EU, you may also use the European Commission&rsquo;s online dispute
                resolution platform at{" "}
                <span className="font-mono text-xs text-slate-500">ec.europa.eu/consumers/odr</span>.
              </p>
            </LegalSection>

            <LegalSection num={15} heading="Changes to These Terms">
              <p>
                We may update these Terms from time to time. We will notify you of material changes via email to
                your registered address or via a notice on the web portal at least 14 days before the changes take
                effect. Your continued use of the Service after the effective date constitutes acceptance of the
                revised Terms.
              </p>
              <p>
                If you do not accept the revised Terms, you must stop using the Service and cancel your
                subscription before the effective date.
              </p>
            </LegalSection>

            <LegalSection num={16} heading="Contact">
              <p>
                For questions about these Terms, please contact:{" "}
                <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                  legal@swifttrade.app
                </a>
              </p>
              <LegalInfoBox>
                Related documents:{" "}
                <Link href="/legal/privacy" className="text-sky-300 hover:underline">Privacy Policy</Link>
                {" · "}
                <Link href="/legal/risk" className="text-sky-300 hover:underline">Risk Disclosure</Link>
              </LegalInfoBox>
            </LegalSection>

          </div>
        </Container>
      </section>
    </LegalDocLayout>
  );
}

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
  title: "Privacy Policy — SwiftTrade",
  description:
    "How SwiftTrade collects, uses, and protects your personal data. GDPR-compliant privacy policy for EU/EEA users.",
};

const EFFECTIVE = "3 June 2026";

export default function PrivacyPage() {
  return (
    <LegalDocLayout>
      <LegalDocHeader
        title="Privacy Policy"
        subtitle="What data we collect, why we collect it, and your rights under GDPR."
        effectiveDate={EFFECTIVE}
      />

      <section className="py-14 lg:py-18">
        <Container>
          <div className="mx-auto max-w-3xl">

            <LegalSection num={1} heading="Who We Are (Data Controller)">
              <p>
                SwiftTrade (&ldquo;SwiftTrade&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;, or &ldquo;our&rdquo;)
                is the data controller responsible for your personal data processed in connection with the
                SwiftTrade service (&ldquo;Service&rdquo;).
              </p>
              <p>
                Contact:{" "}
                <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                  legal@swifttrade.app
                </a>
              </p>
              <LegalInfoBox>
                This policy applies to swifttrade.app (the &ldquo;Site&rdquo;) and the SwiftTrade Windows desktop
                application. It does not cover third-party sites linked from the Service.
              </LegalInfoBox>
            </LegalSection>

            <LegalSection num={2} heading="Data We Collect">
              <p>
                <strong className="text-slate-200">Account data.</strong> When you register, we collect your{" "}
                <strong className="text-slate-200">email address</strong> and a hashed password, processed by
                Supabase Auth.
              </p>
              <p>
                <strong className="text-slate-200">Subscription and billing data.</strong> When you subscribe, Stripe
                processes your payment details. We store the resulting{" "}
                <strong className="text-slate-200">Stripe customer ID</strong>,{" "}
                <strong className="text-slate-200">subscription ID</strong>, plan name, subscription status, and
                billing period dates in our database.
              </p>
              <p>
                <strong className="text-slate-200">License data.</strong> Each active subscription generates a{" "}
                <strong className="text-slate-200">license key UUID</strong>. When the desktop app validates or
                connects using your key, we record the{" "}
                <strong className="text-slate-200">IP address</strong> of the connecting device and a{" "}
                <strong className="text-slate-200">timestamp</strong> (&ldquo;last seen at&rdquo;). This is used
                for fraud prevention and abuse detection only.
              </p>
              <p>
                <strong className="text-slate-200">Trial data.</strong> For free-trial accounts we store a{" "}
                <strong className="text-slate-200">trial expiry timestamp</strong>.
              </p>
            </LegalSection>

            <LegalSection num={3} heading="Data We Do NOT Collect">
              <LegalWarningBox>
                <strong>Your Trading212 API keys are NEVER transmitted to or stored by SwiftTrade.</strong> The
                desktop application encrypts and stores them locally on your Windows computer only. No SwiftTrade
                server ever receives, processes, or has access to your broker credentials.
              </LegalWarningBox>
              <p>We do not collect:</p>
              <LegalList
                items={[
                  "Trading212 API keys or secrets.",
                  "Your Trading212 portfolio holdings, balance, or transaction history.",
                  "Location data beyond the IP address of your desktop connection.",
                  "Device identifiers, hardware fingerprints, or biometric data.",
                  "Browsing behaviour, analytics, or advertising identifiers.",
                  "Any data about minors.",
                ]}
              />
            </LegalSection>

            <LegalSection num={4} heading="Legal Basis for Processing (GDPR Art. 6)">
              <p>We process your personal data on the following legal bases:</p>
              <LegalList
                items={[
                  "Contract performance (Art. 6(1)(b)): processing your email address, subscription status, and license key is necessary to provide the Service you have subscribed to.",
                  "Legitimate interests (Art. 6(1)(f)): recording the IP address and timestamp of desktop connections is necessary for our legitimate interest in detecting fraud, abuse, and unauthorised account sharing. This is proportionate and does not override your privacy rights.",
                  "Legal obligation (Art. 6(1)(c)): retaining billing records for the period required by applicable tax and accounting law.",
                ]}
              />
            </LegalSection>

            <LegalSection num={5} heading="Data Processors and Third Parties">
              <p>
                We use the following sub-processors to deliver the Service. They process your data only on our
                behalf and under data processing agreements:
              </p>
              <div className="space-y-3">
                <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-4">
                  <p className="font-semibold text-slate-200">Supabase, Inc.</p>
                  <p className="mt-1 text-slate-400">
                    Authentication, database (email, subscription data, license data). Servers are located in the
                    EU (Ireland). Supabase participates in the EU-U.S. Data Privacy Framework and provides
                    Standard Contractual Clauses for transfers outside the EU.
                  </p>
                </div>
                <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-4">
                  <p className="font-semibold text-slate-200">Stripe, Inc.</p>
                  <p className="mt-1 text-slate-400">
                    Payment processing (Stripe customer ID, subscription ID). Stripe holds its own PCI-DSS
                    certification and processes payment card data. We never receive or store your card number.
                    Stripe may transfer data to the United States under Standard Contractual Clauses.
                  </p>
                </div>
              </div>
              <p>
                We do not sell, rent, or share your personal data with any other third party for marketing purposes.
              </p>
            </LegalSection>

            <LegalSection num={6} heading="Data Retention">
              <LegalList
                items={[
                  "Account (email, password hash): retained for the lifetime of your account, plus 30 days after deletion to allow recovery.",
                  "Subscription and billing records: retained for 7 years from the date of the last transaction to comply with tax and accounting obligations.",
                  "License key and IP logs: retained for 90 days on a rolling basis, then automatically purged.",
                  "Trial expiry timestamp: deleted when the account is deleted.",
                ]}
              />
              <p>
                When you delete your account, we delete or anonymise all personal data within 30 days, except
                where we are required to retain it by law (e.g. billing records under applicable accounting rules).
              </p>
            </LegalSection>

            <LegalSection num={7} heading="Your Rights Under GDPR">
              <p>
                If you are in the European Union or EEA, you have the following rights. To exercise any of them,
                email{" "}
                <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                  legal@swifttrade.app
                </a>{" "}
                and we will respond within 30 days.
              </p>
              <LegalList
                items={[
                  "Right of access (Art. 15): obtain a copy of the personal data we hold about you.",
                  "Right to rectification (Art. 16): ask us to correct inaccurate data.",
                  "Right to erasure (Art. 17): request deletion of your data where there is no legitimate reason for continued processing.",
                  "Right to restriction (Art. 18): ask us to restrict processing in certain circumstances.",
                  "Right to data portability (Art. 20): receive your data in a structured, machine-readable format.",
                  "Right to object (Art. 21): object to processing based on legitimate interests.",
                  "Right to withdraw consent: where processing is based on consent, you may withdraw it at any time.",
                  "Right to lodge a complaint: you have the right to lodge a complaint with your national supervisory authority (e.g. the Commission for Personal Data Protection in Bulgaria, or your local authority in the EU).",
                ]}
              />
            </LegalSection>

            <LegalSection num={8} heading="Cookies and Local Storage">
              <p>
                The web portal uses the following cookies and browser storage:
              </p>
              <LegalList
                items={[
                  "Session cookies set by Supabase Auth: required to keep you logged in. These are first-party, HttpOnly, Secure cookies and are strictly necessary to provide the Service.",
                  "No analytics cookies, no advertising cookies, no third-party tracking.",
                ]}
              />
              <p>
                Because we use only strictly necessary cookies, we do not display a cookie consent banner. If
                this changes in future, we will update this policy and seek consent where required.
              </p>
            </LegalSection>

            <LegalSection num={9} heading="International Data Transfers">
              <p>
                Your data may be transferred to and stored in countries outside the EU/EEA (primarily the
                United States, where Supabase and Stripe have infrastructure). Such transfers take place under
                appropriate safeguards:
              </p>
              <LegalList
                items={[
                  "Standard Contractual Clauses (SCCs) approved by the European Commission.",
                  "Adequacy decisions where applicable.",
                ]}
              />
              <p>
                You can request details of the specific safeguards in place by contacting{" "}
                <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                  legal@swifttrade.app
                </a>.
              </p>
            </LegalSection>

            <LegalSection num={10} heading="Security">
              <p>
                We implement appropriate technical and organisational measures to protect your personal data,
                including:
              </p>
              <LegalList
                items={[
                  "Passwords hashed by Supabase Auth (bcrypt).",
                  "All web portal connections over TLS (HTTPS).",
                  "Database access restricted via Supabase Row Level Security (RLS).",
                  "Trading212 API keys encrypted at rest on your local machine — SwiftTrade servers never hold broker credentials.",
                ]}
              />
              <p>
                No internet transmission or storage system is 100% secure. If you become aware of a security
                issue, please report it to{" "}
                <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                  legal@swifttrade.app
                </a>{" "}
                immediately.
              </p>
            </LegalSection>

            <LegalSection num={11} heading="Children's Privacy">
              <p>
                The Service is not directed at children under 18 years of age. We do not knowingly collect
                personal data from children. If we learn that we have inadvertently collected data from a child,
                we will delete it promptly. If you believe a child has provided us with data, contact us at{" "}
                <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                  legal@swifttrade.app
                </a>.
              </p>
            </LegalSection>

            <LegalSection num={12} heading="Changes to This Policy">
              <p>
                We may update this Privacy Policy from time to time. Material changes will be notified to your
                registered email address and on the Site at least 14 days before they take effect. The revised
                policy will be effective from the date shown at the top of this page.
              </p>
            </LegalSection>

            <LegalSection num={13} heading="Contact">
              <p>
                For privacy questions, data subject requests, or complaints:{" "}
                <a href="mailto:legal@swifttrade.app" className="text-emerald-400 hover:underline">
                  legal@swifttrade.app
                </a>
              </p>
              <LegalInfoBox>
                Related documents:{" "}
                <Link href="/legal/terms" className="text-sky-300 hover:underline">Terms of Service</Link>
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

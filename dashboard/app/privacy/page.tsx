import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy — Project Lockdown',
  description: 'What Project Lockdown collects, how it is used, and your choices.',
};

// Public page — not behind auth (middleware only protects /verdicts and /settings).
export const dynamic = 'force-static';

const EFFECTIVE = 'August 3, 2026';
const CONTACT = 'support@greensky.tech';

export default function PrivacyPage() {
  return (
    <section className="policy">
      <h1>Privacy Policy</h1>
      <p className="muted">Effective {EFFECTIVE}</p>

      <p>
        Project Lockdown is an opt-in, disclosed safety tool. It monitors a user&apos;s
        messages on supported AI chatbot sites and flags messages that may indicate
        intent to harm other people, so that a designated adult — a parent, guardian,
        or school — can review them. This policy explains what the extension and
        dashboard collect, how that information is used, and the choices available to
        you. Monitoring is intended to be set up with the knowledge of the person
        being monitored.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li>
          <strong>Message content, for analysis.</strong> On supported sites
          (chatgpt.com, claude.ai, gemini.google.com, and our own test site), the
          extension reads a short window of recent messages and sends it to our
          detection service to be classified. This is the core function of the tool.
        </li>
        <li>
          <strong>Account information.</strong> When a parent, guardian, or school
          creates a dashboard account, our authentication provider stores their email
          address and sign-in credentials.
        </li>
        <li>
          <strong>A device token.</strong> The extension stores a single access token
          locally in the browser to connect to your account. It is not a password and
          can be revoked at any time.
        </li>
      </ul>

      <h2>What we store</h2>
      <p>
        We do <strong>not</strong> retain the raw text of monitored conversations.
        Message text is sent for classification and is not saved as a stored
        conversation. When a message is flagged, we keep only a privacy-minimal
        record: the category and severity of the concern, a short rationale, the
        location (character offsets) of the relevant text within the reviewed window,
        the site it occurred on, and a timestamp. Messages that are not flagged
        produce no stored record.
      </p>

      <h2>Third-party services</h2>
      <ul>
        <li>
          <strong>AI classification provider.</strong> To analyze messages, our
          detection service sends message text to a third-party large-language-model
          provider (Anthropic). It is used to process the request and return a result;
          the text is not used by us to build a stored conversation history.
        </li>
        <li>
          <strong>Authentication provider.</strong> We use Clerk to manage dashboard
          sign-in and accounts.
        </li>
        <li>
          <strong>Hosting and database.</strong> Our service and its database are
          hosted on third-party infrastructure providers used to operate the product.
        </li>
      </ul>

      <h2>How information is used</h2>
      <p>
        Collected information is used solely to provide the safety-monitoring feature:
        to classify messages, to show flagged items to the account owner for review,
        to attribute flags to the correct account, and to protect the service from
        abuse. We do <strong>not</strong> sell your data. We do not use or transfer it
        for advertising, for purposes unrelated to the tool&apos;s single purpose, or to
        determine creditworthiness or for lending.
      </p>

      <h2>Your choices and controls</h2>
      <ul>
        <li>
          <strong>Revoke access at any time.</strong> Deleting a device token in the
          dashboard, or disconnecting it in the extension, immediately stops that
          device from being monitored.
        </li>
        <li>
          <strong>Uninstall.</strong> Removing the extension stops all monitoring on
          that device.
        </li>
        <li>
          <strong>Deletion.</strong> You may request deletion of your account and its
          stored flag records by contacting us.
        </li>
      </ul>

      <h2>Children and disclosure</h2>
      <p>
        This tool is designed to be operated by a parent, guardian, or school on
        behalf of a person in their care, and to be used with that person&apos;s
        knowledge. The adult who sets up monitoring is responsible for providing any
        notice and obtaining any consent required by applicable law. If you believe
        information has been collected without appropriate authorization, contact us
        so we can address it.
      </p>

      <h2>Changes to this policy</h2>
      <p>
        We may update this policy as the product evolves. Material changes will be
        reflected by updating the effective date above.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this policy or your data can be sent to{' '}
        <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
      </p>
    </section>
  );
}

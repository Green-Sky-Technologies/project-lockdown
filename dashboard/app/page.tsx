import { SignedIn, SignedOut, SignInButton } from '@clerk/nextjs';

export default function Home() {
  return (
    <section className="hero">
      <h1>Flagged conversations</h1>
      <p className="muted">
        This dashboard shows conversations that Project Lockdown flagged for your
        review. Monitoring is disclosed to the person being monitored. What you see
        here is an observation for review — never a conclusion about a person.
      </p>
      <SignedIn>
        <a className="button" href="/verdicts">
          View flagged conversations →
        </a>
      </SignedIn>
      <SignedOut>
        <SignInButton mode="modal">
          <button className="button">Sign in to continue</button>
        </SignInButton>
      </SignedOut>
    </section>
  );
}

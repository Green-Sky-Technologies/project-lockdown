import type { Metadata } from 'next';
import {
  ClerkProvider,
  SignInButton,
  SignedIn,
  SignedOut,
  UserButton,
} from '@clerk/nextjs';
import './globals.css';

export const metadata: Metadata = {
  title: 'Project Lockdown — Dashboard',
  description: 'Review conversations flagged for your attention.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>
          <header className="topbar">
            <a className="brand" href="/">
              🔒 Project Lockdown
            </a>
            <nav>
              <SignedIn>
                <a className="navlink" href="/verdicts">
                  Flagged
                </a>
                <UserButton />
              </SignedIn>
              <SignedOut>
                <SignInButton mode="modal" />
              </SignedOut>
            </nav>
          </header>
          <main className="content">{children}</main>
        </body>
      </html>
    </ClerkProvider>
  );
}

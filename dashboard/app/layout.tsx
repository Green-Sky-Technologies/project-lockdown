import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import {
  ClerkProvider,
  SignInButton,
  SignedIn,
  SignedOut,
  UserButton,
} from '@clerk/nextjs';
import { NavLinks } from './NavLinks';
import { PREVIEW } from '@/lib/sample';
import './globals.css';

const inter = Inter({ subsets: ['latin'], weight: ['400', '500'] });

export const metadata: Metadata = {
  title: 'Project Lockdown',
  description: 'A quiet companion dashboard. When something needs a parent, it says so plainly.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={inter.className}>
          <header className="topbar">
            <a className="brand" href="/">
              <span className="brand-dot" aria-hidden />
              Project Lockdown
            </a>
            <nav className="topnav">
              {PREVIEW && <NavLinks />}
              <SignedIn>
                <NavLinks />
                <UserButton
                  appearance={{
                    elements: { avatarBox: { width: '28px', height: '28px' } },
                  }}
                />
              </SignedIn>
              <SignedOut>
                <SignInButton mode="modal" />
              </SignedOut>
            </nav>
          </header>
          {children}
          <footer className="sitefooter">
            <a href="/privacy">Privacy policy</a>
          </footer>
        </body>
      </html>
    </ClerkProvider>
  );
}

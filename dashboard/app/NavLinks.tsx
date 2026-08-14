'use client';

import { usePathname } from 'next/navigation';

const LINKS = [
  { href: '/', label: 'Home' },
  { href: '/activity', label: 'Activity' },
  { href: '/devices', label: 'Devices' },
  { href: '/settings', label: 'Settings' },
];

export function NavLinks() {
  const pathname = usePathname();
  return (
    <>
      {LINKS.map(({ href, label }) => {
        const current = href === '/' ? pathname === '/' : pathname.startsWith(href);
        return (
          <a key={href} href={href} aria-current={current ? 'page' : undefined}>
            {label}
          </a>
        );
      })}
    </>
  );
}

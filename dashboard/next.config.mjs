/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    // The design handoff renamed /verdicts → /activity; keep old links working.
    return [
      { source: '/verdicts', destination: '/activity', permanent: true },
      { source: '/verdicts/:id', destination: '/activity/:id', permanent: true },
    ];
  },
};

export default nextConfig;

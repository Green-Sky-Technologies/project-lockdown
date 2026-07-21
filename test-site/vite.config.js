import { defineConfig } from 'vite';

// Static single-page mock chat harness. Vite root is this folder; `vite build`
// emits to dist/, which Vercel's zero-config Vite preset serves. base '/' works
// for a Vercel deployment served at the domain root.
export default defineConfig({
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});

/**
 * SSR API base URL helper.
 *
 * Server components and route handlers should call `serverApiBase()` instead of
 * reading `NEXT_PUBLIC_BACKEND_URL` directly.  Inside Docker Compose the web
 * service sets `API_INTERNAL_URL=http://api:8000` so SSR fetches stay on the
 * internal network and never leave the compose stack — faster, no TLS, no
 * public-DNS dependency at build/render time.
 *
 * On Vercel (all-in-one deployment), VERCEL_URL is set automatically to the
 * deployment host (no protocol). Same-project FastAPI is reachable at the
 * deployment's own origin via the `/api/*` rewrite in vercel.json.
 *
 * Browser/client code should continue to read `NEXT_PUBLIC_BACKEND_URL`
 * directly (baked at build time, accessible on window).
 */
export function serverApiBase(): string {
  // Vercel: same-project FastAPI is reachable at the deployment's own origin.
  // VERCEL_URL is the deployment host (no protocol) and is set automatically.
  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}`;
  }
  return (
    process.env.API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    'http://localhost:8000'
  );
}

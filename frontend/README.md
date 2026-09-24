# Stillwater Next.js frontend

This is an independent, static-export Next.js application. It contains no
Python, Kokoro model, or synthesis code. The browser reads voice catalogs from
the FastAPI REST API after the page loads.

## Local development

```powershell
Copy-Item .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`. Run FastAPI on port 8767 at the same time.

## Cloudflare static deployment

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `out`
- Environment: set `NEXT_PUBLIC_API_BASE_URL` to the public HTTPS API URL and
  `NEXT_PUBLIC_SITE_URL` to the public frontend URL before building.

The API URL is compiled into the browser bundle. CORS on FastAPI must list the
exact deployed frontend origin.

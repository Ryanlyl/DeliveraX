# Vercel Frontend Deployment Notes

## 1) Project import

- Import this repository into Vercel.
- Set `Root Directory` to `frontend`.
- Keep framework auto-detection (Vite).

## 2) Build settings

- Build command: `npm run build`
- Output directory: `dist`

## 3) Routing/proxy config

- Config file: `frontend/vercel.json`
- Current rewrite target is a placeholder:
  - `https://your-backend.onrender.com`
- Replace it with your real Render backend domain before production deploy.

## 4) Verify after deploy

- Open `/` and a deep route like `/projects`.
- Ensure `/api/providers` and `/health` both return backend responses through the Vercel domain.

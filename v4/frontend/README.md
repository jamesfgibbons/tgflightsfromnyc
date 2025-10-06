# SERPRadio v4 Frontend (Vite on Vercel)

## Develop locally
```bash
cd v4/frontend
npm i
npm run dev
# For local API, set VITE_API_BASE=https://your-backend.up.railway.app and update fetches accordingly
```

## Deploy to Vercel
- Create a Vercel project. Set Root Directory = `v4/frontend`.
- Edit `vercel.json`: replace `https://YOUR_BACKEND_HOST` with your Railway backend URL.
- (Optional) Set `XAI_API_KEY` in Vercel env to enable future chat endpoints.
- Deploy. The app calls the backend via the `/api/*` rewrites.

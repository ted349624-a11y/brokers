# Elysium Broker — Whitelist

Static site + two Vercel functions. Entries are stored in Upstash Redis (free tier).

## Setup on Vercel
1. Project → **Storage** → Create / Connect → **Upstash for Redis** (free plan) → connect to this project.
2. Project → Settings → **Environment Variables** → add `ADMIN_KEY` = a long secret only you know.
3. Redeploy.

## Get the list
`https://brokers-ashen.vercel.app/api/export?key=YOUR_ADMIN_KEY` → downloads a CSV.
Add `&format=json` for JSON.

## Settings
`CONFIG` block near the bottom of `index.html`: `X_HANDLE`, `TWEET_ID`, `TOTAL_SPOTS`.

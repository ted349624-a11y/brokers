# Elysium Broker — Whitelist

Static whitelist site for the Elysium Broker NFT. Deploys on Vercel as-is (no build step).

## Settings
Edit the `CONFIG` block near the bottom of `index.html`:
- `X_HANDLE` — project X username
- `TWEET_ID` — post to like / repost / comment on
- `TOTAL_SPOTS` — whitelist size
- `SUBMIT_URL` — Google Apps Script web app URL (empty = demo mode, nothing is saved)

## Saving entries (Google Sheets)
1. Create a Google Sheet → Extensions → Apps Script, paste `apps-script/Code.gs`.
2. Deploy → New deployment → Web app. Execute as: Me. Who has access: Anyone.
3. Paste the web app URL into `SUBMIT_URL` and push.

## Vercel
Import this repo in Vercel → Framework preset: Other → Deploy.

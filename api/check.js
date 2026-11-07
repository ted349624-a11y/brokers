// Whitelist checker: GET /api/check?wallet=0x...
// FCFS = applied on the website (Redis). GTD / OG = wallet posted in #wallet-submit by a member holding that role.
const { redis } = require("./_db");
const { tiersFor } = require("./_tiers");
const WALLET = /^0x[a-f0-9]{40}$/;

module.exports = async (req, res) => {
  res.setHeader("Cache-Control", "no-store");
  const wallet = String(req.query.wallet || "").trim().toLowerCase();
  if (!WALLET.test(wallet)) return res.status(400).json({ ok: false, error: "invalid" });
  try {
    const ip = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "unknown";
    const hits = await redis("INCR", `eb:ck:rl:${ip}`);
    if (hits === 1) await redis("EXPIRE", `eb:ck:rl:${ip}`, 60);
    if (hits > 30) return res.status(429).json({ ok: false, error: "rate" });

    const { tiers, partial } = await tiersFor(wallet);
    return res.status(200).json({ ok: true, wallet, tiers, partial });
  } catch (e) {
    return res.status(500).json({ ok: false, error: "server" });
  }
};

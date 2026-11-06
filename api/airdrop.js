// $BROKER airdrop entries. Stored apart from the whitelist (eb:ad:* keys).
const { redis } = require("./_db");
const HANDLE = /^[a-z0-9_]{1,15}$/;
const WALLET = /^0x[a-f0-9]{40}$/;

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).json({ ok: false, error: "method" });
  try {
    let body = req.body;
    if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
    body = body || {};
    const handle = String(body.handle || "").replace(/^@/, "").toLowerCase().trim();
    const wallet = String(body.wallet || "").toLowerCase().trim();
    if (!HANDLE.test(handle) || !WALLET.test(wallet)) return res.status(400).json({ ok: false, error: "invalid" });

    const ip = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "unknown";
    const hits = await redis("INCR", `eb:ad:rl:${ip}`);
    if (hits === 1) await redis("EXPIRE", `eb:ad:rl:${ip}`, 60);
    if (hits > 5) return res.status(429).json({ ok: false, error: "rate" });

    if (!(await redis("SET", `eb:ad:h:${handle}`, wallet, "NX"))) return res.status(409).json({ ok: false, error: "duplicate" });
    if (!(await redis("SET", `eb:ad:w:${wallet}`, handle, "NX"))) {
      await redis("DEL", `eb:ad:h:${handle}`);
      return res.status(409).json({ ok: false, error: "duplicate" });
    }
    const n = await redis("INCR", "eb:ad:count");
    await redis("RPUSH", "eb:ad:entries", JSON.stringify({
      n, handle, wallet, tasks: String(body.tasks || "").slice(0, 100), ts: new Date().toISOString() }));
    return res.status(200).json({ ok: true, n });
  } catch (e) {
    return res.status(500).json({ ok: false, error: e.message === "db_not_configured" ? "db_not_configured" : "server" });
  }
};

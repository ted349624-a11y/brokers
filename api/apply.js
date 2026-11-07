const { redis } = require("./_db");

const HANDLE = /^[a-z0-9_]{1,15}$/;
const WALLET = /^0x[a-f0-9]{40}$/;

module.exports = async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ ok: false, error: "method" });
  return res.status(403).json({ ok: false, error: "closed" });   // whitelist closed
  try {
    let body = req.body;
    if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
    body = body || {};
    const handle = String(body.handle || "").replace(/^@/, "").toLowerCase().trim();
    const wallet = String(body.wallet || "").toLowerCase().trim();
    if (!HANDLE.test(handle) || !WALLET.test(wallet)) return res.status(400).json({ ok: false, error: "invalid" });

    // basic rate limit: 5 attempts per IP per minute
    const ip = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "unknown";
    const hits = await redis("INCR", `eb:rl:${ip}`);
    if (hits === 1) await redis("EXPIRE", `eb:rl:${ip}`, 60);
    if (hits > 5) return res.status(429).json({ ok: false, error: "rate" });

    // one entry per X account and per wallet
    if (!(await redis("SET", `eb:h:${handle}`, wallet, "NX"))) return res.status(409).json({ ok: false, error: "duplicate" });
    if (!(await redis("SET", `eb:w:${wallet}`, handle, "NX"))) {
      await redis("DEL", `eb:h:${handle}`);
      return res.status(409).json({ ok: false, error: "duplicate" });
    }

    const n = await redis("INCR", "eb:wl:count");
    const entry = { n, handle, wallet, tasks: String(body.tasks || "").slice(0, 100), ts: new Date().toISOString() };
    await redis("RPUSH", "eb:wl:entries", JSON.stringify(entry));
    return res.status(200).json({ ok: true, n });
  } catch (e) {
    return res.status(500).json({ ok: false, error: e.message === "db_not_configured" ? "db_not_configured" : "server" });
  }
};

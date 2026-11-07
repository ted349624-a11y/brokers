// Download lists (CSV, or &format=json):
//   /api/export?key=ADMIN_KEY                 website whitelist (FCFS)
//   /api/export?key=ADMIN_KEY&list=airdrop    airdrop entries
//   /api/export?key=ADMIN_KEY&list=mints      mint reservations (airdrop these wallets on Nov 9)
//   /api/export?key=ADMIN_KEY&list=refunds    payments to refund (underpaid, double, sold out, early)
const { redis } = require("./_db");
const LISTS = {
  whitelist: { key: "eb:wl:entries", cols: ["n", "handle", "wallet", "tasks", "ts"] },
  airdrop:   { key: "eb:ad:entries", cols: ["n", "handle", "wallet", "tasks", "ts"] },
  mints:     { key: "eb:mint:entries", cols: ["n", "wallet", "tier", "chain", "cur", "value", "tx", "ts"] },
  refunds:   { key: "eb:mint:refunds", cols: ["wallet", "reason", "tier", "chain", "cur", "value", "tx", "ts"] },
};
const cell = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };

module.exports = async (req, res) => {
  const key = process.env.ADMIN_KEY;
  if (!key || req.query.key !== key) return res.status(401).send("Unauthorized");
  const name = LISTS[req.query.list] ? req.query.list : "whitelist";
  const L = LISTS[name];
  const rows = ((await redis("LRANGE", L.key, 0, -1)) || []).map(s => JSON.parse(s));
  if (req.query.format === "json") return res.status(200).json(rows);
  const out = rows.map(r => {
    const o = { ...r };
    if (o.handle) o.handle = "@" + o.handle;
    if (o.value) o.value = (Number(BigInt(o.value)) / 1e18).toString();   // in HYPE / ETH
    return L.cols.map(c => cell(o[c])).join(",");
  });
  res.setHeader("Content-Type", "text/csv; charset=utf-8");
  res.setHeader("Content-Disposition", `attachment; filename="elysium-broker-${name}.csv"`);
  return res.status(200).send([L.cols.join(",")].concat(out).join("\n"));
};

// Download lists (CSV, or &format=json):
//   /api/export?key=ADMIN_KEY                 website whitelist (FCFS)
//   /api/export?key=ADMIN_KEY&list=airdrop    airdrop entries
//   /api/export?key=ADMIN_KEY&list=mints      mint reservations (airdrop these wallets on Nov 9)
//   /api/export?key=ADMIN_KEY&list=refunds    payments to refund (underpaid, double, sold out, early)
//   /api/export?key=ADMIN_KEY&list=all        every whitelisted wallet: FCFS (website) + GTD/OG (#wallet-submit), one row per wallet
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
  if (req.query.list === "all") return all(req, res);
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

// ---- combined list -------------------------------------------------------
const API = "https://discord.com/api/v10";
const dc = async path => {
  const r = await fetch(API + path, { headers: { Authorization: `Bot ${process.env.DISCORD_TOKEN}` } });
  if (!r.ok) throw new Error(`discord ${r.status}`);
  return r.json();
};
async function all(req, res) {
  const rows = new Map();   // wallet -> row
  const get = w => rows.get(w) || rows.set(w, { wallet: w, gtd: "", og: "", fcfs: "", x_handle: "", discord: "" }).get(w);
  for (const s of (await redis("LRANGE", "eb:wl:entries", 0, -1)) || []) {
    const e = JSON.parse(s), r = get(e.wallet.toLowerCase());
    r.fcfs = "yes"; r.x_handle = "@" + e.handle;
  }
  const gid = (await dc("/users/@me/guilds"))[0].id;
  const names = Object.fromEntries((await dc(`/guilds/${gid}/roles`)).map(x => [x.id, x.name]));
  const ch = (await dc(`/guilds/${gid}/channels`)).find(c => c.name.split("\uff5c").pop().trim().toLowerCase() === "wallet-submit");
  let msgs = [], before = "";
  if (ch) for (;;) {
    const page = await dc(`/channels/${ch.id}/messages?limit=100${before ? "&before=" + before : ""}`);
    msgs = msgs.concat(page);
    if (page.length < 100) break;
    before = page[page.length - 1].id;
  }
  msgs.sort((a, b) => (BigInt(a.id) < BigInt(b.id) ? -1 : 1));
  const seen = new Set();
  for (const m of msgs) {
    if (m.author.bot || seen.has(m.author.id)) continue;
    const w = (m.content || "").match(/\b0x[a-fA-F0-9]{40}\b/);
    if (!w) continue;
    seen.add(m.author.id);
    let roles = [];
    try { roles = (await dc(`/guilds/${gid}/members/${m.author.id}`)).roles.map(id => names[id]); } catch {}
    const r = get(w[0].toLowerCase());
    if (roles.includes("GTD")) r.gtd = "yes";
    if (roles.includes("OG")) r.og = "yes";
    r.discord = m.author.username;
  }
  const out = [...rows.values()].map(r => ({ ...r, tier: r.gtd || r.og ? "GTD/OG" : r.fcfs ? "WL" : "" }))
    .filter(r => r.tier)
    .sort((a, b) => (a.tier === b.tier ? 0 : a.tier === "GTD/OG" ? -1 : 1));
  if (req.query.format === "json") return res.status(200).json(out);
  const cols = ["wallet", "tier", "gtd", "og", "fcfs", "x_handle", "discord"];
  res.setHeader("Content-Type", "text/csv; charset=utf-8");
  res.setHeader("Content-Disposition", 'attachment; filename="elysium-broker-all-whitelist.csv"');
  return res.status(200).send([cols.join(",")].concat(out.map(r => cols.map(c => cell(r[c])).join(","))).join("\n"));
}

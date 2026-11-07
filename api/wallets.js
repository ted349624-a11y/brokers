// OG/GTD wallets from #wallet-submit: https://YOUR-SITE/api/wallets?key=ADMIN_KEY  (&format=json)
// Reads the channel live with the bot token; first valid wallet per member.
const API = "https://discord.com/api/v10";
const WALLET = /\b0x[a-fA-F0-9]{40}\b/;
const dc = async path => {
  const r = await fetch(API + path, { headers: { Authorization: `Bot ${process.env.DISCORD_TOKEN}` } });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
};
const base = n => n.split("｜").pop().trim().toLowerCase();

module.exports = async (req, res) => {
  const key = process.env.ADMIN_KEY;
  if (!key || req.query.key !== key) return res.status(401).send("Unauthorized");
  try {
    const gid = (await dc("/users/@me/guilds"))[0].id;
    const roles = Object.fromEntries((await dc(`/guilds/${gid}/roles`)).map(r => [r.id, r.name]));
    const ch = (await dc(`/guilds/${gid}/channels`)).find(c => base(c.name) === "wallet-submit");
    if (!ch) return res.status(404).send("wallet-submit channel not found");
    let msgs = [], before = "";
    for (;;) {
      const page = await dc(`/channels/${ch.id}/messages?limit=100${before ? "&before=" + before : ""}`);
      msgs = msgs.concat(page);
      if (page.length < 100) break;
      before = page[page.length - 1].id;
    }
    msgs.sort((a, b) => (BigInt(a.id) < BigInt(b.id) ? -1 : 1));
    const seen = new Set(), rows = [];
    for (const m of msgs) {
      if (m.author.bot || seen.has(m.author.id)) continue;
      const w = (m.content || "").match(WALLET);
      if (!w) continue;
      seen.add(m.author.id);
      let rl = [];
      try { rl = (await dc(`/guilds/${gid}/members/${m.author.id}`)).roles.map(id => roles[id]).filter(n => n === "OG" || n === "GTD"); } catch {}
      rows.push({ n: rows.length + 1, discord: m.author.username, id: m.author.id, wallet: w[0].toLowerCase(), roles: rl.join("+"), time: m.timestamp });
    }
    if (req.query.format === "json") return res.status(200).json(rows);
    const csv = ["no,discord_username,discord_id,wallet,roles,time"]
      .concat(rows.map(r => [r.n, r.discord, r.id, r.wallet, r.roles, r.time].join(","))).join("\n");
    res.setHeader("Content-Type", "text/csv; charset=utf-8");
    res.setHeader("Content-Disposition", 'attachment; filename="elysium-broker-og-gtd-wallets.csv"');
    return res.status(200).send(csv);
  } catch (e) {
    return res.status(500).send("Could not read the channel: " + e.message);
  }
};

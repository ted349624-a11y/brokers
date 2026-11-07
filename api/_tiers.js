// Shared: which lists a wallet is on. GTD/OG from #wallet-submit + Discord roles, FCFS from the website list.
const { redis } = require("./_db");
const API = "https://discord.com/api/v10";
const dc = async path => {
  const r = await fetch(API + path, { headers: { Authorization: `Bot ${process.env.DISCORD_TOKEN}` } });
  if (!r.ok) throw new Error(`discord ${r.status}`);
  return r.json();
};
const base = n => n.split("｜").pop().trim().toLowerCase();

async function walletMap() {
  const hit = await redis("GET", "eb:ws:snap");
  if (hit) return JSON.parse(hit);
  const gid = (await dc("/users/@me/guilds"))[0].id;
  const ch = (await dc(`/guilds/${gid}/channels`)).find(c => base(c.name) === "wallet-submit");
  const roleNames = Object.fromEntries((await dc(`/guilds/${gid}/roles`)).map(r => [r.id, r.name]));
  let msgs = [], before = "";
  if (ch) for (;;) {
    const page = await dc(`/channels/${ch.id}/messages?limit=100${before ? "&before=" + before : ""}`);
    msgs = msgs.concat(page);
    if (page.length < 100) break;
    before = page[page.length - 1].id;
  }
  msgs.sort((a, b) => (BigInt(a.id) < BigInt(b.id) ? -1 : 1));
  const map = {}, seen = new Set();
  for (const m of msgs) {
    if (m.author.bot || seen.has(m.author.id)) continue;
    const w = (m.content || "").match(/\b0x[a-fA-F0-9]{40}\b/);
    if (!w) continue;
    seen.add(m.author.id);
    map[w[0].toLowerCase()] = m.author.id;
  }
  const snap = { gid, roleNames, map };
  await redis("SET", "eb:ws:snap", JSON.stringify(snap), "EX", 180);
  return snap;
}

async function memberRoles(snap, uid) {
  const k = `eb:ws:m:${uid}`;
  const hit = await redis("GET", k);
  if (hit) return JSON.parse(hit);
  let names = [];
  try { names = (await dc(`/guilds/${snap.gid}/members/${uid}`)).roles.map(id => snap.roleNames[id]); } catch {}
  await redis("SET", k, JSON.stringify(names), "EX", 180);
  return names;
}

// -> { tiers: ["GTD","OG","FCFS"], partial: bool }
async function tiersFor(wallet) {
  wallet = wallet.toLowerCase();
  const tiers = [];
  let partial = false;
  try {
    const snap = await walletMap();
    const uid = snap.map[wallet];
    if (uid) {
      const names = await memberRoles(snap, uid);
      if (names.includes("GTD")) tiers.push("GTD");
      if (names.includes("OG")) tiers.push("OG");
    }
  } catch { partial = true; }
  // only our own namespace: the database is shared with another project
  if (await redis("GET", `eb:w:${wallet}`)) tiers.push("FCFS");
  return { tiers, partial };
}

module.exports = { tiersFor };

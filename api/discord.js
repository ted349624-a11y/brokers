// Discord interactions endpoint: handles the "✅ Verify" button.
// Discord → Developer Portal → General Information → Interactions Endpoint URL:
//   https://www.elysiumbroker.xyz/api/discord
// Vercel env vars: DISCORD_TOKEN (bot token). DISCORD_PUBLIC_KEY is optional (public key below).
const crypto = require("crypto");

const PUBLIC_KEY = process.env.DISCORD_PUBLIC_KEY ||
  "a5867423fab4b9804fc5d8411086d1237c1ca831b7980d1eed42df02e1c5c0ee";
const KEY = crypto.createPublicKey({
  key: Buffer.concat([Buffer.from("302a300506032b6570032100", "hex"), Buffer.from(PUBLIC_KEY, "hex")]),
  format: "der", type: "spki"
});
const API = "https://discord.com/api/v10";
const ROLE_NAME = "User";
let roleCache = {};

function raw(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", c => chunks.push(c));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

async function discord(method, path) {
  const r = await fetch(API + path, {
    method,
    headers: { Authorization: `Bot ${process.env.DISCORD_TOKEN}`, "X-Audit-Log-Reason": "Verify button" }
  });
  if (!r.ok && r.status !== 204) throw new Error(`${r.status} ${await r.text()}`);
  return r.status === 204 ? null : r.json();
}

async function userRole(gid) {
  if (roleCache[gid]) return roleCache[gid];
  const roles = await discord("GET", `/guilds/${gid}/roles`);
  const r = roles.find(x => x.name === ROLE_NAME);
  if (!r) throw new Error("User role missing");
  return (roleCache[gid] = r.id);
}

const reply = (res, content) =>
  res.status(200).json({ type: 4, data: { content, flags: 64 } }); // ephemeral

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).end();
  const body = await raw(req);
  const sig = req.headers["x-signature-ed25519"], ts = req.headers["x-signature-timestamp"];
  let ok = false;
  try { ok = !!sig && !!ts && crypto.verify(null, Buffer.concat([Buffer.from(ts), body]), KEY, Buffer.from(sig, "hex")); } catch {}
  if (!ok) return res.status(401).send("invalid request signature");

  const i = JSON.parse(body.toString("utf8"));
  if (i.type === 1) return res.status(200).json({ type: 1 });           // PING
  if (i.type === 3 && i.data && i.data.custom_id === "eb_verify") {     // button click
    const uid = i.member && i.member.user && i.member.user.id;
    try {
      const rid = await userRole(i.guild_id);
      if ((i.member.roles || []).includes(rid)) return reply(res, "You're already verified. Welcome back to the desk.");
      await discord("PUT", `/guilds/${i.guild_id}/members/${uid}/roles/${rid}`);
      return reply(res, "✅ Verified. Welcome to the Elysium Broker desk. The channels are open for you now.");
    } catch (e) {
      console.error(e);
      return reply(res, "Verification failed. Please try again in a minute or ask in support.");
    }
  }
  return reply(res, "Unknown action.");
};

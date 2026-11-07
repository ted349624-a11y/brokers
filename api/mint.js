// Broker reservation mint.
// GET  /api/mint?wallet=0x...        -> status, tier, prices, supply
// POST /api/mint {chain, tx}          -> verifies the payment on-chain and records the reservation
//
// Payments go straight to TREASURY. Nothing is trusted from the browser: the server reads the
// transaction from the chain and checks sender, recipient, amount, success and time.
const { redis } = require("./_db");
const { tiersFor } = require("./_tiers");

const TREASURY = "0x00b09cf7290d7e596ecd92a72404295c9fe4e7d1";
const SUPPLY = 1500;
const PER_WALLET = 1;
const START = Date.parse(process.env.MINT_START || "2026-11-07T17:00:00Z");

const CHAINS = {
  hyperevm: { id: 999,   name: "HyperEVM", cur: "HYPE", rpc: process.env.RPC_HYPEREVM || "https://rpc.hyperliquid.xyz/evm" },
  ethereum: { id: 1,     name: "Ethereum", cur: "ETH",  rpc: process.env.RPC_ETHEREUM || "https://ethereum-rpc.publicnode.com" },
  base:     { id: 8453,  name: "Base",     cur: "ETH",  rpc: process.env.RPC_BASE || "https://mainnet.base.org" },
  arbitrum: { id: 42161, name: "Arbitrum", cur: "ETH",  rpc: process.env.RPC_ARBITRUM || "https://arb1.arbitrum.io/rpc" },
};
const PRICES = {               // decimal strings, per currency
  gtd:    { HYPE: "0.04", ETH: "0.0015" },
  wl:     { HYPE: "0.08", ETH: "0.00285" },
  public: { HYPE: "0.16", ETH: "0.0058" },
};
const TIER_LABEL = { gtd: "GTD / OG", wl: "WL", public: "Public" };

function toWei(dec) {
  const [i, f = ""] = dec.split(".");
  return BigInt(i) * 10n ** 18n + BigInt((f + "0".repeat(18)).slice(0, 18) || "0");
}
function priceTier(tiers) {
  if (tiers.includes("GTD") || tiers.includes("OG")) return "gtd";
  if (tiers.includes("FCFS")) return "wl";
  return "public";
}
async function rpc(chain, method, params) {
  const r = await fetch(chain.rpc, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }) });
  const j = await r.json();
  if (j.error) throw new Error(`${chain.name} rpc: ${j.error.message}`);
  return j.result;
}
async function minted() { return Number(await redis("GET", "eb:mint:count")) || 0; }

async function status(wallet) {
  const t = await tiersFor(wallet);
  const tier = priceTier(t.tiers);
  const mine = await redis("GET", `eb:mint:w:${wallet}`);
  return {
    ok: true, wallet, start: START, now: Date.now(), open: Date.now() >= START,
    supply: SUPPLY, minted: await minted(), treasury: TREASURY,
    tier, tierLabel: TIER_LABEL[tier], lists: t.tiers, partial: t.partial,
    prices: PRICES, chains: Object.fromEntries(Object.entries(CHAINS).map(([k, c]) => [k, { id: c.id, name: c.name, cur: c.cur }])),
    reservation: mine ? JSON.parse(mine) : null,
  };
}

async function refund(entry, reason) {
  await redis("RPUSH", "eb:mint:refunds", JSON.stringify({ ...entry, reason }));
  return { ok: false, status: "refund", reason };
}

async function confirm(chainKey, hash) {
  const chain = CHAINS[chainKey];
  if (!chain || !/^0x[0-9a-fA-F]{64}$/.test(hash || "")) return { ok: false, status: "invalid" };
  hash = hash.toLowerCase();

  const done = await redis("GET", `eb:mint:tx:${chainKey}:${hash}`);
  if (done) return JSON.parse(done);                       // already processed: same answer again

  const tx = await rpc(chain, "eth_getTransactionByHash", [hash]);
  if (!tx || !tx.blockNumber) return { ok: false, status: "pending" };
  const rc = await rpc(chain, "eth_getTransactionReceipt", [hash]);
  if (!rc) return { ok: false, status: "pending" };

  const from = tx.from.toLowerCase();
  const entry = { wallet: from, chain: chain.name, cur: chain.cur, tx: hash, value: BigInt(tx.value).toString(), ts: new Date().toISOString() };
  let result;
  if (rc.status !== "0x1") result = { ok: false, status: "failed" };            // reverted: no money moved
  else if ((tx.to || "").toLowerCase() !== TREASURY) result = { ok: false, status: "wrong_recipient" };
  else {
    const blk = await rpc(chain, "eth_getBlockByNumber", [tx.blockNumber, false]);
    const t = await tiersFor(from);
    if (t.partial) return { ok: false, status: "pending" };                     // roles unreadable: try again shortly
    const tier = priceTier(t.tiers);
    const need = toWei(PRICES[tier][chain.cur]);
    entry.tier = TIER_LABEL[tier];
    if (Number(BigInt(blk.timestamp)) * 1000 < START) result = await refund(entry, "paid_before_mint_opened");
    else if (BigInt(tx.value) < need) result = await refund(entry, "underpaid");
    else if (!(await redis("SET", `eb:mint:w:${from}`, "{}", "NX"))) result = await refund(entry, "wallet_already_reserved");
    else {
      const n = await redis("INCR", "eb:mint:count");
      if (n > SUPPLY) {
        await redis("DECR", "eb:mint:count");
        await redis("DEL", `eb:mint:w:${from}`);
        result = await refund(entry, "sold_out");
      } else {
        const rec = { n, ...entry };
        await redis("SET", `eb:mint:w:${from}`, JSON.stringify(rec));
        await redis("RPUSH", "eb:mint:entries", JSON.stringify(rec));
        result = { ok: true, status: "reserved", reservation: rec };
      }
    }
  }
  await redis("SET", `eb:mint:tx:${chainKey}:${hash}`, JSON.stringify(result));
  return result;
}

module.exports = async (req, res) => {
  res.setHeader("Cache-Control", "no-store");
  try {
    const ip = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "unknown";
    const hits = await redis("INCR", `eb:mint:rl:${ip}`);
    if (hits === 1) await redis("EXPIRE", `eb:mint:rl:${ip}`, 60);
    if (hits > 60) return res.status(429).json({ ok: false, error: "rate" });

    if (req.method === "GET") {
      const w = String(req.query.wallet || "").toLowerCase();
      if (!w) return res.status(200).json({ ok: true, start: START, now: Date.now(), open: Date.now() >= START,
        supply: SUPPLY, minted: await minted(), prices: PRICES, treasury: TREASURY });
      if (!/^0x[a-f0-9]{40}$/.test(w)) return res.status(400).json({ ok: false, error: "invalid" });
      return res.status(200).json(await status(w));
    }
    if (req.method === "POST") {
      let b = req.body;
      if (typeof b === "string") { try { b = JSON.parse(b); } catch { b = {}; } }
      return res.status(200).json(await confirm(String((b || {}).chain || ""), String((b || {}).tx || "")));
    }
    return res.status(405).json({ ok: false, error: "method" });
  } catch (e) {
    return res.status(500).json({ ok: false, error: "server", message: String(e.message || e).slice(0, 200) });
  }
};
module.exports._test = { toWei, priceTier, PRICES };

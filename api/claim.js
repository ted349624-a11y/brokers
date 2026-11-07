// $BROKER allocation: GET /api/claim?wallet=0x...  -> Broker NFTs held on HyperEVM x 500,000
const { redis } = require("./_db");
const NFT = "0xa84f624482246fa94a1d787ff36dcfbc5f1514a7";
const PER_NFT = 500000;
const RPC = process.env.RPC_HYPEREVM || "https://rpc.hyperliquid.xyz/evm";

async function eth(method, params) {
  const r = await fetch(RPC, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }) });
  const j = await r.json();
  if (j.error) throw new Error(j.error.message);
  return j.result;
}

module.exports = async (req, res) => {
  res.setHeader("Cache-Control", "no-store");
  const wallet = String(req.query.wallet || "").trim().toLowerCase();
  if (!/^0x[a-f0-9]{40}$/.test(wallet)) return res.status(400).json({ ok: false, error: "invalid" });
  try {
    const ip = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "unknown";
    const hits = await redis("INCR", `eb:cl:rl:${ip}`);
    if (hits === 1) await redis("EXPIRE", `eb:cl:rl:${ip}`, 60);
    if (hits > 30) return res.status(429).json({ ok: false, error: "rate" });

    const bal = await eth("eth_call", [{ to: NFT, data: "0x70a08231" + wallet.slice(2).padStart(64, "0") }, "latest"]);
    const held = Number(BigInt(bal || "0x0"));
    return res.status(200).json({ ok: true, wallet, held, perNft: PER_NFT, allocation: held * PER_NFT, contract: NFT, chain: "HyperEVM" });
  } catch (e) {
    return res.status(500).json({ ok: false, error: "rpc" });
  }
};

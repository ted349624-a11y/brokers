// Upstash Redis over REST (free tier, added from Vercel → Storage → Upstash for Redis).
// Works with either env var naming the integration creates.
// Finds the vars whatever prefix was chosen when connecting (KV_, STORAGE_, UPSTASH_REDIS_, …).
function pick(re) {
  const k = Object.keys(process.env).filter(n => re.test(n) && !/READ_ONLY/.test(n)).sort((a, b) => a.length - b.length)[0];
  return k ? process.env[k] : undefined;
}
const URL_ = pick(/(REST_API_URL|REDIS_REST_URL|REST_URL)$/);
const TOKEN = pick(/(REST_API_TOKEN|REDIS_REST_TOKEN|REST_TOKEN)$/);

async function redis(...cmd) {
  if (!URL_ || !TOKEN) throw new Error("db_not_configured");
  const r = await fetch(URL_, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify(cmd)
  });
  const j = await r.json();
  if (j.error) throw new Error(j.error);
  return j.result;
}
module.exports = { redis };

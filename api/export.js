// Download the whitelist: https://YOUR-SITE/api/export?key=ADMIN_KEY  (add &format=json for JSON)
const { redis } = require("./_db");

module.exports = async (req, res) => {
  const key = process.env.ADMIN_KEY;
  if (!key || req.query.key !== key) return res.status(401).send("Unauthorized");
  const rows = (await redis("LRANGE", "eb:wl:entries", 0, -1)).map(s => JSON.parse(s));
  if (req.query.format === "json") return res.status(200).json(rows);
  const csv = ["no,x_handle,wallet,tasks,time"]
    .concat(rows.map(r => [r.n, "@" + r.handle, r.wallet, `"${r.tasks}"`, r.ts].join(",")))
    .join("\n");
  res.setHeader("Content-Type", "text/csv; charset=utf-8");
  res.setHeader("Content-Disposition", 'attachment; filename="elysium-broker-whitelist.csv"');
  return res.status(200).send(csv);
};

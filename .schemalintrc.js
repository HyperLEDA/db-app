/** @type {import("schemalint").Config } */
module.exports = {
  connection: {
    host: process.env.PGHOST ?? "localhost",
    port: Number(process.env.PGPORT ?? 6432),
    user: process.env.PGUSER ?? "hyperleda",
    password: process.env.PGPASSWORD ?? "password",
    database: process.env.PGDATABASE ?? "hyperleda",
  },
  schemas: [
    { name: "common" },
    { name: "cz" },
    { name: "dataviews" },
    { name: "designation" },
    { name: "icrs" },
    { name: "layer0" },
    { name: "layer2" },
    { name: "meta" },
    { name: "nature" },
    { name: "note" },
    { name: "photometry" },
    { name: "private" },
    { name: "public" },
    { name: "rawdata" },
  ],
  rules: {
    "name-casing": ["error", "snake"],
    "prefer-text-to-varchar": ["error"],
  },
  ignores: [
    { identifierPattern: "public\\.schema_version.*", rulePattern: ".*" },
  ],
};

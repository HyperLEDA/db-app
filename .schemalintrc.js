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
  },
  ignores: [
    { identifierPattern: "public\\.schema_version.*", rulePattern: ".*" },
    { identifierPattern: "public\\.spatial_ref_sys.*", rulePattern: ".*" },
    { identifierPattern: "public\\.geography_columns.*", rulePattern: ".*" },
    { identifierPattern: "public\\.geometry_columns.*", rulePattern: ".*" },
    { identifierPattern: "public\\.raster_columns.*", rulePattern: ".*" },
    { identifierPattern: "public\\.raster_overviews.*", rulePattern: ".*" },
  ],
};

CREATE TYPE rawdata.status AS ENUM(
  'initiated', 
  'downloading', 
  'failed', 
  'downloaded', 
  'auto x-id', 
  'auto x-id finished', 
  'manual x-id', 
  'processed'
);

COMMENT ON TYPE rawdata.status IS '{
  "initiated": "Structure is initiated",
  "downloading": "Data is downloading",
  "failed": "Data downloading failed",
  "auto x-id": "Automatic cross-identification",
  "auto x-id finished": "Manual cross-identification is finished",
  "manual x-id": "Manual cross-identification",
  "processed": "Table is processed"
}';

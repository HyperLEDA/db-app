UPDATE layer0.records
SET modification_time = NOW()
WHERE modification_time IS NULL;

ALTER TABLE layer0.records
ALTER COLUMN modification_time SET DEFAULT NOW(),
ALTER COLUMN modification_time SET NOT NULL;

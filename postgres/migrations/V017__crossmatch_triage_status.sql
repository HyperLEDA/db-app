/* pgmigrate-encoding: utf-8 */

CREATE TYPE layer0.triage_status AS ENUM ('pending', 'resolved');

ALTER TABLE layer0.crossmatch
ADD COLUMN triage_status layer0.triage_status NOT NULL DEFAULT 'pending';

UPDATE layer0.crossmatch
SET triage_status = 'resolved'
WHERE status IN ('new', 'existing');

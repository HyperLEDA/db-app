/* pgmigrate-encoding: utf-8 */

CREATE INDEX ON layer0.crossmatch (triage_status, status);
CREATE INDEX ON layer0.crossmatch (status);

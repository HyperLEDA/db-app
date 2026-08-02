/* pgmigrate-encoding: utf-8 */
ALTER TABLE layer2.last_update ADD COLUMN catalog text;

UPDATE layer2.last_update SET catalog = 'all';

ALTER TABLE layer2.last_update ALTER COLUMN catalog SET NOT NULL;

ALTER TABLE layer2.last_update ADD PRIMARY KEY (catalog);

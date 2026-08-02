/* pgmigrate-encoding: utf-8 */

ALTER TABLE designation.data DROP CONSTRAINT data_pkey;

ALTER TABLE designation.data ADD PRIMARY KEY (record_id, design);

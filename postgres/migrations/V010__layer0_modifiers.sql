ALTER TABLE layer0.homogenization_rules DROP COLUMN enrichment;

CREATE TABLE layer0.column_modifiers (
	table_id integer REFERENCES rawdata.tables (id),
	column_name text,
	modifier_name text NOT NULL,
	params json,
	sequence integer,
	PRIMARY KEY (table_id, column_name, sequence)
);

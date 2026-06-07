/* pgmigrate-encoding: utf-8 */

CREATE TABLE designation.format_rules (
  id text PRIMARY KEY,
  priority int NOT NULL,
  pattern text NOT NULL,
  template text NOT NULL,
  transforms jsonb NOT NULL DEFAULT '{}',
  enabled boolean NOT NULL DEFAULT true,
  created_at timestamp without time zone NOT NULL DEFAULT NOW(),
  modification_time timestamp without time zone NOT NULL DEFAULT NOW()
);

CREATE INDEX format_rules_enabled_priority_idx ON designation.format_rules (enabled, priority);

COMMENT ON TABLE designation.format_rules IS 'Declarative rules for canonicalizing object designations';
COMMENT ON COLUMN designation.format_rules.id IS 'Stable free-text rule identifier';
COMMENT ON COLUMN designation.format_rules.priority IS 'First-match-wins ordering; lower values are tried first';
COMMENT ON COLUMN designation.format_rules.pattern IS 'Regex pattern (case-insensitive match applied at runtime)';
COMMENT ON COLUMN designation.format_rules.template IS 'Output template with {0}, {1}, ... placeholders for capture groups';
COMMENT ON COLUMN designation.format_rules.transforms IS 'Per-group transform ops, e.g. {"1": [{"op": "upper"}]}';

ALTER TABLE designation.data
  ADD COLUMN raw text,
  ADD COLUMN rule_id text REFERENCES designation.format_rules (id) ON DELETE SET NULL;

CREATE INDEX designation_data_rule_id_idx ON designation.data (rule_id);
CREATE INDEX designation_data_rule_id_null_idx ON designation.data (rule_id) WHERE rule_id IS NULL;

COMMENT ON COLUMN designation.data.raw IS '{"description": "Original designation before formatting", "ucd": "meta.id"}';
COMMENT ON COLUMN designation.data.rule_id IS '{"description": "ID of the format rule that produced design, if any"}';

INSERT INTO designation.format_rules (id, priority, pattern, template, transforms) VALUES
  ('pgc', 1, '^(?:LEDA|PGC|P|#)?\s*0*(\d+)$', 'PGC {0}', '{}'::jsonb),
  ('sdss', 2, '^SDSS\s*J(\d{6}\.\d{2}[+-]\d{6}\.\d)$', 'SDSS J{0}', '{}'::jsonb),
  ('2mass', 3, '^(2MAS[SX])\s*J\s*(\d{8}[+-]\d{7})$', '{0} J{1}', '{"1": [{"op": "upper"}]}'::jsonb),
  ('m', 4, '^M(?:ESSIER)?\s*0*(\d+)$', 'M {0}', '{}'::jsonb),
  ('ngc', 5, '^N(?:GC)?\s*0*(\d{1,4})\s*([A-Z]?)$', 'NGC {0}{1}', '{"1": [{"op": "strip_zeros"}], "2": [{"op": "upper"}]}'::jsonb),
  ('ic', 6, '^IC?\s*0*(\d{1,4})\s*([A-Z]?)$', 'IC {0}{1}', '{"1": [{"op": "strip_zeros"}], "2": [{"op": "upper"}]}'::jsonb),
  ('ugc', 7, '^U(?:GCG?)?\s*0*(\d{1,5})\s*([A-Z]?)$', 'UGC {0}{1}', '{"1": [{"op": "strip_zeros"}], "2": [{"op": "upper"}]}'::jsonb),
  ('ugca', 8, '^U(?:GC)?A\s*0*(\d{1,3})$', 'UGCA {0}', '{}'::jsonb),
  ('agc', 9, '^AGC\s*0*(\d+)$', 'AGC {0}', '{}'::jsonb),
  ('eso', 10, '^ESO\s*0*(\d+)-\s*G?\s*0*(\d+)([a-z]?)$', 'ESO {0}-{1}{2}', '{"3": [{"op": "upper"}]}'::jsonb),
  ('mcg', 11, '^MCG\s*([+-]?)(\d{1,2})-(\d{1,2})-(\d+)$', 'MCG {0}{1}-{2}-{3}', '{"1": [{"op": "default", "arg": "+"}], "2": [{"op": "zfill", "arg": "2"}], "3": [{"op": "zfill", "arg": "2"}], "4": [{"op": "zfill", "arg": "3"}]}'::jsonb),
  ('abell', 12, '^(?:ABELL?|ABGC|ACO)\s*S0*(\d+)$', 'ACO S {0}', '{}'::jsonb),
  ('abell-13', 13, '^(?:ABELL?|ABGC|ACO)\s*0*(\d+)$', 'ACO {0}', '{}'::jsonb),
  ('andromeda', 14, '^And(?:romeda)?\s*(\d+|[IVXLCDM]+)$', 'And {0}', '{"1": [{"op": "roman_or_int"}]}'::jsonb),
  ('cassiopeia', 15, '^Cas(?:siopeia)?\s*0*(\d+)$', 'Cas {0}', '{}'::jsonb),
  ('triangulum', 16, '^Tri(?:angulum)?\s*(\d+|[IVXLCDM]+)$', 'Tri {0}', '{"1": [{"op": "roman_or_int"}]}'::jsonb),
  ('eponym', 17, '^Arp\s*0*(\d{1,3})$', 'Arp {0}', '{}'::jsonb),
  ('eponym-18', 18, '^(?:Frl|Fair|Fairall)\s*0*(\d{1,4})$', 'Frl {0}', '{}'::jsonb),
  ('eponym-19', 19, '^(?:Mkn|Mrk|Markarian|Markarjan)\s*0*(\d{1,4})$', 'Mrk {0}', '{}'::jsonb),
  ('eponym-20', 20, '^(?:Ho|Holm|Holmberg)\s*(\d|[IVX]+)$', 'Holmberg {0}', '{"1": [{"op": "roman_or_int"}]}'::jsonb),
  ('eponym-21', 21, '^(Dwingeloo|Laevens|Maffei)\s*0*(\d)$', '{0} {1}', '{"1": [{"op": "capitalize"}]}'::jsonb),
  ('lsbg', 22, '^(?:LSBG|\[MDS99\])?\s*F([1-5]\d{2})-(\d{1,3})$', '[MDS99] F{0}-{1}', '{"2": [{"op": "zfill", "arg": "3"}]}'::jsonb),
  ('lsbg-23', 23, '^(?:LSBG|ISI96|\[ISI96\])\s*(\d{4}[+-]\d{4})([abx]?)$', '[ISI96] {0}{1}', '{"2": [{"op": "lower"}]}'::jsonb),
  ('ref-j', 24, '^\[([A-Z]{1,3}(?:[6-9]\d|20\d{2}))\]\s*J(\d{6}(?:\.\d+)?[+-]\d{6}(?:\.\d+)?)$', '[{0}] J{1}', '{"1": [{"op": "upper"}]}'::jsonb),
  ('ref-hhmm-ddmm', 25, '^\[([A-Z]{1,3}(?:[6-9]\d|20\d{2}))\]\s*(\d{4}[+-]\d{4})$', '[{0}] {1}', '{"1": [{"op": "upper"}]}'::jsonb),
  ('ref-n', 26, '^\[([A-Z]{1,3}(?:[6-9]\d|20\d{2}))\]\s*0*(\d+)\s*([a-z]?)$', '[{0}] {1}{2}', '{"1": [{"op": "upper"}], "3": [{"op": "lower"}]}'::jsonb),
  ('6df', 27, '^6dF\s*J\s*(\d{7}[+-]\d{6})\:?$', '6dF J{0}', '{}'::jsonb),
  ('usgc', 28, '^USGC\s*([US])\s*(\d+)$', 'USGC {0}{1}', '{"1": [{"op": "upper"}]}'::jsonb),
  ('3c', 29, '^3C\s*(\d+(?:\.\d)?)([a-z]?)$', '3C {0}{1}', '{"1": [{"op": "zfill", "arg": "3"}], "2": [{"op": "upper"}]}'::jsonb),
  ('dw', 30, '^Dw\s*J?(\d{4}[+-]\d{2,4})([ab]?)$', 'dwJ{0}{1}', '{"2": [{"op": "lower"}]}'::jsonb),
  ('cat-n', 31, '^([a-z0-9]{1,5}[a-z])\s*0*(\d+)([a-z]?)$', '{0} {1}{2}', '{"1": [{"op": "upper"}], "2": [{"op": "strip_zeros"}], "3": [{"op": "lower"}]}'::jsonb),
  ('cat-hhmmssss-ddmmsss', 32, '^([a-z0-9]{2,6}?)\s*([JB]?)\s*(\d{8}[+-]\d{7})$', '{0} {1}{2}', '{"1": [{"op": "upper"}], "2": [{"op": "upper"}]}'::jsonb),
  ('cat-hhmmss-ddmmss', 33, '^([a-z0-9]{2,6}?)\s*([JB]?)\s*(\d{7}[+-]\d{6})$', '{0} {1}{2}', '{"1": [{"op": "upper"}], "2": [{"op": "upper"}]}'::jsonb),
  ('cat-hhmmss-sss-ddmmss-sss', 34, '^([a-z0-9]{2,6}?)\s*([JB]?)\s*(\d{6}(?:\.\d+)?[+-]\d{6}(?:\.\d+)?)$', '{0} {1}{2}', '{"1": [{"op": "upper"}], "2": [{"op": "upper"}]}'::jsonb),
  ('cat-hhmm-ddmm', 35, '^([a-z0-9]{2,6}?)\s*([JB]?)\s*(\d{4}[+-]\d{4})$', '{0} {1}{2}', '{"1": [{"op": "upper"}], "2": [{"op": "upper"}]}'::jsonb),
  ('cat-hhmm-dd', 36, '^([a-z0-9]{2,6})\s*([JB]?)\s*(\d{4}[+-]\d{2,3})([a-z]?)$', '{0} {1}{2}{3}', '{"1": [{"op": "upper"}], "2": [{"op": "upper"}]}'::jsonb),
  ('cat-ddd-ddd-dd-ddd', 37, '^([a-z0-9]{2,6})\s*J\s*(\d{1,3}\.\d+[+-]\d{1,3}\.\d+)$', '{0} J{1}', '{"1": [{"op": "upper"}]}'::jsonb),
  ('cat-hhmmss-ddmms', 38, '^([a-z0-9]{2,6})\s*([JB]?)\s*(\d{6}[+-]\d{5})$', '{0} {1}{2}', '{"1": [{"op": "upper"}], "2": [{"op": "upper"}]}'::jsonb),
  ('cat-n-n-n', 39, '^([a-z]{2,6})\s*0*(\d{1,5})-0*(\d{1,5})-0*(\d{1,5})$', '{0} {1}-{2}-{3}', '{"1": [{"op": "upper"}], "2": [{"op": "strip_zeros"}], "3": [{"op": "strip_zeros"}], "4": [{"op": "strip_zeros"}]}'::jsonb),
  ('cgcg', 40, '^CGCG\s*(\d{3})-0*(\d{2,3})$', 'CGCG {0}-{1}', '{}'::jsonb),
  ('ksp-dw', 41, '^KSP-DW\s*0*(\d+)$', 'KSP-DW {0}', '{}'::jsonb),
  ('dr8', 42, '^DR8-(\d{4})([pm])(\d{3})-(\d{1,5})$', 'DR8-{0}{1}{2}-{3}', '{}'::jsonb),
  ('lsbc', 43, '^LSBC\s*D\s*0*(\d+)-0*(\d+)$', 'LSBC D{0}-{1}', '{}'::jsonb),
  ('cnoc2', 44, '^CNOC2_(\d+)\.(\d+)$', 'CNOC2_{0}.{1}', '{}'::jsonb),
  ('galfa', 45, '^GALFAJ(\d+(?:\.\d+)?)\+(\d+(?:\.\d+)?)\+(\d+)$', 'GALFA J{0}+{1}+{2}', '{}'::jsonb),
  ('rxj', 46, '^RXJ(\d{2})(\d{2}(?:\.\d+)?)([+-])(\d{2})(\d{2}(?:\.\d+)?):\[([^\]]+)\](\d+)$', 'RX J{0}{1}{2}{3}{4} [{5}] {6}', '{}'::jsonb),
  ('rxj-47', 47, '^RXJ(\d{2})(\d{2}(?:\.\d+)?)([+-])(\d{2})(\d{2}(?:\.\d+)?)$', 'RX J{0}{1}{2}{3}{4}', '{}'::jsonb),
  ('ngc-48', 48, '^NGC\s*0*(\d+)([a-zA-Z]{0,3}):\[([^\]]+)\](\d+)$', 'NGC {0}{1} [{2}] {3}', '{"1": [{"op": "strip_zeros"}]}'::jsonb),
  ('ngc-49', 49, '^N\s*0*(\d+)([a-zA-Z]{1,3})$', 'NGC {0}{1}', '{}'::jsonb),
  ('2dfgrs', 50, '^2dfgrs\s*([NS]\d+Z\d+)$', '2dFGRS {0}', '{}'::jsonb),
  ('j', 51, '^J\s*(\d{2})(\d{2})(\d{2}(?:\.\d+)?)([+-])(\d{2})(\d{2})(\d{2}(?:\.\d+)?)$', 'J{0}{1}{2}{3}{4}{5}{6}', '{}'::jsonb),
  ('cat-hhmmss', 52, '^([A-Za-z]{2,5})\s*([+-])(\d{6})$', '{0} {1}{2}', '{"1": [{"op": "upper"}]}'::jsonb),
  ('cat-dd-d', 53, '^((?:[A-Za-z][A-Za-z0-9]{1,4}|[0-9][A-Za-z][A-Za-z0-9]{0,3}|[0-9]{2}[A-Za-z][A-Za-z0-9]{0,2}|[0-9]{3}[A-Za-z][A-Za-z0-9]?))([+-])(\d{2}(?:\.\d+)?)$', '{0} {1}{2}', '{"1": [{"op": "upper"}]}'::jsonb),
  ('cgmw', 54, '^CGMW([1-5])-0*(\d{5})$', 'CGMW {0}-{1}', '{"2": [{"op": "strip_zeros"}]}'::jsonb),
  ('reformat', 55, '^.*?\[TKA2006\]\s*F\s*0*(\d)-\s*0*(\d{1,2})\s*([ab]?)$', '[TKA2006] F{0}-{1}{2}', '{"2": [{"op": "strip_zeros"}], "3": [{"op": "lower"}]}'::jsonb),
  ('reformat-56', 56, '^ABELL.*\[M(?:CF)?2008\]\s*0*(\d+)$', '[MCF2008] {0}', '{}'::jsonb),
  ('reformat-57', 57, '^ABELL.*\[([a-z]{1,3}(?:20\d\d|\d\d))\]\s*0*(\d+)$', '[{0}] {1}', '{"1": [{"op": "upper"}], "2": [{"op": "strip_zeros"}]}'::jsonb),
  ('abell-58', 58, '^ABELL\s*0*(\d+)_(\d+):\[([^\]]+)\](\d+)$', 'ABELL {0}_{1} [{2}] {3}', '{"1": [{"op": "strip_zeros"}], "2": [{"op": "strip_zeros"}]}'::jsonb);

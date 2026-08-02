CREATE TABLE private.runs (
  id                 text PRIMARY KEY,
  user_id            integer NOT NULL REFERENCES private.users(id) ON DELETE CASCADE,
  action_description text NOT NULL,
  created_at         timestamp without time zone NOT NULL DEFAULT now()
);

CREATE TABLE private.action_log (
  id         bigserial PRIMARY KEY,
  user_id    integer NOT NULL REFERENCES private.users(id) ON DELETE CASCADE,
  run_id     text REFERENCES private.runs(id) ON DELETE SET NULL,
  method     text NOT NULL,
  created_at timestamp without time zone NOT NULL DEFAULT now()
);

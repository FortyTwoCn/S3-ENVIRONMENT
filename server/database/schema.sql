BEGIN;
CREATE TABLE IF NOT EXISTS settings(id int PRIMARY KEY CHECK(id=1),value jsonb NOT NULL);
INSERT INTO settings VALUES(1,'{"retention_days":60,"mail_enabled":false,"mail_cooldown_s":900,"smtp":{"host":"","port":587,"encryption":"tls","username":"","password_enc":"","from_address":"","from_name":"传感器监测","recipients":[]}}') ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS devices(
 id uuid PRIMARY KEY,name varchar(80) NOT NULL,token_hash char(64) NOT NULL UNIQUE,
 enabled boolean NOT NULL DEFAULT true,config jsonb NOT NULL,config_version int NOT NULL DEFAULT 1,
 last_seen timestamptz,connected boolean NOT NULL DEFAULT false,firmware varchar(80),created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS samples(
 id bigserial PRIMARY KEY,device_id uuid NOT NULL REFERENCES devices ON DELETE CASCADE,
 boot_id varchar(32) NOT NULL,seq bigint NOT NULL CHECK(seq>=0),observed_at timestamptz NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now(),clock_quality varchar(16) NOT NULL,
 reason varchar(16) NOT NULL,data jsonb NOT NULL, UNIQUE(device_id,boot_id,seq));
CREATE INDEX IF NOT EXISTS samples_device_time ON samples(device_id,observed_at DESC,id DESC);
CREATE INDEX IF NOT EXISTS samples_retention ON samples(observed_at);
CREATE TABLE IF NOT EXISTS commands(
 id uuid PRIMARY KEY,device_id uuid NOT NULL REFERENCES devices ON DELETE CASCADE,type varchar(20) NOT NULL,
 state varchar(16) NOT NULL DEFAULT 'queued',created_at timestamptz NOT NULL DEFAULT now(),
 deadline timestamptz NOT NULL,result jsonb,sent_at timestamptz);
CREATE INDEX IF NOT EXISTS commands_dispatch ON commands(state,deadline);
CREATE TABLE IF NOT EXISTS remember_tokens(
 selector char(24) PRIMARY KEY,validator_hash char(64) NOT NULL,expires_at timestamptz NOT NULL);
CREATE TABLE IF NOT EXISTS ws_tickets(token_hash char(64) PRIMARY KEY,expires_at timestamptz NOT NULL,remember_selector char(24));
CREATE TABLE IF NOT EXISTS login_limits(ip_hash char(64) PRIMARY KEY,failures int NOT NULL DEFAULT 0,window_start timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS alert_state(
 device_id uuid PRIMARY KEY REFERENCES devices ON DELETE CASCADE,active boolean NOT NULL DEFAULT false,
 last_mail_at timestamptz,incident_id uuid,last_observed_at timestamptz);
ALTER TABLE alert_state ADD COLUMN IF NOT EXISTS last_observed_at timestamptz;
CREATE TABLE IF NOT EXISTS alerts(
 id uuid PRIMARY KEY,device_id uuid NOT NULL REFERENCES devices ON DELETE CASCADE,
 started_at timestamptz NOT NULL DEFAULT now(),ended_at timestamptz,sample_id bigint REFERENCES samples ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS mail_queue(
 id bigserial PRIMARY KEY,device_id uuid REFERENCES devices ON DELETE CASCADE,incident_id uuid REFERENCES alerts ON DELETE SET NULL,
 kind varchar(16) NOT NULL DEFAULT 'smoke',payload jsonb NOT NULL,state varchar(16) NOT NULL DEFAULT 'pending',
 attempts int NOT NULL DEFAULT 0,next_attempt timestamptz NOT NULL DEFAULT now(),created_at timestamptz NOT NULL DEFAULT now(),
 sent_at timestamptz,last_error text,claimed_at timestamptz);
CREATE INDEX IF NOT EXISTS mail_pending ON mail_queue(state,next_attempt);
COMMIT;

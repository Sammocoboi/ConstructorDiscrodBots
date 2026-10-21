CREATE TABLE IF NOT EXISTS bots (
    id uuid PRIMARY KEY,
    name text NOT NULL DEFAULT 'Bot',
    token_encrypted text NOT NULL DEFAULT '',
    desired_state text NOT NULL DEFAULT 'stopped',
    status text NOT NULL DEFAULT 'stopped',
    last_error text,
    config jsonb NOT NULL DEFAULT '{}'::jsonb,
    active_version_id uuid,
    deleted_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE bots ADD COLUMN IF NOT EXISTS config jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE bots ADD COLUMN IF NOT EXISTS active_version_id uuid;
ALTER TABLE bots ADD COLUMN IF NOT EXISTS deleted_at timestamptz;
ALTER TABLE bots ADD COLUMN IF NOT EXISTS last_error_at timestamptz;
ALTER TABLE bots ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE bots ADD COLUMN IF NOT EXISTS intents jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS bots_desired_state_idx ON bots (desired_state) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS bot_versions (
    id uuid PRIMARY KEY,
    bot_id uuid NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    number integer NOT NULL,
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'archived')),
    config jsonb NOT NULL,
    comment text NOT NULL DEFAULT '',
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (bot_id, number)
);

CREATE INDEX IF NOT EXISTS bot_versions_bot_idx ON bot_versions (bot_id, number DESC);

CREATE TABLE IF NOT EXISTS runtime_commands (
    id uuid PRIMARY KEY,
    bot_id uuid NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    command text NOT NULL CHECK (command IN ('start', 'stop', 'restart', 'reload')),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'acked', 'done', 'failed')),
    error text,
    requested_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    acked_at timestamptz,
    finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS runtime_commands_pending_idx
    ON runtime_commands (status, created_at);
CREATE INDEX IF NOT EXISTS runtime_commands_bot_idx
    ON runtime_commands (bot_id, created_at DESC);

CREATE OR REPLACE FUNCTION notify_runtime_command() RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('runtime_commands_channel', NEW.id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS runtime_commands_notify ON runtime_commands;
CREATE TRIGGER runtime_commands_notify
    AFTER INSERT ON runtime_commands
    FOR EACH ROW EXECUTE FUNCTION notify_runtime_command();

CREATE TABLE IF NOT EXISTS bot_runtime_state (
    bot_id uuid PRIMARY KEY REFERENCES bots(id) ON DELETE CASCADE,
    worker_id text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'stopped'
        CHECK (status IN ('stopped', 'starting', 'online', 'error', 'suspended')),
    latency_ms integer NOT NULL DEFAULT 0,
    uptime_seconds bigint NOT NULL DEFAULT 0,
    heartbeat_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    last_error text
);

CREATE INDEX IF NOT EXISTS bot_runtime_state_heartbeat_idx
    ON bot_runtime_state (heartbeat_at);

CREATE TABLE IF NOT EXISTS templates (
    id uuid PRIMARY KEY,
    owner_id text,
    slug text NOT NULL,
    title text NOT NULL,
    description text NOT NULL DEFAULT '',
    category text NOT NULL,
    version text NOT NULL DEFAULT '1.0.0',
    config jsonb NOT NULL,
    author text NOT NULL DEFAULT '',
    is_system boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS templates_owner_idx ON templates (owner_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS templates_owner_slug_idx
    ON templates (owner_id, slug) WHERE is_system = false;

CREATE TABLE IF NOT EXISTS flow_traces (
    id bigserial PRIMARY KEY,
    bot_id uuid REFERENCES bots(id) ON DELETE CASCADE,
    flow_id text NOT NULL,
    status text NOT NULL DEFAULT 'ok',
    trace jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS flow_traces_created_idx ON flow_traces (created_at);
CREATE INDEX IF NOT EXISTS flow_traces_bot_idx ON flow_traces (bot_id, created_at DESC);

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id uuid PRIMARY KEY,
    name text NOT NULL UNIQUE,
    cron text NOT NULL,
    handler text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    enabled boolean NOT NULL DEFAULT true,
    status text NOT NULL DEFAULT 'idle',
    last_run_at timestamptz,
    last_started_at timestamptz,
    next_run_at timestamptz,
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS scheduled_jobs_due_idx
    ON scheduled_jobs (next_run_at) WHERE enabled = true;

INSERT INTO scheduled_jobs (id, name, cron, handler, payload, next_run_at)
VALUES
    (gen_random_uuid(), 'cleanup-runtime-commands', '0 3 * * *',
     'cleanup_runtime_commands', '{"days": 14}'::jsonb, now()),
    (gen_random_uuid(), 'cleanup-flow-traces', '15 3 * * *',
     'cleanup_flow_traces', '{"days": 30}'::jsonb, now()),
    (gen_random_uuid(), 'reset-usage-counters', '0 0 1 * *',
     'reset_usage_counters', '{}'::jsonb, now())
ON CONFLICT (name) DO NOTHING;

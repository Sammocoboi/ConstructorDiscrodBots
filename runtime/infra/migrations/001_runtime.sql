-- Runtime-owned schema only.
--
-- Django owns bots_bot, bots_botversion, bots_botdraft, bots_runtimecommand,
-- bots_botruntimestate and templates_catalog_* and creates them with its own
-- migrations. This file must never create or alter those tables; it only adds
-- the two tables Runtime needs for its scheduler and flow traces plus a
-- notification trigger on the Django-owned command table.
--
-- Run order: Django `manage.py migrate` first, then this script.

CREATE TABLE IF NOT EXISTS runtime_scheduled_jobs (
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
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS runtime_scheduled_jobs_due_idx
    ON runtime_scheduled_jobs (next_run_at) WHERE enabled = true;

CREATE TABLE IF NOT EXISTS runtime_flow_traces (
    id bigserial PRIMARY KEY,
    bot_id uuid,
    flow_id text NOT NULL,
    status text NOT NULL DEFAULT 'ok',
    trace jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS runtime_flow_traces_created_idx
    ON runtime_flow_traces (created_at);
CREATE INDEX IF NOT EXISTS runtime_flow_traces_bot_idx
    ON runtime_flow_traces (bot_id, created_at DESC);

INSERT INTO runtime_scheduled_jobs (id, name, cron, handler, payload, next_run_at)
VALUES
    (gen_random_uuid(), 'cleanup-runtime-commands', '0 3 * * *',
     'cleanup_runtime_commands', '{"days": 14}'::jsonb, now()),
    (gen_random_uuid(), 'cleanup-flow-traces', '15 3 * * *',
     'cleanup_flow_traces', '{"days": 30}'::jsonb, now())
ON CONFLICT (name) DO NOTHING;

-- Older runtime installations seeded a no-op usage-counter job. Django's
-- UsageCounter is period-based and must not be reset by Runtime.
DELETE FROM runtime_scheduled_jobs WHERE name = 'reset-usage-counters';

-- The command table belongs to Django. Add a helpful pending index and a
-- LISTEN/NOTIFY trigger only when Django migrations have created it, so this
-- script can also run on a fresh database before Django migrate.
DO $$
BEGIN
    IF to_regclass('public.bots_runtimecommand') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS runtime_command_pending_idx
            ON bots_runtimecommand (created_at) WHERE status = 'pending';

        CREATE OR REPLACE FUNCTION runtime_notify_command() RETURNS trigger AS $fn$
        BEGIN
            PERFORM pg_notify('runtime_commands_channel', NEW.id::text);
            RETURN NEW;
        END;
        $fn$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS runtime_command_notify ON bots_runtimecommand;
        CREATE TRIGGER runtime_command_notify
            AFTER INSERT ON bots_runtimecommand
            FOR EACH ROW EXECUTE FUNCTION runtime_notify_command();
    END IF;
END;
$$;

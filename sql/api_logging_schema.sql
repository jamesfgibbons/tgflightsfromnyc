-- Generic API logging schema for prompt intake + job audit

create table if not exists api_results (
  id uuid primary key default gen_random_uuid(),
  source text,
  prompt_metadata jsonb,
  request_payload jsonb,
  response_data jsonb,
  status text,                 -- accepted|completed|failed
  error text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_api_results_created on api_results (created_at);
create index if not exists idx_api_results_status on api_results (status);

create table if not exists job_logs (
  id uuid primary key default gen_random_uuid(),
  job_id text,
  event text,
  details jsonb,
  level text default 'info',
  ts timestamptz not null default now()
);

create index if not exists idx_job_logs_job on job_logs (job_id);


-- Introspect schema: tables + columns + indexes (for Supabase Postgres)
\pset format unaligned
\pset tuples_only on
\echo '=== TABLES ==='
select table_schema||'.'||table_name from information_schema.tables 
where table_schema in ('public') and table_type='BASE TABLE' order by 1;

\echo '\n=== COLUMNS ==='
select table_schema||'.'||table_name||','||column_name||','||data_type||','||is_nullable||','||coalesce(column_default,'')
from information_schema.columns 
where table_schema in ('public') order by 1, ordinal_position;

\echo '\n=== INDEXES ==='
select schemaname||'.'||relname||','||indexrelname||','||pg_get_indexdef(indexrelid)
from pg_stat_all_indexes where schemaname='public' order by 1;


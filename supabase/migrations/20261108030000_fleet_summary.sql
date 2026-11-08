-- Fleet-wide totals for the dashboard on the latest real scoring day (runs with the caller's RLS).
create function fleet_summary(fid uuid, k int default 50)
returns jsonb language sql stable security invoker as $$
  with d as (
    select max(score_date) as day from drive_scores where fleet_id = fid and model_version <> 'seed'
  ), s as (
    select rank, risk, risk_7d, risk_90d from drive_scores
    where fleet_id = fid and score_date = (select day from d)
  )
  select jsonb_build_object(
    'day', (select day from d),
    'drives', (select count(*) from s),
    'expected_7d', (select sum(risk_7d) from s),
    'expected_30d', (select sum(risk) from s),
    'expected_90d', (select sum(risk_90d) from s),
    'expected_topk', (select sum(risk) from s where rank <= k),
    'tiers', jsonb_build_array(
      (select count(*) from s where risk >= 0.1),
      (select count(*) from s where risk >= 0.01 and risk < 0.1),
      (select count(*) from s where risk >= 0.001 and risk < 0.01),
      (select count(*) from s where risk < 0.001)),
    'alerts', (select count(*) from alerts where fleet_id = fid and score_date = (select day from d)),
    'entered', (select count(*) from alerts
                where fleet_id = fid and score_date = (select day from d) and kind = 'entered_top_k')
  )
$$;

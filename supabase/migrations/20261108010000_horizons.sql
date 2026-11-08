-- Calibrated chance of failing within 7 and 90 days (risk stays the 30-day chance and drives rank).
alter table drive_scores add column risk_7d real, add column risk_90d real;

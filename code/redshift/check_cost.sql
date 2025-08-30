-- Daily cost breakdown
-- Replace <RPU_PRICE> with your region's RPU price (e.g., $0.375 for US East).
SELECT
    trunc(start_time) "Day",
    (sum(charged_seconds)/3600::double precision) * <RPU_PRICE> as daily_cost,
    sum(charged_seconds) as total_charged_seconds,
    count(*) as number_of_queries
FROM sys_serverless_usage
GROUP BY 1
ORDER BY 1;

-- Individual query analyzing query
WITH daily_cost AS (
    SELECT
        trunc(start_time) "Day",
        max(compute_capacity) max_compute_capacity,
        (sum(charged_seconds) / 3600::double precision) * 0.375 as daily_cost
    FROM sys_serverless_usage
    GROUP BY 1
),
daily_queries AS (
    SELECT
        query_id,
        user_id,
        query_text,
        trunc(start_time) "Day",
        elapsed_time,
        elapsed_time / sum(elapsed_time) OVER (PARTITION BY trunc(start_time)) as perc
    FROM sys_query_history
)
SELECT
    q.*,
    c.daily_cost * q.perc as estimated_query_cost,
    c.daily_cost,
    c.max_compute_capacity
FROM daily_cost c
JOIN daily_queries q USING ("Day")
WHERE Day = '2025-08-28'  -- Replace with your date
ORDER BY estimated_query_cost DESC;

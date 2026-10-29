-- Cookie Cats A/B test: gate moved from level 30 (control) to level 40 (treatment).
-- Table `players(userid, version, sum_gamerounds, retention_1, retention_7)`. The retention columns are 0/1.

-- Q1. Arm sizes and headline retention metrics
SELECT
    version,
    COUNT(*)                          AS n_players,
    ROUND(AVG(retention_1), 5)        AS d1_retention,
    ROUND(AVG(retention_7), 5)        AS d7_retention,
    ROUND(AVG(sum_gamerounds), 3)     AS mean_rounds
FROM players
GROUP BY version
ORDER BY version;

-- Q2. Median rounds per arm (window functions; SQLite has no MEDIAN)
WITH ranked AS (
    SELECT
        version,
        sum_gamerounds,
        ROW_NUMBER() OVER (PARTITION BY version ORDER BY sum_gamerounds) AS rn,
        COUNT(*)     OVER (PARTITION BY version)                          AS cnt
    FROM players
)
SELECT version, AVG(sum_gamerounds) AS median_rounds
FROM ranked
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
GROUP BY version
ORDER BY version;

-- Q3. Retention funnel: share of each arm by (day-1, day-7) return pattern
SELECT
    version,
    retention_1,
    retention_7,
    COUNT(*)                                                           AS n_players,
    ROUND(1.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY version), 5) AS share_of_arm
FROM players
GROUP BY version, retention_1, retention_7
ORDER BY version, retention_1, retention_7;

-- Q4. Day-7 retention by engagement bucket (exploratory; buckets use a post-treatment variable)
SELECT
    version,
    CASE
        WHEN sum_gamerounds = 0   THEN '0'
        WHEN sum_gamerounds < 10  THEN '1-9'
        WHEN sum_gamerounds < 30  THEN '10-29'
        WHEN sum_gamerounds < 100 THEN '30-99'
        ELSE '100+'
    END                               AS rounds_bucket,
    COUNT(*)                          AS n_players,
    ROUND(AVG(retention_7), 5)        AS d7_retention
FROM players
GROUP BY version, rounds_bucket
ORDER BY rounds_bucket, version;

-- Q5. Data-quality checks
SELECT COUNT(*) AS rows, COUNT(DISTINCT userid) AS distinct_users,
       SUM(sum_gamerounds IS NULL OR version IS NULL) AS null_rows,
       MAX(sum_gamerounds) AS max_rounds
FROM players;

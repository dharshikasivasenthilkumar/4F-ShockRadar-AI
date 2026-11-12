SELECT VERSION() AS mysql_version;

CREATE DATABASE IF NOT EXISTS shockradar;
USE shockradar;
SELECT DATABASE() AS current_database;

USE shockradar;

-- create a table --
CREATE TABLE IF NOT EXISTS commodity_prices (
    observation_date DATE NOT NULL,
    commodity_name VARCHAR(100) NOT NULL,
    price DECIMAL(14, 4),
    unit VARCHAR(30),
    source VARCHAR(100),
    PRIMARY KEY (observation_date, commodity_name)
);

-- verify loading data --
DESCRIBE commodity_prices;
select count(*) as total_rows
from commodity_prices;

SELECT *
FROM commodity_prices
ORDER BY observation_date, commodity_name
LIMIT 10;

SELECT
    MIN(observation_date) AS first_date,
    MAX(observation_date) AS latest_date,
    COUNT(DISTINCT commodity_name) AS total_commodities
FROM commodity_prices;

-- find most recent prices --
SELECT
    observation_date,
    commodity_name,
    price
FROM commodity_prices
WHERE observation_date = (
    SELECT MAX(observation_date)
    FROM commodity_prices
)
ORDER BY commodity_name;

-- check data coverage by commodity --
SELECT
    commodity_name,
    COUNT(*) AS observations,
    MIN(observation_date) AS first_date,
    MAX(observation_date) AS latest_date
FROM commodity_prices
GROUP BY commodity_name
ORDER BY observations DESC;


-- calculate monthly price changes -- 
WITH monthly_changes AS (
    SELECT
        observation_date,
        commodity_name,
        price,
        LAG(price) OVER (
            PARTITION BY commodity_name
            ORDER BY observation_date
        ) AS previous_price
    FROM commodity_prices
)
SELECT
    observation_date,
    commodity_name,
    price,
    previous_price,
    ROUND(
        100.0 * (price - previous_price) / NULLIF(previous_price, 0),
        2
    ) AS monthly_change_pct
FROM monthly_changes
WHERE previous_price IS NOT NULL
ORDER BY observation_date DESC, commodity_name
LIMIT 30;


-- Find our selected indicators --
SELECT DISTINCT commodity_name
FROM commodity_prices
WHERE commodity_name LIKE '%Brent%'
   OR commodity_name LIKE '%Maize%'
   OR commodity_name LIKE '%Rice, Thai 5%'
   OR commodity_name LIKE '%Wheat, US HRW%'
   OR commodity_name LIKE '%Urea%'
   OR commodity_name LIKE '%DAP%'
ORDER BY commodity_name;

-- analyzing only the 6 selected indicators --

WITH selected_commodities AS (
    SELECT
        observation_date,
        commodity_name,
        price,
        LAG(price) OVER (
            PARTITION BY commodity_name
            ORDER BY observation_date
        ) AS previous_price
    FROM commodity_prices
    WHERE commodity_name IN (
        'Maize',
        'Rice, Thai 5%',
        'Wheat, US HRW',
        'Crude oil, Brent',
        'Urea',
        'DAP'
    )
)
SELECT
    observation_date,
    commodity_name,
    price,
    previous_price,
    ROUND(
        100.0 * (price - previous_price)
        / NULLIF(previous_price, 0),
        2
    ) AS price_change_pct
FROM selected_commodities
WHERE previous_price IS NOT NULL
ORDER BY observation_date DESC, commodity_name
LIMIT 50;


-- checking history of 6 indicators --

SELECT
    TRIM(commodity_name) AS commodity_name,
    COUNT(*) AS observations,
    MIN(observation_date) AS first_date,
    MAX(observation_date) AS latest_date
FROM shockradar.commodity_prices
WHERE LOWER(TRIM(commodity_name)) IN (
    'crude oil, brent',
    'dap',
    'maize',
    'rice, thai 5%',
    'urea',
    'wheat, us hrw'
)
GROUP BY TRIM(commodity_name)
ORDER BY commodity_name;

-- verify rice and urea --
SELECT
    commodity_name,
    COUNT(*) AS observations,
    MIN(observation_date) AS first_date,
    MAX(observation_date) AS latest_date
FROM commodity_prices
WHERE commodity_name LIKE '%Rice%'
   OR commodity_name LIKE '%Urea%'
GROUP BY commodity_name
ORDER BY commodity_name;


-- check for missing months --
WITH monthly_gaps AS (
    SELECT
        commodity_name,
        observation_date,
        LAG(observation_date) OVER (
            PARTITION BY commodity_name
            ORDER BY observation_date
        ) AS previous_date
    FROM commodity_prices
    WHERE commodity_name IN (
        'Maize',
        'Rice, Thai 5%',
        'Wheat, US HRW',
        'Crude oil, Brent',
        'Urea',
        'DAP'
    )
)
SELECT
    commodity_name,
    COUNT(*) AS gap_count
FROM monthly_gaps
WHERE previous_date IS NOT NULL
  AND observation_date <>
      DATE_ADD(previous_date, INTERVAL 1 MONTH)
GROUP BY commodity_name
ORDER BY commodity_name;


-- reusable sql view --
USE shockradar;

CREATE OR REPLACE VIEW v_commodity_monthly_changes AS
WITH price_history AS (
    SELECT
        observation_date,
        TRIM(commodity_name) AS commodity_name,
        price,
        LAG(price) OVER (
            PARTITION BY TRIM(commodity_name)
            ORDER BY observation_date
        ) AS previous_price
    FROM commodity_prices
    WHERE LOWER(TRIM(commodity_name)) IN (
        'crude oil, brent',
        'dap',
        'maize',
        'rice, thai 5%',
        'urea',
        'wheat, us hrw'
    )
)
SELECT
    observation_date,
    commodity_name,
    price,
    previous_price,
    ROUND(
        100.0 * (price - previous_price)
        / NULLIF(previous_price, 0),
        2
    ) AS monthly_change_pct
FROM price_history;

-- verifying view--

SELECT
    commodity_name,
    COUNT(*) AS observations
FROM v_commodity_monthly_changes
GROUP BY commodity_name
ORDER BY commodity_name;

SELECT *
FROM shockradar.v_commodity_monthly_changes
ORDER BY observation_date, commodity_name;


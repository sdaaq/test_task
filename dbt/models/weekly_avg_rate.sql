{{
  config(
    materialized='incremental',
    unique_key='start_of_week'
  )
}}

WITH weekly_data AS (
    SELECT
        toDate(date) - toDayOfWeek(date) + 2 AS start_of_week,  -- Начало недели со вторника
        currency AS from_currency,
        'USD' AS to_currency,
        to_usd AS rate
    FROM
        exchange_rates
    {% if is_incremental() %}
    WHERE
        toDate(date) - toDayOfWeek(date) + 2 > (SELECT MAX(start_of_week) FROM {{ this }})  -- Инкрементальная фильтрация
    {% endif %}
)
SELECT
    start_of_week,
    from_currency,
    to_currency,
    AVG(rate) AS rate
FROM
    weekly_data
GROUP BY
    start_of_week,
    from_currency,
    to_currency


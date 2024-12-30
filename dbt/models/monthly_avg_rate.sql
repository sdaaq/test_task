{{
  config(
    materialized='incremental',
    unique_key=['month', 'from_currency']
  )
}}

WITH monthly_data AS (
    SELECT
        monthName(date) AS month,
        'EUR' AS from_currency,
        'USD' AS to_currency,
        to_usd / to_eur AS rate
    FROM
        exchange_rates
    {% if is_incremental() %}
    WHERE
        toStartOfMonth(date) > (SELECT MAX(toStartOfMonth(month)) FROM {{ this }})
    {% endif %}
)
SELECT
    month,
    from_currency,
    to_currency,
    AVG(rate) AS rate
FROM
    monthly_data
GROUP BY
    month,
    from_currency,
    to_currency

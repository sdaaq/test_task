from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.python import ShortCircuitOperator
from airflow.utils.dates import days_ago
from airflow.operators.python import get_current_context
from airflow.exceptions import AirflowException, AirflowSkipException
from airflow_dbt.operators.dbt_operator import DbtRunOperator
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import clickhouse_connect

ECB_ENDPOINT = "http://www.cbr.ru/scripts/XML_daily.asp"
FIAT_CURRENCIES = ['JPY', 'BGN', 'CZK', 'DKK', 'GBP', 'HUF', 'PLN', 'RON', 'SEK', 'CHF', 'ISK', 'NOK', 'TRY', 'AUD', 'BRL', 'CAD', 'CNY', 'HKD', 'IDR', 'ILS', 'INR', 'KRW', 'MXN', 'MYR', 'NZD', 'PHP', 'SGD', 'THB', 'ZAR', 'USD', 'EUR']

def fetch_currency_rates(date):
    params = {"date_req": date.strftime("%d/%m/%Y")}
    try:
        response = requests.get(ECB_ENDPOINT, params=params)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        raise AirflowException(f"Failed to fetch currency rates: {e}")

def parse_currency_rates(xml_data):
    soup = BeautifulSoup(xml_data, 'xml')
    rates = {}
    for valute in soup.find_all("Valute"):
        code = valute.CharCode.text
        rate = valute.Value.text
        nominal = valute.Nominal.text
        if code in FIAT_CURRENCIES:
            rates[code] = float(rate.replace(",", ".")) / float(nominal.replace(",", "."))
    val_curs = datetime.strptime(soup.find("ValCurs")["Date"], "%d.%m.%Y").date()
    return rates, val_curs

def generate_exchange_pairs(rates, date):
    pairs = []
    if "USD" not in rates or "EUR" not in rates:
        raise ValueError("USD or EUR rate is missing from the data.")
    usd_to_rub = rates["USD"]
    eur_to_rub = rates["EUR"]
    for code, rate in rates.items():
        if code == "USD" or code == "EUR":
            continue
        x_to_usd = rate / usd_to_rub
        usd_to_x = 1 / x_to_usd
        x_to_eur = rate / eur_to_rub
        eur_to_x = 1 / x_to_eur
        pairs.append((date, code, x_to_usd, usd_to_x, x_to_eur, eur_to_x))
    return pairs

def fetch_and_parse_data():
    context = get_current_context()
    start = context["data_interval_start"]
    date_obj = start.date()
    try:
        xml_data = fetch_currency_rates(date_obj)
        rates, date_obj = parse_currency_rates(xml_data)
        return rates, date_obj
    except Exception as e:
        raise AirflowException(f"Error in fetch_and_parse_data: {e}")

def process_data_for_date():
    context = get_current_context()
    start = context["data_interval_start"]
    date_obj = start.date()
    date = date_obj.strftime('%Y-%m-%d')

    print('Execution Date:', start, 'Formatted Date:', date)

    # Подключение к ClickHouse
    try:
        client = clickhouse_connect.get_client(host='clickhouse-server', port=8123, username='default', password='')
    except Exception as e:
        raise AirflowException(f"Failed to connect to ClickHouse: {e}")

    # Проверка наличия данных за указанную дату
    result = 0
    if client.command("EXISTS TABLE exchange_rates"):
        result = client.command(f"SELECT COUNT(*) FROM exchange_rates WHERE date = '{date}'")
    if result > 0:
        raise AirflowSkipException(f"Данные за {date} уже существуют. Пропускаем вставку.")

    # Если данных нет, продолжаем обработку
    rates, date_obj = fetch_and_parse_data()
    clickhouse_data = generate_exchange_pairs(rates, date_obj)

    # Создание таблицы (если она еще не существует)
    client.command('''
    CREATE TABLE IF NOT EXISTS exchange_rates (
        date Date,
        currency String,
        to_usd Decimal(18, 6),
        from_usd Decimal(18, 6),
        to_eur Decimal(18, 6),
        from_eur Decimal(18, 6)
    ) ENGINE = MergeTree()
    ORDER BY date
    ''')

    # Вставка данных
    client.insert('exchange_rates', clickhouse_data)
    print(f"Данные за {date} успешно вставлены!")

def should_run_dbt():
    context = get_current_context()
    return not context["dag_run"].is_backfill

default_args = {
    'owner': 'airflow',
    'depends_on_past': True,
    'start_date': days_ago(1),
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    'daily_currency_exchange_rates_dag_test',
    default_args=default_args,
    description='A DAG to fetch and process currency exchange rates daily at 23:00',
    schedule_interval='0 23 * * *',  # Запуск каждый день в 23:00
    catchup=True,
)

fetch_and_parse_task = PythonOperator(
    task_id='fetch_and_parse_task',
    python_callable=fetch_and_parse_data,
    dag=dag,
)

process_task = PythonOperator(
    task_id='process_currency_rates_task',
    python_callable=process_data_for_date,
    dag=dag,
)

check_backfill_task = ShortCircuitOperator(
    task_id='check_backfill_task',
    python_callable=should_run_dbt,
    dag=dag,
)

dbt_run_task = DbtRunOperator(
    task_id='dbt_run_task',
    dir='/dbt',
    profiles_dir='/dbt',
    target='dev',
    dag=dag,
    full_refresh=True,
    pool='dbt_pool',
    trigger_rule='all_success',
)

fetch_and_parse_task >> process_task >> check_backfill_task >> dbt_run_task

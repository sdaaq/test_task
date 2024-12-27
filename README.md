# test_task
Тестовое задание
*DDL сырой таблицы находится в репозитории. Также приложен сам dag и файлы dbt.
* Даг выполняется каждый день в 23:00.
Можно сделать backfill за определенные даты или интервалы, но задача c DbtRunOperator пропускается в режиме backfill.
Она запускается в автомате по расписанию, либо если запустить даг в ручную.
* В примере делается backfill с 1 января по 1 декабря 2024 года.

* Скриншоты из веб интерфейса airflow:
![Screenshot from 2024-12-26 22-23-24](https://github.com/user-attachments/assets/eb11b9e3-e235-49a7-95ef-a83539c7c341)

* ![Screenshot from 2024-12-26 22-23-35](https://github.com/user-attachments/assets/1d854595-6d0f-4bba-9c92-fcfbe3821a1a)

* Скриншот с запуском dbt run:
* Вывод лога dbt run можно увидеть в выводе логов airflow:
![Screenshot from 2024-12-26 22-24-14](https://github.com/user-attachments/assets/9bb4bc5d-d692-4a36-9557-04e2015598f2)

* Скриншот из таблицы weekly_avg_rate:
![Screenshot from 2024-12-26 22-26-00](https://github.com/user-attachments/assets/e25d5a41-b8c5-44fc-a788-1335d4b6f754)


* Скриншот из таблицы monthly_avg_rate:
![Screenshot from 2024-12-26 22-27-25](https://github.com/user-attachments/assets/95210603-f62f-430b-8419-4a122fa8fd98)

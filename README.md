# Money Tracker
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Веб-приложение для учёта личного бюджета и расходов.

## Возможности

- Дашборд с общим балансом, доходами, расходами и процентом накоплений за месяц
- Учёт доходов, расходов и возвратов по категориям
- Настраиваемые категории с иконками и цветами (14 категорий по умолчанию)
- Регулярные (рекуррентные) платежи с ежемесячным подтверждением
- Аналитика: круговая диаграмма расходов, сравнение доходов/расходов за 6 месяцев, тренды за 12 месяцев
- Интеллектуальные рекомендации (рост расходов, накопления, топ-категории, фиксированные платежи)
- История по месяцам с итогами
- Светлая и тёмная тема

## Технологии

- Python / Flask
- SQLite / Flask-SQLAlchemy
- Bootstrap 5 / Bootstrap Icons
- Chart.js

## Установка

```bash
git clone https://github.com/<username>/money-tracker.git
cd money-tracker
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## Настройка

```bash
export SECRET_KEY=your-secret-key          # Linux/Mac
set SECRET_KEY=your-secret-key             # Windows
```

## Запуск

```bash
python app.py
```

Приложение будет доступно на http://localhost:5000

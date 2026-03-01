from database import db
from models import Entry, Category, RecurringExpense, RecurringConfirmation, format_kopecks
from sqlalchemy import func


def get_recommendations(year, month):
    """Генерирует список рекомендаций для указанного месяца."""
    recs = []

    # Данные текущего месяца
    income = _total(year, month, 'income')
    expense = _net_expense(year, month)
    balance = income - expense
    savings_pct = round((balance / income) * 100, 1) if income > 0 else 0

    # 1. Отрицательный баланс
    if balance < 0:
        recs.append({
            'type': 'warning',
            'title': 'Отрицательный баланс',
            'text': f'Расходы превышают доходы на {format_kopecks(abs(balance))}. '
                    f'Рекомендуется сократить необязательные траты.',
        })

    # 2. Скачок категории (>20% от среднего за 3 мес.)
    prev_months = _prev_months(year, month, 3)
    if prev_months:
        cat_avgs = _net_category_averages(prev_months)
        cur_cats = _net_category_totals(year, month)
        for cat_id, cur_val in cur_cats.items():
            avg_val = cat_avgs.get(cat_id, 0)
            if avg_val > 0 and cur_val > avg_val * 1.2:
                cat = db.session.get(Category, cat_id)
                if cat:
                    pct = round((cur_val - avg_val) / avg_val * 100)
                    recs.append({
                        'type': 'warning',
                        'title': f'Рост расходов: {cat.name}',
                        'text': f'Расходы в категории «{cat.name}» выросли на {pct}% '
                                f'по сравнению со средним за 3 месяца '
                                f'({format_kopecks(cur_val)} vs {format_kopecks(avg_val)}).',
                    })

    # 3. Крупнейшая категория
    cur_expense_cats = _net_category_totals(year, month)
    if cur_expense_cats and income > 0:
        max_cat_id = max(cur_expense_cats, key=cur_expense_cats.get)
        max_val = cur_expense_cats[max_cat_id]
        cat = db.session.get(Category, max_cat_id)
        if cat:
            pct_of_income = round(max_val / income * 100, 1)
            recs.append({
                'type': 'info',
                'title': f'Крупнейшая категория: {cat.name}',
                'text': f'Категория «{cat.name}» составляет {pct_of_income}% от дохода '
                        f'({format_kopecks(max_val)}).',
            })

    # 4. Топ-3 категории
    if cur_expense_cats and expense > 0:
        sorted_cats = sorted(cur_expense_cats.items(), key=lambda x: x[1], reverse=True)[:3]
        top3_total = sum(v for _, v in sorted_cats)
        pct = round(top3_total / expense * 100, 1)
        names = []
        for cid, val in sorted_cats:
            cat = db.session.get(Category, cid)
            if cat:
                names.append(f'{cat.name} ({format_kopecks(val)})')
        if names:
            recs.append({
                'type': 'info',
                'title': f'Топ-3 категории — {pct}% расходов',
                'text': ', '.join(names) + '.',
            })

    # 5. Процент накоплений
    if income > 0:
        if savings_pct < 0:
            level, tp = 'Отрицательные накопления', 'warning'
        elif savings_pct < 10:
            level, tp = 'Низкие накопления', 'warning'
        elif savings_pct < 20:
            level, tp = 'Умеренные накопления', 'info'
        else:
            level, tp = 'Хорошие накопления', 'success'
        recs.append({
            'type': tp,
            'title': level,
            'text': f'Вы сохраняете {savings_pct}% дохода ({format_kopecks(balance)}).',
        })

    # 6. Изменение общих расходов vs прошлый месяц
    py, pm = _prev_month(year, month)
    prev_expense = _net_expense(py, pm)
    if prev_expense > 0:
        change = expense - prev_expense
        change_pct = round(change / prev_expense * 100, 1)
        if change > 0:
            recs.append({
                'type': 'warning',
                'title': f'Расходы выросли на {change_pct}%',
                'text': f'В этом месяце расходы составили {format_kopecks(expense)} '
                        f'(+{format_kopecks(change)} к прошлому месяцу).',
            })
        elif change < 0:
            recs.append({
                'type': 'success',
                'title': f'Расходы снизились на {abs(change_pct)}%',
                'text': f'В этом месяце расходы составили {format_kopecks(expense)} '
                        f'({format_kopecks(change)} к прошлому месяцу).',
            })

    # 7. Доля фиксированных расходов
    if expense > 0:
        recurring_total = _recurring_total(year, month)
        if recurring_total > 0:
            pct = round(recurring_total / expense * 100, 1)
            recs.append({
                'type': 'info',
                'title': f'Фиксированные расходы — {pct}%',
                'text': f'Регулярные платежи составляют {format_kopecks(recurring_total)} '
                        f'из {format_kopecks(expense)} общих расходов.',
            })

    # 8. Пустые категории дохода
    empty_income = _empty_income_categories(year, month)
    if empty_income:
        names = ', '.join(empty_income)
        recs.append({
            'type': 'info',
            'title': 'Категории дохода без записей',
            'text': f'В этом месяце нет поступлений по: {names}.',
        })

    return recs


# ── Вспомогательные функции ──

def _total(year, month, entry_type):
    result = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.year == year, Entry.month == month, Entry.type == entry_type
    ).scalar()
    return result


def _net_expense(year, month):
    """Расход - возвраты за месяц."""
    exp = _total(year, month, 'expense')
    ref = _total(year, month, 'refund')
    return exp - ref


def _prev_month(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _prev_months(year, month, count):
    months = []
    y, m = year, month
    for _ in range(count):
        y, m = _prev_month(y, m)
        months.append((y, m))
    return months


def _category_totals(year, month, entry_type):
    rows = db.session.query(
        Entry.category_id, func.sum(Entry.amount)
    ).filter(
        Entry.year == year, Entry.month == month, Entry.type == entry_type
    ).group_by(Entry.category_id).all()
    return {cid: total for cid, total in rows}


def _net_category_totals(year, month):
    """Расходы по категориям с вычетом возвратов."""
    expenses = _category_totals(year, month, 'expense')
    refunds = _category_totals(year, month, 'refund')
    for cat_id, ref_amount in refunds.items():
        expenses[cat_id] = expenses.get(cat_id, 0) - ref_amount
    return expenses


def _net_category_averages(months_list):
    """Средние чистые расходы по категориям за несколько месяцев."""
    if not months_list:
        return {}
    totals = {}
    for y, m in months_list:
        net = _net_category_totals(y, m)
        for cat_id, val in net.items():
            totals[cat_id] = totals.get(cat_id, 0) + val
    n = len(months_list)
    return {cat_id: total // n for cat_id, total in totals.items()}


def _category_averages(months_list, entry_type):
    if not months_list:
        return {}
    from sqlalchemy import or_
    conditions = [db.and_(Entry.year == y, Entry.month == m) for y, m in months_list]
    rows = db.session.query(
        Entry.category_id, func.sum(Entry.amount)
    ).filter(
        Entry.type == entry_type,
        or_(*conditions)
    ).group_by(Entry.category_id).all()
    n = len(months_list)
    return {cid: total // n for cid, total in rows}


def _recurring_total(year, month):
    result = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.year == year, Entry.month == month, Entry.is_from_recurring == True
    ).scalar()
    return result


def _empty_income_categories(year, month):
    cats = Category.query.filter_by(type='income', is_active=True).all()
    empty = []
    for cat in cats:
        count = Entry.query.filter_by(
            year=year, month=month, type='income', category_id=cat.id
        ).count()
        if count == 0:
            empty.append(cat.name)
    return empty

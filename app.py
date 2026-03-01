import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from database import db, init_db
from models import Category, Entry, RecurringExpense, RecurringConfirmation, format_kopecks
from recommendations import get_recommendations
from sqlalchemy import func, case

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)


# ── Дефолтные категории ──

DEFAULT_CATEGORIES = [
    # Расходы
    {'name': 'Еда', 'type': 'expense', 'icon': 'bi-cart', 'color': '#e74c3c', 'sort_order': 1},
    {'name': 'Транспорт', 'type': 'expense', 'icon': 'bi-bus-front', 'color': '#3498db', 'sort_order': 2},
    {'name': 'Аренда', 'type': 'expense', 'icon': 'bi-house', 'color': '#9b59b6', 'sort_order': 3},
    {'name': 'ЖКХ', 'type': 'expense', 'icon': 'bi-lightning', 'color': '#f39c12', 'sort_order': 4},
    {'name': 'Связь', 'type': 'expense', 'icon': 'bi-phone', 'color': '#1abc9c', 'sort_order': 5},
    {'name': 'Здоровье', 'type': 'expense', 'icon': 'bi-heart-pulse', 'color': '#e91e63', 'sort_order': 6},
    {'name': 'Одежда', 'type': 'expense', 'icon': 'bi-bag', 'color': '#ff9800', 'sort_order': 7},
    {'name': 'Развлечения', 'type': 'expense', 'icon': 'bi-controller', 'color': '#00bcd4', 'sort_order': 8},
    {'name': 'Образование', 'type': 'expense', 'icon': 'bi-book', 'color': '#607d8b', 'sort_order': 9},
    {'name': 'Прочие расходы', 'type': 'expense', 'icon': 'bi-three-dots', 'color': '#95a5a6', 'sort_order': 10},
    # Доходы
    {'name': 'Зарплата', 'type': 'income', 'icon': 'bi-briefcase', 'color': '#27ae60', 'sort_order': 1},
    {'name': 'Подработка', 'type': 'income', 'icon': 'bi-cash-stack', 'color': '#2ecc71', 'sort_order': 2},
    {'name': 'Инвестиции', 'type': 'income', 'icon': 'bi-graph-up-arrow', 'color': '#16a085', 'sort_order': 3},
    {'name': 'Прочие доходы', 'type': 'income', 'icon': 'bi-plus-circle', 'color': '#8bc34a', 'sort_order': 4},
]


def seed_categories():
    if Category.query.count() == 0:
        for c in DEFAULT_CATEGORIES:
            db.session.add(Category(**c))
        db.session.commit()


with app.app_context():
    seed_categories()


# ── Утилиты ──

def current_year_month():
    now = datetime.now()
    return now.year, now.month


def get_ym():
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)
    return year, month


def prev_month(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def next_month(year, month):
    if month == 12:
        return year + 1, 1
    return year, month + 1


MONTH_NAMES = [
    '', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]


@app.context_processor
def inject_globals():
    year, month = get_ym()
    py, pm = prev_month(year, month)
    ny, nm = next_month(year, month)
    return {
        'current_year': year,
        'current_month': month,
        'month_name': MONTH_NAMES[month],
        'prev_year': py, 'prev_month': pm,
        'next_year': ny, 'next_month': nm,
        'month_names': MONTH_NAMES,
        'format_kopecks': format_kopecks,
    }


# ══════════════════════════════════════════════
# Страницы
# ══════════════════════════════════════════════

@app.route('/')
def dashboard():
    year, month = get_ym()
    return render_template('dashboard.html', year=year, month=month)


@app.route('/entries')
def entries_page():
    year, month = get_ym()
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    return render_template('entries.html', year=year, month=month, categories=[c.to_dict() for c in categories])


@app.route('/categories')
def categories_page():
    return render_template('categories.html')


@app.route('/history')
def history_page():
    return render_template('history.html')


@app.route('/recommendations')
def recommendations_page():
    year, month = get_ym()
    return render_template('recommendations.html', year=year, month=month)


# ══════════════════════════════════════════════
# API — Категории
# ══════════════════════════════════════════════

@app.route('/api/categories', methods=['GET'])
def api_get_categories():
    cats = Category.query.order_by(Category.type, Category.sort_order).all()
    return jsonify([c.to_dict() for c in cats])


@app.route('/api/categories', methods=['POST'])
def api_create_category():
    data = request.get_json()
    cat = Category(
        name=data['name'],
        type=data['type'],
        icon=data.get('icon', ''),
        color=data.get('color', '#6c757d'),
        sort_order=data.get('sort_order', 0),
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201


@app.route('/api/categories/<int:cat_id>', methods=['PUT'])
def api_update_category(cat_id):
    cat = db.session.get(Category, cat_id)
    if not cat:
        return jsonify({'error': 'Не найдено'}), 404
    data = request.get_json()
    for field in ('name', 'type', 'icon', 'color', 'sort_order', 'is_active'):
        if field in data:
            setattr(cat, field, data[field])
    db.session.commit()
    return jsonify(cat.to_dict())


@app.route('/api/categories/<int:cat_id>', methods=['DELETE'])
def api_delete_category(cat_id):
    cat = db.session.get(Category, cat_id)
    if not cat:
        return jsonify({'error': 'Не найдено'}), 404
    # Мягкое удаление — деактивируем
    cat.is_active = False
    db.session.commit()
    return jsonify({'ok': True})


# ══════════════════════════════════════════════
# API — Записи
# ══════════════════════════════════════════════

@app.route('/api/entries', methods=['GET'])
def api_get_entries():
    year, month = get_ym()
    entries = Entry.query.filter_by(year=year, month=month)\
        .order_by(Entry.day.desc(), Entry.created_at.desc()).all()
    return jsonify([e.to_dict() for e in entries])


@app.route('/api/entries', methods=['POST'])
def api_create_entry():
    data = request.get_json()
    amount = int(round(float(data['amount']) * 100))
    entry = Entry(
        year=data['year'],
        month=data['month'],
        day=data.get('day'),
        category_id=data['category_id'],
        amount=amount,
        type=data['type'],
        description=data.get('description', ''),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@app.route('/api/entries/<int:entry_id>', methods=['PUT'])
def api_update_entry(entry_id):
    entry = db.session.get(Entry, entry_id)
    if not entry:
        return jsonify({'error': 'Не найдено'}), 404
    data = request.get_json()
    if 'amount' in data:
        entry.amount = int(round(float(data['amount']) * 100))
    for field in ('year', 'month', 'day', 'category_id', 'type', 'description'):
        if field in data:
            setattr(entry, field, data[field])
    db.session.commit()
    return jsonify(entry.to_dict())


@app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
def api_delete_entry(entry_id):
    entry = db.session.get(Entry, entry_id)
    if not entry:
        return jsonify({'error': 'Не найдено'}), 404
    # Если это запись от рекуррентного — снять подтверждение
    if entry.is_from_recurring and entry.recurring_id:
        conf = RecurringConfirmation.query.filter_by(
            entry_id=entry.id
        ).first()
        if conf:
            conf.is_confirmed = False
            conf.entry_id = None
            conf.confirmed_at = None
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'ok': True})


# ══════════════════════════════════════════════
# API — Регулярные платежи
# ══════════════════════════════════════════════

@app.route('/api/recurring', methods=['GET'])
def api_get_recurring():
    items = RecurringExpense.query.filter_by(is_active=True).order_by(RecurringExpense.name).all()
    year, month = get_ym()
    result = []
    for r in items:
        d = r.to_dict()
        conf = RecurringConfirmation.query.filter_by(
            recurring_id=r.id, year=year, month=month
        ).first()
        d['is_confirmed'] = conf.is_confirmed if conf else False
        d['actual_amount'] = conf.actual_amount if conf else None
        d['confirmation_id'] = conf.id if conf else None
        d['entry_id'] = conf.entry_id if conf else None
        result.append(d)
    return jsonify(result)


@app.route('/api/recurring', methods=['POST'])
def api_create_recurring():
    data = request.get_json()
    amount = int(round(float(data['amount']) * 100))
    r = RecurringExpense(
        name=data['name'],
        category_id=data['category_id'],
        amount=amount,
        type=data.get('type', 'expense'),
        due_day=data.get('due_day'),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict()), 201


@app.route('/api/recurring/<int:rid>', methods=['PUT'])
def api_update_recurring(rid):
    r = db.session.get(RecurringExpense, rid)
    if not r:
        return jsonify({'error': 'Не найдено'}), 404
    data = request.get_json()
    if 'amount' in data:
        r.amount = int(round(float(data['amount']) * 100))
    for field in ('name', 'category_id', 'type', 'is_active', 'due_day'):
        if field in data:
            setattr(r, field, data[field])
    db.session.commit()
    return jsonify(r.to_dict())


@app.route('/api/recurring/<int:rid>', methods=['DELETE'])
def api_delete_recurring(rid):
    r = db.session.get(RecurringExpense, rid)
    if not r:
        return jsonify({'error': 'Не найдено'}), 404
    r.is_active = False
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/recurring/confirm', methods=['POST'])
def api_confirm_recurring():
    data = request.get_json()
    recurring_id = data['recurring_id']
    year = data['year']
    month = data['month']
    confirm = data.get('confirm', True)
    actual_amount = data.get('actual_amount')  # в рублях, опционально

    r = db.session.get(RecurringExpense, recurring_id)
    if not r:
        return jsonify({'error': 'Не найдено'}), 404

    conf = RecurringConfirmation.query.filter_by(
        recurring_id=recurring_id, year=year, month=month
    ).first()

    if confirm:
        amount_kopecks = int(round(float(actual_amount) * 100)) if actual_amount else r.amount
        # Создаём запись
        entry = Entry(
            year=year, month=month, day=None,
            category_id=r.category_id,
            amount=amount_kopecks,
            type=r.type,
            description=f'Регулярный: {r.name}',
            is_from_recurring=True,
            recurring_id=r.id,
        )
        db.session.add(entry)
        db.session.flush()

        if not conf:
            conf = RecurringConfirmation(
                recurring_id=recurring_id, year=year, month=month
            )
            db.session.add(conf)
        conf.is_confirmed = True
        conf.actual_amount = amount_kopecks if actual_amount else None
        conf.entry_id = entry.id
        conf.confirmed_at = datetime.now(timezone.utc)
    else:
        # Снимаем подтверждение
        if conf and conf.entry_id:
            entry = db.session.get(Entry, conf.entry_id)
            if entry:
                db.session.delete(entry)
        if conf:
            conf.is_confirmed = False
            conf.entry_id = None
            conf.confirmed_at = None

    db.session.commit()
    return jsonify({'ok': True})


# ══════════════════════════════════════════════
# API — Графики
# ══════════════════════════════════════════════

@app.route('/api/charts/category-breakdown')
def api_chart_category_breakdown():
    year, month = get_ym()
    # Факт — уже потраченное (с учётом возвратов)
    rows = db.session.query(
        Category.id, Category.name, Category.color,
        func.sum(case(
            (Entry.type == 'expense', Entry.amount),
            (Entry.type == 'refund', -Entry.amount),
            else_=0
        )).label('net')
    ).join(Entry).filter(
        Entry.year == year, Entry.month == month, Entry.type.in_(['expense', 'refund'])
    ).group_by(Category.id).order_by(db.text('net DESC')).all()

    fact = {r[0]: {'name': r[1], 'color': r[2], 'amount': r[3]} for r in rows}

    # Запланированное — неподтверждённые регулярные расходы
    planned = {}
    recurring_items = RecurringExpense.query.filter_by(is_active=True, type='expense').all()
    for r in recurring_items:
        conf = RecurringConfirmation.query.filter_by(
            recurring_id=r.id, year=year, month=month, is_confirmed=True
        ).first()
        if not conf:
            cat_id = r.category_id
            if cat_id not in planned:
                planned[cat_id] = 0
            planned[cat_id] += r.amount

    # Собираем все категории (факт + план)
    all_cat_ids = set(fact.keys()) | set(planned.keys())
    labels = []
    colors = []
    data_fact = []
    data_planned = []
    for cid in all_cat_ids:
        if cid in fact:
            labels.append(fact[cid]['name'])
            colors.append(fact[cid]['color'])
            data_fact.append(fact[cid]['amount'] / 100)
        else:
            cat = db.session.get(Category, cid)
            labels.append(cat.name if cat else '?')
            colors.append(cat.color if cat else '#999')
            data_fact.append(0)
        data_planned.append(planned.get(cid, 0) / 100)

    return jsonify({
        'labels': labels,
        'colors': colors,
        'data': data_fact,
        'planned': data_planned,
    })


@app.route('/api/charts/monthly-comparison')
def api_chart_monthly_comparison():
    year, month = get_ym()
    months = []
    y, m = year, month
    for _ in range(6):
        months.insert(0, (y, m))
        y, m = prev_month(y, m)

    labels = []
    incomes = []
    expenses = []
    for y, m in months:
        labels.append(f'{MONTH_NAMES[m]} {y}')
        inc = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
            Entry.year == y, Entry.month == m, Entry.type == 'income').scalar()
        exp = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
            Entry.year == y, Entry.month == m, Entry.type == 'expense').scalar()
        ref = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
            Entry.year == y, Entry.month == m, Entry.type == 'refund').scalar()
        incomes.append(inc / 100)
        expenses.append((exp - ref) / 100)

    return jsonify({'labels': labels, 'incomes': incomes, 'expenses': expenses})


@app.route('/api/charts/trends')
def api_chart_trends():
    year, month = get_ym()
    months = []
    y, m = year, month
    for _ in range(12):
        months.insert(0, (y, m))
        y, m = prev_month(y, m)

    labels = []
    incomes = []
    expenses = []
    balances = []
    for y, m in months:
        labels.append(f'{MONTH_NAMES[m][:3]} {y}')
        inc = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
            Entry.year == y, Entry.month == m, Entry.type == 'income').scalar()
        exp = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
            Entry.year == y, Entry.month == m, Entry.type == 'expense').scalar()
        ref = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
            Entry.year == y, Entry.month == m, Entry.type == 'refund').scalar()
        net_exp = exp - ref
        incomes.append(inc / 100)
        expenses.append(net_exp / 100)
        balances.append((inc - net_exp) / 100)

    return jsonify({'labels': labels, 'incomes': incomes, 'expenses': expenses, 'balances': balances})


@app.route('/api/charts/income-vs-expense')
def api_chart_income_vs_expense():
    year, month = get_ym()
    inc = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.year == year, Entry.month == month, Entry.type == 'income').scalar()
    exp = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.year == year, Entry.month == month, Entry.type == 'expense').scalar()
    ref = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.year == year, Entry.month == month, Entry.type == 'refund').scalar()
    net_exp = exp - ref
    return jsonify({'income': inc / 100, 'expense': net_exp / 100, 'balance': (inc - net_exp) / 100})


# ══════════════════════════════════════════════
# API — Рекомендации
# ══════════════════════════════════════════════

@app.route('/api/recommendations')
def api_recommendations():
    year, month = get_ym()
    recs = get_recommendations(year, month)
    return jsonify(recs)


# ══════════════════════════════════════════════
# API — Сводка для дашборда
# ══════════════════════════════════════════════

@app.route('/api/dashboard-summary')
def api_dashboard_summary():
    year, month = get_ym()
    # Доход/расход за ТЕКУЩИЙ месяц
    month_inc = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.year == year, Entry.month == month, Entry.type == 'income').scalar()
    month_exp_gross = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.year == year, Entry.month == month, Entry.type == 'expense').scalar()
    month_refund = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.year == year, Entry.month == month, Entry.type == 'refund').scalar()
    month_exp = month_exp_gross - month_refund
    month_balance = month_inc - month_exp
    savings_pct = round((month_balance / month_inc) * 100, 1) if month_inc > 0 else 0

    # Накопительный баланс за ВСЁ ВРЕМЯ (как в банке)
    total_inc = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.type == 'income').scalar()
    total_exp_gross = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.type == 'expense').scalar()
    total_refund = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
        Entry.type == 'refund').scalar()
    total_exp = total_exp_gross - total_refund
    total_balance = total_inc - total_exp

    # Неподтверждённые регулярные платежи за этот месяц
    recurring_items = RecurringExpense.query.filter_by(is_active=True).all()
    pending_recurring = []
    pending_recurring_total = 0
    for r in recurring_items:
        conf = RecurringConfirmation.query.filter_by(
            recurring_id=r.id, year=year, month=month, is_confirmed=True
        ).first()
        if not conf:
            pending_recurring.append({
                'id': r.id,
                'name': r.name,
                'amount': r.amount,
                'amount_display': format_kopecks(r.amount),
                'due_day': r.due_day,
                'category_name': r.category.name if r.category else '',
            })
            pending_recurring_total += r.amount

    # Топ-5 категорий расходов (с учётом возвратов)
    top5 = db.session.query(
        Category.name, Category.color,
        func.sum(case(
            (Entry.type == 'expense', Entry.amount),
            (Entry.type == 'refund', -Entry.amount),
            else_=0
        )).label('net')
    ).join(Entry).filter(
        Entry.year == year, Entry.month == month, Entry.type.in_(['expense', 'refund'])
    ).group_by(Category.id).order_by(db.text('net DESC')).limit(5).all()

    return jsonify({
        'month_income': month_inc,
        'month_expense': month_exp,
        'month_balance': month_balance,
        'savings_pct': savings_pct,
        'month_income_display': format_kopecks(month_inc),
        'month_expense_display': format_kopecks(month_exp),
        'month_balance_display': format_kopecks(month_balance),
        'total_balance': total_balance,
        'total_balance_display': format_kopecks(total_balance),
        'pending_recurring': pending_recurring,
        'pending_recurring_total': pending_recurring_total,
        'pending_recurring_total_display': format_kopecks(pending_recurring_total),
        'top5': [{'name': r[0], 'color': r[1], 'amount': r[2], 'display': format_kopecks(r[2])} for r in top5],
    })


# ══════════════════════════════════════════════
# API — История
# ══════════════════════════════════════════════

@app.route('/api/history')
def api_history():
    # Найти все уникальные (year, month) с записями
    months_q = db.session.query(
        Entry.year, Entry.month
    ).group_by(Entry.year, Entry.month).order_by(Entry.year.desc(), Entry.month.desc()).all()

    result = []
    for y, m in months_q:
        inc = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
            Entry.year == y, Entry.month == m, Entry.type == 'income').scalar()
        exp = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
            Entry.year == y, Entry.month == m, Entry.type == 'expense').scalar()
        ref = db.session.query(func.coalesce(func.sum(Entry.amount), 0)).filter(
            Entry.year == y, Entry.month == m, Entry.type == 'refund').scalar()
        exp = exp - ref
        balance = inc - exp
        savings_pct = round((balance / inc) * 100, 1) if inc > 0 else 0
        result.append({
            'year': y, 'month': m,
            'month_name': f'{MONTH_NAMES[m]} {y}',
            'income': inc, 'expense': exp, 'balance': balance,
            'income_display': format_kopecks(inc),
            'expense_display': format_kopecks(exp),
            'balance_display': format_kopecks(balance),
            'savings_pct': savings_pct,
        })
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

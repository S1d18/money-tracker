from datetime import datetime, timezone
from database import db


class Category(db.Model):
    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' / 'expense' (categories)
    icon = db.Column(db.String(50), default='')
    color = db.Column(db.String(7), default='#6c757d')
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    entries = db.relationship('Entry', backref='category', lazy='dynamic')
    recurring_expenses = db.relationship('RecurringExpense', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'icon': self.icon,
            'color': self.color,
            'sort_order': self.sort_order,
            'is_active': self.is_active,
        }


class Entry(db.Model):
    __tablename__ = 'entry'
    __table_args__ = (
        db.Index('ix_entry_year_month_type', 'year', 'month', 'type'),
    )

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # в копейках
    type = db.Column(db.String(10), nullable=False)  # 'income' / 'expense' / 'refund'
    description = db.Column(db.String(255), default='')
    is_from_recurring = db.Column(db.Boolean, default=False)
    recurring_id = db.Column(db.Integer, db.ForeignKey('recurring_expense.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'year': self.year,
            'month': self.month,
            'day': self.day,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else '',
            'category_color': self.category.color if self.category else '#6c757d',
            'amount': self.amount,
            'amount_display': format_kopecks(self.amount),
            'type': self.type,
            'description': self.description,
            'is_from_recurring': self.is_from_recurring,
            'recurring_id': self.recurring_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class RecurringExpense(db.Model):
    __tablename__ = 'recurring_expense'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # в копейках
    type = db.Column(db.String(10), nullable=False, default='expense')
    due_day = db.Column(db.Integer, nullable=True)  # день месяца списания (1-31)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    confirmations = db.relationship('RecurringConfirmation', backref='recurring', lazy='dynamic')
    entries = db.relationship('Entry', backref='recurring_source', lazy='dynamic',
                              foreign_keys='Entry.recurring_id')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else '',
            'amount': self.amount,
            'amount_display': format_kopecks(self.amount),
            'type': self.type,
            'due_day': self.due_day,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class RecurringConfirmation(db.Model):
    __tablename__ = 'recurring_confirmation'
    __table_args__ = (
        db.UniqueConstraint('recurring_id', 'year', 'month', name='uq_recurring_year_month'),
    )

    id = db.Column(db.Integer, primary_key=True)
    recurring_id = db.Column(db.Integer, db.ForeignKey('recurring_expense.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    is_confirmed = db.Column(db.Boolean, default=False)
    actual_amount = db.Column(db.Integer, nullable=True)  # если отличается
    entry_id = db.Column(db.Integer, db.ForeignKey('entry.id'), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    entry = db.relationship('Entry', foreign_keys=[entry_id])

    def to_dict(self):
        return {
            'id': self.id,
            'recurring_id': self.recurring_id,
            'year': self.year,
            'month': self.month,
            'is_confirmed': self.is_confirmed,
            'actual_amount': self.actual_amount,
            'entry_id': self.entry_id,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
        }


def format_kopecks(kopecks):
    """Форматирует копейки в строку вида '1 234,56 ₽'."""
    negative = kopecks < 0
    kopecks = abs(kopecks)
    rubles = kopecks // 100
    kop = kopecks % 100
    rubles_str = f'{rubles:,}'.replace(',', ' ')
    result = f'{rubles_str},{kop:02d} \u20bd'
    if negative:
        result = f'-{result}'
    return result

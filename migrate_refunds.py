"""Миграция: конвертировать записи "Возврат от Мам" из income в refund.

Записи id=14 и id=17 — это возвраты за продукты, привязываем к категории Еда (id=1).
Запустить один раз: python migrate_refunds.py
"""
from app import app
from database import db
from models import Entry

REFUND_ENTRIES = [14, 17]
FOOD_CATEGORY_ID = 1  # Еда


def migrate():
    with app.app_context():
        for entry_id in REFUND_ENTRIES:
            entry = db.session.get(Entry, entry_id)
            if not entry:
                print(f'  Запись id={entry_id} не найдена, пропуск')
                continue
            old_type = entry.type
            old_cat = entry.category_id
            entry.type = 'refund'
            entry.category_id = FOOD_CATEGORY_ID
            print(f'  id={entry_id}: type {old_type}->{entry.type}, '
                  f'category {old_cat}->{entry.category_id} '
                  f'({entry.description})')
        db.session.commit()
        print('Миграция завершена.')


if __name__ == '__main__':
    migrate()

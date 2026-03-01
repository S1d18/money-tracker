/* recurring.js — Управление регулярными платежами */

document.addEventListener('DOMContentLoaded', () => {
    loadRecurring();
    document.getElementById('rec-save').addEventListener('click', saveRecurring);
    document.getElementById('rec-type').addEventListener('change', () => {
        const type = document.getElementById('rec-type').value;
        const catType = type === 'refund' ? 'expense' : type;
        fillSelect('rec-category', ALL_CATEGORIES, catType);
    });
});

function loadRecurring() {
    fetch(`/api/recurring?year=${YEAR}&month=${MONTH}`)
        .then(r => r.json())
        .then(items => {
            const tbody = document.getElementById('recurring-body');
            if (!items.length) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Нет регулярных платежей</td></tr>';
                return;
            }
            tbody.innerHTML = items.map(r => `
                <tr class="${r.is_confirmed ? 'recurring-confirmed' : ''} ${!r.is_confirmed ? 'table-warning' : ''}">
                    <td class="text-center">
                        <input type="checkbox" class="form-check-input recurring-check"
                               data-id="${r.id}" data-amount="${r.amount / 100}"
                               ${r.is_confirmed ? 'checked' : ''}
                               onchange="toggleRecurring(this)">
                    </td>
                    <td>
                        ${r.name}
                        ${!r.is_confirmed ? '<span class="badge bg-warning text-dark ms-1">Не оплачено</span>' : ''}
                    </td>
                    <td>${r.category_name}</td>
                    <td class="text-end">${r.due_day ? r.due_day + '-го' : '—'}</td>
                    <td class="text-end">${r.amount_display}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteRecurring(${r.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        });
}

function toggleRecurring(checkbox) {
    const recurringId = parseInt(checkbox.dataset.id);
    const isConfirm = checkbox.checked;
    const amount = parseFloat(checkbox.dataset.amount);

    let actualAmount = null;
    if (isConfirm) {
        const input = prompt('Сумма (\u20bd), оставьте пустым для суммы по умолчанию:', amount.toFixed(2));
        if (input === null) {
            checkbox.checked = !isConfirm;
            return;
        }
        if (input.trim() !== '' && input.trim() !== amount.toFixed(2)) {
            actualAmount = parseFloat(input);
        }
    }

    fetch('/api/recurring/confirm', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            recurring_id: recurringId,
            year: YEAR,
            month: MONTH,
            confirm: isConfirm,
            actual_amount: actualAmount,
        }),
    }).then(r => {
        if (r.ok) {
            loadRecurring();
            if (typeof loadEntries === 'function') loadEntries();
        }
    });
}

function saveRecurring() {
    const data = {
        name: document.getElementById('rec-name').value,
        type: document.getElementById('rec-type').value,
        category_id: parseInt(document.getElementById('rec-category').value),
        amount: parseFloat(document.getElementById('rec-amount').value),
        due_day: document.getElementById('rec-due-day').value ? parseInt(document.getElementById('rec-due-day').value) : null,
    };
    fetch('/api/recurring', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    }).then(r => {
        if (r.ok) {
            bootstrap.Modal.getInstance(document.getElementById('recurringModal')).hide();
            document.getElementById('recurring-form').reset();
            loadRecurring();
        }
    });
}

function deleteRecurring(id) {
    if (!confirm('Удалить регулярный платёж?')) return;
    fetch(`/api/recurring/${id}`, {method: 'DELETE'})
        .then(() => loadRecurring());
}

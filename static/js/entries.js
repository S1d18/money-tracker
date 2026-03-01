/* entries.js — Управление записями */

document.addEventListener('DOMContentLoaded', () => {
    populateCategorySelects();
    loadEntries();

    document.getElementById('entry-type').addEventListener('change', filterCategories);
    document.getElementById('entry-form').addEventListener('submit', createEntry);
    document.getElementById('edit-entry-save').addEventListener('click', updateEntry);
    document.getElementById('edit-entry-type').addEventListener('change', () => {
        filterCategoriesFor('edit-entry-type', 'edit-entry-category');
    });

    filterCategories();
});

function populateCategorySelects() {
    const cats = typeof ALL_CATEGORIES !== 'undefined' ? ALL_CATEGORIES : [];
    fillSelect('entry-category', cats, 'expense');
    fillSelect('edit-entry-category', cats, 'expense');
    fillSelect('rec-category', cats, 'expense');
}

function fillSelect(selectId, cats, type) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    sel.innerHTML = '';
    cats.forEach(c => {
        if (c.type === type && c.is_active) {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            sel.appendChild(opt);
        }
    });
}

function filterCategories() {
    const type = document.getElementById('entry-type').value;
    // Возврат привязывается к категориям расходов
    const catType = type === 'refund' ? 'expense' : type;
    fillSelect('entry-category', ALL_CATEGORIES, catType);
}

function filterCategoriesFor(typeSelectId, catSelectId) {
    const type = document.getElementById(typeSelectId).value;
    const catType = type === 'refund' ? 'expense' : type;
    fillSelect(catSelectId, ALL_CATEGORIES, catType);
}

function loadEntries() {
    fetch(`/api/entries?year=${YEAR}&month=${MONTH}`)
        .then(r => r.json())
        .then(entries => {
            const tbody = document.getElementById('entries-body');
            if (!entries.length) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Нет записей</td></tr>';
                return;
            }
            tbody.innerHTML = entries.map(e => {
                const badgeClass = e.type === 'income' ? 'bg-success' : e.type === 'refund' ? 'bg-info' : 'bg-danger';
                const badgeText = e.type === 'income' ? 'Доход' : e.type === 'refund' ? 'Возврат' : 'Расход';
                return `
                <tr>
                    <td>${e.day || '—'}</td>
                    <td><span class="badge ${badgeClass}">${badgeText}</span></td>
                    <td><span class="badge rounded-pill" style="background:${e.category_color}">&nbsp;</span> ${e.category_name}</td>
                    <td class="text-end fw-bold">${e.amount_display}</td>
                    <td>${e.description || ''}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-secondary" onclick="editEntry(${e.id})"><i class="bi bi-pencil"></i></button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteEntry(${e.id})"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>`;
            }).join('');
        });
}

function createEntry(event) {
    event.preventDefault();
    const data = {
        year: YEAR,
        month: MONTH,
        type: document.getElementById('entry-type').value,
        amount: parseFloat(document.getElementById('entry-amount').value),
        category_id: parseInt(document.getElementById('entry-category').value),
        day: document.getElementById('entry-day').value ? parseInt(document.getElementById('entry-day').value) : null,
        description: document.getElementById('entry-desc').value,
    };
    fetch('/api/entries', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    }).then(r => {
        if (r.ok) {
            document.getElementById('entry-form').reset();
            filterCategories();
            loadEntries();
        }
    });
}

function editEntry(id) {
    fetch(`/api/entries?year=${YEAR}&month=${MONTH}`)
        .then(r => r.json())
        .then(entries => {
            const e = entries.find(x => x.id === id);
            if (!e) return;
            document.getElementById('edit-entry-id').value = e.id;
            document.getElementById('edit-entry-type').value = e.type;
            filterCategoriesFor('edit-entry-type', 'edit-entry-category');
            document.getElementById('edit-entry-category').value = e.category_id;
            document.getElementById('edit-entry-amount').value = (e.amount / 100).toFixed(2);
            document.getElementById('edit-entry-day').value = e.day || '';
            document.getElementById('edit-entry-desc').value = e.description || '';
            new bootstrap.Modal(document.getElementById('editEntryModal')).show();
        });
}

function updateEntry() {
    const id = document.getElementById('edit-entry-id').value;
    const data = {
        type: document.getElementById('edit-entry-type').value,
        amount: parseFloat(document.getElementById('edit-entry-amount').value),
        category_id: parseInt(document.getElementById('edit-entry-category').value),
        day: document.getElementById('edit-entry-day').value ? parseInt(document.getElementById('edit-entry-day').value) : null,
        description: document.getElementById('edit-entry-desc').value,
    };
    fetch(`/api/entries/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    }).then(r => {
        if (r.ok) {
            bootstrap.Modal.getInstance(document.getElementById('editEntryModal')).hide();
            loadEntries();
        }
    });
}

function deleteEntry(id) {
    if (!confirm('Удалить запись?')) return;
    fetch(`/api/entries/${id}`, {method: 'DELETE'})
        .then(() => loadEntries());
}

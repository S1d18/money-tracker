/* charts.js — Графики для дашборда и истории */

let pieChart = null;
let barChart = null;
let trendsChart = null;

function formatRub(val) {
    return new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(val) + ' \u20bd';
}

function loadDashboard(year, month) {
    // Карточки
    fetch(`/api/dashboard-summary?year=${year}&month=${month}`)
        .then(r => r.json())
        .then(d => {
            document.getElementById('card-income').textContent = d.month_income_display;
            document.getElementById('card-expense').textContent = d.month_expense_display;
            document.getElementById('card-balance').textContent = d.month_balance_display;
            document.getElementById('card-savings').textContent = d.savings_pct + '%';

            // Общий баланс за всё время
            const totalEl = document.getElementById('card-total-balance');
            totalEl.textContent = d.total_balance_display;
            totalEl.className = 'fs-2 fw-bold ' + (d.total_balance >= 0 ? 'text-success' : 'text-danger');

            // Неоплаченные регулярные
            const pendingCard = document.getElementById('pending-recurring-card');
            if (d.pending_recurring && d.pending_recurring.length > 0) {
                pendingCard.style.display = '';
                document.getElementById('pending-recurring-body').innerHTML = d.pending_recurring.map(r => `
                    <tr>
                        <td><i class="bi bi-exclamation-circle text-warning"></i> ${r.name}</td>
                        <td>${r.category_name}</td>
                        <td class="text-end">${r.due_day ? r.due_day + '-го числа' : '\u2014'}</td>
                        <td class="text-end fw-bold">${r.amount_display}</td>
                    </tr>
                `).join('');
                document.getElementById('pending-recurring-total').textContent = d.pending_recurring_total_display;
            } else {
                pendingCard.style.display = 'none';
            }

            // Топ-5
            const tbody = document.getElementById('top5-body');
            if (!d.top5.length) {
                tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">Нет данных</td></tr>';
            } else {
                tbody.innerHTML = d.top5.map((c, i) => `
                    <tr>
                        <td>${i + 1}</td>
                        <td><span class="badge rounded-pill" style="background:${c.color}">&nbsp;</span> ${c.name}</td>
                        <td class="text-end">${c.display}</td>
                    </tr>
                `).join('');
            }
        });

    // Круговая (столбчатая горизонтальная) — факт + план по категориям
    fetch(`/api/charts/category-breakdown?year=${year}&month=${month}`)
        .then(r => r.json())
        .then(d => {
            const ctx = document.getElementById('chartPie');
            if (pieChart) pieChart.destroy();
            const hasData = d.data.some(v => v > 0);
            const hasPlanned = d.planned && d.planned.some(v => v > 0);
            if (!hasData && !hasPlanned) {
                ctx.parentElement.innerHTML = '<div class="text-center text-muted py-5">Нет данных о расходах</div>';
                return;
            }

            const datasets = [{
                label: 'Оплачено',
                data: d.data,
                backgroundColor: d.colors,
            }];

            if (hasPlanned) {
                // Планируемые — те же цвета но полупрозрачные, со штриховкой
                const plannedColors = d.colors.map(c => c + '55');
                datasets.push({
                    label: 'К оплате',
                    data: d.planned,
                    backgroundColor: plannedColors,
                    borderColor: d.colors,
                    borderWidth: 2,
                    borderDash: [5, 3],
                });
            }

            pieChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: d.labels,
                    datasets: datasets,
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            stacked: true,
                            ticks: { callback: v => formatRub(v) },
                            beginAtZero: true,
                        },
                        y: { stacked: true }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.dataset.label}: ${formatRub(ctx.parsed.x)}`
                            }
                        },
                        legend: { display: hasPlanned }
                    }
                }
            });
        });

    // Столбчатая — доходы vs расходы за 6 мес.
    fetch(`/api/charts/monthly-comparison?year=${year}&month=${month}`)
        .then(r => r.json())
        .then(d => {
            const ctx = document.getElementById('chartBar');
            if (barChart) barChart.destroy();
            barChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: d.labels,
                    datasets: [
                        {label: 'Доходы', data: d.incomes, backgroundColor: '#27ae60'},
                        {label: 'Расходы', data: d.expenses, backgroundColor: '#e74c3c'},
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {callback: v => formatRub(v)}
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.dataset.label}: ${formatRub(ctx.parsed.y)}`
                            }
                        }
                    }
                }
            });
        });
}

function loadTrends(year, month) {
    fetch(`/api/charts/trends?year=${year}&month=${month}`)
        .then(r => r.json())
        .then(d => {
            const ctx = document.getElementById('chartTrends');
            if (!ctx) return;
            if (trendsChart) trendsChart.destroy();
            trendsChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: d.labels,
                    datasets: [
                        {label: 'Доходы', data: d.incomes, borderColor: '#27ae60', backgroundColor: 'rgba(39,174,96,0.1)', fill: true, tension: 0.3},
                        {label: 'Расходы', data: d.expenses, borderColor: '#e74c3c', backgroundColor: 'rgba(231,76,60,0.1)', fill: true, tension: 0.3},
                        {label: 'Баланс', data: d.balances, borderColor: '#3498db', borderDash: [5, 5], tension: 0.3},
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            ticks: {callback: v => formatRub(v)}
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.dataset.label}: ${formatRub(ctx.parsed.y)}`
                            }
                        }
                    }
                }
            });
        });
}

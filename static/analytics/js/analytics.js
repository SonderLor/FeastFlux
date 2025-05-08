// Общие функции для аналитических страниц

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация фильтров дат
    initDateFilters();

    // Инициализация экспорта данных
    initExportButtons();

    // Перенаправление при смене ресторана в фильтре
    initRestaurantFilter();
});

// Функция для инициализации фильтров дат
function initDateFilters() {
    // Установка текущей даты как максимальной для полей выбора даты
    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach(input => {
        input.setAttribute('max', today);
    });

    // Проверка, чтобы начальная дата не была позже конечной
    const startDateInputs = document.querySelectorAll('input[name="start_date"]');
    const endDateInputs = document.querySelectorAll('input[name="end_date"]');

    startDateInputs.forEach(startInput => {
        startInput.addEventListener('change', function() {
            endDateInputs.forEach(endInput => {
                if (startInput.value && endInput.value && startInput.value > endInput.value) {
                    endInput.value = startInput.value;
                }
                endInput.setAttribute('min', startInput.value);
            });
        });
    });

    endDateInputs.forEach(endInput => {
        endInput.addEventListener('change', function() {
            startDateInputs.forEach(startInput => {
                if (startInput.value && endInput.value && startInput.value > endInput.value) {
                    startInput.value = endInput.value;
                }
                startInput.setAttribute('max', endInput.value);
            });
        });
    });
}

// Функция для инициализации кнопок экспорта данных
function initExportButtons() {
    const exportSelects = document.querySelectorAll('select[name="export_format"]');

    exportSelects.forEach(select => {
        select.addEventListener('change', function() {
            const form = this.closest('form');
            if (this.value) {
                form.submit();
                // Сбрасываем значение после отправки формы
                setTimeout(() => {
                    this.value = '';
                }, 100);
            }
        });
    });
}

// Функция для перенаправления при смене ресторана
function initRestaurantFilter() {
    const restaurantSelects = document.querySelectorAll('select[name="restaurant"]');

    restaurantSelects.forEach(select => {
        select.addEventListener('change', function() {
            const form = this.closest('form');
            form.submit();
        });
    });
}

// Вспомогательная функция для форматирования чисел в рублях
function formatCurrency(value) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 2
    }).format(value);
}

// Вспомогательная функция для форматирования процентов
function formatPercent(value) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'percent',
        minimumFractionDigits: 1,
        maximumFractionDigits: 1
    }).format(value / 100);
}

// Функция для переключения между разными представлениями данных
function switchDataView(viewType) {
    const viewElements = document.querySelectorAll('.data-view');
    viewElements.forEach(el => {
        el.style.display = 'none';
    });

    const activeElement = document.getElementById(`view-${viewType}`);
    if (activeElement) {
        activeElement.style.display = 'block';
    }

    // Обновляем активные кнопки переключения
    const viewButtons = document.querySelectorAll('.view-switcher');
    viewButtons.forEach(button => {
        button.classList.remove('active');
        if (button.dataset.view === viewType) {
            button.classList.add('active');
        }
    });
}

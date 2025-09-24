# FSA-AstraInstall Automation

## Описание проекта

Автоматизированная система установки Astra.IDE на Astra Linux с графическим интерфейсом мониторинга процессов.

### Основные возможности

- **Автоматизация скрипта astra-setup.sh** - проверка репозиториев, анализ обновлений, автоматические ответы на интерактивные запросы
- **GUI мониторинг** - визуализация процессов установки в реальном времени
- **Перехват интерактивных запросов** - автоматические ответы на системные диалоги (dpkg, apt)
- **Статистика системы** - анализ доступных обновлений и пакетов для установки

### Технические требования

- Python 2.7.16 (базовая версия Astra Linux)
- tkinter (для GUI)
- pexpect (для перехвата интерактивных запросов)
- Astra Linux 1.7

### Структура проекта

```
FSA-AstraInstall/
├── README.md                    # Документация проекта
├── automation/                  # Python модули автоматизации
│   ├── __init__.py
│   ├── astra_setup_automation.py  # Автоматизация astra-setup.sh
│   ├── interactive_handler.py     # Перехват интерактивных запросов
│   └── gui_monitor.py            # GUI мониторинг процессов
├── config/                     # Конфигурационные файлы
│   └── auto_responses.json     # Правила автоматических ответов
├── logs/                       # Логи выполнения
└── original_scripts/           # Оригинальные bash скрипты
    ├── astra-setup.sh
    ├── install.sh
    ├── install-wine.sh
    ├── install-astraregul.sh
    └── uninstall-astraregul.sh
```

### Этапы реализации

1. ✅ Настройка Git и структуры проекта
2. 🔄 Автоматизация astra-setup.sh (проверка репозиториев + статистика)
3. ⏳ GUI мониторинг процессов
4. ⏳ Перехват интерактивных запросов
5. ⏳ Полная интеграция всех скриптов

### Использование

```bash
# Запуск GUI автоматизации (по умолчанию)
sudo python astra-automation.py

# Запуск GUI в режиме тестирования
sudo python astra-automation.py --dry-run

# Консольный режим (без GUI)
sudo python astra-automation.py --console

# Консольный режим с тестированием
sudo python astra-automation.py --console --dry-run
```

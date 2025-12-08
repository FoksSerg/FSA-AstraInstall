# План создания единого исполняемого файла с самообновлением

**Версия документа:** 1.1.0  
**Дата обновления:** 2025.12.02  
**Проект:** FSA-AstraInstall  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Текущая версия проекта:** V3.3.166  
**Статус:** ✅ РЕАЛИЗОВАНО

---

## 📋 Содержание

1. [Цель](#цель)
2. [Текущее состояние](#текущее-состояние)
3. [Архитектура решения](#архитектура-решения)
4. [План реализации](#план-реализации)
5. [Технические детали](#технические-детали)
6. [Сборка на macOS](#сборка-на-macos)
7. [Тестирование](#тестирование)

---

## 🎯 Цель

Создать **единый исполняемый файл** `FSA-AstraInstall` для Linux, который:

1. ✅ Объединяет функциональность трёх файлов:
   - `astra_update.sh` - обновление из сетевых источников
   - `astra_install.sh` - установка зависимостей и определение режима
   - `astra_automation.py` - основное приложение

2. ✅ **Самообновляется** - скачивает и заменяет сам себя (не список файлов)

3. ✅ Компилируется в бинарный файл через PyInstaller

4. ✅ Собирается на **macOS через Docker**

---

## 📊 Текущее состояние

### Существующие файлы:

| Файл | Описание | Статус |
|------|----------|--------|
| `self_updater.py` | Модуль самообновления бинарника | ✅ Готов |
| `build_unified.py` | Объединение 4 файлов в один Python | ✅ Готов |
| `build_executables.py` | Сборка бинарника через Docker | ✅ Работает |
| `FSA-AstraInstall.py` | Объединённый Python файл | ✅ Готов |
| `FSA-AstraInstall` | Бинарник для Linux | ✅ Собирается |
| `astra_update.sh` | Логика обновления из источников | ✅ Работает |
| `astra_install.sh` | Установка зависимостей | ✅ Работает |
| `astra_automation.py` | Основное приложение | ✅ Работает |

### Что реализовано:

1. ✅ Сборка через Docker на macOS (`build_executables.py`)
2. ✅ Объединение файлов с bash-скриптами (`build_unified.py`)
3. ✅ Модуль самообновления (`self_updater.py`)
4. ✅ Логика обновления из git/SMB источников
5. ✅ Разные режимы обновления (GUI/консоль/force)
6. ✅ Версионирование и проверка обновлений

---

## 🏗 Архитектура решения

### Структура единого файла:

```
FSA-AstraInstall (бинарный файл)
├── БЛОК 1: Самообновление
│   ├── check_for_updates() - проверка новой версии
│   ├── download_update() - скачивание нового бинарника
│   └── apply_update() - замена себя и перезапуск
│
├── БЛОК 2: Установка зависимостей (из astra_install.sh)
│   ├── check_root() - проверка прав root
│   ├── check_system_packages() - проверка пакетов
│   ├── install_system_packages() - установка через apt-get
│   └── check_tkinter() - проверка GUI
│
├── БЛОК 3: Основное приложение (из astra_automation.py)
│   ├── Все существующие классы и функции
│   └── main() - точка входа
│
└── БЛОК 4: Точка входа
    └── if __name__ == '__main__':
        ├── Парсинг аргументов
        ├── Проверка обновлений (если не --skip-update)
        ├── Установка зависимостей (если нужно)
        └── Запуск приложения
```

### Алгоритм самообновления по режимам:

```
┌─────────────────────────────────────────────────────────────┐
│                    ЗАПУСК FSA-AstraInstall                   │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
      │ --force-     │ │ --console    │ │ GUI режим    │
      │ update       │ │              │ │ (default)    │
      └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
             │                │                │
             ▼                ▼                ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
      │ Проверка     │ │ Проверка     │ │ Запуск GUI   │
      │ обновлений   │ │ обновлений   │ │ сразу        │
      └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
             │                │                │
             ▼                ▼                ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
      │ Если есть:   │ │ Если есть:   │ │ Через 3 сек: │
      │ скачать,     │ │ вывод в лог  │ │ проверка     │
      │ заменить,    │ │ + инструкция │ │ обновлений   │
      │ перезапуск   │ │              │ │              │
      └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
             │                │                │
             ▼                ▼                ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
      │ Работа с     │ │ Работа в     │ │ Если есть:   │
      │ новой версии │ │ консоли      │ │ диалог       │
      └──────────────┘ └──────────────┘ │ обновления   │
                                        └──────────────┘
```

### Источники обновлений (приоритет):

1. **SMB (10.10.55.77)** - для разработки/тестирования
2. **Git (GitHub)** - для клиентов (fallback)

---

## 📝 План реализации

### Этап 1: Создание модуля самообновления ✅ ГОТОВО

**Файл:** `self_updater.py` (402 строки)

**Реализованные функции:**

```python
class SelfUpdater:
    """Класс для самообновления бинарного файла"""
    
    # SMB сервер (приоритет - для разработки)
    SMB_SERVER = "10.10.55.77"
    SMB_SHARE = "Install"
    SMB_PATH = "ISO/Linux/Astra"
    
    # Git (fallback - для клиентов)
    GIT_RAW_URL = "https://raw.githubusercontent.com/ViRa-Realtime/FSA-AstraInstall"
    
    def check_smb_available(self) -> bool
    def get_version_from_smb(self) -> Optional[str]
    def download_from_smb(self, dest_path: str) -> bool
    
    def check_git_available(self) -> bool
    def get_version_from_git(self) -> Optional[str]
    def download_from_git(self, dest_path: str) -> bool
    
    def check_for_updates(self) -> Optional[str]
    def download_and_apply(self) -> bool
    def restart(self)
```

**Файлы:**
- [x] `self_updater.py` - модуль самообновления

---

### Этап 2: Доработка build_unified.py ✅ ГОТОВО

**Файл:** `build_unified.py` (469 строк)

**Реализовано:**

1. ✅ Bash-скрипты встроены как строковые константы
2. ✅ `self_updater.py` интегрирован в объединённый файл
3. ✅ Новая точка входа с тремя режимами обновления

**Структура объединённого файла:**
```python
# FSA-AstraInstall.py (~29,777 строк, 1.6 MB)

# 1. __future__ импорты
# 2. Константы SMB/Git для самообновления
# 3. Класс SelfUpdater
# 4. Встроенные bash-скрипты (EMBEDDED_ASTRA_UPDATE_SH, EMBEDDED_ASTRA_INSTALL_SH)
# 5. Код из astra_automation.py (все 33 класса)
# 6. Главная точка входа с логикой обновления по режимам
```

**Файлы:**
- [x] `build_unified.py` - скрипт сборки
- [x] `FSA-AstraInstall.py` - результат сборки

---

### Этап 3: Интеграция логики обновления ✅ ГОТОВО

**Логика в точке входа (build_unified.py → FSA-AstraInstall.py):**

```python
if __name__ == '__main__':
    # РЕЖИМ 1: --force-update
    # Проверка → скачивание → замена → перезапуск
    if force_update and not skip_update:
        updater.download_and_apply()
        updater.restart()  # с --skip-update
    
    # РЕЖИМ 2: --console
    # Проверка → вывод в лог (без обновления)
    elif console_mode and not skip_update:
        if new_ver:
            print(f"ДОСТУПНО ОБНОВЛЕНИЕ: {new_ver}")
            print("Для обновления: ./FSA-AstraInstall --force-update")
    
    # РЕЖИМ 3: GUI (по умолчанию)
    # GUI запускается сразу, проверка через 3 сек в фоне
    elif not console_mode and not skip_update:
        threading.Thread(target=delayed_update_check, daemon=True).start()
    
    main()  # Запуск основного приложения
```

**Файлы:**
- [x] Логика встроена в `build_unified.py` → генерируется в `FSA-AstraInstall.py`

---

### Этап 4: Тестирование сборки ✅ ГОТОВО

**Результаты:**
1. [x] `build_executables.py` работает на macOS через Docker
2. [x] Бинарник создаётся в корне: `FSA-AstraInstall`
3. [x] Python версия: `FSA-AstraInstall.py` (1.6 MB, 29,777 строк)
4. [ ] Тестирование на Linux VM (требуется)

---

### Этап 5: Документация ✅ В ПРОЦЕССЕ

**Файлы:**
- [x] `UNIFIED_BUILD_PLAN.md` - обновлён
- [ ] `README.md` - добавить раздел о бинарной версии

---

## 🔧 Технические детали

### Формат версии на сервере

Файл `VERSION.txt` на сервере:
```
V2.6.142
```

Или JSON формат `version.json`:
```json
{
    "version": "V2.6.142",
    "date": "2025.12.02",
    "changelog": "Добавлено самообновление",
    "min_version": "V2.6.140",
    "download_url": "https://example.com/releases/FSA-AstraInstall"
}
```

### Алгоритм замены бинарника

```python
def apply_update(self, new_binary_path: str) -> bool:
    """Заменяет текущий бинарник новым"""
    current_path = sys.executable
    backup_path = current_path + ".backup"
    
    try:
        # 1. Создаём резервную копию
        shutil.copy2(current_path, backup_path)
        
        # 2. Заменяем бинарник
        shutil.move(new_binary_path, current_path)
        
        # 3. Устанавливаем права на выполнение
        os.chmod(current_path, 0o755)
        
        # 4. Удаляем резервную копию
        os.remove(backup_path)
        
        return True
    except Exception as e:
        # Восстанавливаем из резервной копии
        if os.path.exists(backup_path):
            shutil.move(backup_path, current_path)
        return False
```

### Источники обновлений

Поддерживаемые источники (в порядке приоритета):

1. **Git (GitHub/GitLab)**
   ```
   git:https://github.com/company/repo:master:bin/FSA-AstraInstall
   ```

2. **HTTP/HTTPS**
   ```
   http:https://releases.example.com/FSA-AstraInstall
   ```

3. **SMB (сетевая папка)**
   ```
   smb:server:share:path/FSA-AstraInstall:username
   ```

---

## 🍎 Сборка на macOS

### Требования:

1. **Docker Desktop** - установлен и запущен
2. **Python 3.8+** - для запуска скриптов сборки

### Команда сборки:

```bash
cd /Volumes/FSA-PRJ/Project/FSA-AstraInstall
python3 build_executables.py
```

### Что происходит при сборке:

1. ✅ Проверка наличия Docker
2. ✅ Запуск `build_unified.py` для создания объединённого файла
3. ✅ Создание Docker-контейнера с Python и PyInstaller
4. ✅ Компиляция в бинарный файл внутри контейнера
5. ✅ Копирование результата в `bin/FSA-AstraInstall`

### Результат:

```
FSA-AstraInstall/
├── FSA-AstraInstall        # Бинарный файл для Linux (~50-100 MB)
├── FSA-AstraInstall.py     # Объединённый Python файл (1.6 MB)
├── self_updater.py         # Модуль самообновления
├── build_unified.py        # Скрипт сборки Python версии
├── build_executables.py    # Скрипт сборки бинарника через Docker
└── ...
```

### Размер бинарника:

- Ожидаемый размер: **50-100 MB** (включает Python runtime)
- С UPX сжатием: **30-50 MB**

---

## 🧪 Тестирование

### Тест 1: Сборка на macOS

```bash
# 1. Запуск сборки
python3 build_executables.py

# 2. Проверка результата
ls -la bin/FSA-AstraInstall
file bin/FSA-AstraInstall
```

### Тест 2: Запуск на Linux

```bash
# 1. Копируем на Linux VM
scp bin/FSA-AstraInstall user@linux-vm:/tmp/

# 2. Запускаем
ssh user@linux-vm
chmod +x /tmp/FSA-AstraInstall
sudo /tmp/FSA-AstraInstall --console
```

### Тест 3: Самообновление

```bash
# 1. Запуск с проверкой обновлений
sudo ./FSA-AstraInstall

# 2. Запуск без проверки обновлений
sudo ./FSA-AstraInstall --skip-update

# 3. Принудительное обновление
sudo ./FSA-AstraInstall --force-update
```

### Тест 4: Разные режимы

```bash
# GUI режим (по умолчанию)
sudo ./FSA-AstraInstall

# Консольный режим
sudo ./FSA-AstraInstall --console

# Только обновление
sudo ./FSA-AstraInstall --update-only
```

---

## 📊 Оценка времени

| Этап | Описание | Время |
|------|----------|-------|
| 1 | Создание модуля самообновления | 1-2 дня |
| 2 | Доработка build_unified.py | 1-2 дня |
| 3 | Интеграция в astra_automation.py | 1 день |
| 4 | Тестирование сборки | 1 день |
| 5 | Документация | 0.5 дня |
| **ИТОГО** | | **4.5-6.5 дней** |

---

## ✅ Чек-лист готовности

### Перед началом:
- [x] Docker Desktop установлен и запущен
- [x] Python 3.8+ установлен
- [x] Все исходные файлы актуальны и работают

### Реализовано:
- [x] `self_updater.py` создан (402 строки)
- [x] `build_unified.py` доработан (469 строк)
- [x] `build_executables.py` работает без ошибок
- [x] `FSA-AstraInstall.py` создаётся (29,777 строк)
- [x] Бинарник создаётся в корне: `FSA-AstraInstall`
- [x] Логика самообновления по режимам реализована

### Требует тестирования:
- [ ] Тесты на Linux VM
- [ ] Проверка SMB обновления
- [ ] Проверка Git обновления

---

## 🚀 Следующие шаги

1. ✅ ~~Получить разрешение на начало реализации~~
2. ✅ ~~Создать `self_updater.py` - модуль самообновления~~
3. ✅ ~~Доработать `build_unified.py` - улучшить объединение~~
4. ✅ ~~Протестировать сборку на macOS через Docker~~
5. ⏳ **Протестировать результат на Linux VM**
6. ⏳ **Загрузить файлы на SMB и Git для проверки обновлений**

---

## 📋 Команды для использования

### Сборка Python версии:
```bash
cd /Volumes/FSA-PRJ/Project/FSA-AstraInstall
python3 build_unified.py
```

### Сборка бинарника (через Docker):
```bash
python3 build_executables.py
```

### Запуск на Linux:
```bash
# GUI режим (отложенная проверка обновлений)
sudo ./FSA-AstraInstall

# Консольный режим (лог о наличии обновлений)
sudo ./FSA-AstraInstall --console

# Принудительное обновление
sudo ./FSA-AstraInstall --force-update

# Без проверки обновлений
sudo ./FSA-AstraInstall --skip-update
```

---

**Дата обновления:** 2025.12.02  
**Автор:** AI Assistant  
**Версия документа:** 1.1.0


# План рефакторинга Unified-файла

**Версия документа:** 1.0.0  
**Дата создания:** 2025.12.03  
**Проект:** FSA-AstraInstall  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Текущая версия проекта:** V3.3.171 (2025.12.03)

## 📋 Оглавление

1. [Цель рефакторинга](#цель-рефакторинга)
2. [Текущие проблемы](#текущие-проблемы)
3. [Анализ дублирования](#анализ-дублирования)
4. [Новая архитектура](#новая-архитектура)
5. [Пошаговый план реализации](#пошаговый-план-реализации)
6. [Детальные изменения](#детальные-изменения)
7. [Тестирование](#тестирование)
8. [Риски и митигация](#риски-и-митигация)

---

## 🎯 Цель рефакторинга

Преобразовать `FSA-AstraInstall.py` (unified-файл) в полностью самостоятельный Python-скрипт, который:
- ✅ Работает без внешних bash-скриптов
- ✅ Не дублирует функциональность между bash и Python
- ✅ Имеет простую и понятную архитектуру
- ✅ Легко отлаживается и поддерживается
- ✅ Адекватно работает на чистом Linux (обновление репозиториев, установка компонентов)

---

## 🔍 Текущие проблемы

### 1. Ошибка `datetime.now()`
**Местоположение:** `Build/self_updater.py`, строка 69  
**Проблема:** Конфликт импортов `datetime`  
**Ошибка:** `module 'datetime' has no attribute 'now'`

### 2. Поиск внешних bash-скриптов
**Местоположение:** `FSA-AstraInstall.py`, строка 23783  
**Проблема:** Код ищет `astra_install.sh` для создания ярлыков  
**Решение:** Использовать `sys.executable` в unified-режиме

### 3. Встроенные bash-скрипты ищут внешние файлы
**Местоположение:** `EMBEDDED_ASTRA_UPDATE_SH`, `EMBEDDED_ASTRA_INSTALL_SH`  
**Проблема:** Bash-скрипты ищут `astra_automation.py` и `astra_install.sh`  
**Решение:** Модифицировать для работы с unified-файлом или заменить на Python

### 4. Отсутствие автоматической настройки репозиториев
**Проблема:** На чистом Linux нет сетевых репозиториев  
**Решение:** Добавить функцию автоматической настройки для Astra Linux

---

## 📊 Анализ дублирования

### Дублирование 1: Инициализация лог-файла (3 места)

#### Bash: `astra_install.sh` (строки 131-267)
- Создает `LOG_FILE` с timestamp
- Парсит `--log-file` и `--log-timestamp`
- Создает директорию `Log/`
- Инициализирует файл с заголовком

#### Bash: `astra_update.sh` (строки 44-74)
- Создает `ANALYSIS_LOG_FILE` с timestamp
- Дублирует логику создания лога

#### Python: `main()` (строки ~29180-29200)
- Парсит `--log-file` и `--log-timestamp`
- Создает `GLOBAL_LOG_FILE`
- Создает директорию `Log/` (если нужно)
- Инициализирует DualStreamLogger

**Решение:** Оставить только Python-версию, убрать из bash

---

### Дублирование 2: Проверка репозиториев (2 места)

#### Bash: `astra_install.sh` (строки 317-325)
```bash
check_repos_available() {
    grep -v "^#" /etc/apt/sources.list | grep -v "cdrom:" | grep "^deb"
}
```

#### Python: `RepoChecker` (строки ~27658-27676)
```python
def check_system_update_needed(self):
    # Проверяет репозитории через Python
```

**Решение:** Оставить только Python-версию

---

### Дублирование 3: Проверка tkinter (2 места)

#### Bash: `astra_install.sh` (строки 308-315)
```bash
check_tkinter_available() {
    python3 -c "import tkinter" 2>/dev/null
}
```

#### Python: В коде GUI
```python
try:
    import tkinter
except ImportError:
    # Обработка
```

**Решение:** Проверять только в Python

---

### Дублирование 4: Определение режима запуска

#### Bash: `astra_install.sh` (строки 601-687)
- 86 строк логики определения режима
- Передает результат через `--mode`

#### Python: `main()` (строки ~29263-29268)
- Получает `--mode` от bash
- Использует для запуска GUI/консоли

**Решение:** Перенести всю логику в Python

---

### Дублирование 5: Поиск исполняемого файла

#### Bash: `astra_install.sh` (строки 34-83)
- Ищет `astra_automation` или `astra_automation.py`
- Проверяет бинарный/скриптовый режим

**Решение:** В unified-файле не нужно, удалить

---

## 🏗️ Новая архитектура

### Текущая цепочка запуска:
```
astra_update.sh → astra_install.sh → astra_automation.py
     (bash)          (bash)              (Python)
```

### Новая цепочка запуска:
```
FSA-AstraInstall.py (unified)
     │
     ├─→ [ТОЧКА ВХОДА] if __name__ == '__main__':
     │   ├─→ Проверка root (sudo перезапуск)
     │   ├─→ Парсинг аргументов
     │   ├─→ Проверка обновлений (SelfUpdater)
     │   └─→ Вызов main()
     │
     └─→ main() - ЕДИНАЯ функция инициализации
         ├─→ Инициализация лог-файла (ОДИН РАЗ!)
         ├─→ Проверка системных требований (Python)
         ├─→ Определение режима запуска (Python)
         └─→ Запуск приложения
```

### Структура кода:

```python
# ============================================================================
# ГЛАВНАЯ ТОЧКА ВХОДА
# ============================================================================
if __name__ == '__main__':
    # 1. Проверка root
    # 2. Парсинг аргументов
    # 3. Проверка обновлений
    # 4. Вызов main()

# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================
def main():
    # 1. Инициализация логов (ОДИН РАЗ!)
    # 2. Проверка системных требований
    # 3. Определение режима запуска
    # 4. Запуск приложения

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (вместо bash-скриптов)
# ============================================================================
def update_from_network():
    """Обновление из сетевых источников (замена astra_update.sh)"""
    # Python-реализация копирования файлов из SMB/Git

def install_dependencies():
    """Установка зависимостей (замена astra_install.sh)"""
    # Python-реализация установки tkinter и других пакетов

def check_system_requirements():
    """Проверка системных требований"""
    # Проверка tkinter, репозиториев, интернета

def determine_start_mode():
    """Определение режима запуска"""
    # Логика определения gui_ready/gui_install_first/console_forced
```

---

## 📝 Пошаговый план реализации

### Этап 1: Исправление критических ошибок
- [x] 1.1. Исправить ошибку `datetime.now()` в `SelfUpdater` ✅
- [x] 1.2. Исправить создание ярлыков для unified-файла ✅
- [ ] 1.3. Добавить автоматическую настройку репозиториев

### Этап 2: Удаление встроенных bash-скриптов
- [ ] 2.1. Создать Python-функцию `update_from_network()` (замена `astra_update.sh`)
- [ ] 2.2. Создать Python-функцию `install_dependencies()` (замена `astra_install.sh`)
- [ ] 2.3. Удалить `EMBEDDED_ASTRA_UPDATE_SH` и `EMBEDDED_ASTRA_INSTALL_SH`
- [ ] 2.4. Удалить функцию `run_embedded_bash()`
- [ ] 2.5. Обновить точки вызова (`--update-only`, `--install-deps-only`)

### Этап 3: Упрощение инициализации
- [ ] 3.1. Убрать дублирование инициализации логов
- [ ] 3.2. Оставить только Python-версию инициализации
- [ ] 3.3. Упростить передачу параметров (убрать `--log-file`, `--log-timestamp`)

### Этап 4: Перенос логики из bash в Python
- [ ] 4.1. Перенести проверку tkinter в Python
- [ ] 4.2. Перенести проверку репозиториев в Python
- [ ] 4.3. Перенести определение режима запуска в Python
- [ ] 4.4. Удалить функцию `find_python_executable()` из bash-скриптов

### Этап 5: Тестирование
- [ ] 5.1. Тестирование на чистом Linux
- [ ] 5.2. Тестирование обновления репозиториев
- [ ] 5.3. Тестирование установки компонентов
- [ ] 5.4. Тестирование GUI и консольного режима

---

## 🔧 Детальные изменения

### Изменение 1: Исправление `datetime.now()`

**Файл:** `Build/self_updater.py`, строка 69

**Было:**
```python
from datetime import datetime
...
timestamp = datetime.now().strftime("%H:%M:%S")
```

**Будет:**
```python
from datetime import datetime as dt
...
timestamp = dt.now().strftime("%H:%M:%S")
```

**Или:**
```python
import datetime
...
timestamp = datetime.datetime.now().strftime("%H:%M:%S")
```

---

### Изменение 2: Исправление создания ярлыков

**Файл:** `FSA-AstraInstall.py`, строка 23783

**Было:**
```python
script_path = os.path.abspath("astra_install.sh")
if not os.path.exists(script_path):
    print(f"[ERROR] Скрипт не найден: {script_path}", gui_log=True)
    return
```

**Будет:**
```python
# Определяем путь к текущему исполняемому файлу
is_frozen = getattr(sys, 'frozen', False)
if is_frozen or os.path.basename(sys.argv[0]) in ('FSA-AstraInstall', 'FSA-AstraInstall.py'):
    script_path = sys.executable if is_frozen else os.path.abspath(sys.argv[0])
else:
    script_path = os.path.abspath("astra_install.sh")
    if not os.path.exists(script_path):
        print(f"[ERROR] Скрипт не найден: {script_path}", gui_log=True)
        return
```

**Также исправить строку 23804:**
```python
# Было:
Exec=bash "{script_path}"

# Будет:
if is_frozen:
    exec_line = f'"{script_path}"'
else:
    exec_line = f'python3 "{script_path}"'
```

---

### Изменение 3: Создание `update_from_network()`

**Новая функция в `FSA-AstraInstall.py`:**

```python
def update_from_network():
    """
    Обновление из сетевых источников (замена astra_update.sh)
    Копирует файлы из SMB/Git в локальную директорию
    """
    import subprocess
    import os
    from pathlib import Path
    
    # Определяем директорию скрипта
    script_dir = Path(__file__).parent.absolute() if not getattr(sys, 'frozen', False) else Path(sys.executable).parent
    
    # Источники обновлений
    sources = [
        "smb:10.10.55.77:Install:ISO/Linux/Astra:FokinSA",
        "git:https://github.com/your-repo/FSA-AstraInstall.git"
    ]
    
    # Логика копирования файлов из источников
    # (реализация из astra_update.sh, но на Python)
    
    return True
```

---

### Изменение 4: Создание `install_dependencies()`

**Новая функция в `FSA-AstraInstall.py`:**

```python
def install_dependencies():
    """
    Установка зависимостей (замена astra_install.sh)
    Устанавливает tkinter и другие необходимые пакеты
    """
    import subprocess
    
    # Проверяем наличие tkinter
    try:
        import tkinter
        return True  # Уже установлен
    except ImportError:
        pass
    
    # Устанавливаем tkinter
    result = subprocess.run(
        ['apt-get', 'install', '-y', 'python3-tk'],
        check=False
    )
    
    return result.returncode == 0
```

---

### Изменение 5: Создание `check_system_requirements()`

**Новая функция в `FSA-AstraInstall.py`:**

```python
def check_system_requirements():
    """
    Проверка системных требований
    Возвращает словарь с результатами проверок
    """
    result = {
        'tkinter_available': False,
        'repos_available': False,
        'internet_available': False
    }
    
    # Проверка tkinter
    try:
        import tkinter
        result['tkinter_available'] = True
    except ImportError:
        pass
    
    # Проверка репозиториев
    repo_checker = RepoChecker()
    if repo_checker.check_system_update_needed()['needs_update'] is not None:
        result['repos_available'] = True
    
    # Проверка интернета
    import urllib.request
    try:
        urllib.request.urlopen('http://google.com', timeout=3)
        result['internet_available'] = True
    except:
        pass
    
    return result
```

---

### Изменение 6: Создание `determine_start_mode()`

**Новая функция в `FSA-AstraInstall.py`:**

```python
def determine_start_mode():
    """
    Определение режима запуска
    Возвращает: 'gui_ready', 'gui_install_first', или 'console_forced'
    """
    requirements = check_system_requirements()
    
    # Если tkinter доступен - сразу GUI
    if requirements['tkinter_available']:
        return 'gui_ready'
    
    # Если есть репозитории и интернет - можно установить tkinter
    if requirements['repos_available'] and requirements['internet_available']:
        return 'gui_install_first'
    
    # Иначе - консольный режим
    return 'console_forced'
```

---

### Изменение 7: Упрощение `main()`

**Было:**
```python
def main():
    # Парсит --log-file, --log-timestamp
    # Создает GLOBAL_LOG_FILE
    # Получает --mode от bash
    # Запускает GUI/консоль
```

**Будет:**
```python
def main():
    # 1. Инициализация логов (ОДИН РАЗ, без дублирования)
    log_file = initialize_logging()
    
    # 2. Проверка системных требований
    requirements = check_system_requirements()
    
    # 3. Определение режима запуска (в Python, не от bash)
    start_mode = determine_start_mode()
    
    # 4. Установка зависимостей (если нужно)
    if start_mode == 'gui_install_first':
        install_dependencies()
        start_mode = 'gui_ready'  # После установки переключаемся
    
    # 5. Запуск приложения
    if start_mode == 'gui_ready':
        # Запуск GUI
    else:
        # Запуск консольного режима
```

---

## 🧪 Тестирование

### Тест 1: Запуск на чистом Linux
```bash
# На чистой Astra Linux 1.8
sudo ./FSA-AstraInstall --console
```

**Ожидаемый результат:**
- ✅ Автоматическая настройка репозиториев
- ✅ Проверка системных требований
- ✅ Определение режима запуска
- ✅ Успешный запуск консольного режима

### Тест 2: Обновление репозиториев
```bash
sudo ./FSA-AstraInstall --console
```

**Ожидаемый результат:**
- ✅ Обнаружение отсутствия сетевых репозиториев
- ✅ Автоматическая настройка репозиториев для Astra Linux
- ✅ Успешное обновление списка пакетов

### Тест 3: Установка компонентов
```bash
sudo ./FSA-AstraInstall --console
```

**Ожидаемый результат:**
- ✅ Успешное обновление системы
- ✅ Установка Wine (если нужно)
- ✅ Установка других компонентов

### Тест 4: GUI режим
```bash
sudo ./FSA-AstraInstall
```

**Ожидаемый результат:**
- ✅ Проверка tkinter
- ✅ Установка tkinter (если нужно)
- ✅ Успешный запуск GUI

---

## ⚠️ Риски и митигация

### Риск 1: Потеря функциональности при удалении bash-скриптов
**Митигация:**
- Тщательно проанализировать все функции bash-скриптов
- Создать Python-эквиваленты перед удалением
- Тестировать каждый этап рефакторинга

### Риск 2: Проблемы с правами доступа
**Митигация:**
- Сохранить логику проверки root
- Сохранить логику sudo перезапуска
- Тестировать на чистом Linux

### Риск 3: Проблемы с логированием
**Митигация:**
- Сохранить DualStreamLogger
- Убедиться, что логи создаются правильно
- Проверить передачу логов между функциями

### Риск 4: Проблемы с обновлениями
**Митигация:**
- Сохранить SelfUpdater
- Протестировать механизм обновлений
- Убедиться, что обновления работают для unified-файла

---

## 📅 Временные рамки

- **Этап 1:** 1-2 часа (критические исправления)
- **Этап 2:** 2-3 часа (удаление bash-скриптов)
- **Этап 3:** 1-2 часа (упрощение инициализации)
- **Этап 4:** 2-3 часа (перенос логики)
- **Этап 5:** 2-3 часа (тестирование)

**Итого:** 8-13 часов работы

---

## ✅ Критерии успеха

1. ✅ Unified-файл работает без внешних bash-скриптов
2. ✅ Нет дублирования функциональности
3. ✅ Успешный запуск на чистом Linux
4. ✅ Автоматическая настройка репозиториев работает
5. ✅ Все тесты проходят успешно
6. ✅ Код стал проще и понятнее

---

**Статус:** 🟡 В процессе  
**Последнее обновление:** 2025.12.03

---

## 📝 Журнал изменений

### 2025.12.03 - Начало рефакторинга
- ✅ Создан подробный план рефакторинга
- ✅ Исправлена ошибка `datetime.now()` в `SelfUpdater` (Build/self_updater.py)
- ✅ Исправлено создание ярлыков для unified-файла (FSA-AstraInstall.py, строка 23783)
- 🔄 Продолжается работа над остальными этапами


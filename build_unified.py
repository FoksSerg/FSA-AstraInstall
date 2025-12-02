#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт объединения файлов проекта в единый Python файл FSA-AstraInstall_unified.py

Этот скрипт:
1. Берёт astra_automation.py как основу
2. Встраивает bash-скрипты как строковые константы (для выполнения через subprocess)
3. Добавляет модуль самообновления (self_updater.py)
4. Модифицирует точку входа для поддержки самообновления

Версия: V2.7.142 (2025.12.02)
Компания: ООО "НПА Вира-Реалтайм"

ВАЖНО: Исходные файлы НЕ изменяются!
       Результат создаётся в build/FSA-AstraInstall_unified.py
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
BUILD_DIR = SCRIPT_DIR / "build"
# Результат в корень проекта с расширением .py
OUTPUT_FILE = SCRIPT_DIR / "FSA-AstraInstall.py"

# Исходные файлы
ASTRA_UPDATE_SH = SCRIPT_DIR / "astra_update.sh"
ASTRA_INSTALL_SH = SCRIPT_DIR / "astra_install.sh"
ASTRA_AUTOMATION_PY = SCRIPT_DIR / "astra_automation.py"
SELF_UPDATER_PY = SCRIPT_DIR / "self_updater.py"

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def print_step(message):
    print(f"\n[#] {message}")

def print_success(message):
    print(f"[OK] {message}")

def print_error(message):
    print(f"[ERROR] {message}")

def print_info(message):
    print(f"[i] {message}")

def read_file_safe(filepath):
    """Безопасное чтение файла"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print_error(f"Не удалось прочитать {filepath}: {e}")
        sys.exit(1)

def get_version_from_file(filepath):
    """Извлекает версию из файла"""
    content = read_file_safe(filepath)
    # Ищем APP_VERSION = "V2.6.141 (2025.12.02)"
    match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    # Ищем # Версия: V2.6.141
    match = re.search(r'#\s*Версия:\s*(V[\d.]+)', content)
    if match:
        return match.group(1)
    return "V2.6.141"

# ============================================================================
# ИЗВЛЕЧЕНИЕ КОМПОНЕНТОВ
# ============================================================================

def extract_future_imports(python_code):
    """Извлекает __future__ импорты из Python кода"""
    future_imports = []
    other_lines = []
    
    for line in python_code.split('\n'):
        stripped = line.strip()
        if stripped.startswith('from __future__') or stripped.startswith('import __future__'):
            future_imports.append(line)
        else:
            other_lines.append(line)
    
    return future_imports, '\n'.join(other_lines)

def extract_self_updater_class(self_updater_content):
    """
    Извлекает только класс SelfUpdater и функцию check_and_update из self_updater.py
    Убирает shebang, docstring модуля и тестовый код
    """
    lines = self_updater_content.split('\n')
    result_lines = []
    in_class = False
    in_function = False
    in_test = False
    skip_module_docstring = True
    docstring_count = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Пропускаем shebang
        if stripped.startswith('#!'):
            continue
        
        # Пропускаем кодировку
        if stripped.startswith('# -*-'):
            continue
        
        # Пропускаем модульный docstring (первые тройные кавычки)
        if skip_module_docstring:
            if '"""' in stripped:
                docstring_count += stripped.count('"""')
                if docstring_count >= 2:
                    skip_module_docstring = False
                continue
            if docstring_count > 0:
                continue
        
        # Пропускаем тестовый блок if __name__ == '__main__'
        if stripped.startswith("if __name__") and "__main__" in stripped:
            in_test = True
            continue
        if in_test:
            continue
        
        # Добавляем остальные строки
        result_lines.append(line)
    
    return '\n'.join(result_lines)

def escape_bash_for_python(bash_content):
    """
    Экранирует bash-скрипт для встраивания в Python как строковую константу.
    Использует тройные кавычки с raw-строкой.
    """
    # Заменяем обратные слеши на двойные (для Python строки)
    # Но в raw-строке это не нужно
    # Просто убедимся, что нет тройных кавычек внутри
    if '"""' in bash_content:
        bash_content = bash_content.replace('"""', '\\"\\"\\"')
    return bash_content

# ============================================================================
# МОДИФИКАЦИЯ ТОЧКИ ВХОДА
# ============================================================================

def create_new_main_block(version):
    """
    Создаёт новый блок main() с поддержкой самообновления.
    Логика:
    - GUI: отложенная проверка через 3 сек, диалог обновления
    - Консоль: только лог о наличии обновления
    - --force-update: обновляется и перезапускается
    """
    return f'''
# ============================================================================
# ВСТРОЕННЫЕ BASH-СКРИПТЫ (для выполнения через subprocess)
# ============================================================================

def run_embedded_bash(script_name):
    """Выполняет встроенный bash-скрипт"""
    import subprocess
    import tempfile
    import os
    
    scripts = {{
        'astra_update': EMBEDDED_ASTRA_UPDATE_SH,
        'astra_install': EMBEDDED_ASTRA_INSTALL_SH,
    }}
    
    if script_name not in scripts:
        print(f"[ERROR] Неизвестный скрипт: {{script_name}}")
        return False
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write(scripts[script_name])
        temp_script = f.name
    
    try:
        os.chmod(temp_script, 0o755)
        result = subprocess.run(['bash', temp_script], check=False)
        return result.returncode == 0
    finally:
        os.unlink(temp_script)

# ============================================================================
# ГЛАВНАЯ ТОЧКА ВХОДА (UNIFIED VERSION)
# ============================================================================

if __name__ == '__main__':
    import sys
    import os
    import threading
    
    UNIFIED_VERSION = "{version}"
    
    # Парсим аргументы
    skip_update = '--skip-update' in sys.argv
    force_update = '--force-update' in sys.argv
    console_mode = '--console' in sys.argv
    is_frozen = getattr(sys, 'frozen', False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # РЕЖИМ 1: Принудительное обновление (--force-update)
    # Сначала обновляется, потом продолжает работу
    # ═══════════════════════════════════════════════════════════════════════
    if force_update and not skip_update:
        print(f"[INFO] FSA-AstraInstall {{UNIFIED_VERSION}}")
        print("[INFO] Принудительное обновление...")
        try:
            updater = SelfUpdater(UNIFIED_VERSION)
            new_ver = updater.check_for_updates()
            if new_ver:
                print(f"[INFO] Найдена версия: {{new_ver}}")
                if updater.download_and_apply():
                    print("[INFO] ✓ Обновление применено!")
                    updater.restart()  # Перезапуск с --skip-update
            else:
                print("[INFO] ✓ Установлена актуальная версия")
        except Exception as e:
            print(f"[WARNING] Ошибка обновления: {{e}}")
        # Продолжаем работу даже если обновление не удалось
    
    # ═══════════════════════════════════════════════════════════════════════
    # РЕЖИМ 2: Консольный режим (--console)
    # Только выводим информацию о наличии обновления в лог
    # ═══════════════════════════════════════════════════════════════════════
    elif console_mode and not skip_update:
        print(f"[INFO] FSA-AstraInstall {{UNIFIED_VERSION}}")
        print("[INFO] Проверка обновлений...")
        try:
            updater = SelfUpdater(UNIFIED_VERSION)
            new_ver = updater.check_for_updates()
            if new_ver:
                print("[INFO] " + "=" * 50)
                print(f"[INFO] ⬆️  ДОСТУПНО ОБНОВЛЕНИЕ: {{new_ver}}")
                print(f"[INFO]    Для обновления: ./FSA-AstraInstall --force-update")
                print("[INFO] " + "=" * 50)
            else:
                print("[INFO] ✓ Установлена актуальная версия")
        except Exception as e:
            print(f"[WARNING] Не удалось проверить обновления: {{e}}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # РЕЖИМ 3: GUI режим (по умолчанию)
    # Отложенная проверка через 3 сек, показ диалога
    # ═══════════════════════════════════════════════════════════════════════
    elif not console_mode and not skip_update:
        def delayed_update_check():
            \"\"\"Отложенная проверка обновлений для GUI\"\"\"
            import time
            time.sleep(3)  # Ждём 3 секунды после запуска GUI
            
            try:
                updater = SelfUpdater(UNIFIED_VERSION)
                new_ver = updater.check_for_updates()
                if new_ver:
                    # Показываем диалог в главном потоке
                    # Используем глобальную переменную для передачи данных
                    global _update_available
                    _update_available = (new_ver, updater)
            except Exception:
                pass
        
        # Запускаем проверку в фоновом потоке
        _update_available = None
        update_thread = threading.Thread(target=delayed_update_check, daemon=True)
        update_thread.start()
    
    # ═══════════════════════════════════════════════════════════════════════
    # Специальные режимы
    # ═══════════════════════════════════════════════════════════════════════
    if '--update-only' in sys.argv:
        print("[INFO] Режим: только обновление из сети")
        run_embedded_bash('astra_update')
        sys.exit(0)
    
    if '--install-deps-only' in sys.argv:
        print("[INFO] Режим: только установка зависимостей")
        run_embedded_bash('astra_install')
        sys.exit(0)
    
    # ═══════════════════════════════════════════════════════════════════════
    # Запуск основного приложения
    # ═══════════════════════════════════════════════════════════════════════
    clean_argv = [arg for arg in sys.argv if arg not in (
        '--skip-update', '--force-update', '--update-only', '--install-deps-only'
    )]
    sys.argv = clean_argv
    
    main()
'''

# ============================================================================
# СБОРКА ОБЪЕДИНЁННОГО ФАЙЛА
# ============================================================================

def build_unified_file():
    """Создаёт объединённый файл"""
    
    print("=" * 60)
    print("=== Сборка FSA-AstraInstall Unified ===")
    print("=" * 60)
    
    # Создаём директорию build
    BUILD_DIR.mkdir(exist_ok=True)
    
    # Проверяем наличие всех файлов
    print_step("Проверка исходных файлов...")
    required_files = [
        (ASTRA_AUTOMATION_PY, "astra_automation.py"),
        (ASTRA_UPDATE_SH, "astra_update.sh"),
        (ASTRA_INSTALL_SH, "astra_install.sh"),
        (SELF_UPDATER_PY, "self_updater.py"),
    ]
    
    for filepath, name in required_files:
        if not filepath.exists():
            print_error(f"Файл не найден: {name}")
            sys.exit(1)
        size = filepath.stat().st_size / 1024
        print_info(f"  {name}: {size:.1f} KB")
    
    # Читаем исходные файлы
    print_step("Чтение исходных файлов...")
    astra_automation_content = read_file_safe(ASTRA_AUTOMATION_PY)
    astra_update_content = read_file_safe(ASTRA_UPDATE_SH)
    astra_install_content = read_file_safe(ASTRA_INSTALL_SH)
    self_updater_content = read_file_safe(SELF_UPDATER_PY)
    
    # Получаем версию
    version = get_version_from_file(ASTRA_AUTOMATION_PY)
    print_info(f"Версия: {version}")
    
    # Извлекаем __future__ импорты
    print_step("Обработка импортов...")
    future_imports, astra_automation_rest = extract_future_imports(astra_automation_content)
    if future_imports:
        print_info(f"  Найдено __future__ импортов: {len(future_imports)}")
    
    # Извлекаем класс SelfUpdater
    print_step("Извлечение модуля самообновления...")
    self_updater_class = extract_self_updater_class(self_updater_content)
    
    # Экранируем bash-скрипты
    print_step("Подготовка bash-скриптов...")
    astra_update_escaped = escape_bash_for_python(astra_update_content)
    astra_install_escaped = escape_bash_for_python(astra_install_content)
    
    # Удаляем оригинальный блок if __name__ == '__main__' из astra_automation.py
    print_step("Модификация точки входа...")
    # Ищем последний if __name__ == '__main__' и удаляем всё после него
    main_block_pattern = r"\nif\s+__name__\s*==\s*['\"]__main__['\"]\s*:"
    matches = list(re.finditer(main_block_pattern, astra_automation_rest))
    if matches:
        last_match = matches[-1]
        astra_automation_rest = astra_automation_rest[:last_match.start()]
        print_info("  Оригинальный блок __main__ удалён")
    
    # Формируем объединённый файл
    print_step("Формирование объединённого файла...")
    
    today = datetime.now().strftime("%Y.%m.%d")
    
    unified_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FSA-AstraInstall - Единый исполняемый файл

Объединяет функциональность:
- astra_update.sh (обновление из сетевых источников)
- astra_install.sh (установка зависимостей)
- astra_automation.py (основное приложение)
- self_updater.py (самообновление бинарника)

Версия: {version}
Дата сборки: {today}
Компания: ООО "НПА Вира-Реалтайм"

АВТОМАТИЧЕСКИ СГЕНЕРИРОВАННЫЙ ФАЙЛ
Не редактируйте вручную - изменения будут потеряны при пересборке!
Редактируйте исходные файлы и запускайте build_unified.py
"""

# КРИТИЧНО: __future__ импорты должны быть в самом начале
{chr(10).join(future_imports) if future_imports else '# (нет __future__ импортов)'}

# ============================================================================
# ВСТРОЕННЫЕ BASH-СКРИПТЫ
# ============================================================================

# astra_update.sh - обновление из сетевых источников
EMBEDDED_ASTRA_UPDATE_SH = r"""
{astra_update_escaped}
"""

# astra_install.sh - установка зависимостей
EMBEDDED_ASTRA_INSTALL_SH = r"""
{astra_install_escaped}
"""

# ============================================================================
# МОДУЛЬ САМООБНОВЛЕНИЯ (из self_updater.py)
# ============================================================================

{self_updater_class}

# ============================================================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ (из astra_automation.py)
# ============================================================================

{astra_automation_rest}

{create_new_main_block(version)}
'''
    
    # Записываем объединённый файл
    print_step(f"Запись объединённого файла...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(unified_content)
    
    # Статистика
    output_size = OUTPUT_FILE.stat().st_size
    output_lines = len(unified_content.split('\n'))
    
    print_success(f"Объединённый файл создан: {OUTPUT_FILE}")
    print_info(f"  Размер: {output_size / 1024:.1f} KB ({output_size / 1024 / 1024:.2f} MB)")
    print_info(f"  Строк: {output_lines}")
    
    return OUTPUT_FILE

# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

if __name__ == '__main__':
    try:
        output_file = build_unified_file()
        
        print("\n" + "=" * 60)
        print("=== Сборка завершена успешно ===")
        print("=" * 60)
        print(f"\nРезультат: {output_file}")
        print("\nСледующие шаги:")
        print("  1. Проверить синтаксис: python3 -m py_compile build/FSA-AstraInstall_unified.py")
        print("  2. Запустить сборку бинарника: python3 build_executables.py")
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n[!] Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print_error(f"Ошибка сборки: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт сборки бинарных файлов для Linux
Работает только на macOS, собирает через Docker
На Linux нужен только один файл - он подтянет остальное из источников
Версия: V2.6.133 (2025.11.16)
Компания: ООО "НПА Вира-Реалтайм"
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
BIN_DIR = SCRIPT_DIR / "bin"
BUILD_DIR = SCRIPT_DIR / "build"
TEMP_UNIFIED_FILE = BUILD_DIR / "astra_automation_unified_temp.py"

HOST_PLATFORM = platform.system().lower()

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

def check_docker():
    """Проверяет наличие Docker"""
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def wait_for_docker(max_wait=120):
    """Ожидает запуска Docker daemon"""
    print_info("Ожидание запуска Docker daemon...")
    for i in range(max_wait):
        try:
            result = subprocess.run(["docker", "ps"], 
                                  capture_output=True, text=True, timeout=2)
            # Проверяем что нет ошибок подключения
            error_text = result.stderr + result.stdout
            if result.returncode == 0 and "Cannot connect" not in error_text:
                print_success("Docker daemon запущен")
                return True
        except:
            pass
        if i % 10 == 0 and i > 0:
            print_info(f"Ожидание... ({i}/{max_wait} сек)")
        import time
        time.sleep(1)
    print_error("Docker daemon не запустился за отведенное время")
    print_info("Запустите Docker Desktop вручную")
    return False

def run_command(cmd, check=True, **kwargs):
    """Выполняет команду"""
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True, **kwargs)
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Ошибка: {' '.join(cmd)}")
        if e.stderr:
            print(e.stderr)
        raise

# ============================================================================
# ПРОВЕРКА ПЛАТФОРМЫ
# ============================================================================

def check_platform():
    """Проверяет что сборка запущена на macOS"""
    print("=" * 60)
    print("=== Сборка бинарных файлов для Linux ===")
    print("=" * 60)
    print_info(f"Платформа: {HOST_PLATFORM}")
    
    if HOST_PLATFORM != "darwin":
        print_error("Сборка должна запускаться на macOS!")
        print_info("На Linux бинарники не нужны - там работают скрипты")
        return False
    
    if not check_docker():
        print_error("Docker не найден!")
        print_info("Установите Docker Desktop: https://www.docker.com/products/docker-desktop")
        return False
    
    # Проверяем доступность Docker daemon
    docker_ready = False
    try:
        result = subprocess.run(["docker", "ps"], 
                              capture_output=True, text=True, timeout=3)
        # Проверяем и returncode и отсутствие ошибок в stderr
        if result.returncode == 0 and "Cannot connect" not in result.stderr:
            docker_ready = True
    except:
        pass
    
    if not docker_ready:
        if not wait_for_docker():
            return False
    
    print_success("Docker доступен")
    BIN_DIR.mkdir(exist_ok=True)
    BUILD_DIR.mkdir(exist_ok=True)
    return True

# ============================================================================
# ГЕНЕРАЦИЯ ОБЪЕДИНЕННОГО ФАЙЛА
# ============================================================================

def get_install_functions():
    """Функции из astra_install.sh (переписаны на Python)"""
    return '''# ============================================================================
# БЛОК 1: ФУНКЦИИ ИЗ astra_install.sh (переписаны на Python)
# Автоматически добавлено при сборке
# ============================================================================

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

def minimize_terminal_window(terminal_pid=None):
    """Сворачивает окно терминала через xdotool"""
    if not shutil.which("xdotool"):
        return False
    try:
        if terminal_pid:
            cmd = ["xdotool", "search", "--pid", str(terminal_pid)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                window_ids = result.stdout.strip().split('\\n')
                for window_id in window_ids:
                    if window_id:
                        subprocess.run(["xdotool", "windowminimize", window_id], 
                                     capture_output=True, timeout=1)
                return True
    except:
        pass
    return False

def check_root_and_restart():
    """Проверяет права root и перезапускается через sudo если нужно"""
    if os.geteuid() != 0:
        print("[i] Требуются права root. Перезапуск через sudo...")
        env = os.environ.copy()
        sudo_cmd = ["sudo", "-E"] + sys.argv
        os.execvpe("sudo", sudo_cmd, env)
    return True

def sync_time():
    """Синхронизирует системное время"""
    time_sync_flag = Path("/tmp/fsa-time-synced")
    if time_sync_flag.exists():
        return True
    
    if shutil.which("timedatectl"):
        try:
            result = subprocess.run(["timedatectl", "set-ntp", "true"], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                time_sync_flag.write_text(time.strftime('%Y-%m-%d %H:%M:%S'))
                return True
        except:
            pass
    
    if shutil.which("ntpdate"):
        for server in ["time.nist.gov", "pool.ntp.org"]:
            try:
                result = subprocess.run(["ntpdate", "-s", server], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    time_sync_flag.write_text(time.strftime('%Y-%m-%d %H:%M:%S'))
                    return True
            except:
                continue
    
    return False

def check_tkinter():
    """Проверяет доступность tkinter"""
    try:
        import tkinter
        return True
    except ImportError:
        return False

def install_tkinter():
    """Устанавливает tkinter через apt-get"""
    packages = ["python3-tk", "python3-tkinter", "tk"]
    env = os.environ.copy()
    env.update({
        "DEBIAN_FRONTEND": "noninteractive",
        "DEBIAN_PRIORITY": "critical",
        "APT_LISTCHANGES_FRONTEND": "none"
    })
    
    dpkg_opts = [
        "-o", "Dpkg::Options::=--force-confdef",
        "-o", "Dpkg::Options::=--force-confnew",
        "-o", "Dpkg::Options::=--force-confmiss"
    ]
    
    for pkg in packages:
        try:
            result = subprocess.run(["apt-cache", "show", pkg], 
                                  capture_output=True, timeout=5)
            if result.returncode != 0:
                continue
            
            cmd = ["apt-get", "install", "-y"] + dpkg_opts + [pkg]
            result = subprocess.run(cmd, env=env, capture_output=True, timeout=300)
            if result.returncode == 0:
                if check_tkinter():
                    return True
        except:
            continue
    return False

# Выполняем инициализацию перед основным кодом
if __name__ == "__main__" or True:
    check_root_and_restart()
    if "--console" not in sys.argv:
        minimize_terminal_window()
    sync_time()
    os.environ.setdefault("DEBIAN_FRONTEND", "noninteractive")
    os.environ.setdefault("DEBIAN_PRIORITY", "critical")
    os.environ.setdefault("APT_LISTCHANGES_FRONTEND", "none")

# ============================================================================
# БЛОК 2: ВЕСЬ КОД ИЗ astra_automation.py
# ============================================================================

'''

def generate_unified_file():
    """Генерирует объединенный файл"""
    print_step("Генерация временного объединенного файла...")
    
    automation_file = SCRIPT_DIR / "astra_automation.py"
    if not automation_file.exists():
        print_error(f"Файл не найден: {automation_file}")
        return False
    
    with open(automation_file, 'r', encoding='utf-8') as f:
        automation_content = f.read()
    
    # Убираем shebang и encoding
    lines = automation_content.split('\n')
    start_line = 0
    if lines[0].startswith('#!'):
        start_line = 1
    if start_line < len(lines) and ('coding' in lines[start_line] or 'encoding' in lines[start_line]):
        start_line += 1
    
    # Извлекаем все __future__ импорты из ВСЕГО файла (не только после start_line)
    future_imports = []
    remaining_lines = []
    
    # Обрабатываем все строки начиная с start_line
    for i, line in enumerate(lines[start_line:], start=start_line):
        stripped = line.strip()
        # Проверяем на __future__ импорт
        if stripped.startswith('from __future__') or stripped.startswith('import __future__'):
            if line not in future_imports:  # Избегаем дубликатов
                future_imports.append(line)
        else:
            remaining_lines.append(line)
    
    # Также проверяем весь automation_content на наличие __future__ и удаляем
    automation_content_clean = '\n'.join(remaining_lines)
    # Дополнительная очистка - удаляем все __future__ импорты которые могли остаться
    automation_lines_clean = []
    for line in automation_content_clean.split('\n'):
        stripped = line.strip()
        if not (stripped.startswith('from __future__') or stripped.startswith('import __future__')):
            automation_lines_clean.append(line)
    
    automation_content = '\n'.join(automation_lines_clean)
    
    # Формируем future_imports_str
    if future_imports:
        future_imports_str = '\n'.join(future_imports) + '\n'
    else:
        future_imports_str = ''
    
    # ОТЛАДКА: проверяем что извлекли
    if not future_imports and 'from __future__' in automation_content:
        print_error("ОШИБКА: __future__ импорты не извлечены из automation_content!")
        # Принудительно ищем и удаляем
        automation_lines = automation_content.split('\n')
        automation_content = '\n'.join([l for l in automation_lines if 'from __future__' not in l and 'import __future__' not in l])
        # Ищем в исходном файле
        for line in lines[start_line:]:
            if 'from __future__' in line or 'import __future__' in line:
                if not future_imports_str:
                    future_imports_str = line + '\n'
                else:
                    future_imports_str += line + '\n'
    
    # КРИТИЧНО: убеждаемся что future_imports_str правильный
    if future_imports and not future_imports_str.strip():
        future_imports_str = '\n'.join(future_imports) + '\n'
    
    # Формируем unified_content с __future__ импортами сразу после encoding
    unified_content = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
{future_imports_str}"""
ОБЪЕДИНЕННЫЙ ФАЙЛ: автоматически сгенерирован из astra_install.sh + astra_automation.py
Версия: V2.5.124 (2025.11.14)
Компания: ООО "НПА Вира-Реалтайм"

ВНИМАНИЕ: Этот файл создан автоматически при сборке и будет удален после компиляции!
"""

{get_install_functions()}

{automation_content}
'''
    
    # Записываем файл
    with open(TEMP_UNIFIED_FILE, 'w', encoding='utf-8') as f:
        f.write(unified_content)
    
    # КРИТИЧНО: Принудительно исправляем файл используя рабочую логику
    with open(TEMP_UNIFIED_FILE, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n\r') for line in f.readlines()]
    
    future_imps = [l.strip() for l in lines if l.strip().startswith('from __future__') or l.strip().startswith('import __future__')]
    other_lns = [l for l in lines if not (l.strip().startswith('from __future__') or l.strip().startswith('import __future__'))]
    
    if future_imps:
        enc_idx = next((i for i, l in enumerate(other_lns) if 'coding' in l or 'encoding' in l), -1)
        if enc_idx >= 0:
            new_lns = []
            for i, l in enumerate(other_lns):
                new_lns.append(l)
                if i == enc_idx:
                    new_lns.extend(future_imps)
            with open(TEMP_UNIFIED_FILE, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lns) + '\n')
    
    # Проверка
    with open(TEMP_UNIFIED_FILE, 'r', encoding='utf-8') as f:
        first_5 = f.readlines()[:5]
        if any('from __future__' in line for line in first_5):
            print_success("Объединенный файл создан (__future__ импорты в начале)")
        else:
            print_error("ПРОБЛЕМА: __future__ импорты не в начале!")
    
    return True

# ============================================================================
# СБОРКА ЧЕРЕЗ DOCKER
# ============================================================================

def build_in_docker():
    """Собирает бинарники для Linux в Docker"""
    print_step("Сборка для Linux через Docker...")
    
    # КРИТИЧНО: Сначала создаем объединенный файл через build_unified.py
    print_step("Создание объединенного файла через build_unified.py...")
    build_unified_script = SCRIPT_DIR / "build_unified.py"
    if not build_unified_script.exists():
        print_error(f"Файл не найден: {build_unified_script}")
        return False
    
    try:
        result = subprocess.run([
            sys.executable, str(build_unified_script)
        ], capture_output=True, text=True, check=True)
        print_success("Объединенный файл создан")
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print_error(f"Ошибка создания объединенного файла: {e}")
        if e.stderr:
            print(e.stderr)
        return False
    
    # Проверяем что объединенный файл создан
    unified_file = BUILD_DIR / "FSA-AstraInstall_unified.py"
    if not unified_file.exists():
        print_error(f"Объединенный файл не создан: {unified_file}")
        return False
    
    print_success(f"Объединенный файл готов: {unified_file}")
    
    # Dockerfile для сборки
    dockerfile_content = '''FROM python:3.9-slim

# Устанавливаем инструменты сборки
RUN apt-get update && apt-get install -y \\
    gcc \\
    make \\
    wget \\
    autoconf \\
    binutils \\
    && rm -rf /var/lib/apt/lists/*

# Компилируем shc из исходников (shc нет в репозиториях Debian)
# Используем оригинальный репозиторий shc
RUN cd /tmp && \\
    wget -q https://github.com/neurobin/shc/archive/refs/tags/4.0.3.tar.gz -O shc.tar.gz && \\
    tar -xzf shc.tar.gz && \\
    cd shc-4.0.3 && \\
    ./configure && \\
    make && \\
    mkdir -p /usr/local/bin /usr/local/man/man1 && \\
    cp src/shc /usr/local/bin/ && \\
    cp shc.1 /usr/local/man/man1/ 2>/dev/null || true && \\
    chmod +x /usr/local/bin/shc && \\
    cd / && \\
    rm -rf /tmp/shc-* && \\
    test -f /usr/local/bin/shc && echo "shc установлен"

# Устанавливаем PyInstaller
RUN pip install pyinstaller

WORKDIR /build

# Копируем файлы проекта
COPY . /build/
'''
    
    dockerfile_path = SCRIPT_DIR / "Dockerfile.build"
    with open(dockerfile_path, 'w') as f:
        f.write(dockerfile_content)
    
    # .dockerignore
    dockerignore_content = '''bin/
build/
__pycache__/
*.pyc
*.x.c
*.x
History/
Log/
.git/
'''
    
    dockerignore_path = SCRIPT_DIR / ".dockerignore.build"
    with open(dockerignore_path, 'w') as f:
        f.write(dockerignore_content)
    
    # Проверяем Docker daemon перед сборкой
    print_step("Проверка Docker daemon...")
    docker_ready = False
    try:
        result = subprocess.run(["docker", "ps"], 
                              capture_output=True, text=True, timeout=3)
        if result.returncode == 0 and "Cannot connect" not in result.stderr:
            docker_ready = True
    except:
        pass
    
    if not docker_ready:
        print_info("Docker daemon недоступен, ожидание запуска...")
        if not wait_for_docker():
            print_error("Не удалось подключиться к Docker daemon")
            return False
    
    # Собираем образ
    image_name = "fsa-astrainstall-builder"
    print_step("Сборка Docker образа (это может занять время)...")
    try:
        run_command([
            "docker", "build",
            "--platform", "linux/amd64",
            "--no-cache",
            "-f", str(dockerfile_path),
            "-t", image_name,
            str(SCRIPT_DIR)
        ])
        print_success("Docker образ собран")
    except:
        print_error("Не удалось собрать Docker образ")
        return False
    
    # КРИТИЧНО: Принудительно исправляем файл перед сборкой
    print_step("Проверка и исправление объединенного файла...")
    if TEMP_UNIFIED_FILE.exists():
        with open(TEMP_UNIFIED_FILE, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n\r') for line in f.readlines()]
        
        future_imports = []
        other_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('from __future__') or stripped.startswith('import __future__'):
                if stripped not in [f.strip() for f in future_imports]:
                    future_imports.append(stripped)
            else:
                other_lines.append(line)
        
        if future_imports:
            encoding_idx = -1
            for i, line in enumerate(other_lines):
                if 'coding' in line or 'encoding' in line:
                    encoding_idx = i
                    break
            
            if encoding_idx >= 0:
                new_lines = []
                for i, line in enumerate(other_lines):
                    new_lines.append(line)
                    if i == encoding_idx:
                        for future_imp in future_imports:
                            new_lines.append(future_imp)
                
                with open(TEMP_UNIFIED_FILE, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                    f.write('\n')
                print_success("Файл исправлен: __future__ импорты перемещены в начало")
    
    # Запускаем сборку
    print_step("Запуск сборки в Docker...")
    container_name = "fsa-builder-temp"
    
    try:
        subprocess.run(["docker", "rm", "-f", container_name], 
                      capture_output=True)
        
        # Создаем Python скрипт для исправления __future__ импортов
        fix_script_path = BUILD_DIR / "fix_future_imports.py"
        # Удаляем старый скрипт если есть
        if fix_script_path.exists():
            fix_script_path.unlink()
        fix_script_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

f = Path('build/FSA-AstraInstall_unified.py')
if f.exists():
    with open(f, 'r', encoding='utf-8') as file:
        lines = [l.rstrip('\\n\\r') for l in file.readlines()]
    future = [l.strip() for l in lines if l.strip().startswith('from __future__') or l.strip().startswith('import __future__')]
    other = [l for l in lines if not (l.strip().startswith('from __future__') or l.strip().startswith('import __future__'))]
    if future:
        enc_idx = next((i for i, l in enumerate(other) if 'coding' in l or 'encoding' in l), -1)
        if enc_idx >= 0:
            new = []
            for i, l in enumerate(other):
                new.append(l)
                if i == enc_idx:
                    new.extend(future)
            with open(f, 'w', encoding='utf-8') as file:
                file.write('\\n'.join(new) + '\\n')
            print(f'[OK] Исправлено: {len(future)} __future__ импортов', file=sys.stderr)
            sys.exit(0)
        else:
            print('[ERROR] Не найдена строка encoding!', file=sys.stderr)
            sys.exit(1)
    else:
        print('[INFO] __future__ импорты не найдены', file=sys.stderr)
        sys.exit(0)
else:
    print('[ERROR] Файл не найден!', file=sys.stderr)
    sys.exit(1)
'''
        
        with open(fix_script_path, 'w') as f:
            f.write(fix_script_content)
        os.chmod(fix_script_path, 0o755)
        
        # Создаем временный скрипт сборки
        build_script_path = BUILD_DIR / "docker_build.sh"
        # Удаляем старый скрипт если есть
        if build_script_path.exists():
            build_script_path.unlink()
        build_script_content = '''#!/bin/bash
set -e
export PATH="/usr/local/bin:$PATH"

cd /build
mkdir -p bin build

# КРИТИЧНО: Сначала исправляем __future__ импорты в объединенном файле
echo "[#] Исправление __future__ импортов (ПЕРВЫМ ДЕЛОМ)..." >&2
python3 /build/build/fix_future_imports.py

# Компилируем объединенный файл FSA-AstraInstall_unified.py в FSA-AstraInstall
echo "[#] Компиляция FSA-AstraInstall_unified.py в FSA-AstraInstall..."
pyinstaller --onefile --console \\
    --name FSA-AstraInstall \\
    --distpath bin \\
    --workpath build \\
    --specpath build \\
    --clean \\
    build/FSA-AstraInstall_unified.py

# Устанавливаем права на выполнение
chmod +x bin/FSA-AstraInstall 2>/dev/null || true

echo "[OK] Сборка завершена"
echo "[OK] Создан файл: bin/FSA-AstraInstall"
'''
        
        with open(build_script_path, 'w') as f:
            f.write(build_script_content)
        os.chmod(build_script_path, 0o755)
        
        # Запускаем сборку через bash с файлом скрипта
        # Используем прямой subprocess.run чтобы видеть вывод в реальном времени
        print_step("Запуск сборки в Docker (вывод будет виден в реальном времени)...")
        try:
            result = subprocess.run([
                "docker", "run",
                "--platform", "linux/amd64",
                "--name", container_name,
                "-v", f"{SCRIPT_DIR}:/build",
                image_name,
                "bash", "/build/build/docker_build.sh"
            ], check=True)  # Не используем capture_output - вывод будет виден
        except subprocess.CalledProcessError as e:
            print_error(f"Ошибка сборки в Docker (код выхода: {e.returncode})")
            print_info("Проверьте логи контейнера: docker logs fsa-builder-temp")
            raise
        
        # Копируем результаты
        print_step("Копирование результатов...")
        result = subprocess.run([
            "docker", "cp", f"{container_name}:/build/bin/.", str(BIN_DIR)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print_success("Результаты скопированы")
        else:
            print_error(f"Ошибка копирования: {result.stderr}")
        
        subprocess.run(["docker", "rm", "-f", container_name], 
                      capture_output=True)
        
        return True
        
    except Exception as e:
        print_error(f"Ошибка: {e}")
        subprocess.run(["docker", "rm", "-f", container_name], 
                      capture_output=True)
        return False

# ============================================================================
# ОЧИСТКА
# ============================================================================

def cleanup():
    """Удаляет временные файлы"""
    print_step("Очистка временных файлов...")
    
    if TEMP_UNIFIED_FILE.exists():
        TEMP_UNIFIED_FILE.unlink()
    
    fix_script = BUILD_DIR / "fix_future_imports.py"
    if fix_script.exists():
        fix_script.unlink()
    
    dockerfile = SCRIPT_DIR / "Dockerfile.build"
    if dockerfile.exists():
        dockerfile.unlink()
    
    dockerignore = SCRIPT_DIR / ".dockerignore.build"
    if dockerignore.exists():
        dockerignore.unlink()
    
    print_success("Временные файлы удалены")

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    """Главная функция"""
    try:
        if not check_platform():
            return 1
        
        if not generate_unified_file():
            return 1
        
        if not build_in_docker():
            return 1
        
        cleanup()
        
        print("\n" + "=" * 60)
        print("=== Сборка завершена успешно ===")
        print("=" * 60)
        print(f"\nБинарные файлы для Linux: {BIN_DIR}")
        print("\nФайлы:")
        for file in sorted(BIN_DIR.glob("astra_*")):
            if file.is_file():
                size = file.stat().st_size / (1024 * 1024)
                print(f"  {file.name:30} {size:8.2f} MB")
        
        print("\n[OK] Готово! На Linux эти файлы подтянут остальное из источников.")
        return 0
        
    except KeyboardInterrupt:
        print("\n[ERROR] Прервано пользователем")
        cleanup()
        return 1
    except Exception as e:
        print_error(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        return 1

if __name__ == "__main__":
    sys.exit(main())


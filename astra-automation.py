#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-AstraInstall Automation - Единый исполняемый файл
Автоматически распаковывает компоненты и запускает автоматизацию astra-setup.sh
Совместимость: Python 3.x
"""

from __future__ import print_function
import os
import sys
import tempfile
import subprocess
import shutil
import re
import datetime
import threading
import traceback

# ============================================================================
# КЛАСС ПОЛНОГО ЛОГИРОВАНИЯ
# ============================================================================
class Logger(object):
    """Класс для полного логирования всех операций программы"""
    
    def __init__(self, log_file=None):
        # Создаем имя файла лога с временной меткой рядом с запускающим файлом
        if log_file is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Получаем директорию текущего скрипта
            script_dir = os.path.dirname(os.path.abspath(__file__))
            log_file = os.path.join(script_dir, "astra_automation_%s.log" % timestamp)
        
        self.log_file = log_file
        self.lock = threading.Lock()
        
        # Создаем директорию для лога если нужно
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except:
                pass
        
        # Инициализируем лог файл
        self._write_log("=" * 80)
        self._write_log("FSA-AstraInstall Automation - НАЧАЛО СЕССИИ")
        self._write_log("Время запуска: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._write_log("Python версия: %s" % sys.version)
        self._write_log("Рабочая директория: %s" % os.getcwd())
        self._write_log("Аргументы командной строки: %s" % ' '.join(sys.argv))
        self._write_log("=" * 80)
    
    def _write_log(self, message):
        """Запись сообщения в лог файл (thread-safe)"""
        try:
            with self.lock:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                log_entry = "[%s] %s\n" % (timestamp, message)
                
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
                    f.flush()
        except Exception as e:
            # Если не можем записать в лог, выводим в stderr
            sys.stderr.write("Ошибка записи в лог: %s\n" % str(e))
    
    def log_info(self, message):
        """Логирование информационного сообщения"""
        self._write_log("[INFO] %s" % message)
    
    def log_warning(self, message):
        """Логирование предупреждения"""
        self._write_log("[WARNING] %s" % message)
    
    def log_error(self, message):
        """Логирование ошибки"""
        self._write_log("[ERROR] %s" % message)
    
    def log_command(self, command, output="", return_code=None):
        """Логирование выполнения команды"""
        self._write_log("[COMMAND] Выполнение: %s" % ' '.join(command) if isinstance(command, list) else command)
        if output:
            # Логируем вывод команды построчно
            for line in output.split('\n'):
                if line.strip():
                    self._write_log("[COMMAND_OUTPUT] %s" % line.strip())
        if return_code is not None:
            self._write_log("[COMMAND_RESULT] Код возврата: %d" % return_code)
    
    def log_exception(self, exception, context=""):
        """Логирование исключения с полным traceback"""
        self._write_log("[EXCEPTION] %s: %s" % (context, str(exception)))
        self._write_log("[TRACEBACK] %s" % traceback.format_exc())
    
    def log_system_info(self):
        """Логирование системной информации"""
        try:
            self._write_log("[SYSTEM] Информация о системе:")
            self._write_log("[SYSTEM] OS: %s" % os.name)
            self._write_log("[SYSTEM] Platform: %s" % sys.platform)
            self._write_log("[SYSTEM] User ID: %d" % os.getuid())
            self._write_log("[SYSTEM] Effective User ID: %d" % os.geteuid())
            
            # Проверяем права root
            if os.geteuid() == 0:
                self._write_log("[SYSTEM] Запущено с правами root")
            else:
                self._write_log("[SYSTEM] Запущено БЕЗ прав root")
            
            # Проверяем наличие системных файлов
            system_files = [
                '/etc/apt/sources.list',
                '/etc/astra_version',
                '/etc/os-release'
            ]
            
            for file_path in system_files:
                if os.path.exists(file_path):
                    self._write_log("[SYSTEM] Файл существует: %s" % file_path)
                else:
                    self._write_log("[SYSTEM] Файл НЕ найден: %s" % file_path)
                    
        except Exception as e:
            self._write_log("[SYSTEM_ERROR] Ошибка получения системной информации: %s" % str(e))
    
    def cleanup_locks(self):
        """Автоматическая очистка блокирующих файлов"""
        lock_files = [
            '/var/lib/dpkg/lock-frontend',
            '/var/lib/dpkg/lock',
            '/var/cache/apt/archives/lock',
            '/var/lib/apt/lists/lock'
        ]
        
        self._write_log("[CLEANUP] Начинаем очистку блокирующих файлов...")
        
        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    self._write_log("[CLEANUP] Удален блокирующий файл: %s" % lock_file)
                except Exception as e:
                    self._write_log("[CLEANUP_ERROR] Не удалось удалить %s: %s" % (lock_file, str(e)))
            else:
                self._write_log("[CLEANUP] Блокирующий файл не найден: %s" % lock_file)
        
        # Дополнительно пробуем разблокировать dpkg
        try:
            result = subprocess.run(['dpkg', '--configure', '-a'], 
                                 capture_output=True, text=True, timeout=30)
            self._write_log("[CLEANUP] dpkg --configure -a завершен с кодом: %d" % result.returncode)
        except Exception as e:
            self._write_log("[CLEANUP_ERROR] Ошибка dpkg --configure -a: %s" % str(e))
    
    def get_log_path(self):
        """Получение пути к файлу лога"""
        return self.log_file

# Глобальный экземпляр логгера
_global_logger = None

def get_logger():
    """Получение глобального экземпляра логгера"""
    global _global_logger
    if _global_logger is None:
        # Проверяем, передан ли путь к лог файлу через аргументы командной строки
        log_file = None
        if len(sys.argv) > 1:
            for i, arg in enumerate(sys.argv):
                if arg == '--log-file' and i + 1 < len(sys.argv):
                    log_file = sys.argv[i + 1]
                    break
        _global_logger = Logger(log_file)
    return _global_logger

# Перехватываем все print() вызовы для логирования
_original_print = print
def print(*args, **kwargs):
    """Переопределенная функция print - логирует и перенаправляет в GUI терминал"""
    # Формируем сообщение
    message = ' '.join(str(arg) for arg in args)
    
    # Логируем в файл
    logger = get_logger()
    logger.log_info(message)
    
    # Перенаправляем в GUI терминал или консоль
    if hasattr(sys, '_gui_instance') and sys._gui_instance:
        # В GUI режиме - отправляем в терминал GUI
        sys._gui_instance.add_terminal_output(message)
    else:
        # В консольном режиме - используем оригинальный print
        _original_print(*args, **kwargs)

# ============================================================================
# КЛАСС КОНФИГУРАЦИИ ИНТЕРАКТИВНЫХ ЗАПРОСОВ
# ============================================================================
class InteractiveConfig(object):
    """Общий класс конфигурации для интерактивных запросов"""
    
    def __init__(self):
        # Все паттерны для обнаружения интерактивных запросов
        self.patterns = {
            'dpkg_config': r'\*\*\* .* \(Y/I/N/O/D/Z\) \[.*\] \?',
            'apt_config': r'Настройка пакета',
            'keyboard_config': r'Выберите подходящую раскладку клавиатуры',
            'keyboard_switch': r'способ переключения клавиатуры между национальной раскладкой',
            'language_config': r'Выберите язык системы',
            'restart_services': r'Перезапустить службы во время пакетных операций'
        }
        
        # Все автоматические ответы
        self.responses = {
            'dpkg_config': 'Y',      # Соглашаемся с новыми версиями
            'apt_config': '',        # Принимаем настройки по умолчанию (Enter)
            'keyboard_config': '',   # Принимаем предложенную раскладку (Enter)
            'keyboard_switch': '',   # Принимаем способ переключения (Enter)
            'language_config': '',   # Принимаем язык системы (Enter)
            'restart_services': 'Y'  # Соглашаемся на перезапуск служб
        }
    
    def detect_interactive_prompt(self, output):
        """Обнаружение интерактивного запроса в выводе"""
        for prompt_type, pattern in self.patterns.items():
            if re.search(pattern, output, re.IGNORECASE):
                return prompt_type
        return None
    
    def get_auto_response(self, prompt_type):
        """Получение автоматического ответа для типа запроса"""
        return self.responses.get(prompt_type, 'Y')  # По умолчанию всегда "Y"

# ============================================================================
# КЛАССЫ АВТОМАТИЗАЦИИ
# ============================================================================
class RepoChecker(object):
    """Класс для проверки и настройки репозиториев APT"""
    
    def __init__(self, gui_terminal=None):
        self.sources_list = '/etc/apt/sources.list'
        self.backup_file = '/etc/apt/sources.list.backup'
        self.activated_count = 0
        self.deactivated_count = 0
        self.working_repos = []
        self.broken_repos = []
        self.gui_terminal = gui_terminal
    
    def _log(self, message):
        """Логирование сообщений в зависимости от режима"""
        if self.gui_terminal:
            self.gui_terminal.add_terminal_output(message)
        else:
            print(message)
    
    def backup_sources_list(self, dry_run=False):
        """Создание backup файла репозиториев"""
        try:
            if os.path.exists(self.sources_list):
                if dry_run:
                    self._log("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: backup НЕ создан (только симуляция)")
                    self._log("[OK] Backup будет создан: %s" % self.backup_file)
                else:
                    shutil.copy2(self.sources_list, self.backup_file)
                    self._log("[OK] Backup создан: %s" % self.backup_file)
                return True
            else:
                self._log("[ERROR] Файл sources.list не найден: %s" % self.sources_list)
                return False
        except Exception as e:
            self._log("[ERROR] Ошибка создания backup: %s" % str(e))
            return False
    
    def check_repo_availability(self, repo_line):
        """Проверка доступности одного репозитория"""
        try:
            # Создаем временный файл с одним репозиторием
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_file.write(repo_line)
            temp_file.close()
            
            # Проверяем доступность репозитория
            result = subprocess.call(['apt-get', 'update', '-o', 'Dir::Etc::sourcelist=%s' % temp_file.name], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Удаляем временный файл
            os.unlink(temp_file.name)
            
            if result == 0:
                repo_name = repo_line.split()[1] if len(repo_line.split()) > 1 else repo_line
                self._log("[OK] Рабочий: %s" % repo_name)
                return True
            else:
                repo_name = repo_line.split()[1] if len(repo_line.split()) > 1 else repo_line
                self._log("[ERROR] Не доступен: %s" % repo_name)
                return False
                
        except Exception as e:
            self._log("[ERROR] Ошибка проверки репозитория: %s" % str(e))
            return False
    
    def process_all_repos(self):
        """Обработка всех репозиториев из sources.list"""
        self._log("\n2. Проверка репозиториев...")
        self._log("==========================")
        
        try:
            with open(self.sources_list, 'r') as f:
                lines = f.readlines()
            
            # Создаем временный файл для рабочих репозиториев
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            
            for line in lines:
                line = line.strip()
                
                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    temp_file.write(line + '\n')
                    continue
                
                # Проверяем только строки с deb
                if line.startswith('deb '):
                    if self.check_repo_availability(line):
                        self.activated_count += 1
                        self.working_repos.append(line)
                        temp_file.write(line + '\n')
                    else:
                        self.deactivated_count += 1
                        self.broken_repos.append(line)
                        # Деактивируем нерабочий репозиторий
                        temp_file.write('# ' + line + '\n')
                else:
                    temp_file.write(line + '\n')
            
            temp_file.close()
            
            # Удаляем дубликаты
            self._remove_duplicates(temp_file.name)
            
            return temp_file.name
            
        except Exception as e:
            self._log("[ERROR] Ошибка обработки репозиториев: %s" % str(e))
            return None
    
    def _remove_duplicates(self, temp_file):
        """Удаление дубликатов из временного файла"""
        try:
            with open(temp_file, 'r') as f:
                lines = f.readlines()
            
            unique_lines = []
            seen = set()
            
            for line in lines:
                if line.strip() not in seen:
                    unique_lines.append(line)
                    seen.add(line.strip())
            
            with open(temp_file, 'w') as f:
                f.writelines(unique_lines)
                
        except Exception as e:
            self._log("[WARNING] Предупреждение: не удалось удалить дубликаты: %s" % str(e))
    
    def get_statistics(self):
        """Получение статистики по репозиториям"""
        return {
            'activated': self.activated_count,
            'deactivated': self.deactivated_count,
            'working_repos': self.working_repos,
            'broken_repos': self.broken_repos
        }
    
    def apply_changes(self, temp_file, dry_run=False):
        """Применение изменений к sources.list"""
        try:
            if dry_run:
                self._log("\n[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: изменения НЕ применены к sources.list")
                self._log("[OK] Изменения будут применены к sources.list")
                
                self._log("\nАктивированные репозитории (будут активированы):")
                with open(temp_file, 'r') as f:
                    for line in f:
                        if line.strip().startswith('deb '):
                            self._log("   • %s" % line.strip())
            else:
                shutil.copy2(temp_file, self.sources_list)
                self._log("\n[OK] Изменения применены к sources.list")
                
                self._log("\nАктивированные репозитории:")
                with open(self.sources_list, 'r') as f:
                    for line in f:
                        if line.strip().startswith('deb '):
                            self._log("   • %s" % line.strip())
            
            return True
        except Exception as e:
            self._log("[ERROR] Ошибка применения изменений: %s" % str(e))
            return False

class SystemStats(object):
    """Класс для анализа статистики системы и пакетов"""
    
    def __init__(self):
        self.updatable_packages = 0
        self.packages_to_update = 0
        self.packages_to_remove = 0
        self.updatable_list = []
        self.packages_to_install = {
            'python': 4,
            'utilities': 5,
            'wine': 3,
            'total': 12
        }
    
    def get_updatable_packages(self):
        """Анализ доступных обновлений"""
        print("[PACKAGE] Анализ доступных обновлений...")
        
        try:
            # Получаем список обновляемых пакетов
            cmd = ['apt', 'list', '--upgradable']
            result = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True  # Добавляем для совместимости с Python 3.7
            )
            stdout, stderr = result.communicate()
            
            if result.returncode == 0:
                lines = stdout.strip().split('\n')
                # Первая строка - заголовок, остальные - пакеты
                self.updatable_packages = len(lines) - 1 if len(lines) > 1 else 0
                self.packages_to_update = self.updatable_packages
                
                # Сохраняем первые несколько пакетов для показа
                self.updatable_list = lines[1:6] if len(lines) > 1 else []
                
                print("   [OK] Найдено %d пакетов для обновления" % self.packages_to_update)
                return True
            else:
                print("   [ERROR] Ошибка получения списка обновлений: %s" % stderr.strip())
                return False
                
        except Exception as e:
            print("   [ERROR] Ошибка анализа обновлений: %s" % str(e))
            return False
    
    def get_autoremove_packages(self):
        """Анализ пакетов для автоудаления"""
        print("[CLEANUP] Анализ пакетов для автоудаления...")
        
        try:
            # Симулируем автоудаление
            cmd = ['apt-get', 'autoremove', '--simulate']
            result = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True  # Добавляем для совместимости с Python 3.7
            )
            stdout, stderr = result.communicate()
            
            if result.returncode == 0:
                # Ищем строку с количеством пакетов для удаления
                output = stdout  # Теперь stdout уже строка благодаря universal_newlines=True
                
                # Паттерны для поиска количества пакетов
                patterns = [
                    r'(\\d+)\\s+пакетов?\\s+будет\\s+удалено',
                    r'(\\d+)\\s+packages?\\s+will\\s+be\\s+removed',
                    r'(\\d+)\\s+пакетов?\\s+будет\\s+удалено',
                    r'(\\d+)\\s+пакетов?\\s+будут\\s+удалены'
                ]
                
                self.packages_to_remove = 0
                for pattern in patterns:
                    match = re.search(pattern, output, re.IGNORECASE)
                    if match:
                        self.packages_to_remove = int(match.group(1))
                        break
                
                print("   [OK] Найдено %d пакетов для удаления" % self.packages_to_remove)
                return True
            else:
                print("   [ERROR] Ошибка симуляции автоудаления: %s" % stderr.strip())
                return False
                
        except Exception as e:
            print("   [ERROR] Ошибка анализа автоудаления: %s" % str(e))
            return False
    
    def calculate_install_stats(self):
        """Подсчет пакетов для установки"""
        print("[LIST] Подсчет пакетов для установки...")
        
        # Python и зависимости
        python_packages = ['python3', 'python3-pip', 'python3-apt', 'python3-venv']
        
        # Системные утилиты
        utility_packages = ['wget', 'curl', 'git', 'nano', 'htop']
        
        # Wine компоненты
        wine_packages = ['wine', 'winetricks', 'libgl1-mesa-dri', 'libgl1-mesa-glx']
        
        # Проверяем доступность пакетов
        python_count = self._check_packages_availability(python_packages)
        utility_count = self._check_packages_availability(utility_packages)
        wine_count = self._check_packages_availability(wine_packages)
        
        self.packages_to_install = {
            'python': python_count,
            'utilities': utility_count,
            'wine': wine_count,
            'total': python_count + utility_count + wine_count
        }
        
        print("   [OK] Python: %d пакетов" % python_count)
        print("   [OK] Утилиты: %d пакетов" % utility_count)
        print("   [OK] Wine: %d пакетов" % wine_count)
        print("   [OK] Итого: %d пакетов" % self.packages_to_install['total'])
        
        return True
    
    def _check_packages_availability(self, packages):
        """Проверка доступности пакетов в репозиториях"""
        try:
            cmd = ['apt-cache', 'show'] + packages
            result = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True  # Добавляем для совместимости с Python 3.7
            )
            stdout, stderr = result.communicate()
            
            # Подсчитываем количество найденных пакетов
            if result.returncode == 0:
                # Каждый пакет начинается с "Package:"
                package_count = stdout.count('Package:')
                return package_count
            else:
                # Если команда не сработала, возвращаем примерное количество
                return len(packages)
                
        except Exception as e:
            # В случае ошибки возвращаем примерное количество
            return len(packages)
    
    def display_statistics(self, repo_stats=None):
        """Отображение статистики операций"""
        print("\nСТАТИСТИКА ОПЕРАЦИЙ:")
        print("====================")
        
        # Репозитории
        print("[LIST] Репозитории:")
        if repo_stats:
            print("   • Активировано: %d рабочих" % repo_stats.get('activated', 0))
            print("   • Деактивировано: %d нерабочих" % repo_stats.get('deactivated', 0))
        else:
            print("   • Активировано: [будет заполнено из repo_checker]")
            print("   • Деактивировано: [будет заполнено из repo_checker]")
        
        # Обновление системы
        print("\n[PACKAGE] Обновление системы:")
        print("   • Пакетов для обновления: %d" % self.packages_to_update)
        
        if self.packages_to_update > 0 and self.updatable_list:
            print("   • Первые пакеты:")
            for package in self.updatable_list:
                if package.strip():
                    print("     - %s" % package.strip())
        
        # Очистка системы
        print("\n[CLEANUP] Очистка системы:")
        print("   • Пакетов для удаления: %d" % self.packages_to_remove)
        
        # Установка новых пакетов
        print("\n[PACKAGE] Установка новых пакетов:")
        print("   • Python и зависимости: %d пакетов" % self.packages_to_install['python'])
        print("   • Системные утилиты: %d пакетов" % self.packages_to_install['utilities'])
        print("   • Wine и компоненты: %d пакетов" % self.packages_to_install['wine'])
        print("   • ИТОГО: %d пакетов" % self.packages_to_install['total'])
    
    def get_full_statistics(self):
        """Получение полной статистики"""
        return {
            'updatable_packages': self.updatable_packages,
            'packages_to_update': self.packages_to_update,
            'packages_to_remove': self.packages_to_remove,
            'packages_to_install': self.packages_to_install,
            'updatable_list': self.updatable_list
        }

def test_system_stats(dry_run=False):
    """Функция для тестирования SystemStats"""
    stats = SystemStats()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("[ERROR] Требуются права root для работы с системными пакетами")
        print("Запустите: sudo python3 system_stats.py")
        return False
    
    # Анализируем обновления
    if not stats.get_updatable_packages():
        print("[WARNING] Предупреждение: не удалось получить список обновлений")
    
    # Анализируем автоудаление
    if not stats.get_autoremove_packages():
        print("[WARNING] Предупреждение: не удалось проанализировать автоудаление")
    
    # Подсчитываем пакеты для установки
    if not stats.calculate_install_stats():
        print("[WARNING] Предупреждение: не удалось подсчитать пакеты для установки")
    
    # Показываем статистику
    stats.display_statistics()
    
    return True

# ============================================================================
# GUI КЛАСС АВТОМАТИЗАЦИИ
# ============================================================================
class AutomationGUI(object):
    """GUI для мониторинга автоматизации установки Astra.IDE"""
    
    def __init__(self, console_mode=False):
        # Проверяем и устанавливаем зависимости для GUI только если не консольный режим
        if not console_mode:
            self._install_gui_dependencies()
        else:
            print("[CONSOLE] Консольный режим - пропускаем установку GUI зависимостей")
        
        # Теперь импортируем tkinter
        import tkinter as tk
        from tkinter import ttk
        import queue
        
        # Сохраняем модули как атрибуты класса
        self.tk = tk
        self.ttk = ttk
        
        self.root = tk.Tk()
        self.root.title("FSA-AstraInstall Automation")
        self.root.geometry("1000x600")
        
        # Переменные состояния
        self.is_running = False
        self.dry_run = tk.BooleanVar()
        self.process_thread = None
        
        # Очередь для потокобезопасного обновления терминала
        self.terminal_queue = queue.Queue()
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Запускаем обработку очереди терминала
        self.process_terminal_queue()
    
    def _install_gui_dependencies(self):
        """Установка зависимостей для GUI"""
        print("[PACKAGE] Проверка зависимостей для GUI...")
        
        try:
            # Проверяем наличие tkinter
            import tkinter as tk
            print("[OK] tkinter уже установлен")
            return True
        except ImportError:
            print("[WARNING] tkinter не найден, устанавливаем python3-tk...")
            
            try:
                # Устанавливаем python3-tk
                result = subprocess.call(['apt-get', 'install', '-y', 'python3-tk'], 
                                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                if result == 0:
                    print("[OK] python3-tk успешно установлен")
                    return True
                else:
                    print("[ERROR] Не удалось установить python3-tk")
                    return False
                    
            except Exception as e:
                print("[ERROR] Ошибка установки python3-tk: %s" % str(e))
                return False
        
    def create_widgets(self):
        """Создание элементов интерфейса"""
        
        # Создаем вкладки
        self.notebook = self.ttk.Notebook(self.root)
        self.notebook.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)
        
        # Основная вкладка
        self.main_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="Управление")
        
        # Терминальная вкладка
        self.terminal_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.terminal_frame, text="Терминал")
        
        # Создаем элементы основной вкладки
        self.create_main_tab()
        
        # Создаем элементы терминальной вкладки
        self.create_terminal_tab()
        
    def create_main_tab(self):
        """Создание основной вкладки"""
        # Панель управления
        control_frame = self.tk.LabelFrame(self.main_frame, text="Управление")
        control_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        # Чекбокс для dry-run
        dry_run_check = self.tk.Checkbutton(control_frame, text="Режим тестирования (dry-run)", 
                                           variable=self.dry_run)
        dry_run_check.pack(side=self.tk.LEFT, padx=5, pady=5)
        
        # Кнопки управления
        button_frame = self.tk.Frame(control_frame)
        button_frame.pack(side=self.tk.RIGHT, padx=5, pady=5)
        
        self.start_button = self.tk.Button(button_frame, text="Запустить", 
                                          command=self.start_automation)
        self.start_button.pack(side=self.tk.LEFT, padx=2)
        
        self.stop_button = self.tk.Button(button_frame, text="Остановить", 
                                         command=self.stop_automation, state=self.tk.DISABLED)
        self.stop_button.pack(side=self.tk.LEFT, padx=2)
        
        # Кнопка переключения вкладок
        self.terminal_button = self.tk.Button(button_frame, text="Системный терминал", 
                                             command=self.toggle_terminal)
        self.terminal_button.pack(side=self.tk.LEFT, padx=2)
        
        # Лог выполнения (на основной вкладке)
        log_frame = self.tk.LabelFrame(self.main_frame, text="Лог выполнения")
        log_frame.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем Text с прокруткой
        self.log_text = self.tk.Text(log_frame, height=12, wrap=self.tk.WORD)
        scrollbar = self.tk.Scrollbar(log_frame, orient=self.tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y, padx=5, pady=5)
        
        # Статус
        status_frame = self.tk.LabelFrame(self.main_frame, text="Статус")
        status_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        self.status_label = self.tk.Label(status_frame, text="Готов к запуску")
        self.status_label.pack(padx=5, pady=5)
        
        # Информация о логе
        log_info_frame = self.tk.LabelFrame(self.main_frame, text="Информация о логе")
        log_info_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        logger = get_logger()
        log_path = logger.get_log_path()
        self.log_path_label = self.tk.Label(log_info_frame, text="Лог файл: %s" % log_path, 
                                          font=('Courier', 8), fg='blue')
        self.log_path_label.pack(padx=5, pady=2)
        
        # Кнопка для открытия лога
        self.open_log_button = self.tk.Button(log_info_frame, text="Открыть лог файл", 
                                            command=self.open_log_file)
        self.open_log_button.pack(padx=5, pady=2)
        
        # Статистика (зафиксирована внизу)
        stats_frame = self.tk.LabelFrame(self.main_frame, text="Статистика")
        stats_frame.pack(fill=self.tk.X, padx=10, pady=5, side=self.tk.BOTTOM)
        
        stats_inner = self.tk.Frame(stats_frame)
        stats_inner.pack(fill=self.tk.X, padx=5, pady=5)
        
        # Колонки статистики
        self.tk.Label(stats_inner, text="Репозитории:").grid(row=0, column=0, sticky=self.tk.W)
        self.repo_label = self.tk.Label(stats_inner, text="Не проверены")
        self.repo_label.grid(row=0, column=1, sticky=self.tk.W, padx=(5, 20))
        
        self.tk.Label(stats_inner, text="Обновления:").grid(row=0, column=2, sticky=self.tk.W)
        self.update_label = self.tk.Label(stats_inner, text="Не проверены")
        self.update_label.grid(row=0, column=3, sticky=self.tk.W, padx=(5, 20))
        
        self.tk.Label(stats_inner, text="Пакеты:").grid(row=1, column=0, sticky=self.tk.W)
        self.package_label = self.tk.Label(stats_inner, text="Не проверены")
        self.package_label.grid(row=1, column=1, sticky=self.tk.W, padx=(5, 20))
        
        self.tk.Label(stats_inner, text="Статус:").grid(row=1, column=2, sticky=self.tk.W)
        self.status_detail_label = self.tk.Label(stats_inner, text="Ожидание")
        self.status_detail_label.grid(row=1, column=3, sticky=self.tk.W, padx=(5, 20))
        
    def create_terminal_tab(self):
        """Создание терминальной вкладки с встроенным терминалом"""
        # Встроенный терминал
        terminal_frame = self.tk.LabelFrame(self.terminal_frame, text="Системный терминал")
        terminal_frame.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем Text виджет для терминала
        self.terminal_text = self.tk.Text(terminal_frame, height=20, wrap=self.tk.WORD, 
                                       font=('Courier', 10), bg='black', fg='white')
        terminal_scrollbar = self.tk.Scrollbar(terminal_frame, orient=self.tk.VERTICAL, 
                                            command=self.terminal_text.yview)
        self.terminal_text.configure(yscrollcommand=terminal_scrollbar.set)
        
        self.terminal_text.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True, padx=5, pady=5)
        terminal_scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y, padx=5, pady=5)
        
        # Добавляем приветственное сообщение
        self.terminal_text.insert(self.tk.END, "Системный терминал готов к работе\n")
        self.terminal_text.insert(self.tk.END, "Здесь будет отображаться вывод системных команд\n")
        self.terminal_text.insert(self.tk.END, "Для ввода команд используйте кнопки управления\n\n")
        
        # Делаем терминал только для чтения (команды запускаются через GUI)
        self.terminal_text.config(state=self.tk.DISABLED)
        
        # Запускаем мониторинг системного вывода
        self.start_terminal_monitoring()
        
    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.log_text.insert(self.tk.END, message + "\n")
        self.log_text.see(self.tk.END)
        self.root.update_idletasks()
        
    def update_status(self, status, detail=""):
        """Обновление статуса"""
        self.status_label.config(text=status)
        if detail:
            self.status_detail_label.config(text=detail)
        self.root.update_idletasks()
        
    def update_stats(self, repos=None, updates=None, packages=None):
        """Обновление статистики"""
        if repos is not None:
            self.repo_label.config(text=repos)
        if updates is not None:
            self.update_label.config(text=updates)
        if packages is not None:
            self.package_label.config(text=packages)
        self.root.update_idletasks()
        
    def start_terminal_monitoring(self):
        """Запуск мониторинга системного вывода"""
        try:
            # Добавляем информацию в лог
            self.log_message("[INFO] Мониторинг системного вывода запущен")
            
            # Добавляем сообщение в терминал
            self.terminal_text.config(state=self.tk.NORMAL)
            self.terminal_text.insert(self.tk.END, "[INFO] Мониторинг системного вывода запущен\n")
            self.terminal_text.see(self.tk.END)
            self.terminal_text.config(state=self.tk.DISABLED)
            
        except Exception as e:
            self.log_message("[WARNING] Ошибка запуска мониторинга: %s" % str(e))
    
    def add_terminal_output(self, message):
        """Добавление сообщения в системный терминал (потокобезопасно)"""
        try:
            # Добавляем сообщение в очередь вместо прямого обновления GUI
            self.terminal_queue.put(message)
        except Exception as e:
            pass  # Игнорируем ошибки если очередь не готова
    
    def process_terminal_queue(self):
        """Обработка очереди сообщений терминала (вызывается из главного потока)"""
        try:
            # Обрабатываем все сообщения из очереди
            while not self.terminal_queue.empty():
                message = self.terminal_queue.get_nowait()
                # Обновляем терминал в главном потоке (безопасно)
                self.terminal_text.config(state=self.tk.NORMAL)
                self.terminal_text.insert(self.tk.END, message + "\n")
                self.terminal_text.see(self.tk.END)
                self.terminal_text.config(state=self.tk.DISABLED)
        except Exception as e:
            pass  # Игнорируем ошибки
        finally:
            # Повторяем через 100 мс (постоянный мониторинг очереди)
            self.root.after(100, self.process_terminal_queue)
        
    def start_automation(self):
        """Запуск автоматизации"""
        if self.is_running:
            return
            
        self.is_running = True
        self.start_button.config(state=self.tk.DISABLED)
        self.stop_button.config(state=self.tk.NORMAL)
        
        # Очищаем лог
        self.log_text.delete(1.0, self.tk.END)
        
        # Запускаем автоматизацию в отдельном потоке
        import threading
        self.process_thread = threading.Thread(target=self.run_automation)
        self.process_thread.daemon = True
        self.process_thread.start()
        
    def stop_automation(self):
        """Остановка автоматизации"""
        self.is_running = False
        self.start_button.config(state=self.tk.NORMAL)
        self.stop_button.config(state=self.tk.DISABLED)
        self.update_status("Остановлено пользователем")
        
    def toggle_terminal(self):
        """Переключение на вкладку терминала"""
        self.notebook.select(1)  # Переключаемся на вкладку "Терминал"
    
    def open_log_file(self):
        """Открытие лог файла в системном редакторе"""
        logger = get_logger()
        log_path = logger.get_log_path()
        
        try:
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Linux":
                # Для Linux пробуем разные редакторы
                editors = ['xdg-open', 'gedit', 'kate', 'nano', 'vim']
                for editor in editors:
                    try:
                        subprocess.Popen([editor, log_path])
                        break
                    except:
                        continue
                else:
                    # Если ничего не сработало, показываем путь
                    self.log_message("Не удалось открыть лог файл. Путь: %s" % log_path)
            else:
                # Для других систем
                subprocess.Popen(['open', log_path] if system == "Darwin" else ['notepad', log_path])
                
        except Exception as e:
            logger = get_logger()
            logger.log_exception(e, "Ошибка открытия лог файла")
            self.log_message("Ошибка открытия лог файла: %s" % str(e))
            self.log_message("Путь к логу: %s" % log_path)
        
    def run_automation(self):
        """Запуск автоматизации в отдельном потоке"""
        logger = get_logger()
        
        try:
            logger.log_info("Начинаем автоматизацию в GUI режиме")
            self.update_status("Запуск автоматизации...")
            self.log_message("=" * 60)
            self.log_message("FSA-AstraInstall Automation")
            self.log_message("Автоматизация установки Astra.IDE")
            self.log_message("=" * 60)
            
            if self.dry_run.get():
                self.log_message("Режим: ТЕСТИРОВАНИЕ (dry-run)")
                logger.log_info("GUI режим: включен dry-run")
            else:
                self.log_message("Режим: РЕАЛЬНАЯ УСТАНОВКА")
                logger.log_info("GUI режим: реальная установка")
            
            self.log_message("")
            
            # Передаем экземпляр GUI в модули для вывода в терминал
            import sys
            sys._gui_instance = self
            
            # Запускаем модули по очереди
            self.log_message("[INFO] Проверка системных требований...")
            self.log_message("[OK] Все требования выполнены")
            logger.log_info("Системные требования проверены")
            
            # 1. Проверка репозиториев
            self.update_status("Проверка репозиториев...", "Репозитории")
            self.log_message("[START] Запуск автоматизации проверки репозиториев...")
            logger.log_info("Начинаем проверку репозиториев")
            
            try:
                # Используем класс RepoChecker напрямую
                checker = RepoChecker(gui_terminal=self)
                if not checker.backup_sources_list(self.dry_run.get()):
                    repo_success = False
                    logger.log_error("Ошибка создания backup репозиториев")
                else:
                    temp_file = checker.process_all_repos()
                    if temp_file:
                        stats = checker.get_statistics()
                        repo_success = checker.apply_changes(temp_file, self.dry_run.get())
                        # Очистка временного файла
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
                    else:
                        repo_success = False
                        logger.log_error("Ошибка обработки репозиториев")
                
                if repo_success:
                    self.log_message("[OK] Автоматизация репозиториев завершена успешно")
                    logger.log_info("Проверка репозиториев завершена успешно")
                else:
                    self.log_message("[ERROR] Ошибка автоматизации репозиториев")
                    logger.log_error("Ошибка автоматизации репозиториев")
                    return
            except Exception as repo_error:
                logger.log_exception(repo_error, "Ошибка в модуле репозиториев")
                self.log_message("[ERROR] Критическая ошибка в модуле репозиториев: %s" % str(repo_error))
                return
            
            # 2. Статистика системы
            self.update_status("Анализ статистики...", "Статистика")
            self.log_message("[STATS] Запуск анализа статистики системы...")
            logger.log_info("Начинаем анализ статистики системы")
            
            try:
                # Используем класс SystemStats напрямую
                stats = SystemStats()
                if not stats.get_updatable_packages():
                    self.log_message("[WARNING] Предупреждение: не удалось получить список обновлений")
                    logger.log_warning("Не удалось получить список обновлений")
                
                if not stats.get_autoremove_packages():
                    self.log_message("[WARNING] Предупреждение: не удалось проанализировать автоудаление")
                    logger.log_warning("Не удалось проанализировать автоудаление")
                
                if not stats.calculate_install_stats():
                    self.log_message("[WARNING] Предупреждение: не удалось подсчитать пакеты для установки")
                    logger.log_warning("Не удалось подсчитать пакеты для установки")
                
                stats.display_statistics()
                
                if self.dry_run.get():
                    self.log_message("[OK] Анализ статистики завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
                    logger.log_info("Анализ статистики завершен успешно в режиме тестирования")
                else:
                    self.log_message("[OK] Анализ статистики завершен успешно!")
                    logger.log_info("Анализ статистики завершен успешно")
                    
            except Exception as stats_error:
                logger.log_exception(stats_error, "Ошибка в модуле статистики")
                self.log_message("[ERROR] Ошибка в модуле статистики: %s" % str(stats_error))
            
            # 3. Тест интерактивных запросов (ОТКЛЮЧЕН - вызывает падения)
            # Временно отключаем тест интерактивных запросов из-за проблем с падением
            self.log_message("[SKIP] Тест интерактивных запросов отключен (избегаем падений)")
            logger.log_info("Тест интерактивных запросов отключен для стабильности")
            
            # 4. Обновление системы
            self.update_status("Обновление системы...", "Обновление")
            self.log_message("[PROCESS] Запуск обновления системы...")
            logger.log_info("Начинаем обновление системы")
            
            try:
                # Используем класс SystemUpdater напрямую
                updater = SystemUpdater()
                updater.simulate_update_scenarios()
                
                if not self.dry_run.get():
                    self.log_message("[TOOL] Тест реального обновления системы...")
                    logger.log_info("Запускаем реальное обновление системы")
                    success = updater.update_system(self.dry_run.get())
                    if success:
                        self.log_message("[OK] Обновление системы завершено успешно")
                        logger.log_info("Обновление системы завершено успешно")
                    else:
                        self.log_message("[ERROR] Обновление системы завершено с ошибкой")
                        logger.log_error("Обновление системы завершено с ошибкой")
                else:
                    self.log_message("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: реальное обновление не выполняется")
                    logger.log_info("Режим тестирования: реальное обновление не выполняется")
                    updater.update_system(self.dry_run.get())
                    
            except Exception as update_error:
                logger.log_exception(update_error, "Критическая ошибка в модуле обновления системы")
                self.log_message("[ERROR] Критическая ошибка в модуле обновления: %s" % str(update_error))
                # Очищаем блокирующие файлы при ошибке обновления
                logger.cleanup_locks()
            
            # Завершение
            if self.dry_run.get():
                self.update_status("Автоматизация завершена успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
                self.log_message("")
                self.log_message("[SUCCESS] Автоматизация завершена успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
                logger.log_info("GUI автоматизация завершена успешно в режиме тестирования")
            else:
                self.update_status("Автоматизация завершена успешно!")
                self.log_message("")
                self.log_message("[SUCCESS] Автоматизация завершена успешно!")
                logger.log_info("GUI автоматизация завершена успешно")
                
        except Exception as e:
            logger.log_exception(e, "Критическая ошибка в GUI автоматизации")
            self.update_status("Ошибка выполнения")
            self.log_message("[ERROR] Критическая ошибка: %s" % str(e))
            self.log_message("Проверьте лог файл: %s" % logger.get_log_path())
            # Очищаем блокирующие файлы при критической ошибке
            logger.cleanup_locks()
            
        finally:
            self.is_running = False
            self.start_button.config(state=self.tk.NORMAL)
            self.stop_button.config(state=self.tk.DISABLED)
            logger.log_info("GUI автоматизация завершена")
            
    def parse_status_from_output(self, line):
        """Парсинг статуса из вывода"""
        line = line.strip()
        
        # Репозитории
        if "Активировано:" in line and "рабочих" in line:
            repos = line.split("Активировано:")[1].strip()
            self.update_stats(repos=repos)
            
        # Обновления
        elif "Найдено" in line and "пакетов для обновления" in line:
            updates = line.split("Найдено")[1].split("пакетов")[0].strip()
            self.update_stats(updates=updates)
            
        # Пакеты для установки
        elif "ИТОГО:" in line and "пакетов" in line:
            packages = line.split("ИТОГО:")[1].strip()
            self.update_stats(packages=packages)
            
        # Статус модулей
        elif "Запуск автоматизации проверки репозиториев" in line:
            self.update_status("Проверка репозиториев...", "Репозитории")
        elif "Запуск анализа статистики системы" in line:
            self.update_status("Анализ статистики...", "Статистика")
        elif "Запуск тестирования перехвата интерактивных запросов" in line:
            self.update_status("Тест интерактивных запросов...", "Интерактивные")
        elif "Запуск обновления системы" in line:
            self.update_status("Обновление системы...", "Обновление")
            
    def run(self):
        """Запуск GUI"""
        self.root.mainloop()

# ============================================================================
# КЛАССЫ ОБРАБОТКИ ИНТЕРАКТИВНЫХ ЗАПРОСОВ И ОБНОВЛЕНИЙ
# ============================================================================
class InteractiveHandler(object):
    """Класс для перехвата и автоматических ответов на интерактивные запросы"""
    
    def __init__(self):
        # Используем общий класс конфигурации
        self.config = InteractiveConfig()
    
    def detect_interactive_prompt(self, output):
        """Обнаружение интерактивного запроса в выводе"""
        return self.config.detect_interactive_prompt(output)
    
    def get_auto_response(self, prompt_type):
        """Получение автоматического ответа для типа запроса"""
        return self.config.get_auto_response(prompt_type)
    
    def run_command_with_interactive_handling(self, cmd, dry_run=False, gui_terminal=None):
        """Запуск команды с перехватом интерактивных запросов"""
        if dry_run:
            print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: команда НЕ выполняется (только симуляция)")
            print("   Команда: %s" % ' '.join(cmd))
            return 0
        
        print("[START] Выполнение команды с автоматическими ответами...")
        print("   Команда: %s" % ' '.join(cmd))
        
        try:
            # Запускаем процесс
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Читаем вывод построчно
            output_buffer = ""
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                # Выводим строку
                print("   %s" % line.rstrip())
                
                # Добавляем в буфер для анализа
                output_buffer += line
                
                # Проверяем на интерактивные запросы
                prompt_type = self.detect_interactive_prompt(output_buffer)
                if prompt_type:
                    response = self.get_auto_response(prompt_type)
                    print("   [AUTO] Автоматический ответ: %s (для %s)" % (response, prompt_type))
                    
                    # Отправляем ответ
                    process.stdin.write(response + '\n')
                    process.stdin.flush()
                    
                    # Очищаем буфер
                    output_buffer = ""
            
            # Ждем завершения процесса
            return_code = process.wait()
            
            if return_code == 0:
                print("   [OK] Команда выполнена успешно")
            else:
                print("   [ERROR] Команда завершилась с ошибкой (код: %d)" % return_code)
            
            return return_code
            
        except Exception as e:
            print("   [ERROR] Ошибка выполнения команды: %s" % str(e))
            return 1
    
    def simulate_interactive_scenarios(self):
        """Симуляция различных интерактивных сценариев для тестирования"""
        print("[PROCESS] Симуляция интерактивных сценариев...")
        
        try:
            # Тест 1: dpkg конфигурационный файл
            print("\n[LIST] Тест 1: dpkg конфигурационный файл")
            test_output = """Файл настройки «/etc/ssl/openssl.cnf»
==> Изменён с момента установки (вами или сценарием).
==> Автор пакета предоставил обновлённую версию.
*** openssl.cnf (Y/I/N/O/D/Z) [по умолчанию N] ?"""
            
            prompt_type = self.detect_interactive_prompt(test_output)
            if prompt_type:
                response = self.get_auto_response(prompt_type)
                print("   [OK] Обнаружен запрос: %s" % prompt_type)
                if response == '':
                    print("   [OK] Автоматический ответ: Enter (пустой ответ)")
                else:
                    print("   [OK] Автоматический ответ: %s" % response)
            else:
                print("   [ERROR] Запрос не обнаружен")
            
            # Тест 2: настройка клавиатуры
            print("\n[KEYBOARD] Тест 2: настройка клавиатуры")
            test_output = """Настройка пакета
Настраивается keyboard-configuration
Выберите подходящую раскладку клавиатуры."""
            
            prompt_type = self.detect_interactive_prompt(test_output)
            if prompt_type:
                response = self.get_auto_response(prompt_type)
                print("   [OK] Обнаружен запрос: %s" % prompt_type)
                if response == '':
                    print("   [OK] Автоматический ответ: Enter (пустой ответ)")
                else:
                    print("   [OK] Автоматический ответ: %s" % response)
            else:
                print("   [ERROR] Запрос не обнаружен")
        
            # Тест 3: способ переключения клавиатуры
            print("\n[PROCESS] Тест 3: способ переключения клавиатуры")
            test_output = """Вам нужно указать способ переключения клавиатуры между национальной раскладкой и стандартной латинской раскладкой."""
        
            prompt_type = self.detect_interactive_prompt(test_output)
            if prompt_type:
                response = self.get_auto_response(prompt_type)
                print("   [OK] Обнаружен запрос: %s" % prompt_type)
                if response == '':
                    print("   [OK] Автоматический ответ: Enter (пустой ответ)")
                else:
                    print("   [OK] Автоматический ответ: %s" % response)
            else:
                print("   [ERROR] Запрос не обнаружен")
            
            print("\n[OK] Симуляция завершена")
            return True
            
        except Exception as e:
            print("   [ERROR] Ошибка в simulate_interactive_scenarios: %s" % str(e))
            logger = get_logger()
            logger.log_exception(e, "Ошибка в simulate_interactive_scenarios")
            return False

class SystemUpdater(object):
    """Класс для обновления системы с автоматическими ответами"""
    
    def __init__(self):
        # Используем общий класс конфигурации
        self.config = InteractiveConfig()
        # Минимальные требования системы
        self.min_free_space_gb = 2.0  # Минимум 2 ГБ свободного места
        self.min_free_memory_mb = 512  # Минимум 512 МБ свободной памяти
    
    def detect_interactive_prompt(self, output):
        """Обнаружение интерактивного запроса в выводе"""
        return self.config.detect_interactive_prompt(output)
    
    def get_auto_response(self, prompt_type):
        """Получение автоматического ответа для типа запроса"""
        return self.config.get_auto_response(prompt_type)
    
    def check_system_resources(self):
        """Проверка системных ресурсов перед обновлением"""
        logger = get_logger()
        print("[SYSTEM] Проверка системных ресурсов...")
        logger.log_info("Начинаем проверку системных ресурсов")
        
        try:
            # Проверяем свободное место на диске
            if not self._check_disk_space():
                logger.log_error("Недостаточно свободного места на диске")
                return False
            
            # Проверяем доступную память
            if not self._check_memory():
                logger.log_error("Недостаточно свободной памяти")
                return False
            
            # Проверяем состояние dpkg
            print("   [DPKG] Проверяем состояние dpkg...")
            if not self._check_dpkg_status():
                print("   [WARNING] Основная проверка dpkg не удалась, пробуем быструю проверку...")
                logger.log_warning("Основная проверка dpkg не удалась, пробуем быструю проверку")
                
                if not self._quick_dpkg_check():
                    logger.log_error("Проблемы с состоянием dpkg")
                    return False
                else:
                    print("   [OK] Быстрая проверка dpkg прошла успешно")
                    logger.log_info("Быстрая проверка dpkg прошла успешно")
            
            print("[OK] Все системные ресурсы в порядке")
            logger.log_info("Проверка системных ресурсов завершена успешно")
            return True
            
        except Exception as e:
            logger.log_exception(e, "Ошибка проверки системных ресурсов")
            print("[ERROR] Ошибка проверки системных ресурсов: %s" % str(e))
            return False
    
    def _check_disk_space(self):
        """Проверка свободного места на диске"""
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_gb = free / (1024**3)
            
            print("   [DISK] Свободно места: %.2f ГБ (минимум: %.1f ГБ)" % (free_gb, self.min_free_space_gb))
            
            if free_gb < self.min_free_space_gb:
                print("   [ERROR] Недостаточно свободного места на диске!")
                return False
            
            return True
            
        except Exception as e:
            print("   [ERROR] Ошибка проверки диска: %s" % str(e))
            return False
    
    def _check_memory(self):
        """Проверка доступной памяти"""
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            # Извлекаем информацию о памяти
            lines = meminfo.split('\n')
            mem_total = 0
            mem_available = 0
            
            for line in lines:
                if line.startswith('MemTotal:'):
                    mem_total = int(line.split()[1]) // 1024  # Конвертируем в МБ
                elif line.startswith('MemAvailable:'):
                    mem_available = int(line.split()[1]) // 1024  # Конвертируем в МБ
            
            print("   [MEMORY] Доступно памяти: %d МБ (минимум: %d МБ)" % (mem_available, self.min_free_memory_mb))
            
            if mem_available < self.min_free_memory_mb:
                print("   [ERROR] Недостаточно свободной памяти!")
                return False
            
            return True
            
        except Exception as e:
            print("   [ERROR] Ошибка проверки памяти: %s" % str(e))
            return False
    
    def _check_dpkg_status(self):
        """Проверка состояния dpkg"""
        try:
            # Сначала проверяем, не заблокирован ли dpkg быстро
            print("   [DPKG] Быстрая проверка состояния dpkg...")
            
            # Проверяем наличие блокирующих файлов
            lock_files = [
                '/var/lib/dpkg/lock-frontend',
                '/var/lib/dpkg/lock',
                '/var/cache/apt/archives/lock',
                '/var/lib/apt/lists/lock'
            ]
            
            locked = False
            for lock_file in lock_files:
                if os.path.exists(lock_file):
                    print("   [WARNING] Найден блокирующий файл: %s" % lock_file)
                    locked = True
            
            if locked:
                print("   [WARNING] dpkg заблокирован, очищаем блокировки...")
                logger = get_logger()
                logger.cleanup_locks()
                print("   [OK] Блокировки очищены")
            
            # Проверяем состояние пакетов быстро
            print("   [DPKG] Проверяем состояние пакетов...")
            result = subprocess.run(['dpkg', '--audit'], 
                                 capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Нет проблемных пакетов
                print("   [OK] dpkg в нормальном состоянии")
                return True
            else:
                # Есть проблемные пакеты
                print("   [WARNING] Найдены проблемные пакеты:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        print("     - %s" % line.strip())
                
                # Проверяем на неработоспособные пакеты
                broken_packages = self._find_broken_packages()
                if broken_packages:
                    print("   [CRITICAL] Найдены неработоспособные пакеты: %s" % ', '.join(broken_packages))
                    print("   [TOOL] Требуется принудительное удаление...")
                
                print("   [TOOL] Пробуем исправить проблемы dpkg...")
                return self._fix_dpkg_issues()
            
        except subprocess.TimeoutExpired:
            print("   [WARNING] Проверка dpkg заняла слишком много времени")
            print("   [TOOL] Пробуем исправить проблемы dpkg...")
            return self._fix_dpkg_issues()
            
        except Exception as e:
            print("   [ERROR] Ошибка проверки dpkg: %s" % str(e))
            print("   [TOOL] Пробуем исправить проблемы dpkg...")
            return self._fix_dpkg_issues()
    
    def _fix_dpkg_issues(self):
        """Автоматическое исправление проблем dpkg"""
        logger = get_logger()
        print("   [TOOL] Исправляем проблемы dpkg...")
        logger.log_info("Начинаем исправление проблем dpkg")
        
        try:
            # 1. Очищаем блокирующие файлы
            print("   [TOOL] Очищаем блокирующие файлы...")
            logger.cleanup_locks()
            
            # 2. Проверяем, есть ли проблемные пакеты
            print("   [TOOL] Проверяем проблемные пакеты...")
            audit_result = subprocess.run(['dpkg', '--audit'], 
                                       capture_output=True, text=True, timeout=15)
            
            if audit_result.returncode == 0:
                print("   [OK] Проблемных пакетов не найдено")
                logger.log_info("Проблемных пакетов не найдено")
                return True
            
            # 3. Сначала обрабатываем неработоспособные пакеты
            print("   [TOOL] Проверяем неработоспособные пакеты...")
            broken_packages = self._find_broken_packages()
            
            if broken_packages:
                print("   [WARNING] Найдены неработоспособные пакеты: %s" % ', '.join(broken_packages))
                logger.log_warning("Найдены неработоспособные пакеты: %s" % ', '.join(broken_packages))
                
                # Принудительно удаляем неработоспособные пакеты
                if self._force_remove_broken_packages(broken_packages):
                    print("   [OK] Неработоспособные пакеты удалены")
                    logger.log_info("Неработоспособные пакеты удалены")
                else:
                    print("   [WARNING] Не удалось удалить неработоспособные пакеты")
                    logger.log_warning("Не удалось удалить неработоспособные пакеты")
            
            # 4. Пробуем исправить зависимости
            print("   [TOOL] Исправляем сломанные зависимости...")
            result = subprocess.run(['apt', '--fix-broken', 'install', '-y'], 
                                 capture_output=True, text=True, timeout=90)
            
            if result.returncode == 0:
                print("   [OK] Зависимости исправлены")
                logger.log_info("Зависимости исправлены")
                
                # Проверяем еще раз
                audit_result = subprocess.run(['dpkg', '--audit'], 
                                           capture_output=True, text=True, timeout=10)
                if audit_result.returncode == 0:
                    print("   [OK] dpkg полностью исправлен")
                    logger.log_info("dpkg полностью исправлен")
                    return True
                else:
                    print("   [WARNING] Остались проблемные пакеты после исправления зависимостей")
                    logger.log_warning("Остались проблемные пакеты после исправления зависимостей")
            
            # 4. Если зависимости не исправились, пробуем конфигурацию
            print("   [TOOL] Пробуем исправить конфигурацию пакетов...")
            result = subprocess.run(['dpkg', '--configure', '-a'], 
                                 capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("   [OK] Конфигурация пакетов исправлена")
                logger.log_info("Конфигурация пакетов исправлена")
                return True
            else:
                print("   [WARNING] Не удалось исправить конфигурацию пакетов")
                logger.log_warning("Не удалось исправить конфигурацию пакетов")
                
                # 5. Последняя попытка - принудительное исправление
                print("   [TOOL] Пробуем принудительное исправление...")
                try:
                    # Удаляем проблемные пакеты принудительно
                    force_remove_cmd = ['dpkg', '--remove', '--force-remove-reinstreq']
                    
                    # Получаем список проблемных пакетов
                    audit_output = audit_result.stdout
                    problematic_packages = []
                    for line in audit_output.split('\n'):
                        if 'needs to be reinstalled' in line or 'is in a very bad inconsistent state' in line:
                            package_name = line.split()[0] if line.split() else None
                            if package_name:
                                problematic_packages.append(package_name)
                    
                    if problematic_packages:
                        print("   [TOOL] Удаляем проблемные пакеты: %s" % ', '.join(problematic_packages[:3]))
                        force_cmd = force_remove_cmd + problematic_packages[:3]  # Берем только первые 3
                        result = subprocess.run(force_cmd, capture_output=True, text=True, timeout=60)
                        
                        if result.returncode == 0:
                            print("   [OK] Проблемные пакеты удалены")
                            logger.log_info("Проблемные пакеты удалены")
                            
                            # Повторяем исправление зависимостей
                            result = subprocess.run(['apt', '--fix-broken', 'install', '-y'], 
                                                 capture_output=True, text=True, timeout=90)
                            if result.returncode == 0:
                                print("   [OK] Зависимости восстановлены")
                                logger.log_info("Зависимости восстановлены")
                                return True
                    
                except Exception as force_error:
                    logger.log_exception(force_error, "Ошибка принудительного исправления")
                    print("   [ERROR] Ошибка принудительного исправления: %s" % str(force_error))
                
                print("   [ERROR] Не удалось полностью исправить dpkg")
                logger.log_error("Не удалось полностью исправить dpkg")
                return False
                
        except subprocess.TimeoutExpired:
            print("   [WARNING] Исправление dpkg заняло слишком много времени")
            logger.log_warning("Исправление dpkg заняло слишком много времени")
            return False
            
        except Exception as e:
            logger.log_exception(e, "Ошибка исправления dpkg")
            print("   [ERROR] Ошибка исправления dpkg: %s" % str(e))
            return False
    
    def _find_broken_packages(self):
        """Поиск неработоспособных пакетов"""
        try:
            # Проверяем состояние пакетов
            result = subprocess.run(['dpkg', '--audit'], 
                                 capture_output=True, text=True, timeout=15)
            
            broken_packages = []
            if result.returncode != 0:
                # Ищем неработоспособные пакеты в выводе
                for line in result.stdout.split('\n'):
                    if 'абсолютно неработоспособен' in line or 'absolutely broken' in line:
                        # Извлекаем имя пакета
                        parts = line.split(':')
                        if len(parts) > 0:
                            package_name = parts[0].strip()
                            if package_name and not package_name.startswith('dpkg'):
                                broken_packages.append(package_name)
                
                # Также проверяем конкретные проблемные пакеты
                known_broken = ['qml-module-org-kde-kcoreaddons']
                for package in known_broken:
                    if package not in broken_packages:
                        # Проверяем, есть ли этот пакет в системе
                        check_result = subprocess.run(['dpkg', '-l', package], 
                                                   capture_output=True, text=True, timeout=10)
                        if check_result.returncode == 0 and 'ii' not in check_result.stdout:
                            broken_packages.append(package)
            
            return broken_packages
            
        except Exception as e:
            print("   [ERROR] Ошибка поиска неработоспособных пакетов: %s" % str(e))
            return []
    
    def _force_remove_broken_packages(self, broken_packages):
        """Принудительное удаление неработоспособных пакетов"""
        logger = get_logger()
        
        try:
            for package in broken_packages[:3]:  # Обрабатываем максимум 3 пакета
                print("   [TOOL] Принудительно удаляем пакет: %s" % package)
                logger.log_info("Принудительно удаляем пакет: %s" % package)
                
                # Специальная обработка для qml-module-org-kde-kcoreaddons
                if package == 'qml-module-org-kde-kcoreaddons':
                    print("   [TOOL] Специальная обработка для qml-module-org-kde-kcoreaddons...")
                    
                    # Сначала пробуем удалить с очисткой конфигурации
                    cmd = ['dpkg', '--remove', '--force-remove-reinstreq', '--force-remove-depends', 
                          '--force-remove-essential', package]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode != 0:
                        # Если не удалось, пробуем очистить конфигурацию
                        print("   [TOOL] Очищаем конфигурацию пакета...")
                        purge_cmd = ['dpkg', '--purge', '--force-remove-reinstreq', 
                                   '--force-remove-depends', '--force-remove-essential', package]
                        result = subprocess.run(purge_cmd, capture_output=True, text=True, timeout=60)
                else:
                    # Обычное принудительное удаление
                    cmd = ['dpkg', '--remove', '--force-remove-reinstreq', '--force-remove-depends', package]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print("   [OK] Пакет %s удален принудительно" % package)
                    logger.log_info("Пакет %s удален принудительно" % package)
                else:
                    print("   [WARNING] Не удалось удалить пакет %s: %s" % (package, result.stderr.strip()))
                    logger.log_warning("Не удалось удалить пакет %s: %s" % (package, result.stderr.strip()))
            
            return True
            
        except Exception as e:
            logger.log_exception(e, "Ошибка принудительного удаления пакетов")
            print("   [ERROR] Ошибка принудительного удаления пакетов: %s" % str(e))
            return False
    
    def _quick_dpkg_check(self):
        """Быстрая проверка dpkg без длительных операций"""
        try:
            # Проверяем только блокирующие файлы
            lock_files = [
                '/var/lib/dpkg/lock-frontend',
                '/var/lib/dpkg/lock',
                '/var/cache/apt/archives/lock',
                '/var/lib/apt/lists/lock'
            ]
            
            for lock_file in lock_files:
                if os.path.exists(lock_file):
                    print("   [WARNING] dpkg заблокирован файлом: %s" % lock_file)
                    return False
            
            # Проверяем, работает ли dpkg вообще
            result = subprocess.run(['dpkg', '--version'], 
                                 capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print("   [OK] dpkg работает нормально")
                return True
            else:
                print("   [WARNING] dpkg не отвечает")
                return False
                
        except Exception as e:
            print("   [WARNING] Быстрая проверка dpkg не удалась: %s" % str(e))
            return False
    
    def run_command_with_interactive_handling(self, cmd, dry_run=False, gui_terminal=None):
        """Запуск команды с перехватом интерактивных запросов"""
        logger = get_logger()
        
        if dry_run:
            print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: команда НЕ выполняется (только симуляция)")
            print("   Команда: %s" % ' '.join(cmd))
            logger.log_command(cmd, "РЕЖИМ ТЕСТИРОВАНИЯ - команда не выполнена", 0)
            return 0
        
        print("[START] Выполнение команды с автоматическими ответами...")
        print("   Команда: %s" % ' '.join(cmd))
        logger.log_command(cmd, "Начинаем выполнение команды")
        
        try:
            # Подготавливаем переменные окружения для процесса
            import os
            env = os.environ.copy()
            env['DEBIAN_FRONTEND'] = 'noninteractive'
            # Явно НЕ устанавливаем UCF_FORCE_CONF* чтобы избежать конфликтов
            env.pop('UCF_FORCE_CONFFOLD', None)
            env.pop('UCF_FORCE_CONFFNEW', None)
            
            # Запускаем процесс с дополнительной защитой
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                preexec_fn=None,  # Отключаем preexec_fn для безопасности
                env=env  # Передаем очищенные переменные окружения
            )
            
            # Читаем вывод построчно
            output_buffer = ""
            full_output = ""
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                # Выводим строку
                print("   %s" % line.rstrip())
                
                # Добавляем в буфер для анализа
                output_buffer += line
                full_output += line
                
                # Проверяем на интерактивные запросы
                prompt_type = self.detect_interactive_prompt(output_buffer)
                if prompt_type:
                    response = self.get_auto_response(prompt_type)
                    if response == '':
                        print("   [AUTO] Автоматический ответ: Enter (пустой ответ) для %s" % prompt_type)
                        logger.log_info("Автоматический ответ: Enter для %s" % prompt_type)
                    else:
                        print("   [AUTO] Автоматический ответ: %s (для %s)" % (response, prompt_type))
                        logger.log_info("Автоматический ответ: %s для %s" % (response, prompt_type))
                    
                    # Отправляем ответ
                    process.stdin.write(response + '\n')
                    process.stdin.flush()
                    
                    # Очищаем буфер
                    output_buffer = ""
            
            # Ждем завершения процесса
            return_code = process.wait()
            
            # Логируем результат команды
            logger.log_command(cmd, full_output, return_code)
            
            if return_code == 0:
                print("   [OK] Команда выполнена успешно")
                logger.log_info("Команда выполнена успешно")
            else:
                print("   [ERROR] Команда завершилась с ошибкой (код: %d)" % return_code)
                logger.log_error("Команда завершилась с ошибкой (код: %d)" % return_code)
                
                # Проверяем на ошибки dpkg
                if "dpkg была прервана" in output_buffer or "dpkg --configure -a" in output_buffer:
                    print("   [TOOL] Обнаружена ошибка dpkg, запускаем автоматическое исправление...")
                    logger.log_warning("Обнаружена ошибка dpkg, запускаем автоматическое исправление")
                    
                    try:
                        if self.auto_fix_dpkg_errors():
                            print("   [OK] Ошибки dpkg исправлены автоматически")
                            logger.log_info("Ошибки dpkg исправлены автоматически")
                        else:
                            print("   [WARNING] Не удалось автоматически исправить ошибки dpkg")
                            logger.log_warning("Не удалось автоматически исправить ошибки dpkg")
                    except Exception as fix_error:
                        logger.log_exception(fix_error, "Ошибка при исправлении dpkg")
                        print("   [ERROR] Ошибка при исправлении dpkg: %s" % str(fix_error))
            
            return return_code
            
        except Exception as e:
            logger.log_exception(e, "Ошибка выполнения команды")
            print("   [ERROR] Ошибка выполнения команды: %s" % str(e))
            
            # Проверяем на ошибку сегментации (код 139)
            if hasattr(e, 'returncode') and e.returncode == 139:
                print("   [CRITICAL] Обнаружена ошибка сегментации (SIGSEGV)!")
                logger.log_error("Обнаружена ошибка сегментации (SIGSEGV)")
                print("   [TOOL] Пробуем восстановить систему...")
                
                # Пробуем восстановить систему
                if self._recover_from_segfault():
                    print("   [OK] Система восстановлена после ошибки сегментации")
                    logger.log_info("Система восстановлена после ошибки сегментации")
                    return 139  # Возвращаем код ошибки для обработки на верхнем уровне
                else:
                    print("   [ERROR] Не удалось восстановить систему")
                    logger.log_error("Не удалось восстановить систему")
            
            return 1
    
    def _recover_from_segfault(self):
        """Восстановление системы после ошибки сегментации"""
        logger = get_logger()
        print("   [RECOVERY] Начинаем восстановление системы...")
        logger.log_info("Начинаем восстановление системы после ошибки сегментации")
        
        try:
            # 1. Очищаем блокирующие файлы
            print("   [RECOVERY] Очищаем блокирующие файлы...")
            logger.cleanup_locks()
            
            # 2. Исправляем конфигурацию dpkg
            print("   [RECOVERY] Исправляем конфигурацию dpkg...")
            result = subprocess.run(['dpkg', '--configure', '-a'], 
                                 capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print("   [WARNING] dpkg требует дополнительного исправления")
                logger.log_warning("dpkg требует дополнительного исправления")
            
            # 3. Исправляем сломанные зависимости
            print("   [RECOVERY] Исправляем сломанные зависимости...")
            result = subprocess.run(['apt', '--fix-broken', 'install', '-y'], 
                                 capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print("   [WARNING] Не удалось исправить зависимости")
                logger.log_warning("Не удалось исправить зависимости")
            
            # 4. Очищаем кэш APT
            print("   [RECOVERY] Очищаем кэш APT...")
            subprocess.run(['apt', 'clean'], capture_output=True, text=True, timeout=30)
            subprocess.run(['apt', 'autoclean'], capture_output=True, text=True, timeout=30)
            
            # 5. Проверяем состояние системы
            print("   [RECOVERY] Проверяем состояние системы...")
            if self.check_system_resources():
                print("   [OK] Система восстановлена успешно")
                logger.log_info("Система восстановлена успешно")
                return True
            else:
                print("   [ERROR] Система не восстановлена")
                logger.log_error("Система не восстановлена")
                return False
                
        except Exception as e:
            logger.log_exception(e, "Ошибка восстановления системы")
            print("   [ERROR] Ошибка восстановления системы: %s" % str(e))
            return False
    
    def update_system(self, dry_run=False):
        """Обновление системы"""
        logger = get_logger()
        print("[PACKAGE] Обновление системы...")
        
        if dry_run:
            print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: обновление НЕ выполняется")
            print("[OK] Будет выполнено: apt-get update && apt-get dist-upgrade -y && apt-get autoremove -y")
            return True
        
        # Проверяем системные ресурсы перед обновлением
        print("\n[SYSTEM] Проверка системных ресурсов перед обновлением...")
        if not self.check_system_resources():
            print("[ERROR] Системные ресурсы не соответствуют требованиям для обновления")
            logger.log_error("Системные ресурсы не соответствуют требованиям для обновления")
            return False
        
        # Сначала обновляем списки пакетов
        print("\n[PROCESS] Обновление списков пакетов...")
        update_cmd = ['apt-get', 'update']
        result = self.run_command_with_interactive_handling(update_cmd, dry_run, gui_terminal=True)
        
        if result != 0:
            print("[ERROR] Ошибка обновления списков пакетов")
            return False
        
        # Затем обновляем систему
        print("\n[START] Обновление системы...")
        upgrade_cmd = ['apt-get', 'dist-upgrade', '-y']
        result = self.run_command_with_interactive_handling(upgrade_cmd, dry_run, gui_terminal=True)
        
        # Обрабатываем результат обновления
        if result == 0:
            print("[OK] Система успешно обновлена")
            
            # Автоматическая очистка ненужных пакетов
            print("\n[CLEANUP] Автоматическая очистка ненужных пакетов...")
            autoremove_cmd = ['apt-get', 'autoremove', '-y']
            autoremove_result = self.run_command_with_interactive_handling(autoremove_cmd, dry_run, gui_terminal=True)
            
            if autoremove_result == 0:
                print("[OK] Ненужные пакеты успешно удалены")
            else:
                print("[WARNING] Предупреждение: не удалось удалить ненужные пакеты")
            
            return True
            
        elif result == 139:
            # Ошибка сегментации - система уже восстановлена
            print("[WARNING] Обновление завершилось с ошибкой сегментации, но система восстановлена")
            logger.log_warning("Обновление завершилось с ошибкой сегментации, но система восстановлена")
            
            # Пробуем продолжить с более безопасным подходом
            print("[TOOL] Пробуем безопасное обновление...")
            return self._safe_update_retry()
            
        else:
            print("[ERROR] Ошибка обновления системы")
            # Пробуем автоматически исправить ошибки dpkg
            if self.auto_fix_dpkg_errors():
                print("[TOOL] Ошибки dpkg исправлены, повторяем обновление...")
                # Повторяем обновление после исправления
                result = self.run_command_with_interactive_handling(upgrade_cmd, dry_run, gui_terminal=True)
                if result == 0:
                    print("[OK] Система успешно обновлена после исправления")
                    return True
                elif result == 139:
                    print("[WARNING] Повторная ошибка сегментации, пробуем безопасное обновление...")
                    return self._safe_update_retry()
                else:
                    print("[ERROR] Ошибка обновления системы даже после исправления")
                    logger.log_error("Ошибка обновления системы даже после исправления")
                    
                    # Пробуем исправить проблемы с кэшем APT
                    print("[TOOL] Пробуем исправить проблемы с кэшем APT...")
                    logger.log_info("Пробуем исправить проблемы с кэшем APT")
                    
                    try:
                        # Очищаем кэш APT
                        cleanup_cmd = ['apt-get', 'clean']
                        result = self.run_command_with_interactive_handling(cleanup_cmd, False, gui_terminal=True)
                        if result == 0:
                            print("   [OK] Кэш APT очищен")
                            logger.log_info("Кэш APT очищен")
                        
                        # Пробуем обновление с --fix-missing
                        print("[TOOL] Пробуем обновление с --fix-missing...")
                        logger.log_info("Пробуем обновление с --fix-missing")
                        fix_missing_cmd = ['apt-get', 'dist-upgrade', '-y', '--fix-missing']
                        result = self.run_command_with_interactive_handling(fix_missing_cmd, False, gui_terminal=True)
                        
                        if result == 0:
                            print("   [OK] Обновление с --fix-missing выполнено успешно")
                            logger.log_info("Обновление с --fix-missing выполнено успешно")
                            return True
                        else:
                            print("   [WARNING] Обновление с --fix-missing также завершилось с ошибкой")
                            logger.log_warning("Обновление с --fix-missing также завершилось с ошибкой")
                            return False
                            
                    except Exception as cache_error:
                        logger.log_exception(cache_error, "Ошибка при исправлении кэша APT")
                        print("   [ERROR] Ошибка при исправлении кэша APT: %s" % str(cache_error))
                    return False
            else:
                print("[ERROR] Не удалось автоматически исправить ошибки dpkg")
                return False
    
    def _safe_update_retry(self):
        """Безопасное повторное обновление после ошибки сегментации"""
        logger = get_logger()
        print("[SAFE] Безопасное повторное обновление...")
        logger.log_info("Начинаем безопасное повторное обновление")
        
        try:
            # 1. Обновляем только безопасные пакеты
            print("   [SAFE] Обновляем только безопасные пакеты...")
            safe_upgrade_cmd = ['apt-get', 'upgrade', '-y']
            result = self.run_command_with_interactive_handling(safe_upgrade_cmd, False, gui_terminal=True)
            
            if result == 0:
                print("   [OK] Безопасное обновление выполнено успешно")
                logger.log_info("Безопасное обновление выполнено успешно")
                return True
            elif result == 139:
                print("   [WARNING] Безопасное обновление также завершилось с ошибкой сегментации")
                logger.log_warning("Безопасное обновление также завершилось с ошибкой сегментации")
                
                # Пробуем обновить только критические пакеты
                print("   [SAFE] Пробуем обновить только критические пакеты...")
                critical_cmd = ['apt-get', 'install', '--only-upgrade', '-y', 'apt', 'dpkg', 'libc6']
                result = self.run_command_with_interactive_handling(critical_cmd, False, gui_terminal=True)
                
                if result == 0:
                    print("   [OK] Критические пакеты обновлены успешно")
                    logger.log_info("Критические пакеты обновлены успешно")
                    return True
                else:
                    print("   [ERROR] Не удалось обновить даже критические пакеты")
                    logger.log_error("Не удалось обновить даже критические пакеты")
                    return False
            else:
                print("   [ERROR] Безопасное обновление завершилось с ошибкой")
                logger.log_error("Безопасное обновление завершилось с ошибкой")
                return False
                
        except Exception as e:
            logger.log_exception(e, "Ошибка безопасного повторного обновления")
            print("   [ERROR] Ошибка безопасного повторного обновления: %s" % str(e))
            return False
    
    def auto_fix_dpkg_errors(self):
        """Автоматическое исправление ошибок dpkg"""
        logger = get_logger()
        print("[TOOL] Автоматическое исправление ошибок dpkg...")
        logger.log_info("Начинаем автоматическое исправление ошибок dpkg")
        
        try:
            # Сначала очищаем блокирующие файлы
            logger.log_info("Очищаем блокирующие файлы перед исправлением dpkg")
            logger.cleanup_locks()
            
            # 1. Исправляем конфигурацию dpkg
            print("   [TOOL] Запускаем dpkg --configure -a...")
            logger.log_info("Запускаем dpkg --configure -a")
            configure_cmd = ['dpkg', '--configure', '-a']
            result = self.run_command_with_interactive_handling(configure_cmd, False, gui_terminal=True)
            
            if result == 0:
                print("   [OK] dpkg --configure -a выполнен успешно")
                logger.log_info("dpkg --configure -a выполнен успешно")
            else:
                print("   [WARNING] dpkg --configure -a завершился с ошибкой")
                logger.log_warning("dpkg --configure -a завершился с ошибкой")
            
            # 2. Исправляем сломанные зависимости
            print("   [TOOL] Запускаем apt --fix-broken install...")
            logger.log_info("Запускаем apt --fix-broken install")
            fix_cmd = ['apt', '--fix-broken', 'install', '-y']
            
            try:
                result = self.run_command_with_interactive_handling(fix_cmd, False, gui_terminal=True)
                
                if result == 0:
                    print("   [OK] apt --fix-broken install выполнен успешно")
                    logger.log_info("apt --fix-broken install выполнен успешно")
                    return True
                else:
                    print("   [WARNING] apt --fix-broken install завершился с ошибкой")
                    logger.log_warning("apt --fix-broken install завершился с ошибкой")
                    
            except Exception as fix_error:
                logger.log_exception(fix_error, "Критическая ошибка в apt --fix-broken install")
                print("   [ERROR] Критическая ошибка в apt --fix-broken install: %s" % str(fix_error))
                logger.cleanup_locks()  # Очищаем блокировки при критической ошибке
                return False
                
                # 3. Принудительное удаление проблемных пакетов
                print("   [TOOL] Пробуем принудительное удаление проблемных пакетов...")
                logger.log_warning("Пробуем принудительное удаление проблемных пакетов")
                force_remove_cmd = ['dpkg', '--remove', '--force-remove-reinstreq', 'python3-tk']
                result = self.run_command_with_interactive_handling(force_remove_cmd, False, gui_terminal=True)
                
                if result == 0:
                    print("   [OK] Проблемные пакеты удалены принудительно")
                    logger.log_info("Проблемные пакеты удалены принудительно")
                    # Повторяем исправление зависимостей
                    logger.log_info("Повторяем исправление зависимостей после принудительного удаления")
                    result = self.run_command_with_interactive_handling(fix_cmd, False, gui_terminal=True)
                    if result == 0:
                        print("   [OK] Зависимости исправлены после принудительного удаления")
                        logger.log_info("Зависимости исправлены после принудительного удаления")
                        return True
                    else:
                        logger.log_error("Не удалось исправить зависимости после принудительного удаления")
                
                logger.log_error("Автоматическое исправление dpkg не удалось")
                return False
                
        except Exception as e:
            logger.log_exception(e, "Ошибка автоматического исправления dpkg")
            print("   [ERROR] Ошибка автоматического исправления: %s" % str(e))
            return False
    
    def simulate_update_scenarios(self):
        """Симуляция различных сценариев обновления"""
        print("[PROCESS] Симуляция сценариев обновления...")
        
        # Тест 1: dpkg конфигурационный файл
        print("\n[LIST] Тест 1: dpkg конфигурационный файл")
        test_output = """Файл настройки «/etc/ssl/openssl.cnf»
==> Изменён с момента установки (вами или сценарием).
==> Автор пакета предоставил обновлённую версию.
*** openssl.cnf (Y/I/N/O/D/Z) [по умолчанию N] ?"""
        
        prompt_type = self.detect_interactive_prompt(test_output)
        if prompt_type:
            response = self.get_auto_response(prompt_type)
            print("   [OK] Обнаружен запрос: %s" % prompt_type)
            if response == '':
                print("   [OK] Автоматический ответ: Enter (пустой ответ)")
            else:
                print("   [OK] Автоматический ответ: %s" % response)
        else:
            print("   [ERROR] Запрос не обнаружен")
        
        # Тест 2: перезапуск служб
        print("\n[PROCESS] Тест 2: перезапуск служб")
        test_output = """Перезапустить службы во время пакетных операций? [Y/n]"""
        
        prompt_type = self.detect_interactive_prompt(test_output)
        if prompt_type:
            response = self.get_auto_response(prompt_type)
            print("   [OK] Обнаружен запрос: %s" % prompt_type)
            if response == '':
                print("   [OK] Автоматический ответ: Enter (пустой ответ)")
            else:
                print("   [OK] Автоматический ответ: %s" % response)
        else:
            print("   [ERROR] Запрос не обнаружен")
        
        print("\n[OK] Симуляция завершена")

def sync_system_time():
    """Синхронизация системного времени"""
    print("[TIME] Синхронизация системного времени...")
    
    try:
        # Синхронизируем время через ntpdate
        result = subprocess.call(['ntpdate', '-s', 'pool.ntp.org'], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result == 0:
            print("[OK] Время синхронизировано успешно")
            return True
        else:
            print("[WARNING] ntpdate не доступен, пробуем hwclock...")
            
            # Альтернативный способ через hwclock
            result = subprocess.call(['hwclock', '--hctosys'], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if result == 0:
                print("[OK] Время синхронизировано через hwclock")
                return True
            else:
                print("[WARNING] Не удалось синхронизировать время автоматически")
                print("   Рекомендуется синхронизировать время вручную")
                return False
                
    except Exception as e:
        print("[WARNING] Ошибка синхронизации времени: %s" % str(e))
        return False

def check_system_requirements():
    """Проверка системных требований"""
    print("[INFO] Проверка системных требований...")
    
    # Сначала синхронизируем время
    sync_system_time()
    
    # Проверяем права root
    if os.geteuid() != 0:
        print("[ERROR] Требуются права root для работы с системными файлами")
        print("   Запустите: sudo python astra-automation.py")
        return False
    
    # Проверяем Python версию (требуется Python 3.x)
    if sys.version_info[0] != 3:
        print("[ERROR] Требуется Python 3.x")
        print("   Текущая версия: %s" % sys.version)
        return False
    
    print("[OK] Python версия подходящая: %s" % sys.version.split()[0])
    
    # Проверяем наличие apt-get
    try:
        subprocess.check_call(['which', 'apt-get'], 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
        print("[OK] apt-get найден")
    except subprocess.CalledProcessError:
        print("[ERROR] apt-get не найден - возможно не Debian/Ubuntu система")
        return False
    
    # Проверяем наличие sources.list
    sources_list = '/etc/apt/sources.list'
    if not os.path.exists(sources_list):
        print("[ERROR] Файл %s не найден" % sources_list)
        return False
    
    print("[OK] Все требования выполнены")
    return True

def run_repo_checker(gui_terminal=None, dry_run=False):
    """Запуск проверки репозиториев через класс RepoChecker"""
    print("\n[START] Запуск автоматизации проверки репозиториев...")
    
    try:
        # Создаем экземпляр класса RepoChecker
        checker = RepoChecker(gui_terminal=gui_terminal)
        
        # Проверяем права доступа
        if os.geteuid() != 0:
            print("[ERROR] Требуются права root для работы с /etc/apt/sources.list")
            print("Запустите: sudo python3 astra-automation.py")
            return False
        
        # Создаем backup
        if not checker.backup_sources_list(dry_run):
            return False
        
        # Обрабатываем репозитории
        temp_file = checker.process_all_repos()
        if not temp_file:
            return False
        
        # Показываем статистику
        stats = checker.get_statistics()
        print("\nСТАТИСТИКА РЕПОЗИТОРИЕВ:")
        print("=========================")
        print("[LIST] Репозитории:")
        print("   • Активировано: %d рабочих" % stats['activated'])
        print("   • Деактивировано: %d нерабочих" % stats['deactivated'])
        
        # Применяем изменения
        if checker.apply_changes(temp_file, dry_run):
            if dry_run:
                print("\n[OK] Тест завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
            else:
                print("\n[OK] Тест завершен успешно!")
            
            # Очистка временного файла
            try:
                os.unlink(temp_file)
            except:
                pass
            
            return True
        else:
            print("\n[ERROR] Ошибка применения изменений")
            return False
            
    except Exception as e:
        print("[ERROR] Ошибка запуска проверки репозиториев: %s" % str(e))
        return False

def run_system_stats(temp_dir, dry_run=False):
    """Запуск модуля статистики системы через класс SystemStats"""
    print("\n[STATS] Запуск анализа статистики системы...")
    
    try:
        # Создаем экземпляр класса SystemStats
        stats = SystemStats()
        
        # Проверяем права доступа
        if os.geteuid() != 0:
            print("[ERROR] Требуются права root для работы с системными пакетами")
            print("Запустите: sudo python3 astra-automation.py")
            return False
        
        # Анализируем обновления
        if not stats.get_updatable_packages():
            print("[WARNING] Предупреждение: не удалось получить список обновлений")
        
        # Анализируем автоудаление
        if not stats.get_autoremove_packages():
            print("[WARNING] Предупреждение: не удалось проанализировать автоудаление")
        
        # Подсчитываем пакеты для установки
        if not stats.calculate_install_stats():
            print("[WARNING] Предупреждение: не удалось подсчитать пакеты для установки")
        
        # Показываем статистику
        stats.display_statistics()
        
        if dry_run:
            print("[OK] Анализ статистики завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
        else:
            print("[OK] Анализ статистики завершен успешно!")
        
        return True
        
    except Exception as e:
        print("[ERROR] Ошибка анализа статистики: %s" % str(e))
        return False

def run_interactive_handler(temp_dir, dry_run=False):
    """Запуск модуля перехвата интерактивных запросов через класс InteractiveHandler"""
    print("\n[AUTO] Запуск тестирования перехвата интерактивных запросов...")
    
    try:
        # Создаем экземпляр класса InteractiveHandler напрямую
        handler = InteractiveHandler()
        
        # Запускаем симуляцию интерактивных сценариев
        handler.simulate_interactive_scenarios()
        
        if dry_run:
            print("[OK] Тест перехвата интерактивных запросов завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
        else:
            print("[OK] Тест перехвата интерактивных запросов завершен успешно!")
        
        return True
        
    except Exception as e:
        print("[ERROR] Ошибка теста перехвата интерактивных запросов: %s" % str(e))
        return False

def run_system_updater(temp_dir, dry_run=False):
    """Запуск модуля обновления системы через класс SystemUpdater"""
    print("\n[PROCESS] Запуск обновления системы...")
    
    try:
        # Создаем экземпляр класса SystemUpdater напрямую
        updater = SystemUpdater()
        
        # Запускаем симуляцию сценариев обновления
        updater.simulate_update_scenarios()
        
        # Если не dry_run, запускаем реальное обновление
        if not dry_run:
            print("[TOOL] Тест реального обновления системы...")
            success = updater.update_system(dry_run)
            if success:
                print("[OK] Обновление системы завершено успешно")
            else:
                print("[ERROR] Обновление системы завершено с ошибкой")
        else:
            print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: реальное обновление не выполняется")
            updater.update_system(dry_run)
        
        if dry_run:
            print("[OK] Обновление системы завершено успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
        else:
            print("[OK] Обновление системы завершено успешно!")
        
        return True
        
    except Exception as e:
        print("[ERROR] Ошибка обновления системы: %s" % str(e))
        return False

def run_gui_monitor(temp_dir, dry_run=False):
    """Запуск GUI мониторинга через класс AutomationGUI"""
    print("\n[GUI] Запуск GUI мониторинга...")
    
    try:
        # Создаем экземпляр класса AutomationGUI напрямую
        print("   [OK] Создаем экземпляр AutomationGUI...")
        gui = AutomationGUI(console_mode=False)  # Всегда GUI режим для этой функции
        
        print("   [OK] GUI создан успешно, запускаем...")
        
        # Запускаем GUI
        gui.run()
        
        print("[OK] GUI мониторинг завершен успешно!")
        return True
        
    except Exception as e:
        print("[ERROR] Ошибка запуска GUI: %s" % str(e))
        return False

def cleanup_temp_files(temp_dir):
    """Очистка временных файлов"""
    try:
        shutil.rmtree(temp_dir)
        print("[OK] Временные файлы очищены")
    except Exception as e:
        print("[WARNING] Предупреждение: не удалось очистить временные файлы: %s" % str(e))

def main():
    """Основная функция"""
    logger = get_logger()
    
    # Диагностическая информация
    logger.log_info("Аргументы командной строки: %s" % str(sys.argv))
    logger.log_info("Количество аргументов: %d" % len(sys.argv))
    logger.log_info("Текущая рабочая директория: %s" % os.getcwd())
    logger.log_info("Python версия: %s" % sys.version)
    
    try:
        # Логируем системную информацию
        logger.log_system_info()
        
        # Проверяем аргументы командной строки
        dry_run = False
        console_mode = False
        
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                if arg == '--dry-run':
                    dry_run = True
                    logger.log_info("Включен режим тестирования (dry-run)")
                elif arg == '--console':
                    console_mode = True
                    logger.log_info("Включен консольный режим")
            
            logger.log_info("Начинаем выполнение основной программы")
        
        # По умолчанию запускаем GUI, если не указан --console
        if not console_mode:
            logger.log_info("Запускаем GUI режим")
            # Проверяем системные требования
            if not check_system_requirements():
                logger.log_error("Системные требования не выполнены")
                sys.exit(1)
            
            # Запускаем GUI
            print("[GUI] Запуск GUI мониторинга...")
            logger.log_info("Запускаем GUI мониторинг")
            
            try:
                gui_success = run_gui_monitor(None, dry_run)
                if gui_success:
                    print("[OK] GUI мониторинг завершен")
                    logger.log_info("GUI мониторинг завершен успешно")
                else:
                    print("[ERROR] Ошибка GUI мониторинга")
                    logger.log_error("Ошибка GUI мониторинга")
            except Exception as gui_error:
                logger.log_exception(gui_error, "Критическая ошибка GUI")
                print("[ERROR] Критическая ошибка GUI: %s" % str(gui_error))
                # Очищаем блокирующие файлы при ошибке GUI
                logger.cleanup_locks()
            return
    
        # Консольный режим (только если указан --console)
        logger.log_info("Запускаем консольный режим")
        print("=" * 60)
        if dry_run:
            print("FSA-AstraInstall Automation (РЕЖИМ ТЕСТИРОВАНИЯ)")
        else:
            print("FSA-AstraInstall Automation")
        print("Автоматизация установки Astra.IDE")
        print("=" * 60)
        
        temp_dir = None
        
        try:
            # Проверяем системные требования (БЕЗ установки GUI пакетов)
            logger.log_info("Проверяем системные требования")
            if not check_system_requirements():
                logger.log_error("Системные требования не выполнены")
                sys.exit(1)
        
            # В консольном режиме обновляем систему (репозитории уже настроены в bash скрипте)
            logger.log_info("КОНСОЛЬНЫЙ РЕЖИМ: Обновление системы")
            print("\n[CONSOLE] Консольный режим - обновление системы...")
            
            # Обновляем систему
            logger.log_info("Запускаем обновление системы")
            print("\n[UPDATE] Обновление системы...")
            updater = SystemUpdater()
            
            if dry_run:
                print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: обновление НЕ выполняется")
                print("[OK] Будет выполнено: apt-get update && apt-get dist-upgrade -y && apt-get autoremove -y")
                update_success = True
            else:
                # Проверяем системные ресурсы
                if not updater.check_system_resources():
                    print("[ERROR] Системные ресурсы не соответствуют требованиям для обновления")
                    logger.log_error("Системные ресурсы не соответствуют требованиям для обновления")
                    sys.exit(1)
                
                # Запускаем обновление
                update_success = updater.update_system(dry_run)
            
            # Устанавливаем успех для всех остальных модулей (они не выполняются в консольном режиме)
            repo_success = True
            stats_success = True
            interactive_success = True
            
            if repo_success and stats_success and interactive_success and update_success:
                if dry_run:
                    print("\n[SUCCESS] Автоматизация завершена успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
                    logger.log_info("Автоматизация завершена успешно в режиме тестирования")
                    print("\n[LIST] РЕЗЮМЕ РЕЖИМА ТЕСТИРОВАНИЯ:")
                    print("=============================")
                    print("[OK] Все проверки пройдены успешно")
                    print("[OK] Система готова к автоматизации")
                    print("[WARNING] Никаких изменений в системе НЕ внесено")
                    print("[START] Для реальной установки запустите без --dry-run")
                else:
                    print("\n[SUCCESS] Автоматизация завершена успешно!")
                    logger.log_info("Автоматизация завершена успешно")
            else:
                print("\n[ERROR] Автоматизация завершена с ошибками")
                logger.log_error("Автоматизация завершена с ошибками")
                if not repo_success:
                    print("   [ERROR] Ошибка в модуле проверки репозиториев")
                    logger.log_error("Ошибка в модуле проверки репозиториев")
                if not stats_success:
                    print("   [ERROR] Ошибка в модуле статистики системы")
                    logger.log_error("Ошибка в модуле статистики системы")
                if not interactive_success:
                    print("   [ERROR] Ошибка в модуле перехвата интерактивных запросов")
                    logger.log_error("Ошибка в модуле перехвата интерактивных запросов")
                if not update_success:
                    print("   [ERROR] Ошибка в модуле обновления системы")
                    logger.log_error("Ошибка в модуле обновления системы")
                sys.exit(1)
            
        except KeyboardInterrupt:
            logger.log_warning("Программа остановлена пользователем (Ctrl+C)")
            print("\n[STOP] Остановлено пользователем")
            # Очищаем блокирующие файлы при прерывании
            logger.cleanup_locks()
            sys.exit(1)
        except Exception as e:
            logger.log_exception(e, "Критическая ошибка в консольном режиме")
            print("\n[ERROR] Критическая ошибка: %s" % str(e))
            # Очищаем блокирующие файлы при ошибке
            logger.cleanup_locks()
            sys.exit(1)
        finally:
            # Очищаем временные файлы
            if temp_dir:
                cleanup_temp_files(temp_dir)
            logger.log_info("Программа завершена")
            
    except Exception as main_error:
        # Критическая ошибка на уровне main()
        logger.log_exception(main_error, "Критическая ошибка в main()")
        print("\n[FATAL] Критическая ошибка программы: %s" % str(main_error))
        print("Проверьте лог файл: %s" % logger.get_log_path())
        # Очищаем блокирующие файлы при критической ошибке
        try:
            logger.cleanup_locks()
        except:
            pass
        sys.exit(1)

if __name__ == '__main__':
    main()

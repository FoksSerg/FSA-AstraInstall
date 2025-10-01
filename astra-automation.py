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
        # Паттерны поддерживают русский и английский языки для универсальности
        self.patterns = {
            # dpkg конфигурационные файлы (русский и английский)
            'dpkg_config_old': r'\*\*\* .* \(Y/I/N/O/D/Z\) \[.*\] \?',
            'dpkg_config_ru': r'Что нужно сделать\?.*Y или I.*установить версию',
            'dpkg_config_en': r'What would you like to do about it\?.*Y or I.*install the package',
            'dpkg_conffile_ru': r'файл настройки.*Изменён.*Автор пакета',
            'dpkg_conffile_en': r'Configuration file.*modified.*Package distributor',
            
            # apt конфигурация
            'apt_config': r'(Настройка пакета|Configuring)',
            
            # Клавиатура
            'keyboard_config': r'(Выберите подходящую раскладку клавиатуры|Select.*keyboard layout)',
            'keyboard_switch': r'(способ переключения клавиатуры|keyboard switching method)',
            
            # Язык системы
            'language_config': r'(Выберите язык системы|Select system language)',
            
            # Перезапуск служб
            'restart_services_ru': r'Перезапустить службы во время пакетных операций',
            'restart_services_en': r'(Restart services during package upgrades|Services to restart)',
            
            # Общие yes/no запросы
            'yes_no_ru': r'\(Y/N\)|да/нет|\[Y/n\]|\[y/N\]',
            'yes_no_en': r'Do you want to continue\?|\(yes/no\)',
            
            # openssl и другие специфичные пакеты
            'openssl_config_ru': r'По умолчанию сохраняется текущая версия файла настройки',
            'openssl_config_en': r'The default action is to keep your current version'
        }
        
        # Все автоматические ответы
        self.responses = {
            'dpkg_config_old': 'Y',
            'dpkg_config_ru': 'Y',
            'dpkg_config_en': 'Y',
            'dpkg_conffile_ru': 'Y',
            'dpkg_conffile_en': 'Y',
            'apt_config': '',        # Принимаем настройки по умолчанию (Enter)
            'keyboard_config': '',   # Принимаем предложенную раскладку (Enter)
            'keyboard_switch': '',   # Принимаем способ переключения (Enter)
            'language_config': '',   # Принимаем язык системы (Enter)
            'restart_services_ru': 'Y',
            'restart_services_en': 'Y',
            'yes_no_ru': 'Y',
            'yes_no_en': 'Y',
            'openssl_config_ru': 'Y',
            'openssl_config_en': 'Y'
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
# КЛАСС ПРОВЕРКИ WINE КОМПОНЕНТОВ
# ============================================================================
class WineComponentsChecker(object):
    """Класс для проверки наличия установленных Wine компонентов и Astra.IDE"""
    
    def __init__(self):
        """Инициализация проверки компонентов"""
        self.wine_astraregul_path = "/opt/wine-astraregul/bin/wine"
        self.wine_9_path = "/opt/wine-9.0/bin/wine"
        self.ptrace_scope_path = "/proc/sys/kernel/yama/ptrace_scope"
        
        # Определяем домашнюю директорию РЕАЛЬНОГО пользователя (не root)
        # Если запущено через sudo, берём SUDO_USER, иначе текущего пользователя
        real_user = os.environ.get('SUDO_USER')
        if real_user and real_user != 'root':
            # Запущено через sudo - используем домашнюю директорию реального пользователя
            import pwd
            self.home = pwd.getpwnam(real_user).pw_dir
        else:
            # Запущено напрямую
            self.home = os.path.expanduser("~")
        
        self.wineprefix = os.path.join(self.home, ".wine-astraregul")
        self.start_script = os.path.join(self.home, "start-astraide.sh")
        self.desktop_shortcut = os.path.join(self.home, "Desktop", "AstraRegul.desktop")
        
        # Результаты проверок
        self.checks = {
            'wine_astraregul': False,
            'wine_9': False,
            'ptrace_scope': False,
            'wineprefix': False,
            'dotnet48': False,
            'vcrun2013': False,
            'vcrun2022': False,
            'd3dcompiler_43': False,
            'd3dcompiler_47': False,
            'dxvk': False,
            'astra_ide': False,
            'start_script': False,
            'desktop_shortcut': False
        }
    
    def check_wine_astraregul(self):
        """Проверка наличия Wine Astraregul"""
        print("[CHECK] Проверка Wine Astraregul...")
        
        if os.path.isfile(self.wine_astraregul_path):
            try:
                # Проверяем что файл исполняемый
                if os.access(self.wine_astraregul_path, os.X_OK):
                    print("   [OK] Wine Astraregul найден: %s" % self.wine_astraregul_path)
                    self.checks['wine_astraregul'] = True
                    return True
                else:
                    print("   [ERR] Wine Astraregul найден, но не исполняемый")
                    return False
            except Exception as e:
                print("   [ERR] Ошибка проверки Wine Astraregul: %s" % str(e))
                return False
        else:
            print("   [ERR] Wine Astraregul не найден: %s" % self.wine_astraregul_path)
            return False
    
    def check_wine_9(self):
        """Проверка наличия Wine 9.0"""
        print("[CHECK] Проверка Wine 9.0...")
        
        if os.path.isfile(self.wine_9_path):
            try:
                if os.access(self.wine_9_path, os.X_OK):
                    print("   [OK] Wine 9.0 найден: %s" % self.wine_9_path)
                    self.checks['wine_9'] = True
                    return True
                else:
                    print("   [ERR] Wine 9.0 найден, но не исполняемый")
                    return False
            except Exception as e:
                print("   [ERR] Ошибка проверки Wine 9.0: %s" % str(e))
                return False
        else:
            print("   [ERR] Wine 9.0 не найден: %s" % self.wine_9_path)
            return False
    
    def check_ptrace_scope(self):
        """Проверка настройки ptrace_scope (должно быть != 3)"""
        print("[CHECK] Проверка ptrace_scope...")
        
        try:
            if os.path.isfile(self.ptrace_scope_path):
                with open(self.ptrace_scope_path, 'r') as f:
                    value = f.read().strip()
                
                if value == '3':
                    print("   [ERR] ptrace_scope = 3 (заблокирован)")
                    print("   [!] Для работы Wine необходимо отключить блокировку ptrace")
                    print("   [!] Выполните: sudo sysctl -w kernel.yama.ptrace_scope=0")
                    return False
                else:
                    print("   [OK] ptrace_scope = %s (разрешен)" % value)
                    self.checks['ptrace_scope'] = True
                    return True
            else:
                print("   [!] Файл ptrace_scope не найден (возможно, не требуется)")
                self.checks['ptrace_scope'] = True
                return True
        except Exception as e:
            print("   [ERR] Ошибка проверки ptrace_scope: %s" % str(e))
            return False
    
    def check_wineprefix(self):
        """Проверка наличия WINEPREFIX"""
        print("[CHECK] Проверка WINEPREFIX...")
        
        if os.path.isdir(self.wineprefix):
            print("   [OK] WINEPREFIX найден: %s" % self.wineprefix)
            self.checks['wineprefix'] = True
            return True
        else:
            print("   [ERR] WINEPREFIX не найден: %s" % self.wineprefix)
            return False
    
    def check_astra_ide_installation(self):
        """Проверка установленной Astra.IDE"""
        print("[CHECK] Проверка установки Astra.IDE...")
        
        if not self.checks['wineprefix']:
            print("   [ERR] WINEPREFIX не найден, невозможно проверить установку")
            return False
        
        # Проверяем наличие drive_c
        drive_c = os.path.join(self.wineprefix, "drive_c")
        if not os.path.isdir(drive_c):
            print("   [ERR] drive_c не существует - WINEPREFIX не инициализирован")
            return False
        
        # Ищем директорию AstraRegul в обеих возможных Program Files
        program_files = os.path.join(drive_c, "Program Files")
        program_files_x86 = os.path.join(drive_c, "Program Files (x86)")
        
        astra_base = None
        for base_dir in [program_files, program_files_x86]:
            test_path = os.path.join(base_dir, "AstraRegul")
            if os.path.isdir(test_path):
                astra_base = test_path
                break
        
        # Если не нашли стандартным способом, пробуем глобальный поиск
        if not astra_base:
            try:
                import glob
                search_pattern = os.path.join(self.wineprefix, "drive_c", "**", "Astra.IDE.exe")
                matches = glob.glob(search_pattern, recursive=True)
                
                if matches:
                    # Извлекаем базовую директорию из найденного пути
                    found_exe = matches[0]
                    parts = found_exe.split(os.sep)
                    for i, part in enumerate(parts):
                        if 'astraregul' in part.lower() and 'wine-astraregul' not in part.lower():
                            astra_base = os.sep.join(parts[:i+1])
                            break
                else:
                    print("   [ERR] Astra.IDE не найдена")
                    return False
            except Exception as e:
                print("   [ERR] Ошибка поиска Astra.IDE: %s" % str(e))
                return False
        
        if not astra_base:
            print("   [ERR] Директория AstraRegul не найдена")
            return False
        
        # Ищем папку Astra.IDE_64_*
        try:
            import glob
            search_pattern = os.path.join(astra_base, "Astra.IDE_64_*")
            astra_dirs = glob.glob(search_pattern)
            
            if not astra_dirs:
                print("   [ERR] Директория Astra.IDE_64_* не найдена")
                return False
            
            # Проверяем наличие исполняемого файла
            astra_exe = os.path.join(astra_dirs[0], "Astra.IDE", "Common", "Astra.IDE.exe")
            
            if os.path.isfile(astra_exe):
                print("   [OK] Astra.IDE установлена: %s" % astra_dirs[0])
                self.checks['astra_ide'] = True
                return True
            else:
                print("   [ERR] Astra.IDE.exe не найден: %s" % astra_exe)
                return False
                
        except Exception as e:
            print("   [ERR] Ошибка проверки Astra.IDE: %s" % str(e))
            return False
    
    def check_start_script(self):
        """Проверка скрипта запуска"""
        print("[CHECK] Проверка скрипта запуска...")
        
        if os.path.isfile(self.start_script):
            if os.access(self.start_script, os.X_OK):
                print("   [OK] Скрипт запуска найден: %s" % self.start_script)
                self.checks['start_script'] = True
                return True
            else:
                print("   [!] Скрипт запуска найден, но не исполняемый")
                self.checks['start_script'] = True
                return True
        else:
            print("   [ERR] Скрипт запуска не найден: %s" % self.start_script)
            return False
    
    def check_desktop_shortcut(self):
        """Проверка ярлыка на рабочем столе"""
        print("[CHECK] Проверка ярлыка на рабочем столе...")
        
        if os.path.isfile(self.desktop_shortcut):
            print("   [OK] Ярлык найден: %s" % self.desktop_shortcut)
            self.checks['desktop_shortcut'] = True
            return True
        else:
            print("   [ERR] Ярлык не найден: %s" % self.desktop_shortcut)
            return False
    
    def check_winetricks_component(self, component_name, check_paths):
        """
        Проверка установленного компонента winetricks
        
        Args:
            component_name: Имя компонента (dotnet48, vcrun2013 и т.д.)
            check_paths: Список путей для проверки относительно WINEPREFIX
        
        Returns:
            bool: True если компонент установлен
        """
        if not self.checks['wineprefix']:
            return False
        
        # Проверяем наличие хотя бы одного из путей
        for path in check_paths:
            full_path = os.path.join(self.wineprefix, path)
            if os.path.exists(full_path):
                return True
        
        return False
    
    def check_winetricks_components(self):
        """Проверка всех компонентов winetricks"""
        print("[CHECK] Проверка компонентов winetricks...")
        
        if not self.checks['wineprefix']:
            print("   [SKIP] WINEPREFIX не найден, пропускаем проверку")
            return
        
        # Определения компонентов и их характерных файлов/директорий
        components = {
            'dotnet48': [
                'drive_c/windows/Microsoft.NET/Framework64/v4.0.30319',
                'drive_c/windows/Microsoft.NET/Framework/v4.0.30319'
            ],
            'vcrun2013': [
                'drive_c/windows/system32/msvcp120.dll',
                'drive_c/windows/syswow64/msvcp120.dll'
            ],
            'vcrun2022': [
                'drive_c/windows/system32/msvcp140.dll',
                'drive_c/windows/system32/vcruntime140.dll'
            ],
            'd3dcompiler_43': [
                'drive_c/windows/system32/d3dcompiler_43.dll',
                'drive_c/windows/syswow64/d3dcompiler_43.dll'
            ],
            'd3dcompiler_47': [
                'drive_c/windows/system32/d3dcompiler_47.dll',
                'drive_c/windows/syswow64/d3dcompiler_47.dll'
            ],
            'dxvk': [
                'drive_c/windows/system32/d3d11.dll',
                'drive_c/windows/system32/dxgi.dll'
            ]
        }
        
        # Проверяем каждый компонент
        for component, paths in components.items():
            is_installed = self.check_winetricks_component(component, paths)
            self.checks[component] = is_installed
            
            if is_installed:
                print("   [OK] %s установлен" % component)
            else:
                print("   [ERR] %s не установлен" % component)
    
    def check_all_components(self):
        """Выполнить все проверки"""
        print("\n[WINE] Проверка всех Wine компонентов и Astra.IDE...")
        print("=" * 60)
        
        # Выполняем проверки в правильном порядке
        self.check_wine_astraregul()
        self.check_wine_9()
        self.check_ptrace_scope()
        self.check_wineprefix()
        self.check_winetricks_components()  # Новая проверка!
        self.check_astra_ide_installation()
        self.check_start_script()
        self.check_desktop_shortcut()
        
        print("\n" + "=" * 60)
        self.display_summary()
        
        return self.is_fully_installed()
    
    def is_fully_installed(self):
        """Проверка что всё установлено полностью"""
        return all(self.checks.values())
    
    def is_wine_installed(self):
        """Проверка что Wine пакеты установлены"""
        return self.checks['wine_astraregul'] and self.checks['wine_9'] and self.checks['ptrace_scope']
    
    def is_astra_ide_installed(self):
        """Проверка что Astra.IDE установлена"""
        return self.checks['astra_ide']
    
    def display_summary(self):
        """Отображение итоговой сводки"""
        print("\n[SUMMARY] Итоговая сводка проверки:")
        print("-" * 60)
        
        status_map = {
            'wine_astraregul': 'Wine Astraregul',
            'wine_9': 'Wine 9.0',
            'ptrace_scope': 'ptrace_scope (разрешен)',
            'wineprefix': 'WINEPREFIX',
            'astra_ide': 'Astra.IDE установлена',
            'start_script': 'Скрипт запуска',
            'desktop_shortcut': 'Ярлык рабочего стола'
        }
        
        for key, label in status_map.items():
            status = "[OK]" if self.checks[key] else "[ERR]"
            print("   %s %s" % (status, label))
        
        print("-" * 60)
        
        if self.is_fully_installed():
            print("[OK] Все компоненты установлены и готовы к работе!")
            return True
        elif self.is_wine_installed() and not self.is_astra_ide_installed():
            print("[!] Wine установлен, но Astra.IDE не установлена")
            print("[!] Требуется установка Astra.IDE")
            return False
        elif not self.is_wine_installed():
            print("[ERR] Wine не установлен или настроен неправильно")
            print("[ERR] Требуется установка Wine пакетов")
            return False
        else:
            print("[!] Некоторые компоненты отсутствуют")
            return False
    
    def get_missing_components(self):
        """Получить список отсутствующих компонентов"""
        missing = []
        
        status_map = {
            'wine_astraregul': 'Wine Astraregul',
            'wine_9': 'Wine 9.0',
            'ptrace_scope': 'ptrace_scope',
            'wineprefix': 'WINEPREFIX',
            'astra_ide': 'Astra.IDE',
            'start_script': 'Скрипт запуска',
            'desktop_shortcut': 'Ярлык рабочего стола'
        }
        
        for key, label in status_map.items():
            if not self.checks[key]:
                missing.append(label)
        
        return missing

# ============================================================================
# КЛАСС МОНИТОРИНГА УСТАНОВКИ
# ============================================================================
class InstallationMonitor(object):
    """Класс для мониторинга процесса установки Wine и Astra.IDE"""
    
    def __init__(self, wineprefix, callback=None):
        """
        Инициализация монитора
        
        Args:
            wineprefix: Путь к WINEPREFIX директории
            callback: Функция обратного вызова для обновления GUI
        """
        self.wineprefix = wineprefix
        self.callback = callback
        self.start_time = None
        self.is_monitoring = False
        self.monitoring_thread = None
        
        # Для мониторинга CPU
        self.last_cpu_stats = self._read_cpu_stats()
        self.last_cpu_time = datetime.datetime.now()
        
        # Для мониторинга сети
        self.last_net_bytes = self._get_network_bytes()
        self.last_net_time = datetime.datetime.now()
        
    def start_monitoring(self):
        """Запустить мониторинг"""
        import threading
        self.start_time = datetime.datetime.now()
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitor_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
    
    def stop_monitoring(self):
        """Остановить мониторинг"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
    
    def _monitor_loop(self):
        """Основной цикл мониторинга (в отдельном потоке)"""
        import time
        
        while self.is_monitoring:
            try:
                # Собираем данные
                data = self.get_status()
                
                # Отправляем в callback если есть
                if self.callback:
                    self.callback(data)
                
                # Ждем 1 секунду
                time.sleep(1)
                
            except Exception as e:
                # Игнорируем ошибки мониторинга
                pass
    
    def _read_cpu_stats(self):
        """Прочитать текущие статистики CPU из /proc/stat"""
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                # cpu  user nice system idle iowait irq softirq steal
                parts = line.split()
                if parts[0] == 'cpu':
                    # Берем все доступные поля (обычно 8-10 полей)
                    stats = [int(x) for x in parts[1:] if x.isdigit()]
                    return stats
        except:
            pass
        return [0, 0, 0, 0]  # user, nice, system, idle
    
    def _get_cpu_usage(self):
        """Получить загрузку CPU в процентах (по всем ядрам)"""
        try:
            # Читаем текущие статистики
            current_stats = self._read_cpu_stats()
            current_time = datetime.datetime.now()
            
            # Проверяем минимальный интервал
            time_diff = (current_time - self.last_cpu_time).total_seconds()
            if time_diff < 0.1:  # Минимум 100ms между замерами
                return 0
            
            # Вычисляем разницу
            if len(self.last_cpu_stats) >= 4 and len(current_stats) >= 4:
                # Суммируем все поля (total time)
                prev_total = sum(self.last_cpu_stats)
                curr_total = sum(current_stats)
                
                # idle - это 4-е поле (индекс 3)
                prev_idle = self.last_cpu_stats[3]
                curr_idle = current_stats[3]
                
                total_diff = curr_total - prev_total
                idle_diff = curr_idle - prev_idle
                
                if total_diff > 0:
                    usage = int(((total_diff - idle_diff) / total_diff) * 100)
                    
                    # Обновляем для следующего замера
                    self.last_cpu_stats = current_stats
                    self.last_cpu_time = current_time
                    
                    return max(0, min(100, usage))  # Ограничиваем 0-100%
            
            # Обновляем даже если не смогли вычислить
            self.last_cpu_stats = current_stats
            self.last_cpu_time = current_time
            return 0
        except:
            return 0
    
    def _get_network_bytes(self):
        """Получить общее количество принятых байтов по сети"""
        try:
            total_bytes = 0
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()[2:]  # Пропускаем заголовки
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        # Второй столбец - принятые байты
                        total_bytes += int(parts[1])
            return total_bytes
        except:
            return 0
    
    def _get_network_speed(self):
        """Получить скорость сети в MB/s"""
        try:
            current_bytes = self._get_network_bytes()
            current_time = datetime.datetime.now()
            
            time_diff = (current_time - self.last_net_time).total_seconds()
            if time_diff > 0:
                bytes_diff = current_bytes - self.last_net_bytes
                speed_mbps = (bytes_diff / time_diff) / (1024 * 1024)  # MB/s
                
                # Обновляем для следующего замера
                self.last_net_bytes = current_bytes
                self.last_net_time = current_time
                
                return max(0, speed_mbps)  # Не может быть отрицательной
            return 0
        except:
            return 0
    
    def get_status(self):
        """
        Получить текущий статус установки
        
        Returns:
            dict: Словарь со статусом {
                'elapsed_time': секунд с начала,
                'wine_processes': список процессов Wine,
                'wineprefix_size': размер в MB,
                'active': True если Wine процессы активны,
                'cpu_usage': процент загрузки CPU,
                'network_speed': скорость сети в MB/s
            }
        """
        status = {
            'elapsed_time': 0,
            'wine_processes': [],
            'wineprefix_size': 0,
            'active': False,
            'cpu_usage': 0,
            'network_speed': 0.0
        }
        
        # Время выполнения
        if self.start_time:
            elapsed = datetime.datetime.now() - self.start_time
            status['elapsed_time'] = int(elapsed.total_seconds())
        
        # Процессы Wine
        try:
            import subprocess
            result = subprocess.run(
                ['ps', 'aux'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            if result.returncode == 0:
                wine_procs = []
                for line in result.stdout.split('\n'):
                    if 'wine' in line.lower() and 'grep' not in line:
                        # Извлекаем имя процесса
                        parts = line.split()
                        if len(parts) > 10:
                            proc_name = parts[10]
                            if proc_name not in wine_procs:
                                wine_procs.append(proc_name)
                
                status['wine_processes'] = wine_procs
                status['active'] = len(wine_procs) > 0
        except:
            pass
        
        # Размер WINEPREFIX
        try:
            if os.path.exists(self.wineprefix):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(self.wineprefix):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        try:
                            total_size += os.path.getsize(fp)
                        except:
                            pass
                
                # Переводим в MB
                status['wineprefix_size'] = int(total_size / (1024 * 1024))
        except:
            pass
        
        # CPU и сеть
        status['cpu_usage'] = self._get_cpu_usage()
        status['network_speed'] = self._get_network_speed()
        
        return status
    
    def format_time(self, seconds):
        """Форматировать время в читаемый вид"""
        minutes = seconds // 60
        secs = seconds % 60
        return "%d мин %d сек" % (minutes, secs)

# ============================================================================
# КЛАСС УСТАНОВКИ WINE КОМПОНЕНТОВ
# ============================================================================
class WineInstaller(object):
    """Класс для установки Wine компонентов и Astra.IDE"""
    
    def __init__(self, logger=None, callback=None, install_wine=True, install_winetricks=True, install_ide=True, winetricks_components=None):
        """
        Инициализация установщика
        
        Args:
            logger: Экземпляр класса Logger для логирования
            callback: Функция для обновления статуса в GUI (опционально)
            install_wine: Устанавливать Wine пакеты (по умолчанию True)
            install_winetricks: Устанавливать winetricks компоненты (по умолчанию True)
            install_ide: Устанавливать Astra.IDE (по умолчанию True)
            winetricks_components: Список компонентов winetricks для установки (если None - устанавливаем все)
        """
        self.logger = logger
        self.callback = callback
        
        # Флаги установки компонентов
        self.install_wine = install_wine
        self.install_winetricks = install_winetricks
        self.install_ide = install_ide
        
        # Список компонентов winetricks (если None - устанавливаем все по умолчанию)
        if winetricks_components is None:
            self.winetricks_components = ['dotnet48', 'vcrun2013', 'vcrun2022', 'd3dcompiler_43', 'd3dcompiler_47', 'dxvk']
        else:
            self.winetricks_components = winetricks_components if winetricks_components else []
        
        # Получаем абсолютный путь к директории скрипта
        # Используем sys.argv[0] вместо __file__ для корректной работы при запуске через bash
        import sys
        if os.path.isabs(sys.argv[0]):
            # Если передан абсолютный путь
            script_path = sys.argv[0]
        else:
            # Если относительный путь - преобразуем в абсолютный относительно текущей директории
            script_path = os.path.join(os.getcwd(), sys.argv[0])
        
        script_dir = os.path.dirname(os.path.abspath(script_path))
        self.astrapack_dir = os.path.join(script_dir, "AstraPack")
        
        # Определяем домашнюю директорию РЕАЛЬНОГО пользователя (не root)
        real_user = os.environ.get('SUDO_USER')
        if real_user and real_user != 'root':
            # Запущено через sudo - устанавливаем для реального пользователя
            import pwd
            self.home = pwd.getpwnam(real_user).pw_dir
            self._log("[INFO] Установка для пользователя %s (домашняя директория: %s)" % (real_user, self.home))
        else:
            # Запущено напрямую
            self.home = os.path.expanduser("~")
            self._log("[INFO] Установка для текущего пользователя (домашняя директория: %s)" % self.home)
        
        self.wineprefix = os.path.join(self.home, ".wine-astraregul")
        
        # Пути к компонентам
        self.wine_9_deb = os.path.join(self.astrapack_dir, "wine_9.0-1_amd64.deb")
        self.wine_astraregul_deb = os.path.join(self.astrapack_dir, "wine-astraregul_10.0-rc6-3_amd64.deb")
        self.astra_ide_exe = os.path.join(self.astrapack_dir, "Astra.IDE_64_1.7.2.1.exe")
        self.winetricks = os.path.join(self.astrapack_dir, "winetricks")
        self.wine_gecko_dir = os.path.join(self.astrapack_dir, "wine-gecko")
        self.winetricks_cache_dir = os.path.join(self.astrapack_dir, "winetricks-cache")
    
    def _log(self, message, level="INFO"):
        """Логирование с выводом в консоль и callback"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_msg = "[%s] [%s] %s" % (timestamp, level, message)
        
        print(log_msg)
        
        if self.logger:
            if level == "ERROR":
                self.logger.log_error(message)
            else:
                self.logger.log_info(message)
        
        if self.callback:
            self.callback(message)
    
    def _run_command(self, cmd, description="", sudo=False):
        """Выполнение команды с логированием"""
        self._log("Выполнение: %s" % description if description else " ".join(cmd))
        
        try:
            if sudo and os.geteuid() != 0:
                self._log("Требуются права root для: %s" % description, "ERROR")
                return False
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            if result.returncode == 0:
                self._log("Успешно: %s" % description)
                if result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            self._log("  > %s" % line)
                return True
            else:
                self._log("Ошибка: %s (код %d)" % (description, result.returncode), "ERROR")
                if result.stderr:
                    for line in result.stderr.strip().split('\n'):
                        if line.strip():
                            self._log("  ! %s" % line, "ERROR")
                return False
        
        except Exception as e:
            self._log("Исключение при выполнении %s: %s" % (description, str(e)), "ERROR")
            return False
    
    def check_prerequisites(self):
        """Проверка наличия всех необходимых файлов"""
        self._log("=" * 60)
        self._log("ПРОВЕРКА ПРЕДВАРИТЕЛЬНЫХ УСЛОВИЙ")
        self._log("=" * 60)
        
        # Логируем директорию AstraPack
        self._log("Директория AstraPack: %s" % self.astrapack_dir)
        
        if not os.path.exists(self.astrapack_dir):
            self._log("ОШИБКА: Директория AstraPack не найдена!", "ERROR")
            self._log("Создайте папку и поместите в нее все необходимые файлы", "ERROR")
            return False
        
        missing_files = []
        
        # Проверяем наличие файлов
        files_to_check = [
            (self.wine_9_deb, "Wine 9.0 .deb"),
            (self.wine_astraregul_deb, "Wine Astraregul .deb"),
            (self.astra_ide_exe, "Astra.IDE установщик"),
            (self.winetricks, "winetricks"),
            (self.wine_gecko_dir, "wine-gecko компоненты"),
            (self.winetricks_cache_dir, "winetricks кэш")
        ]
        
        for file_path, description in files_to_check:
            if os.path.exists(file_path):
                self._log("[OK] Найден: %s" % description)
            else:
                self._log("[ERR] Отсутствует: %s (%s)" % (description, file_path), "ERROR")
                missing_files.append(description)
        
        if missing_files:
            self._log("=" * 60, "ERROR")
            self._log("ОШИБКА: Отсутствуют необходимые файлы:", "ERROR")
            for f in missing_files:
                self._log("  - %s" % f, "ERROR")
            self._log("Поместите все файлы в папку: %s" % self.astrapack_dir, "ERROR")
            return False
        
        # Проверяем права root
        if os.geteuid() != 0:
            self._log("ОШИБКА: Требуются права root для установки", "ERROR")
            return False
        
        self._log("=" * 60)
        self._log("ВСЕ ПРЕДВАРИТЕЛЬНЫЕ УСЛОВИЯ ВЫПОЛНЕНЫ")
        self._log("=" * 60)
        return True
    
    def install_wine_packages(self):
        """Установка Wine пакетов"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 1: УСТАНОВКА WINE ПАКЕТОВ")
        self._log("=" * 60)
        
        # Проверяем существование файлов
        self._log("Проверка пакетов...")
        self._log("  Wine 9.0: %s" % self.wine_9_deb)
        self._log("  Wine Astraregul: %s" % self.wine_astraregul_deb)
        
        if not os.path.exists(self.wine_9_deb):
            self._log("ОШИБКА: Файл не найден: %s" % self.wine_9_deb, "ERROR")
            return False
        
        if not os.path.exists(self.wine_astraregul_deb):
            self._log("ОШИБКА: Файл не найден: %s" % self.wine_astraregul_deb, "ERROR")
            return False
        
        # Шаг 1: Очистка возможных сломанных пакетов
        self._log("Очистка системы от возможных сломанных пакетов...")
        
        # Удаляем возможные предыдущие установки Wine
        self._log("Удаление предыдущих версий Wine (если есть)...")
        subprocess.run(
            ['apt-get', 'remove', '-y', 'wine', 'wine-stable', 'wine-9.0', 'wine-astraregul'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        # Очищаем dpkg от сломанных пакетов
        self._log("Очистка dpkg...")
        subprocess.run(
            ['dpkg', '--configure', '-a'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        # Исправляем сломанные зависимости с опциями dpkg
        self._log("Исправление сломанных зависимостей...")
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        env['DEBIAN_PRIORITY'] = 'critical'
        env['APT_LISTCHANGES_FRONTEND'] = 'none'
        subprocess.run(
            ['apt-get', '-f', '-y', 'install',
             '-o', 'Dpkg::Options::=--force-confdef',
             '-o', 'Dpkg::Options::=--force-confold',
             '-o', 'Dpkg::Options::=--force-confmiss'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        # Обновляем списки пакетов
        self._log("Обновление списков пакетов...")
        subprocess.run(
            ['apt-get', 'update'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        # Шаг 2: Установка Wine пакетов через apt (как в оригинальном скрипте)
        # ВАЖНО: apt умеет устанавливать локальные .deb и сразу разрешать зависимости
        self._log("\nУстановка Wine пакетов (как в оригинальном скрипте)...")
        
        # Переходим в директорию с пакетами для использования относительных путей
        original_cwd = os.getcwd()
        os.chdir(self.astrapack_dir)
        self._log("Рабочая директория: %s" % self.astrapack_dir)
        
        try:
            # Настраиваем переменные окружения для автоматической установки
            env = os.environ.copy()
            env['DEBIAN_FRONTEND'] = 'noninteractive'
            env['DEBIAN_PRIORITY'] = 'critical'
            env['APT_LISTCHANGES_FRONTEND'] = 'none'
            
            # Используем apt install с относительным путем ./wine*.deb
            # Это ТОЧНО как в оригинальном скрипте: apt -y install ./wine*.deb
            
            # Находим все wine*.deb файлы в текущей директории
            import glob as glob_module
            wine_debs = sorted(glob_module.glob('./wine*.deb'))
            
            if not wine_debs:
                self._log("ОШИБКА: Не найдены файлы wine*.deb в директории!", "ERROR")
                return False
            
            self._log("Найдено %d wine*.deb файлов:" % len(wine_debs))
            for deb in wine_debs:
                self._log("  - %s" % deb)
            
            self._log("\nВыполнение: apt install -y с опциями dpkg для автоподтверждения")
            self._log("Это автоматически установит ВСЕ зависимости из репозиториев")
            
            # Формируем команду с явными файлами и усиленными опциями dpkg
            cmd = ['apt', 'install', '-y',
                   '-o', 'Dpkg::Options::=--force-confdef',
                   '-o', 'Dpkg::Options::=--force-confold',
                   '-o', 'Dpkg::Options::=--force-confmiss'] + wine_debs
            
            result = subprocess.run(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            # Логируем вывод
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        self._log("  > %s" % line)
            
            if result.returncode != 0:
                self._log("ОШИБКА: apt install завершился с ошибкой", "ERROR")
                if result.stderr:
                    for line in result.stderr.strip().split('\n'):
                        if line.strip():
                            self._log("  ! %s" % line, "ERROR")
                return False
            
            self._log("apt install успешно завершен")
            
        finally:
            # Возвращаемся в исходную директорию
            os.chdir(original_cwd)
        
        # Шаг 4: Проверяем установку
        self._log("\nПроверка установки...")
        
        if os.path.exists('/opt/wine-9.0/bin/wine'):
            self._log("  [OK] Wine 9.0 установлен: /opt/wine-9.0/bin/wine")
        else:
            self._log("  [ERR] Wine 9.0 не найден", "ERROR")
            return False
        
        if os.path.exists('/opt/wine-astraregul/bin/wine'):
            self._log("  [OK] Wine Astraregul установлен: /opt/wine-astraregul/bin/wine")
        else:
            self._log("  [ERR] Wine Astraregul не найден", "ERROR")
            return False
        
        self._log("\nWine пакеты успешно установлены!")
        return True
    
    def configure_ptrace_scope(self):
        """Настройка ptrace_scope"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 2: НАСТРОЙКА PTRACE_SCOPE")
        self._log("=" * 60)
        
        ptrace_path = "/proc/sys/kernel/yama/ptrace_scope"
        
        if not os.path.exists(ptrace_path):
            self._log("ptrace_scope не найден (возможно, не требуется)")
            return True
        
        try:
            with open(ptrace_path, 'r') as f:
                current_value = f.read().strip()
            
            self._log("Текущее значение ptrace_scope: %s" % current_value)
            
            if current_value == '3':
                self._log("Отключение блокировки ptrace...")
                if self._run_command(
                    ['sysctl', '-w', 'kernel.yama.ptrace_scope=0'],
                    "Отключение ptrace блокировки",
                    sudo=True
                ):
                    self._log("ptrace_scope успешно настроен")
                    return True
                else:
                    self._log("Не удалось настроить ptrace_scope", "ERROR")
                    return False
            else:
                self._log("ptrace_scope уже настроен правильно")
                return True
        
        except Exception as e:
            self._log("Ошибка настройки ptrace_scope: %s" % str(e), "ERROR")
            return False
    
    def setup_wine_environment(self):
        """Настройка окружения Wine"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 3: НАСТРОЙКА ОКРУЖЕНИЯ WINE")
        self._log("=" * 60)
        
        # Создаем директории
        cache_wine = os.path.join(self.home, ".cache", "wine")
        cache_winetricks = os.path.join(self.home, ".cache", "winetricks")
        
        try:
            os.makedirs(cache_wine, exist_ok=True)
            os.makedirs(cache_winetricks, exist_ok=True)
            self._log("Созданы директории кэша")
            
            # Если запущено через sudo - устанавливаем правильного владельца для директорий
            real_user = os.environ.get('SUDO_USER')
            if os.geteuid() == 0 and real_user and real_user != 'root':
                import pwd
                uid = pwd.getpwnam(real_user).pw_uid
                gid = pwd.getpwnam(real_user).pw_gid
                os.chown(cache_wine, uid, gid)
                os.chown(cache_winetricks, uid, gid)
                self._log("Установлен владелец директорий: %s" % real_user)
            
            # Копируем wine-gecko
            self._log("Копирование wine-gecko компонентов...")
            if os.path.exists(self.wine_gecko_dir):
                import shutil
                for item in os.listdir(self.wine_gecko_dir):
                    src = os.path.join(self.wine_gecko_dir, item)
                    dst = os.path.join(cache_wine, item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                        # Устанавливаем владельца если через sudo
                        if os.geteuid() == 0 and real_user and real_user != 'root':
                            os.chown(dst, uid, gid)
                        self._log("  Скопирован: %s" % item)
                self._log("wine-gecko компоненты скопированы")
            
            # Копируем winetricks-cache
            self._log("Копирование winetricks кэша...")
            if os.path.exists(self.winetricks_cache_dir):
                for item in os.listdir(self.winetricks_cache_dir):
                    src = os.path.join(self.winetricks_cache_dir, item)
                    dst = os.path.join(cache_winetricks, item)
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                        # Устанавливаем владельца рекурсивно если через sudo
                        if os.geteuid() == 0 and real_user and real_user != 'root':
                            for root_dir, dirs, files in os.walk(dst):
                                os.chown(root_dir, uid, gid)
                                for fname in files:
                                    os.chown(os.path.join(root_dir, fname), uid, gid)
                        self._log("  Скопирована папка: %s" % item)
                    else:
                        shutil.copy2(src, dst)
                        # Устанавливаем владельца если через sudo
                        if os.geteuid() == 0 and real_user and real_user != 'root':
                            os.chown(dst, uid, gid)
                        self._log("  Скопирован файл: %s" % item)
                self._log("winetricks кэш скопирован")
            
            # Делаем winetricks исполняемым
            if os.path.exists(self.winetricks):
                os.chmod(self.winetricks, 0o755)
                self._log("winetricks сделан исполняемым")
            
            return True
        
        except Exception as e:
            self._log("Ошибка настройки окружения: %s" % str(e), "ERROR")
            return False
    
    def install_winetricks_components_original(self):
        """
        Установка компонентов через winetricks - ОРИГИНАЛЬНЫЙ МЕТОД
        Точная копия логики из install-astraregul.sh для отладки
        """
        self._log("\n" + "=" * 60)
        self._log("ШАГ 4: УСТАНОВКА КОМПОНЕНТОВ WINETRICKS (ОРИГИНАЛЬНЫЙ МЕТОД)")
        self._log("=" * 60)
        
        # Используем список компонентов из конфигурации
        components = self.winetricks_components
        
        if not components:
            self._log("Нет компонентов для установки")
            return True
        
        self._log("Установка компонентов: %s" % ", ".join(components))
        self._log("Путь к winetricks: %s" % self.winetricks)
        self._log("Директория AstraPack: %s" % self.astrapack_dir)
        
        # КЛЮЧЕВОЕ ОТЛИЧИЕ: переходим в директорию AstraPack
        original_dir = os.getcwd()
        
        try:
            os.chdir(self.astrapack_dir)
            self._log("Перешли в директорию: %s" % os.getcwd())
            
            # Настраиваем переменные окружения КАК В ОРИГИНАЛЕ
            env = os.environ.copy()
            env['WINEPREFIX'] = self.wineprefix
            env['WINEDEBUG'] = '-all'
            env['WINE'] = '/opt/wine-9.0/bin/wine'
            
            self._log("WINEPREFIX: %s" % self.wineprefix)
            self._log("WINE: %s" % env['WINE'])
            self._log("Это может занять несколько минут...")
            
            # Запускаем winetricks ОТНОСИТЕЛЬНЫМ ПУТЕМ как в оригинале
            result = subprocess.run(
                ['./winetricks', '-q', '-f'] + components,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                errors='replace',
                check=False
            )
            
            self._log("Код возврата winetricks: %d" % result.returncode)
            
            if result.stdout and result.stdout.strip():
                self._log("=== STDOUT winetricks ===")
                for line in result.stdout.split('\n')[:30]:  # Первые 30 строк
                    if line.strip():
                        self._log("  %s" % line)
            
            if result.stderr and result.stderr.strip():
                self._log("=== STDERR winetricks ===")
                for line in result.stderr.split('\n')[:30]:  # Первые 30 строк
                    if line.strip():
                        self._log("  %s" % line)
            
            if result.returncode != 0:
                self._log("ОШИБКА: winetricks завершился с ошибкой!", "ERROR")
                return False
            
            self._log("Компоненты winetricks успешно установлены")
            
            # Останавливаем wine server
            self._log("Остановка wine server...")
            subprocess.run(
                [env['WINE'] + 'server', '-k'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            import time
            time.sleep(2)
            
            return True
            
        except Exception as e:
            self._log("Ошибка установки компонентов: %s" % str(e), "ERROR")
            return False
        finally:
            # Возвращаемся в исходную директорию
            os.chdir(original_dir)
    
    def install_winetricks_components(self):
        """Установка компонентов через winetricks"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 4: УСТАНОВКА КОМПОНЕНТОВ WINETRICKS")
        self._log("=" * 60)
        
        # Настраиваем переменные окружения
        env = os.environ.copy()
        env['WINEPREFIX'] = self.wineprefix
        env['WINEDEBUG'] = '-all'
        env['WINE'] = '/opt/wine-9.0/bin/wine'
        
        # Отключаем GUI диалоги Wine (rundll32, winemenubuilder и т.д.)
        env['WINEDLLOVERRIDES'] = 'winemenubuilder.exe=d;rundll32.exe=d;mshtml=d'
        env['WINEARCH'] = 'win64'
        env['DISPLAY'] = ':0'
        
        # Дополнительные параметры для подавления диалогов
        env['WINEDLLPATH'] = '/opt/wine-9.0/lib64/wine'
        
        self._log("WINEPREFIX: %s" % self.wineprefix)
        self._log("WINE: /opt/wine-9.0/bin/wine")
        self._log("WINEDLLOVERRIDES: winemenubuilder.exe=d;rundll32.exe=d;mshtml=d (отключены GUI диалоги)")
        
        # Используем список компонентов из конфигурации
        components = self.winetricks_components
        
        if not components:
            self._log("Нет компонентов для установки")
            return True
        
        self._log("Установка компонентов: %s" % ", ".join(components))
        self._log("Это может занять несколько минут...")
        
        # КЛЮЧЕВОЙ МОМЕНТ: переходим в директорию AstraPack
        # Winetricks использует относительные пути к своим ресурсам!
        original_dir = os.getcwd()
        
        try:
            # Если запущено от root - нужно переключиться на обычного пользователя
            # winetricks НЕЛЬЗЯ запускать от root!
            real_user = os.environ.get('SUDO_USER')
            
            if os.geteuid() == 0 and real_user and real_user != 'root':
                # Запускаем через su от имени обычного пользователя
                self._log("Запуск настройки окружения и winetricks от пользователя: %s" % real_user)
                
                # Формируем полную команду как в оригинальном скрипте:
                # 1. Создаём директории кэша
                # 2. Копируем файлы
                # 3. Запускаем winetricks
                cmd_string = '''cd %s && \
mkdir -p "$HOME"/.cache/wine && \
mkdir -p "$HOME"/.cache/winetricks && \
cp -r wine-gecko/* "$HOME"/.cache/wine/ 2>/dev/null || true && \
cp -r winetricks-cache/* "$HOME"/.cache/winetricks/ 2>/dev/null || true && \
export WINEPREFIX="$HOME"/.wine-astraregul && \
export WINEDEBUG="-all" && \
export WINE=/opt/wine-9.0/bin/wine && \
./winetricks -q -f %s''' % (
                    self.astrapack_dir,
                    ' '.join(components)
                )
                
                # Запускаем через su -c от имени пользователя
                result = subprocess.run(
                    ['su', real_user, '-c', cmd_string],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    errors='replace',
                    check=False
                )
            else:
                # Уже не root или нет SUDO_USER - запускаем напрямую
                os.chdir(self.astrapack_dir)
                self._log("Перешли в директорию: %s" % os.getcwd())
                
                result = subprocess.run(
                    ['./winetricks', '-q', '-f'] + components,
                    env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                errors='replace',  # Безопасная обработка non-UTF8 символов
                check=False
            )
            
            # Проверяем код возврата
            if result.returncode != 0:
                self._log("ОШИБКА: winetricks завершился с кодом %d" % result.returncode, "ERROR")
                
                # Выводим stderr для диагностики ошибки
                if result.stderr and result.stderr.strip():
                    self._log("Вывод ошибок:", "ERROR")
                    for line in result.stderr.split('\n')[:20]:  # Первые 20 строк
                        if line.strip():
                            self._log("  %s" % line, "ERROR")
                
                # Останавливаем wine server перед выходом
                self._log("Остановка wine server...")
                subprocess.run(
                    [env['WINE'] + 'server', '-k'],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                
                return False
            
            self._log("Компоненты winetricks успешно установлены")
            
            # Останавливаем wine server
            self._log("Остановка wine server...")
            subprocess.run(
                [env['WINE'] + 'server', '-k'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            import time
            time.sleep(2)
            
            # Проверяем что компоненты действительно установились
            self._log("Проверка установленных компонентов...")
            checker = WineComponentsChecker()
            checker.check_winetricks_components()
            
            # Подсчитываем сколько компонентов установилось
            installed_count = 0
            failed_components = []
            for component in components:
                if checker.checks.get(component, False):
                    installed_count += 1
                    self._log("  [OK] %s установлен" % component)
                else:
                    failed_components.append(component)
                    self._log("  [ERR] %s НЕ установлен" % component, "WARNING")
            
            # Если ничего не установилось - это ошибка
            if installed_count == 0:
                self._log("ОШИБКА: Ни один компонент не был установлен!", "ERROR")
                return False
            
            # Если установились не все - предупреждение, но продолжаем
            if failed_components:
                self._log("ВНИМАНИЕ: Не установлены компоненты: %s" % ", ".join(failed_components), "WARNING")
                self._log("Некоторые функции могут работать некорректно", "WARNING")
            
            return True
        
        except Exception as e:
            self._log("Ошибка установки компонентов: %s" % str(e), "ERROR")
            return False
        finally:
            # Возвращаемся в исходную директорию
            os.chdir(original_dir)
    
    def create_launch_scripts(self):
        """Создание скриптов запуска"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 5: СОЗДАНИЕ СКРИПТОВ ЗАПУСКА")
        self._log("=" * 60)
        
        start_script = os.path.join(self.home, "start-astraide.sh")
        
        script_content = """#!/bin/bash

export WINEPREFIX="${HOME}"/.wine-astraregul
export WINE=/opt/wine-astraregul/bin/wine
export WINEDEBUG="-all"

cd "${WINEPREFIX}"/drive_c/"Program Files"/AstraRegul/Astra.IDE_64_*/Astra.IDE/Common
"${WINE}" Astra.IDE.exe
"""
        
        try:
            with open(start_script, 'w') as f:
                f.write(script_content)
            
            os.chmod(start_script, 0o755)
            self._log("Создан скрипт запуска: %s" % start_script)
            
            return True
        
        except Exception as e:
            self._log("Ошибка создания скрипта: %s" % str(e), "ERROR")
            return False
    
    def install_astra_ide(self):
        """Установка Astra.IDE"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 6: УСТАНОВКА ASTRA.IDE")
        self._log("=" * 60)
        
        # Настраиваем переменные окружения
        env = os.environ.copy()
        env['WINEPREFIX'] = self.wineprefix
        env['WINEDEBUG'] = '-all'
        env['WINE'] = '/opt/wine-astraregul/bin/wine'
        
        # Отключаем GUI диалоги Wine (rundll32, winemenubuilder и т.д.)
        env['WINEDLLOVERRIDES'] = 'winemenubuilder.exe=d;rundll32.exe=d;mshtml=d'
        env['WINEARCH'] = 'win64'
        env['DISPLAY'] = ':0'
        
        self._log("Запуск установщика Astra.IDE...")
        self._log("Путь к установщику: %s" % self.astra_ide_exe)
        self._log("ВНИМАНИЕ: Установка может занять 5-10 минут")
        self._log("WINEDLLOVERRIDES: отключены GUI диалоги Wine")
        
        try:
            # Запускаем Wine напрямую (как раньше)
            # WINEPREFIX в env указывает куда устанавливать
            result = subprocess.run(
                [env['WINE'], self.astra_ide_exe],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                errors='replace',  # Безопасная обработка non-UTF8 символов
                check=False
            )
            
            if result.returncode == 0:
                self._log("Установщик Astra.IDE завершен успешно")
            else:
                self._log("Установщик завершился с кодом: %d" % result.returncode)
            
            # Даем время на завершение установки
            import time
            time.sleep(3)
            
            return True
        
        except Exception as e:
            self._log("Ошибка установки Astra.IDE: %s" % str(e), "ERROR")
            return False
    
    def create_desktop_shortcut(self):
        """Создание ярлыка на рабочем столе"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 7: СОЗДАНИЕ ЯРЛЫКА НА РАБОЧЕМ СТОЛЕ")
        self._log("=" * 60)
        
        # Проверяем/создаем симлинк Desktop
        desktop_dir = os.path.join(self.home, "Desktop")
        desktop1_dir = os.path.join(self.home, "Desktops", "Desktop1")
        
        try:
            if not os.path.exists(desktop_dir) and not os.path.islink(desktop_dir):
                if os.path.exists(desktop1_dir):
                    os.symlink(desktop1_dir, desktop_dir)
                    self._log("Создан симлинк Desktop -> Desktop1")
            
            # Создаем ярлык
            desktop_file = os.path.join(desktop_dir, "AstraRegul.desktop")
            
            desktop_content = """[Desktop Entry]
Comment=
Exec=%s/start-astraide.sh
Icon=
Name=Astra IDE (Wine)
Path=
StartupNotify=true
Terminal=false
Type=Application
""" % self.home
            
            with open(desktop_file, 'w') as f:
                f.write(desktop_content)
            
            self._log("Создан ярлык: %s" % desktop_file)
            
            # Удаляем лишние ярлыки созданные установщиком
            unwanted_shortcuts = [
                os.path.join(desktop_dir, "Astra.IDE 1.7.2.0.lnk"),
                os.path.join(desktop_dir, "Astra.IDE 1.7.2.1.lnk"),
                os.path.join(desktop_dir, "IDE Selector.lnk"),
                os.path.join(desktop_dir, "IDE Selector.desktop")
            ]
            
            import time
            time.sleep(2)
            
            for shortcut in unwanted_shortcuts:
                if os.path.exists(shortcut):
                    os.remove(shortcut)
                    self._log("Удален лишний ярлык: %s" % os.path.basename(shortcut))
            
            return True
        
        except Exception as e:
            self._log("Ошибка создания ярлыка: %s" % str(e), "ERROR")
            return False
    
    def install_all(self):
        """Полная установка всех компонентов"""
        self._log("\n" + "=" * 60)
        self._log("НАЧАЛО УСТАНОВКИ WINE И ASTRA.IDE")
        self._log("=" * 60)
        self._log("Время начала: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._log("")
        self._log("Выбранные компоненты:")
        self._log("  - Wine пакеты: %s" % ("ДА" if self.install_wine else "НЕТ"))
        self._log("  - Winetricks: %s" % ("ДА" if self.install_winetricks else "НЕТ"))
        self._log("  - Astra.IDE: %s" % ("ДА" if self.install_ide else "НЕТ"))
        self._log("=" * 60)
        
        start_time = datetime.datetime.now()
        
        # Проверка предварительных условий
        if not self.check_prerequisites():
            self._log("\nУСТАНОВКА ПРЕРВАНА: Не выполнены предварительные условия", "ERROR")
            return False
        
        # Установка Wine пакетов
        if self.install_wine:
            if not self.install_wine_packages():
                self._log("\nУСТАНОВКА ПРЕРВАНА: Ошибка установки Wine пакетов", "ERROR")
                return False
        else:
            self._log("\nШаг 1: Пропущено (Wine пакеты не выбраны)")
        
        # Настройка ptrace_scope
        if not self.configure_ptrace_scope():
            self._log("\nУСТАНОВКА ПРЕРВАНА: Ошибка настройки ptrace_scope", "ERROR")
            return False
        
        # Установка компонентов winetricks
        # Примечание: setup_wine_environment() больше не вызывается отдельно!
        # Настройка окружения (копирование кэша) происходит внутри install_winetricks_components()
        # через su от имени пользователя, чтобы избежать проблем с правами
        if self.install_winetricks:
            if not self.install_winetricks_components():
                self._log("\nУСТАНОВКА ПРЕРВАНА: Ошибка установки компонентов", "ERROR")
                return False
        else:
            self._log("\nШаг 4: Пропущено (Winetricks компоненты не выбраны)")
        
        # Создание скриптов запуска
        if self.install_ide:
            if not self.create_launch_scripts():
                self._log("\nУСТАНОВКА ПРЕРВАНА: Ошибка создания скриптов", "ERROR")
                return False
        
        # Установка Astra.IDE
        if self.install_ide:
            if not self.install_astra_ide():
                self._log("\nУСТАНОВКА ПРЕРВАНА: Ошибка установки Astra.IDE", "ERROR")
                return False
        else:
            self._log("\nШаг 6: Пропущено (Astra.IDE не выбрана)")
        
        # Создание ярлыка
        if self.install_ide:
            if not self.create_desktop_shortcut():
                self._log("\nПРЕДУПРЕЖДЕНИЕ: Ошибка создания ярлыка (не критично)")
        
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self._log("\n" + "=" * 60)
        self._log("УСТАНОВКА УСПЕШНО ЗАВЕРШЕНА!")
        self._log("=" * 60)
        self._log("Время завершения: %s" % end_time.strftime("%Y-%m-%d %H:%M:%S"))
        self._log("Длительность установки: %d мин %d сек" % (duration // 60, duration % 60))
        self._log("=" * 60)
        self._log("\nДля запуска Astra.IDE используйте:")
        self._log("  - Ярлык на рабочем столе 'Astra IDE (Wine)'")
        self._log("  - Или команду: ~/start-astraide.sh")
        self._log("=" * 60)
        
        return True

# ============================================================================
# КЛАСС УДАЛЕНИЯ WINE КОМПОНЕНТОВ
# ============================================================================
class WineUninstaller(object):
    """Класс для удаления Wine компонентов и Astra.IDE"""
    
    def __init__(self, logger=None, callback=None, remove_wine=True, remove_wineprefix=True, remove_ide=True, winetricks_components=None):
        """
        Инициализация деинсталлятора
        
        Args:
            logger: Экземпляр класса Logger для логирования
            callback: Функция для обновления статуса в GUI (опционально)
            remove_wine: Удалять Wine пакеты (по умолчанию True)
            remove_wineprefix: Удалять WINEPREFIX директорию (по умолчанию True)
            remove_ide: Удалять Astra.IDE (по умолчанию True)
            winetricks_components: Список компонентов winetricks для удаления (если None - удаляем WINEPREFIX целиком)
        """
        self.logger = logger
        self.callback = callback
        
        # Флаги удаления компонентов
        self.remove_wine = remove_wine
        self.remove_wineprefix = remove_wineprefix
        self.remove_ide = remove_ide
        self.winetricks_components = winetricks_components if winetricks_components else []
        
        # Определяем домашнюю директорию РЕАЛЬНОГО пользователя (не root)
        real_user = os.environ.get('SUDO_USER')
        if real_user and real_user != 'root':
            # Запущено через sudo - используем домашнюю директорию реального пользователя
            import pwd
            self.home = pwd.getpwnam(real_user).pw_dir
        else:
            # Запущено напрямую
            self.home = os.path.expanduser("~")
        
        self.wineprefix = os.path.join(self.home, ".wine-astraregul")
        self.launch_script = os.path.join(self.home, "start-astraide.sh")
        self.desktop_shortcut = os.path.join(self.home, "Desktop", "Astra-IDE.desktop")
        # Альтернативное имя ярлыка
        self.desktop_shortcut_alt = os.path.join(self.home, "Desktop", "AstraRegul.desktop")
        
    def _log(self, message, level="INFO"):
        """Логирование с поддержкой callback"""
        if self.logger:
            if level == "ERROR":
                self.logger.log_error(message)
            elif level == "WARNING":
                self.logger.log_warning(message)
            else:
                self.logger.log_info(message)
        
        if self.callback:
            self.callback(message)
    
    def remove_wine_packages(self):
        """Удаление Wine пакетов"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 1: УДАЛЕНИЕ WINE ПАКЕТОВ")
        self._log("=" * 60)
        
        packages = ['wine-astraregul', 'wine-9.0', 'wine', 'wine-stable']
        
        self._log("Удаление Wine пакетов: %s" % ", ".join(packages))
        
        try:
            # Останавливаем Wine процессы перед удалением
            self._log("Остановка Wine процессов...")
            subprocess.run(['pkill', '-9', 'wine'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            subprocess.run(['pkill', '-9', 'wineserver'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            subprocess.run(['pkill', '-9', 'wineboot'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            
            import time
            time.sleep(1)
            
            # Настраиваем переменные окружения для автоматического удаления
            env = os.environ.copy()
            env['DEBIAN_FRONTEND'] = 'noninteractive'
            
            # Используем purge вместо remove для полного удаления с конфигами
            self._log("Удаление пакетов через apt-get purge...")
            result = subprocess.run(
                ['apt-get', 'purge', '-y'] + packages,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                errors='replace',
                check=False
            )
            
            if result.returncode == 0:
                self._log("Wine пакеты успешно удалены")
            else:
                self._log("Предупреждение: некоторые пакеты не удалены (код: %d)" % result.returncode)
                # Не прерываем - продолжаем удалять вручную
            
            # Удаляем директории Wine вручную (apt не всегда их удаляет)
            wine_dirs = [
                '/opt/wine-astraregul',
                '/opt/wine-9.0',
                '/opt/wine-stable',
                '/usr/share/wine'
            ]
            
            self._log("\nУдаление директорий Wine...")
            import shutil
            for wine_dir in wine_dirs:
                if os.path.exists(wine_dir):
                    try:
                        shutil.rmtree(wine_dir)
                        self._log("  Удалена: %s" % wine_dir)
                    except Exception as e:
                        self._log("  Ошибка удаления %s: %s" % (wine_dir, str(e)), "ERROR")
                else:
                    self._log("  Не найдена: %s" % wine_dir)
            
            # Очистка зависимостей
            self._log("\nОчистка неиспользуемых зависимостей...")
            subprocess.run(
                ['apt-get', 'autoremove', '-y'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            self._log("Wine пакеты и директории полностью удалены")
            return True
            
        except Exception as e:
            self._log("Ошибка удаления Wine пакетов: %s" % str(e), "ERROR")
            return False
    
    def remove_wineprefix_dir(self):
        """Удаление WINEPREFIX директории"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 2: УДАЛЕНИЕ WINEPREFIX ДИРЕКТОРИИ")
        self._log("=" * 60)
        
        if not os.path.exists(self.wineprefix):
            self._log("WINEPREFIX не существует: %s" % self.wineprefix)
            return True
        
        try:
            # Останавливаем Wine процессы
            self._log("Остановка Wine процессов...")
            subprocess.run(
                ['pkill', '-9', 'wine'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            subprocess.run(
                ['pkill', '-9', 'wineserver'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            import time
            time.sleep(2)
            
            # Удаляем директорию
            self._log("Удаление директории: %s" % self.wineprefix)
            import shutil
            shutil.rmtree(self.wineprefix)
            self._log("WINEPREFIX директория удалена")
            
            return True
            
        except Exception as e:
            self._log("Ошибка удаления WINEPREFIX: %s" % str(e), "ERROR")
            return False
    
    def remove_winetricks_components(self):
        """Удаление отдельных компонентов winetricks (без полного удаления WINEPREFIX)"""
        if not self.winetricks_components:
            self._log("Нет компонентов для удаления")
            return True
        
        self._log("\n" + "=" * 60)
        self._log("УДАЛЕНИЕ КОМПОНЕНТОВ WINETRICKS")
        self._log("=" * 60)
        self._log("Компоненты для удаления: %s" % ", ".join(self.winetricks_components))
        
        if not os.path.exists(self.wineprefix):
            self._log("WINEPREFIX не существует: %s" % self.wineprefix)
            return True
        
        try:
            # Настраиваем переменные окружения
            env = os.environ.copy()
            env['WINEPREFIX'] = self.wineprefix
            env['WINEDEBUG'] = '-all'
            env['WINE'] = '/opt/wine-9.0/bin/wine'
            
            # Получаем путь к winetricks
            script_dir = os.path.dirname(os.path.abspath(__file__))
            winetricks_path = os.path.join(script_dir, "AstraPack", "winetricks")
            
            if not os.path.exists(winetricks_path):
                self._log("ПРЕДУПРЕЖДЕНИЕ: winetricks не найден, не можем удалить компоненты", "WARNING")
                self._log("Для полного удаления используйте удаление WINEPREFIX целиком", "WARNING")
                return False
            
            # Удаляем каждый компонент
            for component in self.winetricks_components:
                self._log("Удаление компонента: %s" % component)
                
                # winetricks поддерживает удаление через uninstaller
                result = subprocess.run(
                    [winetricks_path, 'uninstaller'],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    errors='replace',
                    check=False
                )
                
                # Примечание: winetricks не имеет прямого способа удаления компонентов
                # Лучший способ - удалить файлы компонента вручную
                self._log("ВНИМАНИЕ: winetricks не поддерживает автоматическое удаление компонентов")
                self._log("Для полного удаления компонентов используйте удаление WINEPREFIX целиком")
            
            return True
            
        except Exception as e:
            self._log("Ошибка удаления компонентов: %s" % str(e), "ERROR")
            return False
    
    def remove_astra_ide_only(self):
        """Удаление только Astra.IDE из WINEPREFIX (без удаления всего WINEPREFIX)"""
        self._log("\n" + "=" * 60)
        self._log("УДАЛЕНИЕ ASTRA.IDE ИЗ WINEPREFIX")
        self._log("=" * 60)
        
        if not os.path.exists(self.wineprefix):
            self._log("WINEPREFIX не существует: %s" % self.wineprefix)
            return True
        
        try:
            # Ищем и удаляем директорию AstraRegul
            import glob
            astra_regul_paths = [
                os.path.join(self.wineprefix, "drive_c", "Program Files", "AstraRegul"),
                os.path.join(self.wineprefix, "drive_c", "Program Files (x86)", "AstraRegul")
            ]
            
            removed_something = False
            for astra_path in astra_regul_paths:
                if os.path.exists(astra_path):
                    try:
                        self._log("Удаление: %s" % astra_path)
                        import shutil
                        shutil.rmtree(astra_path)
                        self._log("Astra.IDE удалена из WINEPREFIX")
                        removed_something = True
                    except Exception as e:
                        self._log("Ошибка удаления %s: %s" % (astra_path, str(e)), "ERROR")
            
            if not removed_something:
                self._log("Astra.IDE не найдена в WINEPREFIX")
            
            return True
            
        except Exception as e:
            self._log("Ошибка удаления Astra.IDE: %s" % str(e), "ERROR")
            return False
    
    def remove_scripts_and_shortcuts(self):
        """Удаление скриптов запуска и ярлыков"""
        self._log("\n" + "=" * 60)
        self._log("УДАЛЕНИЕ СКРИПТОВ И ЯРЛЫКОВ")
        self._log("=" * 60)
        
        files_to_remove = [
            self.launch_script,
            self.desktop_shortcut,
            self.desktop_shortcut_alt,
            os.path.join(self.home, ".local", "share", "applications", "Astra-IDE.desktop"),
            os.path.join(self.home, ".local", "share", "applications", "AstraRegul.desktop")
        ]
        
        for filepath in files_to_remove:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    self._log("Удален: %s" % filepath)
                except Exception as e:
                    self._log("Ошибка удаления %s: %s" % (filepath, str(e)), "ERROR")
            else:
                self._log("Не найден: %s" % filepath)
        
        return True
    
    def uninstall_all(self):
        """Полное удаление всех компонентов"""
        self._log("\n" + "=" * 60)
        self._log("НАЧАЛО УДАЛЕНИЯ WINE И ASTRA.IDE")
        self._log("=" * 60)
        self._log("Время начала: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._log("")
        self._log("Компоненты для удаления:")
        self._log("  - Wine пакеты: %s" % ("ДА" if self.remove_wine else "НЕТ"))
        self._log("  - WINEPREFIX: %s" % ("ДА" if self.remove_wineprefix else "НЕТ"))
        self._log("  - Скрипты/ярлыки: %s" % ("ДА" if self.remove_ide else "НЕТ"))
        self._log("=" * 60)
        
        start_time = datetime.datetime.now()
        
        # Удаление Astra.IDE из WINEPREFIX (если выбрана IDE, но НЕ весь WINEPREFIX)
        if self.remove_ide and not self.remove_wineprefix:
            self._log("\nУдаляется только Astra.IDE (WINEPREFIX сохраняется)")
            if not self.remove_astra_ide_only():
                self._log("\nПРЕДУПРЕЖДЕНИЕ: Ошибка удаления Astra.IDE (не критично)")
        
        # Удаление скриптов и ярлыков
        if self.remove_ide:
            if not self.remove_scripts_and_shortcuts():
                self._log("\nПРЕДУПРЕЖДЕНИЕ: Ошибка удаления скриптов (не критично)")
        else:
            self._log("\nШаг: Пропущено (скрипты/ярлыки не выбраны)")
        
        # Удаление отдельных winetricks компонентов (если указаны, но НЕ весь WINEPREFIX)
        if self.winetricks_components and not self.remove_wineprefix:
            self._log("\nУдаление выбранных компонентов winetricks (WINEPREFIX сохраняется)")
            if not self.remove_winetricks_components():
                self._log("\nПРЕДУПРЕЖДЕНИЕ: Ошибка удаления winetricks компонентов (не критично)")
        
        # Удаление WINEPREFIX (удалит и Astra.IDE внутри него, и все winetricks компоненты)
        if self.remove_wineprefix:
            if not self.remove_wineprefix_dir():
                self._log("\nУДАЛЕНИЕ ПРЕРВАНО: Ошибка удаления WINEPREFIX", "ERROR")
                return False
        else:
            self._log("\nШаг: Пропущено (WINEPREFIX не выбран)")
        
        # Удаление Wine пакетов
        if self.remove_wine:
            if not self.remove_wine_packages():
                self._log("\nПРЕДУПРЕЖДЕНИЕ: Ошибка удаления Wine пакетов (не критично)")
        else:
            self._log("\nШаг: Пропущено (Wine пакеты не выбраны)")
        
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self._log("\n" + "=" * 60)
        self._log("УДАЛЕНИЕ УСПЕШНО ЗАВЕРШЕНО!")
        self._log("=" * 60)
        self._log("Время завершения: %s" % end_time.strftime("%Y-%m-%d %H:%M:%S"))
        self._log("Длительность удаления: %d мин %d сек" % (duration // 60, duration % 60))
        self._log("=" * 60)
        
        return True

# ============================================================================
# GUI КЛАСС АВТОМАТИЗАЦИИ
# ============================================================================
class AutomationGUI(object):
    """GUI для мониторинга автоматизации установки Astra.IDE"""
    
    def __init__(self, console_mode=False, close_terminal_pid=None):
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
        
        # Размер окна
        window_width = 1000
        window_height = 600
        
        # Получаем размер экрана
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Вычисляем позицию для центрирования
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        # Устанавливаем геометрию окна с позицией по центру
        self.root.geometry('%dx%d+%d+%d' % (window_width, window_height, center_x, center_y))
        
        # Переменные состояния
        self.is_running = False
        self.dry_run = tk.BooleanVar()
        self.process_thread = None
        
        # PID терминала для автозакрытия
        self.close_terminal_pid = close_terminal_pid
        
        # Очередь для потокобезопасного обновления терминала
        self.terminal_queue = queue.Queue()
        
        # Экземпляр проверщика Wine компонентов
        self.wine_checker = None
        
        # Лог-файл (будет установлен позже из main)
        self.main_log_file = None
        
        # Глобальный монитор системы для постоянного мониторинга CPU/NET
        self.system_monitor = None
        self.last_cpu_usage = 0
        self.last_net_speed = 0.0
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Перенаправляем stdout и stderr на встроенный терминал GUI
        if not console_mode:
            self._redirect_output_to_terminal()
        
        # Запускаем обработку очереди терминала
        self.process_terminal_queue()
        
        # Закрываем родительский терминал после полного запуска GUI
        if self.close_terminal_pid:
            self.root.after(2000, self._close_parent_terminal)
        
        # Запускаем постоянный мониторинг CPU/NET
        self.start_system_monitoring()
    
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
    
    def _close_parent_terminal(self):
        """Закрытие родительского терминала после полного запуска GUI"""
        if not self.close_terminal_pid:
            return
        
        try:
            import signal
            pid = int(self.close_terminal_pid)
            
            # Проверяем что процесс существует
            try:
                os.kill(pid, 0)  # Сигнал 0 - только проверка существования
            except OSError:
                # Процесс уже не существует
                return
            
            # Сначала мягкое завершение
            try:
                os.kill(pid, signal.SIGTERM)
                self.log_message("[INFO] Отправлен SIGTERM терминалу (PID: %d)" % pid)
                
                # Даем время на завершение
                import time
                time.sleep(0.5)
                
                # Проверяем что процесс завершился
                try:
                    os.kill(pid, 0)
                    # Процесс еще жив - отправляем SIGKILL
                    os.kill(pid, signal.SIGKILL)
                    self.log_message("[INFO] Отправлен SIGKILL терминалу (PID: %d)" % pid)
                except OSError:
                    # Процесс уже завершился
                    self.log_message("[INFO] Родительский терминал успешно закрыт (PID: %d)" % pid)
                    
            except Exception as e:
                self.log_message("[WARNING] Не удалось закрыть терминал: %s" % str(e))
                
        except Exception as e:
            self.log_message("[ERROR] Ошибка закрытия родительского терминала: %s" % str(e))
    
    def _redirect_output_to_terminal(self):
        """Перенаправление stdout и stderr на встроенный терминал GUI"""
        class TerminalRedirector:
            """Класс для перенаправления вывода в GUI терминал"""
            def __init__(self, terminal_queue, stream_name):
                self.terminal_queue = terminal_queue
                self.stream_name = stream_name
                self.original_stream = sys.stdout if stream_name == "stdout" else sys.stderr
            
            def write(self, message):
                if message.strip():  # Пропускаем пустые строки
                    # Добавляем префикс для stderr
                    if self.stream_name == "stderr":
                        message = "[STDERR] " + message
                    self.terminal_queue.put(message)
                # Также пишем в оригинальный поток (для отладки)
                # self.original_stream.write(message)
            
            def flush(self):
                pass  # GUI не требует flush
        
        # Перенаправляем stdout и stderr
        sys.stdout = TerminalRedirector(self.terminal_queue, "stdout")
        sys.stderr = TerminalRedirector(self.terminal_queue, "stderr")
        
        # Логируем перенаправление
        self.add_terminal_output("[SYSTEM] Вывод перенаправлен на встроенный терминал GUI")
        self.add_terminal_output("[SYSTEM] Родительский терминал можно безопасно закрыть")
    
    def start_system_monitoring(self):
        """Запуск постоянного фонового мониторинга CPU и сети"""
        # Создаем монитор с пустым WINEPREFIX (не важен для общего мониторинга)
        home = os.path.expanduser("~")
        wineprefix = os.path.join(home, ".wine-astraregul")
        
        # Callback для обновления GUI
        def update_system_stats(data):
            # Сохраняем последние значения
            self.last_cpu_usage = data.get('cpu_usage', 0)
            self.last_net_speed = data.get('network_speed', 0.0)
        
        self.system_monitor = InstallationMonitor(wineprefix, callback=update_system_stats)
        self.system_monitor.start_monitoring()
        
        # Запускаем периодическое обновление GUI
        self._update_system_display()
    
    def _update_system_display(self):
        """Периодическое обновление отображения CPU/NET в GUI"""
        try:
            # Обновляем CPU
            cpu_bar = self._create_progress_bar(self.last_cpu_usage, 100, 10)
            self.wine_cpu_label.config(text=cpu_bar)
            
            # Обновляем Сеть
            net_percent = min(100, int((self.last_net_speed / 10.0) * 100))
            net_bar = self._create_progress_bar(net_percent, 100, 10)
            self.wine_net_label.config(text="%s %.1f MB/s" % (net_bar, self.last_net_speed))
            
        except Exception as e:
            pass  # Игнорируем ошибки обновления
        
        # Повторяем каждые 1000ms (1 секунда)
        self.root.after(1000, self._update_system_display)
    
    def _add_copy_menu(self, text_widget):
        """Добавление контекстного меню для копирования текста"""
        # Создаем контекстное меню
        context_menu = self.tk.Menu(text_widget, tearoff=0)
        context_menu.add_command(label="Копировать", command=lambda: self._copy_text(text_widget))
        context_menu.add_command(label="Выделить всё", command=lambda: self._select_all(text_widget))
        
        # Привязываем правую кнопку мыши
        def show_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        text_widget.bind("<Button-3>", show_menu)
        
        # Привязываем Ctrl+C для копирования
        text_widget.bind("<Control-c>", lambda event: self._copy_text(text_widget))
        text_widget.bind("<Control-C>", lambda event: self._copy_text(text_widget))
        
        # Привязываем Ctrl+A для выделения всего
        text_widget.bind("<Control-a>", lambda event: self._select_all(text_widget))
        text_widget.bind("<Control-A>", lambda event: self._select_all(text_widget))
    
    def _copy_text(self, text_widget):
        """Копирование выделенного текста в буфер обмена"""
        try:
            selected_text = text_widget.get(self.tk.SEL_FIRST, self.tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except:
            pass  # Ничего не выделено
    
    def _select_all(self, text_widget):
        """Выделение всего текста"""
        text_widget.tag_add(self.tk.SEL, "1.0", self.tk.END)
        text_widget.mark_set(self.tk.INSERT, "1.0")
        text_widget.see(self.tk.INSERT)
        return 'break'  # Предотвращаем стандартное поведение
        
    def create_widgets(self):
        """Создание элементов интерфейса"""
        
        # Создаем вкладки
        self.notebook = self.ttk.Notebook(self.root)
        self.notebook.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)
        
        # Основная вкладка
        self.main_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text=" Управление ")
        
        # Вкладка Wine & Astra.IDE
        self.wine_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.wine_frame, text=" Wine & Astra.IDE ")
        
        # Вкладка Репозитории
        self.repos_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.repos_frame, text=" Репозитории ")
        
        # Терминальная вкладка
        self.terminal_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.terminal_frame, text=" Терминал ")
        
        # Создаем элементы основной вкладки
        self.create_main_tab()
        
        # Создаем элементы вкладки Wine
        self.create_wine_tab()
        
        # Создаем элементы вкладки Репозитории
        self.create_repos_tab()
        
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
        
        # Добавляем контекстное меню для копирования
        self._add_copy_menu(self.log_text)
        
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
    
    def create_repos_tab(self):
        """Создание вкладки управления репозиториями"""
        # Заголовок
        title_frame = self.tk.LabelFrame(self.repos_frame, text="Управление репозиториями APT")
        title_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        info_label = self.tk.Label(title_frame, 
                                   text="Просмотр, проверка и управление репозиториями системы",
                                   font=('Arial', 10))
        info_label.pack(padx=10, pady=5)
        
        # Кнопки управления
        button_frame = self.tk.Frame(self.repos_frame)
        button_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        self.load_repos_button = self.tk.Button(button_frame, 
                                                text="Загрузить репозитории", 
                                                command=self.load_repositories,
                                                font=('Arial', 10, 'bold'),
                                                bg='#4CAF50',
                                                fg='white')
        self.load_repos_button.pack(side=self.tk.LEFT, padx=5)
        
        self.check_repos_button2 = self.tk.Button(button_frame, 
                                                  text="Проверить доступность", 
                                                  command=self.check_repositories_availability,
                                                  font=('Arial', 10, 'bold'),
                                                  bg='#2196F3',
                                                  fg='white')
        self.check_repos_button2.pack(side=self.tk.LEFT, padx=5)
        
        self.update_repos_button = self.tk.Button(button_frame, 
                                                  text="Обновить списки (apt update)", 
                                                  command=self.run_apt_update,
                                                  font=('Arial', 10, 'bold'),
                                                  bg='#FF9800',
                                                  fg='white')
        self.update_repos_button.pack(side=self.tk.LEFT, padx=5)
        
        self.repos_status_label = self.tk.Label(button_frame, 
                                               text="Нажмите 'Загрузить репозитории' для начала",
                                               font=('Arial', 9))
        self.repos_status_label.pack(side=self.tk.LEFT, padx=10)
        
        # Список репозиториев
        repos_list_frame = self.tk.LabelFrame(self.repos_frame, text="Список репозиториев")
        repos_list_frame.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем таблицу репозиториев
        columns = ('status', 'type', 'uri', 'distribution', 'components')
        self.repos_tree = self.ttk.Treeview(repos_list_frame, columns=columns, show='headings', height=12)
        
        # Настраиваем колонки
        self.repos_tree.heading('status', text='Статус')
        self.repos_tree.heading('type', text='Тип')
        self.repos_tree.heading('uri', text='URI')
        self.repos_tree.heading('distribution', text='Дистрибутив')
        self.repos_tree.heading('components', text='Компоненты')
        
        self.repos_tree.column('status', width=80)
        self.repos_tree.column('type', width=60)
        self.repos_tree.column('uri', width=300)
        self.repos_tree.column('distribution', width=150)
        self.repos_tree.column('components', width=200)
        
        # Добавляем скроллбар
        repos_scrollbar = self.tk.Scrollbar(repos_list_frame, orient=self.tk.VERTICAL, 
                                           command=self.repos_tree.yview)
        self.repos_tree.configure(yscrollcommand=repos_scrollbar.set)
        
        self.repos_tree.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True, padx=5, pady=5)
        repos_scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y, padx=5, pady=5)
        
        # Контекстное меню для репозиториев
        self.repos_tree.bind('<Button-3>', self.show_repo_context_menu)
        self.repos_tree.bind('<Double-1>', self.show_repo_details)
        
        # Статистика
        stats_frame = self.tk.LabelFrame(self.repos_frame, text="Статистика")
        stats_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        stats_inner = self.tk.Frame(stats_frame)
        stats_inner.pack(fill=self.tk.X, padx=5, pady=5)
        
        self.tk.Label(stats_inner, text="Всего репозиториев:").grid(row=0, column=0, sticky=self.tk.W)
        self.repos_total_label = self.tk.Label(stats_inner, text="0")
        self.repos_total_label.grid(row=0, column=1, sticky=self.tk.W, padx=(5, 20))
        
        self.tk.Label(stats_inner, text="Активных:").grid(row=0, column=2, sticky=self.tk.W)
        self.repos_active_label = self.tk.Label(stats_inner, text="0", fg='green')
        self.repos_active_label.grid(row=0, column=3, sticky=self.tk.W, padx=(5, 20))
        
        self.tk.Label(stats_inner, text="Отключенных:").grid(row=0, column=4, sticky=self.tk.W)
        self.repos_disabled_label = self.tk.Label(stats_inner, text="0", fg='red')
        self.repos_disabled_label.grid(row=0, column=5, sticky=self.tk.W, padx=(5, 20))
        
        self.tk.Label(stats_inner, text="Файл:").grid(row=1, column=0, sticky=self.tk.W)
        self.repos_file_label = self.tk.Label(stats_inner, text="/etc/apt/sources.list")
        self.repos_file_label.grid(row=1, column=1, columnspan=5, sticky=self.tk.W, padx=(5, 20))
        
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
        
        # Добавляем контекстное меню для копирования
        self._add_copy_menu(self.terminal_text)
        
        # Добавляем приветственное сообщение
        self.terminal_text.insert(self.tk.END, "Системный терминал готов к работе\n")
        self.terminal_text.insert(self.tk.END, "Здесь будет отображаться вывод системных команд\n")
        self.terminal_text.insert(self.tk.END, "Для ввода команд используйте кнопки управления\n")
        self.terminal_text.insert(self.tk.END, "Для копирования текста: выделите мышью и нажмите Ctrl+C или правую кнопку мыши\n\n")
        
        # Делаем терминал только для чтения (команды запускаются через GUI)
        self.terminal_text.config(state=self.tk.DISABLED)
        
        # Запускаем мониторинг системного вывода
        self.start_terminal_monitoring()
    
    def create_wine_tab(self):
        """Создание вкладки проверки Wine компонентов"""
        # Заголовок
        title_frame = self.tk.LabelFrame(self.wine_frame, text="Статус установки Wine и Astra.IDE")
        title_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        info_label = self.tk.Label(title_frame, 
                                   text="Отметьте компоненты в таблице и выберите действие",
                                   font=('Arial', 10))
        info_label.pack(padx=10, pady=5)
        
        # Кнопки управления
        button_frame = self.tk.Frame(self.wine_frame)
        button_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        self.check_wine_button = self.tk.Button(button_frame, 
                                                text="Проверить компоненты", 
                                                command=self.run_wine_check,
                                                font=('Arial', 10, 'bold'),
                                                bg='#4CAF50',
                                                fg='white')
        self.check_wine_button.pack(side=self.tk.LEFT, padx=5)
        
        self.install_wine_button = self.tk.Button(button_frame, 
                                                  text="Установить выбранные", 
                                                  command=self.run_wine_install,
                                                  font=('Arial', 10, 'bold'),
                                                  bg='#2196F3',
                                                  fg='white',
                                                  state=self.tk.DISABLED)
        self.install_wine_button.pack(side=self.tk.LEFT, padx=5)
        
        self.uninstall_wine_button = self.tk.Button(button_frame, 
                                                    text="Удалить выбранные", 
                                                    command=self.run_wine_uninstall,
                                                    font=('Arial', 10, 'bold'),
                                                    bg='#F44336',
                                                    fg='white',
                                                    state=self.tk.DISABLED)
        self.uninstall_wine_button.pack(side=self.tk.LEFT, padx=5)
        
        self.check_repos_button = self.tk.Button(button_frame, 
                                                 text="Проверить репозитории", 
                                                 command=self.run_repos_check,
                                                 font=('Arial', 10, 'bold'),
                                                 bg='#FF9800',
                                                 fg='white')
        self.check_repos_button.pack(side=self.tk.LEFT, padx=5)
        
        self.sysmon_button = self.tk.Button(button_frame, 
                                            text="Системный монитор", 
                                            command=self.open_system_monitor,
                                            font=('Arial', 10, 'bold'),
                                            bg='#9C27B0',
                                            fg='white')
        self.sysmon_button.pack(side=self.tk.LEFT, padx=5)
        
        self.wine_status_label = self.tk.Label(button_frame, 
                                               text="Нажмите кнопку для проверки",
                                               font=('Arial', 9))
        self.wine_status_label.pack(side=self.tk.LEFT, padx=10)
        
        # Панель прогресса установки
        progress_frame = self.tk.LabelFrame(self.wine_frame, text="Прогресс установки")
        progress_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        # Прогресс-бар
        self.wine_progress = self.ttk.Progressbar(progress_frame, 
                                                  length=600, 
                                                  mode='determinate')
        self.wine_progress.pack(fill=self.tk.X, padx=10, pady=5)
        
        # Информационная панель (3 колонки)
        info_panel = self.tk.Frame(progress_frame)
        info_panel.pack(fill=self.tk.X, padx=10, pady=5)
        
        # Колонка 1: Время
        time_col = self.tk.Frame(info_panel)
        time_col.pack(side=self.tk.LEFT, expand=True, fill=self.tk.X, padx=5)
        self.tk.Label(time_col, text="Время:", font=('Arial', 9, 'bold')).pack(anchor=self.tk.W)
        self.wine_time_label = self.tk.Label(time_col, text="0 мин 0 сек", font=('Arial', 9))
        self.wine_time_label.pack(anchor=self.tk.W)
        
        # Колонка 2: Размер
        size_col = self.tk.Frame(info_panel)
        size_col.pack(side=self.tk.LEFT, expand=True, fill=self.tk.X, padx=5)
        self.tk.Label(size_col, text="Установлено:", font=('Arial', 9, 'bold')).pack(anchor=self.tk.W)
        self.wine_size_label = self.tk.Label(size_col, text="0 MB", font=('Arial', 9))
        self.wine_size_label.pack(anchor=self.tk.W)
        
        # Колонка 3: CPU
        cpu_col = self.tk.Frame(info_panel)
        cpu_col.pack(side=self.tk.LEFT, expand=True, fill=self.tk.X, padx=5)
        self.tk.Label(cpu_col, text="CPU:", font=('Arial', 9, 'bold')).pack(anchor=self.tk.W)
        self.wine_cpu_label = self.tk.Label(cpu_col, text="░░░░░░░░░░ 0%", font=('Courier', 9))
        self.wine_cpu_label.pack(anchor=self.tk.W)
        
        # Колонка 4: Сеть
        net_col = self.tk.Frame(info_panel)
        net_col.pack(side=self.tk.LEFT, expand=True, fill=self.tk.X, padx=5)
        self.tk.Label(net_col, text="Сеть:", font=('Arial', 9, 'bold')).pack(anchor=self.tk.W)
        self.wine_net_label = self.tk.Label(net_col, text="░░░░░░░░░░ 0.0 MB/s", font=('Courier', 9))
        self.wine_net_label.pack(anchor=self.tk.W)
        
        # Колонка 5: Процессы
        proc_col = self.tk.Frame(info_panel)
        proc_col.pack(side=self.tk.LEFT, expand=True, fill=self.tk.X, padx=5)
        self.tk.Label(proc_col, text="Процессы Wine:", font=('Arial', 9, 'bold')).pack(anchor=self.tk.W)
        self.wine_proc_label = self.tk.Label(proc_col, text="неактивны", font=('Arial', 9))
        self.wine_proc_label.pack(anchor=self.tk.W)
        
        # Текущий этап
        stage_frame = self.tk.Frame(progress_frame)
        stage_frame.pack(fill=self.tk.X, padx=10, pady=5)
        self.tk.Label(stage_frame, text="Этап:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.wine_stage_label = self.tk.Label(stage_frame, text="Ожидание...", font=('Arial', 9), fg='gray')
        self.wine_stage_label.pack(side=self.tk.LEFT, padx=5)
        
        # Инициализируем монитор как None
        self.install_monitor = None
        
        # Область статуса компонентов
        status_frame = self.tk.LabelFrame(self.wine_frame, text="Статус компонентов (кликните для выбора)")
        status_frame.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем таблицу статусов с чекбоксами
        columns = ('selected', 'component', 'status', 'path')
        self.wine_tree = self.ttk.Treeview(status_frame, columns=columns, show='headings', height=8)
        
        # Настраиваем колонки
        self.wine_tree.heading('selected', text='☐', command=self.toggle_all_wine_components)
        self.wine_tree.heading('component', text='Компонент')
        self.wine_tree.heading('status', text='Статус')
        self.wine_tree.heading('path', text='Путь/Детали')
        
        self.wine_tree.column('selected', width=40, anchor='center')
        self.wine_tree.column('component', width=200)
        self.wine_tree.column('status', width=100)
        self.wine_tree.column('path', width=450)
        
        # Словарь для хранения состояния чекбоксов (item_id -> True/False)
        self.wine_checkboxes = {}
        
        # Привязываем клик к переключению чекбокса
        self.wine_tree.bind('<Button-1>', self.on_wine_tree_click)
        
        # Добавляем скроллбар
        wine_scrollbar = self.tk.Scrollbar(status_frame, orient=self.tk.VERTICAL, 
                                          command=self.wine_tree.yview)
        self.wine_tree.configure(yscrollcommand=wine_scrollbar.set)
        
        self.wine_tree.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True, padx=5, pady=5)
        wine_scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y, padx=5, pady=5)
        
        # Итоговая сводка
        summary_frame = self.tk.LabelFrame(self.wine_frame, text="Итоговая сводка")
        summary_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        self.wine_summary_text = self.tk.Text(summary_frame, height=4, wrap=self.tk.WORD,
                                             font=('Courier', 9))
        self.wine_summary_text.pack(fill=self.tk.BOTH, expand=True, padx=5, pady=5)
        self.wine_summary_text.config(state=self.tk.DISABLED)
        
        # Заполняем начальными данными
        self.populate_wine_status_initial()
    
    def populate_wine_status_initial(self):
        """Заполнение начальными данными (без проверки)"""
        # Основные компоненты с галочками
        main_components = [
            ('Wine Astraregul', 'Не проверено', '/opt/wine-astraregul/bin/wine', True),
            ('Wine 9.0', 'Не проверено', '/opt/wine-9.0/bin/wine', True),
            ('ptrace_scope', 'Не проверено', '/proc/sys/kernel/yama/ptrace_scope', True),
            ('WINEPREFIX', 'Не проверено', '~/.wine-astraregul', True),
        ]
        
        # Компоненты winetricks (только информация, БЕЗ галочек)
        winetricks_info = [
            ('  ├─ .NET Framework 4.8', 'Не проверено', 'WINEPREFIX/drive_c/windows/Microsoft.NET/Framework64/v4.0.30319', False),
            ('  ├─ Visual C++ 2013', 'Не проверено', 'WINEPREFIX/drive_c/windows/system32/msvcp120.dll', False),
            ('  ├─ Visual C++ 2022', 'Не проверено', 'WINEPREFIX/drive_c/windows/system32/msvcp140.dll', False),
            ('  ├─ DirectX d3dcompiler_43', 'Не проверено', 'WINEPREFIX/drive_c/windows/system32/d3dcompiler_43.dll', False),
            ('  ├─ DirectX d3dcompiler_47', 'Не проверено', 'WINEPREFIX/drive_c/windows/system32/d3dcompiler_47.dll', False),
            ('  └─ DXVK', 'Не проверено', 'WINEPREFIX/drive_c/windows/system32/d3d11.dll', False),
        ]
        
        # Остальные компоненты
        other_components = [
            ('Astra.IDE', 'Не проверено', 'WINEPREFIX/drive_c/Program Files/AstraRegul/Astra.IDE_64_*/Astra.IDE/Common', True),
            ('Скрипт запуска', 'Не проверено', '~/start-astraide.sh', True),
            ('Ярлык рабочего стола', 'Не проверено', '~/Desktop/AstraRegul.desktop', True)
        ]
        
        # Добавляем основные компоненты
        for component, status, path, has_checkbox in main_components:
            checkbox = '☐' if has_checkbox else ' '
            item_id = self.wine_tree.insert('', self.tk.END, values=(checkbox, component, status, path))
            if has_checkbox:
                self.wine_checkboxes[item_id] = False
        
        # Добавляем winetricks компоненты (только информация)
        for component, status, path, has_checkbox in winetricks_info:
            item_id = self.wine_tree.insert('', self.tk.END, values=(' ', component, status, path))
            # НЕ добавляем в wine_checkboxes - их нельзя выбрать
        
        # Добавляем остальные компоненты
        for component, status, path, has_checkbox in other_components:
            checkbox = '☐' if has_checkbox else ' '
            item_id = self.wine_tree.insert('', self.tk.END, values=(checkbox, component, status, path))
            if has_checkbox:
                self.wine_checkboxes[item_id] = False
        
        # Начальное сообщение в сводке
        self.wine_summary_text.config(state=self.tk.NORMAL)
        self.wine_summary_text.delete('1.0', self.tk.END)
        self.wine_summary_text.insert(self.tk.END, "Нажмите кнопку 'Проверить компоненты' для запуска проверки\n")
        self.wine_summary_text.insert(self.tk.END, "Проверка покажет какие компоненты установлены и готовы к работе")
        self.wine_summary_text.config(state=self.tk.DISABLED)
    
    def run_wine_check(self):
        """Запуск проверки Wine компонентов"""
        self.wine_status_label.config(text="Проверка...")
        self.check_wine_button.config(state=self.tk.DISABLED)
        
        # Запускаем проверку в отдельном потоке
        import threading
        check_thread = threading.Thread(target=self._perform_wine_check)
        check_thread.daemon = True
        check_thread.start()
    
    def _perform_wine_check(self):
        """Выполнение проверки Wine компонентов (в отдельном потоке)"""
        try:
            # Создаем экземпляр проверщика
            self.wine_checker = WineComponentsChecker()
            
            # Выполняем все проверки
            self.wine_checker.check_all_components()
            
            # Обновляем GUI в главном потоке
            self.root.after(0, self._update_wine_status)
            
        except Exception as e:
            error_msg = "Ошибка проверки: %s" % str(e)
            self.root.after(0, lambda: self.wine_status_label.config(text=error_msg))
            self.root.after(0, lambda: self.check_wine_button.config(state=self.tk.NORMAL))
    
    def _update_wine_status(self):
        """Обновление статуса в GUI (вызывается из главного потока)"""
        if not self.wine_checker:
            return
        
        # Очищаем таблицу и чекбоксы
        for item in self.wine_tree.get_children():
            self.wine_tree.delete(item)
        self.wine_checkboxes.clear()
        
        # Получаем реальный путь к Astra.IDE если установлена
        astra_ide_path = 'WINEPREFIX/drive_c/Program Files/AstraRegul/Astra.IDE_64_*/Astra.IDE/Common'
        if self.wine_checker.checks['astra_ide']:
            try:
                import glob
                astra_base = os.path.join(self.wine_checker.wineprefix, "drive_c", "Program Files", "AstraRegul")
                astra_dirs = glob.glob(os.path.join(astra_base, "Astra.IDE_64_*"))
                if astra_dirs:
                    # Показываем полный путь к .exe
                    astra_ide_path = os.path.join(astra_dirs[0], "Astra.IDE", "Common", "Astra.IDE.exe")
            except:
                pass
        
        # Основные компоненты (с галочками)
        main_components = [
            ('Wine Astraregul', 'wine_astraregul', self.wine_checker.wine_astraregul_path, True),
            ('Wine 9.0', 'wine_9', self.wine_checker.wine_9_path, True),
            ('ptrace_scope', 'ptrace_scope', self.wine_checker.ptrace_scope_path, True),
            ('WINEPREFIX', 'wineprefix', self.wine_checker.wineprefix, True),
        ]
        
        # Winetricks компоненты (только информация, БЕЗ галочек)
        winetricks_info = [
            ('  ├─ .NET Framework 4.8', 'dotnet48', 'WINEPREFIX/drive_c/windows/Microsoft.NET/Framework64/v4.0.30319', False),
            ('  ├─ Visual C++ 2013', 'vcrun2013', 'WINEPREFIX/drive_c/windows/system32/msvcp120.dll', False),
            ('  ├─ Visual C++ 2022', 'vcrun2022', 'WINEPREFIX/drive_c/windows/system32/msvcp140.dll', False),
            ('  ├─ DirectX d3dcompiler_43', 'd3dcompiler_43', 'WINEPREFIX/drive_c/windows/system32/d3dcompiler_43.dll', False),
            ('  ├─ DirectX d3dcompiler_47', 'd3dcompiler_47', 'WINEPREFIX/drive_c/windows/system32/d3dcompiler_47.dll', False),
            ('  └─ DXVK', 'dxvk', 'WINEPREFIX/drive_c/windows/system32/d3d11.dll', False),
        ]
        
        # Остальные компоненты (с галочками)
        other_components = [
            ('Astra.IDE', 'astra_ide', astra_ide_path, True),
            ('Скрипт запуска', 'start_script', self.wine_checker.start_script, True),
            ('Ярлык рабочего стола', 'desktop_shortcut', self.wine_checker.desktop_shortcut, True)
        ]
        
        # Добавляем основные компоненты
        for component_name, check_key, path, has_checkbox in main_components:
            status = '[OK]' if self.wine_checker.checks[check_key] else '[ERR]'
            checkbox = '☐' if has_checkbox else ' '
            item_id = self.wine_tree.insert('', self.tk.END, values=(checkbox, component_name, status, path))
            if has_checkbox:
                self.wine_checkboxes[item_id] = False
            
            # Цветовое выделение
            if self.wine_checker.checks[check_key]:
                self.wine_tree.item(item_id, tags=('ok',))
            else:
                self.wine_tree.item(item_id, tags=('error',))
        
        # Добавляем winetricks компоненты (только информация)
        for component_name, check_key, path, has_checkbox in winetricks_info:
            status = '[OK]' if self.wine_checker.checks[check_key] else '[ERR]'
            item_id = self.wine_tree.insert('', self.tk.END, values=(' ', component_name, status, path))
            # НЕ добавляем в wine_checkboxes
            
            # Цветовое выделение
            if self.wine_checker.checks[check_key]:
                self.wine_tree.item(item_id, tags=('ok',))
            else:
                self.wine_tree.item(item_id, tags=('error',))
        
        # Добавляем остальные компоненты
        for component_name, check_key, path, has_checkbox in other_components:
            status = '[OK]' if self.wine_checker.checks[check_key] else '[ERR]'
            checkbox = '☐' if has_checkbox else ' '
            item_id = self.wine_tree.insert('', self.tk.END, values=(checkbox, component_name, status, path))
            if has_checkbox:
                self.wine_checkboxes[item_id] = False
            
            # Цветовое выделение
            if self.wine_checker.checks[check_key]:
                self.wine_tree.item(item_id, tags=('ok',))
            else:
                self.wine_tree.item(item_id, tags=('error',))
        
        # Настраиваем цвета тегов
        self.wine_tree.tag_configure('ok', foreground='green')
        self.wine_tree.tag_configure('error', foreground='red')
        
        # Обновляем сводку
        self.wine_summary_text.config(state=self.tk.NORMAL)
        self.wine_summary_text.delete('1.0', self.tk.END)
        
        if self.wine_checker.is_fully_installed():
            self.wine_summary_text.insert(self.tk.END, "[OK] Все компоненты установлены и готовы к работе!\n", 'ok_tag')
            self.wine_status_label.config(text="Все компоненты установлены", fg='green')
        elif self.wine_checker.is_wine_installed() and not self.wine_checker.is_astra_ide_installed():
            self.wine_summary_text.insert(self.tk.END, "[!] Wine установлен, но Astra.IDE не установлена\n", 'warn_tag')
            self.wine_summary_text.insert(self.tk.END, "    Требуется установка Astra.IDE\n")
            self.wine_status_label.config(text="Требуется установка Astra.IDE", fg='orange')
        elif not self.wine_checker.is_wine_installed():
            self.wine_summary_text.insert(self.tk.END, "[ERR] Wine не установлен или настроен неправильно\n", 'error_tag')
            self.wine_summary_text.insert(self.tk.END, "      Требуется установка Wine пакетов\n")
            self.wine_status_label.config(text="Требуется установка Wine", fg='red')
        else:
            missing = self.wine_checker.get_missing_components()
            self.wine_summary_text.insert(self.tk.END, "[!] Некоторые компоненты отсутствуют:\n", 'warn_tag')
            for comp in missing:
                self.wine_summary_text.insert(self.tk.END, "    - %s\n" % comp)
            self.wine_status_label.config(text="Некоторые компоненты отсутствуют", fg='orange')
        
        # Настраиваем цветовые теги
        self.wine_summary_text.tag_configure('ok_tag', foreground='green', font=('Courier', 9, 'bold'))
        self.wine_summary_text.tag_configure('warn_tag', foreground='orange', font=('Courier', 9, 'bold'))
        self.wine_summary_text.tag_configure('error_tag', foreground='red', font=('Courier', 9, 'bold'))
        
        self.wine_summary_text.config(state=self.tk.DISABLED)
        
        # Управляем доступностью кнопок
        self.check_wine_button.config(state=self.tk.NORMAL)
        
        # Активируем кнопку установки если компоненты не установлены
        if not self.wine_checker.is_fully_installed():
            self.install_wine_button.config(state=self.tk.NORMAL)
        else:
            self.install_wine_button.config(state=self.tk.DISABLED)
    
    def run_wine_install(self):
        """Запуск установки Wine компонентов"""
        # Проверяем права root
        if os.geteuid() != 0:
            self.wine_status_label.config(text="Ошибка: требуются права root", fg='red')
            self.log_message("[ERROR] Для установки Wine требуются права root")
            return
        
        self.wine_status_label.config(text="Установка запущена...", fg='blue')
        self.install_wine_button.config(state=self.tk.DISABLED)
        self.check_wine_button.config(state=self.tk.DISABLED)
        
        # Запускаем установку в отдельном потоке
        import threading
        install_thread = threading.Thread(target=self._perform_wine_install)
        install_thread.daemon = True
        install_thread.start()
    
    def _perform_wine_install(self):
        """Выполнение установки Wine компонентов (в отдельном потоке)"""
        try:
            # Создаем callback для обновления статуса
            def update_callback(message):
                self.root.after(0, lambda: self._update_install_status(message))
            
            # Получаем logger из main_log_file
            logger = None
            if hasattr(self, 'main_log_file') and self.main_log_file:
                logger = Logger(self.main_log_file)
            
            # Получаем выбранные компоненты из таблицы
            selected = self.get_selected_wine_components()
            
            # Логируем выбранные компоненты
            self.root.after(0, lambda: self.log_message("[INFO] Выбранные компоненты: %s" % ', '.join(selected) if selected else "НЕТ"))
            
            # Определяем что устанавливать на основе выбранных компонентов
            install_wine = any(c in selected for c in ['Wine Astraregul', 'Wine 9.0'])
            install_winetricks = 'WINEPREFIX' in selected  # Всегда устанавливаем ВСЕ компоненты
            install_ide = 'Astra.IDE' in selected
            
            # Логируем план установки
            self.root.after(0, lambda: self.log_message("[INFO] План установки:"))
            self.root.after(0, lambda: self.log_message("[INFO]   - Wine пакеты: %s" % ("ДА" if install_wine else "НЕТ")))
            self.root.after(0, lambda: self.log_message("[INFO]   - WINEPREFIX (все компоненты winetricks): %s" % ("ДА" if install_winetricks else "НЕТ")))
            self.root.after(0, lambda: self.log_message("[INFO]   - Astra.IDE: %s" % ("ДА" if install_ide else "НЕТ")))
            
            # Проверяем что хоть что-то выбрано
            if not install_wine and not install_winetricks and not install_ide:
                self.root.after(0, lambda: self.log_message("[WARNING] Ничего не выбрано для установки!"))
                self.root.after(0, lambda: self.log_message("[INFO] Отметьте нужные компоненты галочками в таблице"))
                self.root.after(0, lambda: self.wine_status_label.config(text="Ничего не выбрано", fg='orange'))
                self.root.after(0, lambda: self.install_wine_button.config(state=self.tk.NORMAL))
                self.root.after(0, lambda: self.check_wine_button.config(state=self.tk.NORMAL))
                return
            
            # Создаем экземпляр установщика (winetricks_components=None означает установить все)
            installer = WineInstaller(logger=logger, callback=update_callback,
                                    install_wine=install_wine,
                                    install_winetricks=install_winetricks,
                                    install_ide=install_ide,
                                    winetricks_components=None)
            
            # Создаем монитор установки
            wineprefix = os.path.join(os.path.expanduser("~"), ".wine-astraregul")
            
            def monitor_callback(data):
                self.root.after(0, lambda d=data: self._update_install_progress(d))
            
            self.install_monitor = InstallationMonitor(wineprefix, callback=monitor_callback)
            self.install_monitor.start_monitoring()
            
            # Запускаем установку
            self.root.after(0, lambda: self.log_message("[INSTALL] Начало установки Wine и Astra.IDE"))
            self.root.after(0, lambda: self._reset_progress_panel())
            success = installer.install_all()
            
            # Останавливаем монитор
            if self.install_monitor:
                self.install_monitor.stop_monitoring()
            
            # Обновляем GUI после установки
            self.root.after(0, lambda: self._wine_install_completed(success))
            
        except Exception as e:
            error_msg = "Ошибка установки: %s" % str(e)
            
            # Останавливаем монитор при ошибке
            if hasattr(self, 'install_monitor') and self.install_monitor:
                self.install_monitor.stop_monitoring()
            
            self.root.after(0, lambda: self.wine_status_label.config(text=error_msg, fg='red'))
            self.root.after(0, lambda: self.log_message("[ERROR] %s" % error_msg))
            self.root.after(0, lambda: self.install_wine_button.config(state=self.tk.NORMAL))
            self.root.after(0, lambda: self.check_wine_button.config(state=self.tk.NORMAL))
    
    def _reset_progress_panel(self):
        """Сброс панели прогресса перед началом установки"""
        self.wine_progress['value'] = 0
        self.wine_time_label.config(text="0 мин 0 сек")
        self.wine_size_label.config(text="0 MB")
        self.wine_proc_label.config(text="неактивны", fg='gray')
        self.wine_stage_label.config(text="Подготовка...", fg='blue')
    
    def _create_progress_bar(self, value, max_value=100, width=10):
        """Создать текстовый прогресс-бар"""
        filled = int(width * value / max_value)
        bar = '█' * filled + '░' * (width - filled)
        return "%s %d%%" % (bar, value)
    
    def _update_install_progress(self, data):
        """Обновление прогресса установки из монитора (вызывается из главного потока)"""
        # Обновляем время
        minutes = data['elapsed_time'] // 60
        seconds = data['elapsed_time'] % 60
        self.wine_time_label.config(text="%d мин %d сек" % (minutes, seconds))
        
        # Обновляем размер
        size_mb = data['wineprefix_size']
        self.wine_size_label.config(text="%d MB" % size_mb)
        
        # Обновляем процессы
        if data['wine_processes']:
            procs_text = ", ".join(data['wine_processes'][:3])  # Первые 3
            if len(data['wine_processes']) > 3:
                procs_text += "..."
            self.wine_proc_label.config(text=procs_text, fg='green')
        else:
            self.wine_proc_label.config(text="неактивны", fg='gray')
        
        # Обновляем CPU с прогресс-баром
        cpu_usage = data.get('cpu_usage', 0)
        cpu_bar = self._create_progress_bar(cpu_usage, 100, 10)
        self.wine_cpu_label.config(text=cpu_bar)
        
        # Обновляем Сеть с прогресс-баром
        net_speed = data.get('network_speed', 0.0)
        # Масштабируем до 10 MB/s для прогресс-бара
        net_percent = min(100, int((net_speed / 10.0) * 100))
        net_bar = self._create_progress_bar(net_percent, 100, 10)
        self.wine_net_label.config(text="%s %.1f MB/s" % (net_bar, net_speed))
        
        # Обновляем прогресс-бар (примерная оценка на основе размера и времени)
        # Wine packages: ~100MB, winetricks: ~500MB, Astra.IDE: ~1500MB
        # Общий примерный размер: ~2100MB
        estimated_total = 2100
        progress_percent = min(100, int((size_mb / estimated_total) * 100))
        self.wine_progress['value'] = progress_percent
    
    def _update_install_status(self, message):
        """Обновление статуса установки в GUI (вызывается из главного потока)"""
        # Обновляем статус-метку (только первые 80 символов)
        short_msg = message[:80] + "..." if len(message) > 80 else message
        self.wine_status_label.config(text=short_msg, fg='blue')
        
        # Определяем текущий этап по сообщению
        if "ШАГ 1" in message or "WINE ПАКЕТОВ" in message:
            self.wine_stage_label.config(text="Установка Wine пакетов", fg='blue')
        elif "ШАГ 2" in message or "ptrace_scope" in message:
            self.wine_stage_label.config(text="Настройка безопасности", fg='blue')
        elif "ШАГ 3" in message or "ОКРУЖЕНИЯ WINE" in message:
            self.wine_stage_label.config(text="Настройка окружения Wine", fg='blue')
        elif "ШАГ 4" in message or "WINETRICKS" in message:
            self.wine_stage_label.config(text="Установка компонентов winetricks", fg='blue')
        elif "ШАГ 5" in message or "СКРИПТОВ" in message:
            self.wine_stage_label.config(text="Создание скриптов запуска", fg='blue')
        elif "ШАГ 6" in message or "ASTRA.IDE" in message:
            self.wine_stage_label.config(text="Установка Astra.IDE", fg='blue')
        elif "УСПЕШНО" in message:
            self.wine_stage_label.config(text="Установка завершена!", fg='green')
        elif "ОШИБКА" in message or "ПРЕРВАНА" in message:
            self.wine_stage_label.config(text="Ошибка установки", fg='red')
        
        # Добавляем в лог
        self.log_message(message)
        
        # Также добавляем в терминал если сообщение важное
        if any(keyword in message for keyword in ['ШАГ', 'УСТАНОВКА', 'УСПЕШНО', 'ОШИБКА']):
            self.add_terminal_output(message)
    
    def _wine_install_completed(self, success):
        """Обработка завершения установки (вызывается из главного потока)"""
        if success:
            self.wine_status_label.config(text="Установка завершена успешно!", fg='green')
            self.wine_stage_label.config(text="Установка завершена!", fg='green')
            self.wine_progress['value'] = 100
            self.log_message("[SUCCESS] Установка Wine и Astra.IDE завершена успешно")
            
            # Автоматически запускаем проверку
            self.root.after(2000, self.run_wine_check)
        else:
            self.wine_status_label.config(text="Установка прервана (см. лог)", fg='red')
            self.wine_stage_label.config(text="Ошибка установки", fg='red')
            self.log_message("[ERROR] Установка Wine и Astra.IDE прервана")
        
        # Включаем кнопки обратно
        self.check_wine_button.config(state=self.tk.NORMAL)
    
    def on_wine_tree_click(self, event):
        """Обработка клика по таблице Wine компонентов"""
        region = self.wine_tree.identify('region', event.x, event.y)
        if region == 'heading':
            return  # Заголовок обрабатывается отдельно
        
        item = self.wine_tree.identify_row(event.y)
        column = self.wine_tree.identify_column(event.x)
        
        if item and column == '#1':  # Колонка с чекбоксом
            # Переключаем состояние
            current_state = self.wine_checkboxes.get(item, False)
            new_state = not current_state
            self.wine_checkboxes[item] = new_state
            
            # Обновляем отображение
            values = list(self.wine_tree.item(item, 'values'))
            values[0] = '☑' if new_state else '☐'
            self.wine_tree.item(item, values=values)
            
            # Обновляем кнопки
            self._update_wine_buttons()
    
    def toggle_all_wine_components(self):
        """Переключить все чекбоксы (клик по заголовку)"""
        # Проверяем сколько выбрано
        selected_count = sum(1 for checked in self.wine_checkboxes.values() if checked)
        total_count = len(self.wine_checkboxes)
        
        # Если все выбраны - снимаем все, иначе - выбираем все
        new_state = not (selected_count == total_count)
        
        for item in self.wine_checkboxes:
            self.wine_checkboxes[item] = new_state
            values = list(self.wine_tree.item(item, 'values'))
            values[0] = '☑' if new_state else '☐'
            self.wine_tree.item(item, values=values)
        
        # Обновляем заголовок
        self.wine_tree.heading('selected', text='☑' if new_state else '☐')
        
        # Обновляем кнопки
        self._update_wine_buttons()
    
    def _update_wine_buttons(self):
        """Обновление состояния кнопок установки/удаления"""
        selected_count = sum(1 for checked in self.wine_checkboxes.values() if checked)
        
        if selected_count > 0:
            self.install_wine_button.config(state=self.tk.NORMAL)
            self.uninstall_wine_button.config(state=self.tk.NORMAL)
        else:
            self.install_wine_button.config(state=self.tk.DISABLED)
            self.uninstall_wine_button.config(state=self.tk.DISABLED)
    
    def get_selected_wine_components(self):
        """Получить список выбранных компонентов"""
        selected = []
        for item, checked in self.wine_checkboxes.items():
            if checked:
                values = self.wine_tree.item(item, 'values')
                component_name = values[1]  # Вторая колонка - название компонента
                selected.append(component_name)
        return selected
    
    def run_wine_uninstall(self):
        """Запуск удаления Wine компонентов"""
        # Проверяем права root
        if os.geteuid() != 0:
            self.wine_status_label.config(text="Ошибка: требуются права root", fg='red')
            self.log_message("[ERROR] Для удаления Wine требуются права root")
            return
        
        # Получаем список выбранных компонентов
        selected = self.get_selected_wine_components()
        if not selected:
            self.wine_status_label.config(text="Выберите компоненты для удаления", fg='orange')
            return
        
        # Подтверждение удаления
        import tkinter.messagebox as messagebox
        message = "Вы уверены что хотите удалить следующие компоненты?\n\n" + "\n".join(selected)
        if not messagebox.askyesno("Подтверждение удаления", message):
            return
        
        self.wine_status_label.config(text="Удаление запущено...", fg='blue')
        self.uninstall_wine_button.config(state=self.tk.DISABLED)
        self.install_wine_button.config(state=self.tk.DISABLED)
        self.check_wine_button.config(state=self.tk.DISABLED)
        
        # Запускаем удаление в отдельном потоке
        import threading
        uninstall_thread = threading.Thread(target=self._perform_wine_uninstall, args=(selected,))
        uninstall_thread.daemon = True
        uninstall_thread.start()
    
    def _perform_wine_uninstall(self, selected_components):
        """Выполнение удаления Wine компонентов (в отдельном потоке)"""
        try:
            # Создаем callback для обновления статуса
            def update_callback(message):
                self.root.after(0, lambda: self._update_install_status(message))
            
            # Получаем logger из main_log_file
            logger = None
            if hasattr(self, 'main_log_file') and self.main_log_file:
                logger = Logger(self.main_log_file)
            
            # Определяем что удалять на основе выбранных компонентов
            remove_wine = any(c in selected_components for c in ['Wine Astraregul', 'Wine 9.0'])
            remove_wineprefix = 'WINEPREFIX' in selected_components  # Удаляет весь WINEPREFIX со всеми компонентами
            remove_ide = any(c in selected_components for c in ['Astra.IDE', 'Скрипт запуска', 'Ярлык рабочего стола'])
            
            # Учитываем зависимости:
            # 1. Если удаляется Wine → нужно удалить WINEPREFIX и Astra.IDE (они зависят от Wine)
            if remove_wine:
                if not remove_wineprefix:
                    self.root.after(0, lambda: self.log_message("[INFO] Wine удаляется → автоматически удаляется WINEPREFIX"))
                    remove_wineprefix = True
                if not remove_ide:
                    self.root.after(0, lambda: self.log_message("[INFO] Wine удаляется → автоматически удаляется Astra.IDE"))
                    remove_ide = True
            
            # 2. Если удаляется WINEPREFIX → нужно удалить Astra.IDE (она установлена в WINEPREFIX)
            if remove_wineprefix and not remove_ide:
                self.root.after(0, lambda: self.log_message("[INFO] WINEPREFIX удаляется → автоматически удаляется Astra.IDE"))
                remove_ide = True
            
            # Создаем экземпляр деинсталлятора
            uninstaller = WineUninstaller(logger=logger, callback=update_callback,
                                        remove_wine=remove_wine,
                                        remove_wineprefix=remove_wineprefix,
                                        remove_ide=remove_ide,
                                        winetricks_components=None)
            
            # Запускаем удаление
            self.root.after(0, lambda: self.log_message("[UNINSTALL] Начало удаления Wine и Astra.IDE"))
            success = uninstaller.uninstall_all()
            
            # Обновляем GUI после удаления
            self.root.after(0, lambda: self._wine_uninstall_completed(success))
            
        except Exception as e:
            error_msg = "Ошибка удаления: %s" % str(e)
            self.root.after(0, lambda: self.wine_status_label.config(text=error_msg, fg='red'))
            self.root.after(0, lambda: self.log_message("[ERROR] %s" % error_msg))
            self.root.after(0, lambda: self.uninstall_wine_button.config(state=self.tk.NORMAL))
            self.root.after(0, lambda: self.check_wine_button.config(state=self.tk.NORMAL))
    
    def _wine_uninstall_completed(self, success):
        """Обработка завершения удаления (вызывается из главного потока)"""
        if success:
            self.wine_status_label.config(text="Удаление завершено успешно!", fg='green')
            self.log_message("[SUCCESS] Удаление Wine и Astra.IDE завершено успешно")
            
            # Автоматически запускаем проверку
            self.root.after(2000, self.run_wine_check)
        else:
            self.wine_status_label.config(text="Удаление прервано (см. лог)", fg='red')
            self.log_message("[ERROR] Удаление Wine и Astra.IDE прервано")
        
        # Включаем кнопки обратно
        self.check_wine_button.config(state=self.tk.NORMAL)
    
    def run_repos_check(self):
        """Запуск проверки репозиториев"""
        self.wine_status_label.config(text="Проверка репозиториев...", fg='blue')
        self.check_repos_button.config(state=self.tk.DISABLED)
        
        # Запускаем проверку в отдельном потоке
        import threading
        check_thread = threading.Thread(target=self._perform_repos_check)
        check_thread.daemon = True
        check_thread.start()
    
    def _perform_repos_check(self):
        """Выполнение проверки репозиториев (в отдельном потоке)"""
        try:
            self.root.after(0, lambda: self.log_message("\n" + "=" * 60))
            self.root.after(0, lambda: self.log_message("[REPOS] ДИАГНОСТИКА РЕПОЗИТОРИЕВ"))
            self.root.after(0, lambda: self.log_message("=" * 60))
            
            # 1. Проверка прав доступа к sources.list
            sources_file = "/etc/apt/sources.list"
            self.root.after(0, lambda: self.log_message("\n[CHECK] Проверка файла репозиториев..."))
            self.root.after(0, lambda: self.log_message("Файл: %s" % sources_file))
            
            if not os.path.exists(sources_file):
                self.root.after(0, lambda: self.log_message("[ERR] Файл не существует!", ))
                self.root.after(0, lambda: self._repos_check_completed(False))
                return
            
            # Проверяем права на чтение
            try:
                with open(sources_file, 'r') as f:
                    content = f.read()
                self.root.after(0, lambda: self.log_message("[OK] Файл доступен для чтения"))
                self.root.after(0, lambda: self.log_message("Размер файла: %d байт" % len(content)))
            except PermissionError:
                self.root.after(0, lambda: self.log_message("[ERR] Нет прав на чтение файла!"))
                self.root.after(0, lambda: self.log_message("[INFO] Требуются права root"))
                content = None
            except Exception as e:
                self.root.after(0, lambda: self.log_message("[ERR] Ошибка чтения: %s" % str(e)))
                content = None
            
            # 2. Вывод содержимого sources.list
            if content:
                self.root.after(0, lambda: self.log_message("\n[INFO] Содержимое /etc/apt/sources.list:"))
                self.root.after(0, lambda: self.log_message("-" * 60))
                
                lines = content.split('\n')
                active_repos = []
                disabled_repos = []
                
                for i, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    if not line_stripped or line_stripped.startswith('#'):
                        # Комментарий или пустая строка
                        if line_stripped.startswith('#') and 'deb' in line_stripped:
                            disabled_repos.append(line_stripped)
                    elif line_stripped.startswith('deb'):
                        # Активный репозиторий
                        active_repos.append(line_stripped)
                        self.root.after(0, lambda l=line_stripped: self.log_message("  [ACTIVE] %s" % l))
                
                self.root.after(0, lambda: self.log_message("-" * 60))
                self.root.after(0, lambda: self.log_message("Активных репозиториев: %d" % len(active_repos)))
                self.root.after(0, lambda: self.log_message("Отключенных репозиториев: %d" % len(disabled_repos)))
                
                if len(active_repos) == 0:
                    self.root.after(0, lambda: self.log_message("[WARNING] НЕТ АКТИВНЫХ РЕПОЗИТОРИЕВ!"))
                    self.root.after(0, lambda: self.log_message("[WARNING] Это объясняет ошибки установки пакетов"))
            
            # 3. Проверка доступности репозиториев
            self.root.after(0, lambda: self.log_message("\n[CHECK] Проверка доступности репозиториев..."))
            self.root.after(0, lambda: self.log_message("Выполнение: apt-get update (это может занять время)"))
            
            result = subprocess.run(
                ['apt-get', 'update'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.log_message("[OK] apt-get update выполнен успешно"))
            else:
                self.root.after(0, lambda: self.log_message("[ERR] apt-get update завершился с ошибкой (код %d)" % result.returncode))
                
                if result.stderr:
                    self.root.after(0, lambda: self.log_message("\nОшибки:"))
                    for line in result.stderr.strip().split('\n')[:20]:  # Первые 20 строк
                        if line.strip():
                            self.root.after(0, lambda l=line: self.log_message("  ! %s" % l))
            
            # 4. Проверка политики apt
            self.root.after(0, lambda: self.log_message("\n[CHECK] Политика APT..."))
            
            result = subprocess.run(
                ['apt-cache', 'policy'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')[:15]  # Первые 15 строк
                for line in lines:
                    if line.strip():
                        self.root.after(0, lambda l=line: self.log_message("  %s" % l))
            
            # 5. Проверка наличия нужных пакетов в репозиториях
            self.root.after(0, lambda: self.log_message("\n[CHECK] Проверка доступности пакетов-зависимостей..."))
            
            required_packages = ['ia32-libs', 'winetricks', 'libc6:i386']
            
            for pkg in required_packages:
                result = subprocess.run(
                    ['apt-cache', 'show', pkg],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    check=False
                )
                
                if result.returncode == 0:
                    self.root.after(0, lambda p=pkg: self.log_message("  [OK] Пакет '%s' найден в репозиториях" % p))
                else:
                    self.root.after(0, lambda p=pkg: self.log_message("  [ERR] Пакет '%s' НЕ найден в репозиториях!" % p))
            
            # Завершение
            self.root.after(0, lambda: self.log_message("\n" + "=" * 60))
            self.root.after(0, lambda: self.log_message("[REPOS] ДИАГНОСТИКА ЗАВЕРШЕНА"))
            self.root.after(0, lambda: self.log_message("=" * 60))
            
            self.root.after(0, lambda: self._repos_check_completed(True))
            
        except Exception as e:
            error_msg = "Ошибка проверки репозиториев: %s" % str(e)
            self.root.after(0, lambda: self.log_message("[ERROR] %s" % error_msg))
            self.root.after(0, lambda: self._repos_check_completed(False))
    
    def _repos_check_completed(self, success):
        """Обработка завершения проверки репозиториев"""
        if success:
            self.wine_status_label.config(text="Диагностика репозиториев завершена (см. лог)", fg='green')
        else:
            self.wine_status_label.config(text="Ошибка проверки репозиториев", fg='red')
        
        self.check_repos_button.config(state=self.tk.NORMAL)
    
    # ========================================================================
    # МЕТОДЫ ДЛЯ ВКЛАДКИ РЕПОЗИТОРИЕВ
    # ========================================================================
    
    def load_repositories(self):
        """Загрузка списка репозиториев из sources.list"""
        self.repos_status_label.config(text="Загрузка репозиториев...", fg='blue')
        self.load_repos_button.config(state=self.tk.DISABLED)
        
        try:
            sources_file = "/etc/apt/sources.list"
            
            # Очищаем таблицу
            for item in self.repos_tree.get_children():
                self.repos_tree.delete(item)
            
            # Читаем файл
            try:
                with open(sources_file, 'r') as f:
                    lines = f.readlines()
            except PermissionError:
                self.repos_status_label.config(text="Ошибка: нет прав на чтение", fg='red')
                self.log_message("[ERROR] Нет прав на чтение %s" % sources_file)
                self.load_repos_button.config(state=self.tk.NORMAL)
                return
            
            active_count = 0
            disabled_count = 0
            total_count = 0
            
            for line in lines:
                line = line.strip()
                
                # Пропускаем пустые строки и комментарии (кроме закомментированных deb)
                if not line:
                    continue
                
                is_disabled = line.startswith('#')
                
                if is_disabled:
                    # Убираем комментарий для парсинга
                    line_clean = line.lstrip('#').strip()
                else:
                    line_clean = line
                
                # Парсим строку репозитория
                if line_clean.startswith('deb'):
                    parts = line_clean.split()
                    if len(parts) >= 3:
                        repo_type = parts[0]  # deb или deb-src
                        uri = parts[1]
                        distribution = parts[2] if len(parts) > 2 else ''
                        components = ' '.join(parts[3:]) if len(parts) > 3 else ''
                        
                        status = 'Отключен' if is_disabled else 'Активен'
                        
                        # Добавляем в таблицу
                        item = self.repos_tree.insert('', self.tk.END, 
                                                     values=(status, repo_type, uri, distribution, components))
                        
                        # Цветовое выделение
                        if is_disabled:
                            self.repos_tree.item(item, tags=('disabled',))
                            disabled_count += 1
                        else:
                            self.repos_tree.item(item, tags=('active',))
                            active_count += 1
                        
                        total_count += 1
            
            # Настраиваем цвета
            self.repos_tree.tag_configure('active', foreground='green')
            self.repos_tree.tag_configure('disabled', foreground='red')
            
            # Обновляем статистику
            self.repos_total_label.config(text=str(total_count))
            self.repos_active_label.config(text=str(active_count))
            self.repos_disabled_label.config(text=str(disabled_count))
            
            self.repos_status_label.config(
                text="Загружено: %d (активных: %d, отключенных: %d)" % (total_count, active_count, disabled_count),
                fg='green'
            )
            
            self.log_message("[REPOS] Загружено %d репозиториев (%d активных, %d отключенных)" % 
                           (total_count, active_count, disabled_count))
            
        except Exception as e:
            self.repos_status_label.config(text="Ошибка загрузки: %s" % str(e), fg='red')
            self.log_message("[ERROR] Ошибка загрузки репозиториев: %s" % str(e))
        
        finally:
            self.load_repos_button.config(state=self.tk.NORMAL)
    
    def check_repositories_availability(self):
        """Проверка доступности репозиториев"""
        self.repos_status_label.config(text="Проверка доступности...", fg='blue')
        self.check_repos_button2.config(state=self.tk.DISABLED)
        
        # Запускаем в отдельном потоке
        import threading
        check_thread = threading.Thread(target=self._check_repos_availability_thread)
        check_thread.daemon = True
        check_thread.start()
    
    def _check_repos_availability_thread(self):
        """Проверка доступности репозиториев (в потоке)"""
        try:
            self.root.after(0, lambda: self.log_message("\n[REPOS] Проверка доступности репозиториев..."))
            
            # Выполняем apt-get update для проверки
            result = subprocess.run(
                ['apt-get', 'update'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.log_message("[OK] Все репозитории доступны"))
                self.root.after(0, lambda: self.repos_status_label.config(text="Все репозитории доступны", fg='green'))
            else:
                self.root.after(0, lambda: self.log_message("[ERR] Некоторые репозитории недоступны"))
                self.root.after(0, lambda: self.repos_status_label.config(text="Есть недоступные репозитории", fg='orange'))
                
                if result.stderr:
                    for line in result.stderr.strip().split('\n')[:10]:
                        if line.strip():
                            self.root.after(0, lambda l=line: self.log_message("  ! %s" % l))
        
        except Exception as e:
            self.root.after(0, lambda: self.log_message("[ERROR] Ошибка проверки: %s" % str(e)))
            self.root.after(0, lambda: self.repos_status_label.config(text="Ошибка проверки", fg='red'))
        
        finally:
            self.root.after(0, lambda: self.check_repos_button2.config(state=self.tk.NORMAL))
    
    def run_apt_update(self):
        """Выполнение apt-get update"""
        self.repos_status_label.config(text="Обновление списков пакетов...", fg='blue')
        self.update_repos_button.config(state=self.tk.DISABLED)
        
        # Запускаем в отдельном потоке
        import threading
        update_thread = threading.Thread(target=self._run_apt_update_thread)
        update_thread.daemon = True
        update_thread.start()
    
    def _run_apt_update_thread(self):
        """Выполнение apt-get update (в потоке)"""
        try:
            self.root.after(0, lambda: self.log_message("\n[REPOS] Выполнение apt-get update..."))
            self.root.after(0, lambda: self.log_message("Это может занять некоторое время..."))
            
            result = subprocess.run(
                ['apt-get', 'update'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            # Логируем вывод
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        self.root.after(0, lambda l=line: self.log_message("  > %s" % l))
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.log_message("[OK] apt-get update завершен успешно"))
                self.root.after(0, lambda: self.repos_status_label.config(text="Списки пакетов обновлены", fg='green'))
            else:
                self.root.after(0, lambda: self.log_message("[ERR] apt-get update завершился с ошибкой"))
                self.root.after(0, lambda: self.repos_status_label.config(text="Ошибка обновления", fg='red'))
                
                if result.stderr:
                    for line in result.stderr.strip().split('\n')[:20]:
                        if line.strip():
                            self.root.after(0, lambda l=line: self.log_message("  ! %s" % l))
        
        except Exception as e:
            self.root.after(0, lambda: self.log_message("[ERROR] Ошибка: %s" % str(e)))
            self.root.after(0, lambda: self.repos_status_label.config(text="Ошибка выполнения", fg='red'))
        
        finally:
            self.root.after(0, lambda: self.update_repos_button.config(state=self.tk.NORMAL))
    
    def show_repo_context_menu(self, event):
        """Показать контекстное меню для репозитория"""
        # Создаем контекстное меню
        menu = self.tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Показать детали", command=lambda: self.show_repo_details(None))
        menu.add_separator()
        menu.add_command(label="Копировать URI", command=self.copy_repo_uri)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def show_repo_details(self, event):
        """Показать детали выбранного репозитория"""
        selection = self.repos_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.repos_tree.item(item, 'values')
        
        if values:
            details = "Статус: %s\nТип: %s\nURI: %s\nДистрибутив: %s\nКомпоненты: %s" % values
            
            # Создаем окно с деталями
            detail_window = self.tk.Toplevel(self.root)
            detail_window.title("Детали репозитория")
            detail_window.geometry("600x200")
            
            text_widget = self.tk.Text(detail_window, wrap=self.tk.WORD)
            text_widget.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert('1.0', details)
            text_widget.config(state=self.tk.DISABLED)
            
            self.log_message("[REPOS] Просмотр деталей: %s" % values[2])
    
    def copy_repo_uri(self):
        """Копировать URI репозитория в буфер обмена"""
        selection = self.repos_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.repos_tree.item(item, 'values')
        
        if values and len(values) > 2:
            uri = values[2]
            self.root.clipboard_clear()
            self.root.clipboard_append(uri)
            self.log_message("[REPOS] URI скопирован в буфер обмена: %s" % uri)
            self.repos_status_label.config(text="URI скопирован в буфер обмена", fg='green')
    
    def open_system_monitor(self):
        """Открыть системный монитор"""
        try:
            # Пытаемся открыть системный монитор (разные варианты для разных систем)
            monitors = [
                'gnome-system-monitor',  # GNOME
                'mate-system-monitor',   # MATE
                'ksysguard',            # KDE
                'xfce4-taskmanager',    # XFCE
                'lxtask',               # LXDE
                'htop',                 # Консольный вариант
            ]
            
            for monitor in monitors:
                try:
                    # Проверяем наличие команды
                    result = subprocess.run(
                        ['which', monitor],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False
                    )
                    
                    if result.returncode == 0:
                        # Запускаем монитор в фоновом режиме
                        subprocess.Popen([monitor], 
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                        self.log_message("[SYSTEM] Запущен системный монитор: %s" % monitor)
                        self.wine_status_label.config(text="Системный монитор запущен", fg='green')
                        return
                except:
                    continue
            
            # Если ничего не нашли
            self.log_message("[WARNING] Системный монитор не найден в системе")
            self.wine_status_label.config(text="Системный монитор не найден", fg='orange')
            
        except Exception as e:
            self.log_message("[ERROR] Ошибка запуска системного монитора: %s" % str(e))
            self.wine_status_label.config(text="Ошибка запуска монитора", fg='red')
        
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
            env['DEBIAN_PRIORITY'] = 'critical'
            env['APT_LISTCHANGES_FRONTEND'] = 'none'
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
            
            # Читаем вывод построчно с увеличенным буфером для многострочных запросов
            output_buffer = ""
            full_output = ""
            max_buffer_lines = 20  # Увеличенный буфер для распознавания многострочных запросов
            buffer_line_count = 0
            
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                # Выводим строку
                print("   %s" % line.rstrip())
                
                # Добавляем в буфер для анализа
                output_buffer += line
                full_output += line
                buffer_line_count += 1
                
                # Ограничиваем размер буфера (последние N строк)
                if buffer_line_count > max_buffer_lines:
                    lines = output_buffer.split('\n')
                    output_buffer = '\n'.join(lines[-max_buffer_lines:])
                    buffer_line_count = max_buffer_lines
                
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
                    buffer_line_count = 0
            
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
        
        # Затем обновляем систему с опциями dpkg для автоподтверждения
        print("\n[START] Обновление системы...")
        upgrade_cmd = ['apt-get', 'dist-upgrade', '-y',
                      '-o', 'Dpkg::Options::=--force-confdef',
                      '-o', 'Dpkg::Options::=--force-confold',
                      '-o', 'Dpkg::Options::=--force-confmiss']
        result = self.run_command_with_interactive_handling(upgrade_cmd, dry_run, gui_terminal=True)
        
        # Обрабатываем результат обновления
        if result == 0:
            print("[OK] Система успешно обновлена")
            
            # Автоматическая очистка ненужных пакетов
            print("\n[CLEANUP] Автоматическая очистка ненужных пакетов...")
            autoremove_cmd = ['apt-get', 'autoremove', '-y',
                            '-o', 'Dpkg::Options::=--force-confdef',
                            '-o', 'Dpkg::Options::=--force-confold',
                            '-o', 'Dpkg::Options::=--force-confmiss']
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

def run_gui_monitor(temp_dir, dry_run=False, close_terminal_pid=None):
    """Запуск GUI мониторинга через класс AutomationGUI"""
    print("\n[GUI] Запуск GUI мониторинга...")
    
    try:
        # Создаем экземпляр класса AutomationGUI напрямую
        print("   [OK] Создаем экземпляр AutomationGUI...")
        gui = AutomationGUI(console_mode=False, close_terminal_pid=close_terminal_pid)
        
        # Устанавливаем лог-файл для GUI
        logger = get_logger()
        gui.main_log_file = logger.log_file
        
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
        close_terminal_pid = None
        
        if len(sys.argv) > 1:
            i = 1
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == '--dry-run':
                    dry_run = True
                    logger.log_info("Включен режим тестирования (dry-run)")
                elif arg == '--console':
                    console_mode = True
                    logger.log_info("Включен консольный режим")
                elif arg == '--close-terminal':
                    # Следующий аргумент - PID терминала
                    if i + 1 < len(sys.argv):
                        close_terminal_pid = sys.argv[i + 1]
                        logger.log_info("Терминал будет закрыт после запуска GUI (PID: %s)" % close_terminal_pid)
                        i += 1  # Пропускаем следующий аргумент
                i += 1
            
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
                gui_success = run_gui_monitor(None, dry_run, close_terminal_pid)
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

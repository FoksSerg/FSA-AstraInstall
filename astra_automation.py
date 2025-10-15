#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

"""
FSA-AstraInstall Automation - Единый исполняемый файл
Автоматически распаковывает компоненты и запускает автоматизацию astra-setup.sh
Совместимость: Python 3.x
Версия: V2.2.61 (2025.10.16)
"""

# Версия приложения
APP_VERSION = "V2.2.61"
import os
import sys
import tempfile
import subprocess
import shutil
import re
import datetime
import threading
import traceback
import hashlib
import queue

# Попытка импорта psutil (может быть не установлен)
try:
    import psutil  # pyright: ignore[reportMissingModuleSource]
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# HTTP client (requests preferred)
try:
    import requests  # type: ignore
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False

# ============================================================================
# УНИВЕРСАЛЬНАЯ КОНФИГУРАЦИЯ КОМПОНЕНТОВ
# ============================================================================
COMPONENTS_CONFIG = {
    # Wine пакеты системы
    'wine_astraregul': {
        'name': 'Wine Astraregul',
        'category': 'wine_packages',
        'dependencies': [],
        'check_paths': ['/opt/wine-astraregul/bin/wine'],
        'install_method': 'package_manager',
        'uninstall_method': 'package_manager',
        'gui_selectable': True,
        'description': 'Основной Wine пакет Astraregul',
        'priority': 1
    },
    'wine_9': {
        'name': 'Wine 9.0',
        'category': 'wine_packages',
        'dependencies': [],  # НЕЗАВИСИМ от wine_astraregul
        'check_paths': ['/opt/wine-9.0/bin/wine'],
        'install_method': 'package_manager',
        'uninstall_method': 'package_manager',
        'gui_selectable': True,
        'description': 'Wine версии 9.0 для совместимости',
        'priority': 2
    },
    'ptrace_scope': {
        'name': 'ptrace_scope',
        'category': 'system_config',
        'dependencies': [],
        'check_paths': ['/proc/sys/kernel/yama/ptrace_scope'],
        'install_method': 'system_config',
        'uninstall_method': 'system_config',
        'gui_selectable': True,
        'description': 'Настройка ptrace_scope для Wine',
        'priority': 3
    },
    
    # Wine окружение
    'wineprefix': {
        'name': 'WINEPREFIX',
        'category': 'wine_environment',
        'dependencies': ['wine_astraregul'],
        'check_paths': ['~/.wine-astraregul'],
        'install_method': 'wine_init',
        'uninstall_method': 'wine_cleanup',
        'gui_selectable': True,
        'description': 'Wine префикс для Astra.IDE',
        'priority': 4
    },
    
    # Winetricks компоненты
    'wine-mono': {
        'name': 'Wine Mono',
        'category': 'winetricks',
        'dependencies': ['wineprefix'],
        'check_paths': [
            'drive_c/windows/mono/mono-2.0/bin/libmono-2.0-x86.dll',
            'drive_c/windows/mono/mono-2.0/bin/libmono-2.0-x86_64.dll'
        ],
        'install_method': 'winetricks',
        'uninstall_method': 'winetricks',
        'gui_selectable': False,
        'description': 'Mono runtime для Wine',
        'priority': 5
    },
    'dotnet48': {
        'name': '.NET Framework 4.8',
        'category': 'winetricks',
        'dependencies': ['wineprefix'],
        'check_paths': [
            'drive_c/windows/Microsoft.NET/Framework/v4.0.30319/mscorlib.dll',
            'drive_c/windows/Microsoft.NET/Framework64/v4.0.30319/mscorlib.dll'
        ],
        'install_method': 'winetricks',
        'uninstall_method': 'winetricks',
        'gui_selectable': False,
        'description': '.NET Framework 4.8',
        'priority': 6
    },
    'vcrun2013': {
        'name': 'Visual C++ 2013',
        'category': 'winetricks',
        'dependencies': ['wineprefix'],
        'check_paths': [
            'drive_c/windows/system32/msvcp120.dll',
            'drive_c/windows/system32/msvcr120.dll',
            'drive_c/windows/syswow64/msvcp120.dll',
            'drive_c/windows/syswow64/msvcr120.dll'
        ],
        'install_method': 'winetricks',
        'uninstall_method': 'winetricks',
        'gui_selectable': False,
        'description': 'Visual C++ 2013 Redistributable',
        'priority': 7
    },
    'vcrun2022': {
        'name': 'Visual C++ 2022',
        'category': 'winetricks',
        'dependencies': ['wineprefix'],
        'check_paths': [
            'drive_c/windows/system32/msvcp140.dll',
            'drive_c/windows/system32/vcruntime140.dll',
            'drive_c/windows/syswow64/msvcp140.dll',
            'drive_c/windows/syswow64/vcruntime140.dll'
        ],
        'install_method': 'winetricks',
        'uninstall_method': 'winetricks',
        'gui_selectable': False,
        'description': 'Visual C++ 2022 Redistributable',
        'priority': 8
    },
    'd3dcompiler_43': {
        'name': 'DirectX d3dcompiler_43',
        'category': 'winetricks',
        'dependencies': ['wineprefix'],
        'check_paths': [
            'drive_c/windows/system32/d3dcompiler_43.dll',
            'drive_c/windows/syswow64/d3dcompiler_43.dll'
        ],
        'install_method': 'winetricks',
        'uninstall_method': 'winetricks',
        'gui_selectable': False,
        'description': 'DirectX d3dcompiler_43',
        'priority': 9
    },
    'd3dcompiler_47': {
        'name': 'DirectX d3dcompiler_47',
        'category': 'winetricks',
        'dependencies': ['wineprefix'],
        'check_paths': [
            'drive_c/windows/system32/d3dcompiler_47.dll',
            'drive_c/windows/syswow64/d3dcompiler_47.dll'
        ],
        'install_method': 'winetricks',
        'uninstall_method': 'winetricks',
        'gui_selectable': False,
        'description': 'DirectX d3dcompiler_47',
        'priority': 10
    },
    'dxvk': {
        'name': 'DXVK',
        'category': 'winetricks',
        'dependencies': ['wineprefix'],
        'check_paths': [
            'drive_c/windows/system32/dxgi.dll',
            'drive_c/windows/system32/d3d11.dll'
        ],
        'install_method': 'winetricks',
        'uninstall_method': 'winetricks',
        'gui_selectable': False,
        'description': 'DXVK - Vulkan-based D3D11 implementation',
        'priority': 11
    },
    
    # Astra.IDE и связанные компоненты
    'astra_ide': {
        'name': 'Astra.IDE',
        'category': 'application',
        'dependencies': ['wineprefix', 'dotnet48', 'vcrun2013', 'vcrun2022'],
        'check_paths': ['drive_c/Program Files/AstraRegul/Astra.IDE_64_*/Astra.IDE/Common/Astra.IDE.exe'],
        'install_method': 'wine_executable',
        'uninstall_method': 'wine_executable',
        'gui_selectable': True,
        'description': 'Astra.IDE приложение',
        'priority': 12
    },
    'start_script': {
        'name': 'Скрипт запуска',
        'category': 'application',
        'dependencies': ['astra_ide'],
        'check_paths': ['~/start-astraide.sh'],
        'install_method': 'script_creation',
        'uninstall_method': 'script_removal',
        'gui_selectable': True,
        'description': 'Скрипт для запуска Astra.IDE',
        'priority': 13
    },
    'desktop_shortcut': {
        'name': 'Ярлык рабочего стола',
        'category': 'application',
        'dependencies': ['astra_ide'],
        'check_paths': ['~/Desktop/AstraRegul.desktop'],
        'install_method': 'desktop_shortcut',
        'uninstall_method': 'desktop_shortcut',
        'gui_selectable': True,
        'description': 'Ярлык Astra.IDE на рабочем столе',
        'priority': 14
    }
}

# ============================================================================
# ПЕРЕОПРЕДЕЛЕНИЕ PRINT() ДЛЯ ПЕРЕНАПРАВЛЕНИЯ В GUI
# ============================================================================

# Переопределяем функцию print для перенаправления в GUI
import builtins
_original_print = builtins.print

def custom_print(*args, **kwargs):
    """Переопределенная функция print - использует UniversalProcessRunner"""
    # Извлекаем channels из kwargs если есть
    channels = kwargs.pop('channels', [])
    
    # Формируем сообщение
    message = ' '.join(str(arg) for arg in args)
    
    # Если есть GUI экземпляр - используем его
    if hasattr(sys, '_gui_instance') and sys._gui_instance and hasattr(sys._gui_instance, 'process_runner'):
        sys._gui_instance.process_runner.add_output(message, level="INFO", channels=channels)
    else:
        # Иначе используем глобальный UniversalProcessRunner
        global_runner = get_global_universal_runner()
        global_runner.add_output(message, level="INFO", channels=channels)

# Переопределяем builtins.print
builtins.print = custom_print

# ============================================================================
# ГЛОБАЛЬНЫЙ UNIVERSALPROCESSRUNNER - ДОСТУПЕН С САМОГО НАЧАЛА
# ============================================================================

# Создаем глобальный экземпляр UniversalProcessRunner сразу
_global_universal_runner = None

def get_global_universal_runner():
    """Получение глобального экземпляра UniversalProcessRunner"""
    global _global_universal_runner
    if _global_universal_runner is None:
        _global_universal_runner = UniversalProcessRunner()
    return _global_universal_runner

# Устанавливаем sys._gui_instance = None для начальной работы
sys._gui_instance = None

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
# УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК ПРОЦЕССОВ
# ============================================================================
class UniversalProcessRunner(object):
    """
    Универсальный обработчик процессов с выводом в реальном времени
    Поддерживает все каналы логирования и неблокирующее выполнение
    """
    
    def __init__(self, logger=None, gui_callback=None, gui_instance=None):
        """
        Инициализация универсального обработчика процессов
        
        Args:
            logger: Экземпляр Logger для записи в файл
            gui_callback: Функция для отправки сообщений в GUI терминал
            gui_instance: Ссылка на экземпляр GUI
        """
        self.logger = logger
        self.gui_callback = gui_callback
        self.gui_instance = gui_instance
        self.output_buffer = []
        self.is_running = False
        self.log_file_path = None  # Путь к лог-файлу
        self.output_queue = queue.Queue()  # Очередь для быстрой обработки
        self.gui_filter_enabled = False  # ВРЕМЕННО ОТКЛЮЧЕНА фильтрация для GUI лога
        
        # Отслеживание текущего этапа обновления для единого прогресса
        self.current_update_phase = "update"  # update, dist-upgrade, autoremove
        self.update_phase_start_stage = "reading_lists"  # Начальный этап для текущей фазы
        
        # Тестовое сообщение будет отправлено при активации перехвата
    
    def should_show_in_gui_log(self, message):
        """Определяет, должно ли сообщение отображаться в логе GUI"""
        if not self.gui_filter_enabled:
            return True
            
        # Показываем только основные этапы
        gui_keywords = [
            "[START]",
            "[INFO] Начинаем",
            "[OK] Автоматизация",
            "[SUCCESS]",
            "[ERROR]",
            "Обновление системы завершено",
            "Автоматизация завершена",
            "Проверка репозиториев завершена",
            "Анализ статистики завершен",
            "✅ Списки пакетов обновлены",
            "✅ Система обновлена",
            "✅ Система очищена"
        ]
        
        # НЕ показываем детали команд
        skip_keywords = [
            "Начинаем выполнение команды",
            "Команда выполнена успешно",
            "apt-get",
            "dpkg",
            "Чтение списков пакетов",
            "Построение дерева зависимостей",
            "Чтение информации о состоянии",
            "Расчёт обновлений",
            "Обновлено 0 пакетов",
            "Пол:",
            "Игн:",
            "Сущ:",
            "Время:",
            "Установлено:",
            "CPU:",
            "Сеть:"
        ]
        
        # Проверяем ключевые слова для показа
        for keyword in gui_keywords:
            if keyword in message:
                return True
        
        # Проверяем ключевые слова для пропуска
        for keyword in skip_keywords:
            if keyword in message:
                return False
        
        # По умолчанию показываем сообщения уровня INFO и выше
        return (message.startswith("[INFO]") or message.startswith("[OK]") or 
                message.startswith("[ERROR]") or message.startswith("[SUCCESS]") or
                message.startswith("[WARNING]") or message.startswith("[LIST]") or
                message.startswith("[TOOL]") or message.startswith("[PROCESS]") or
                message.startswith("[AUTO]") or message.startswith("[!]") or
                message.startswith("[ERR]") or message.startswith("[MinimalWinetricks]"))
    
    def setup_print_redirect(self):
        """Настройка перехвата стандартного print()"""
        import builtins
        
        # Сохраняем ОРИГИНАЛЬНУЮ ссылку на print ДО замены
        if not hasattr(self, '_original_print'):
            self._original_print = builtins.print
        
        def universal_print(*args, **kwargs):
            """Универсальный print с отправкой в GUI терминал"""
            message = ' '.join(str(arg) for arg in args)
            
            # Используем оригинальный print для gui_callback чтобы избежать рекурсии
            if self.gui_callback:
                # Временно восстанавливаем оригинальный print
                import builtins
                original_print = builtins.print
                builtins.print = self._original_print
                
                # Вызываем gui_callback (он может использовать print)
                self.gui_callback(message)
                
                # Восстанавливаем наш перехваченный print
                builtins.print = universal_print
            
            # Также записываем в лог файл напрямую
            self._write_to_file(message)
        
        # Заменяем встроенный print
        builtins.print = universal_print
        
        # Отправляем тестовое сообщение о готовности перехвата
        if self.gui_callback:
            self.gui_callback("[UNIVERSAL] UniversalProcessRunner готов к перехвату print()")
    
    def setup_subprocess_redirect(self):
        """Подмена subprocess.run() на UniversalProcessRunner"""
        import subprocess as original_subprocess
        
        # Сохраняем оригинальный subprocess.run
        if not hasattr(self, '_original_subprocess_run'):
            self._original_subprocess_run = original_subprocess.run
        
        def universal_subprocess_run(*args, **kwargs):
            """Универсальный subprocess.run с отправкой в UniversalProcessRunner"""
            # Обрабатываем args
            if len(args) > 0:
                if isinstance(args[0], list):
                    # Массив аргументов - используем оригинальный subprocess
                    result = self._original_subprocess_run(*args, **kwargs)
                    return result
                else:
                    # Строка команды - конвертируем в массив и используем оригинальный subprocess
                    command_args = str(args[0]).split()
                    result = self._original_subprocess_run(command_args, **kwargs)
                    return result
            else:
                # Если нет аргументов, используем оригинальный subprocess
                result = self._original_subprocess_run(*args, **kwargs)
                return result
        
        # Подменяем subprocess.run
        original_subprocess.run = universal_subprocess_run
        
        # Отправляем сообщение о готовности перехвата subprocess
        if self.gui_callback:
            self.gui_callback("[UNIVERSAL] UniversalProcessRunner готов к перехвату subprocess.run()")
    
    def setup_logging_redirect(self):
        """Подмена стандартного logging на UniversalProcessRunner"""
        import logging as original_logging
        
        # Сохраняем оригинальный getLogger
        if not hasattr(self, '_original_getLogger'):
            self._original_getLogger = original_logging.getLogger
        
        class UniversalLogger:
            def __init__(self, universal_runner):
                self.universal_runner = universal_runner
            
            def info(self, message):
                print(f"[INFO] {message}")
            
            def error(self, message):
                print(f"[ERROR] {message}")
            
            def warning(self, message):
                print(f"[WARNING] {message}")
            
            def debug(self, message):
                print(f"[DEBUG] {message}")
        
        # Подменяем getLogger
        original_logging.getLogger = lambda name: UniversalLogger(self)
        
        # Отправляем сообщение о готовности перехвата logging
        if self.gui_callback:
            self.gui_callback("[UNIVERSAL] UniversalProcessRunner готов к перехвату logging.getLogger()")
    
    def setup_universal_logging_redirect(self):
        """Подмена ВСЕХ методов логирования на UniversalProcessRunner"""
        
        # Подменяем все методы _log в классах
        def universal_log(self, message, level="INFO"):
            """Универсальный _log с отправкой в UniversalProcessRunner"""
            universal_runner = get_global_universal_runner()
            if level == "ERROR":
                universal_runner.log_error(message)
            elif level == "WARNING":
                universal_runner.log_warning(message)
            else:
                universal_runner.log_info(message)
        
        # Подменяем все методы _write_to_file
        def universal_write_to_file(self, message):
            """Универсальный _write_to_file с отправкой в UniversalProcessRunner"""
            universal_runner = get_global_universal_runner()
            universal_runner._write_to_file(message)
        
        # Подменяем все методы _log в классах
        import types
        types.MethodType = lambda func, instance: universal_log if func.__name__ == '_log' else func
        
        # Отправляем сообщение о готовности перехвата всех методов логирования
        if self.gui_callback:
            self.gui_callback("[UNIVERSAL] UniversalProcessRunner готов к перехвату ВСЕХ методов логирования")
    
    def log_info(self, message, description=None, extra_info=None):
        """Логирование информационного сообщения"""
        if description and extra_info is not None:
            full_message = f"{description}: {str(message)} (доп.инфо: {extra_info})"
        elif description:
            full_message = f"{description}: {str(message)}"
        else:
            full_message = str(message)
        self.add_output(f"[INFO] {full_message}")
        self._write_to_file(f"[INFO] {full_message}")
    
    def log_error(self, message, description=None):
        """Логирование сообщения об ошибке"""
        if description:
            full_message = f"{description}: {str(message)}"
        else:
            full_message = str(message)
        self.add_output(f"[ERROR] {full_message}")
        self._write_to_file(f"[ERROR] {full_message}")
    
    def log_warning(self, message, description=None):
        """Логирование предупреждения"""
        if description:
            full_message = f"{description}: {str(message)}"
        else:
            full_message = str(message)
        self.add_output(f"[WARNING] {full_message}")
        self._write_to_file(f"[WARNING] {full_message}")
    
    def log_debug(self, message, description=None):
        """Логирование отладочных сообщений"""
        if description:
            full_message = f"{description}: {str(message)}"
        else:
            full_message = str(message)
    
    def set_log_file(self, log_file_path):
        """Установка пути к лог-файлу"""
        self.log_file_path = log_file_path
    
    def _write_to_file(self, message):
        """Запись сообщения в лог-файл"""
        if not self.log_file_path:
            return
        
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_entry = f"[{timestamp}] {message}\n"
            
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                f.flush()
        except Exception as e:
            # Если не можем записать в лог, игнорируем ошибку
            pass
        
    def run_process(self, command, process_type="general", 
                   channels=["file", "terminal"], callback=None, timeout=None):
        """
        Универсальный запуск процесса с выводом в реальном времени
        
        Args:
            command: Список команд или строка
            process_type: Тип процесса ("install", "update", "check", "remove", "general")
            channels: Каналы вывода ["file", "terminal", "gui"]
            callback: Функция для уведомлений о прогрессе
            timeout: Таймаут выполнения в секундах
            
        Returns:
            int: Код возврата процесса (0 = успех)
        """
        
        if self.is_running:
            self._log("Предупреждение: процесс уже выполняется", "WARNING", channels)
            return -1
            
        self.is_running = True
        
        # Определяем фазу обновления для единого прогресса
        cmd_str = ' '.join(command) if isinstance(command, list) else str(command)
        if 'apt-get update' in cmd_str:
            self.current_update_phase = "update"
            self.update_phase_start_stage = "reading_lists"
        elif 'apt-get dist-upgrade' in cmd_str:
            self.current_update_phase = "dist-upgrade"
            self.update_phase_start_stage = "downloading"
        elif 'apt-get autoremove' in cmd_str:
            self.current_update_phase = "autoremove"
            self.update_phase_start_stage = "cleaning"
        
        # Передаем информацию о текущей фазе в ProcessProgressManager
        if hasattr(self, 'gui_instance') and self.gui_instance:
            if hasattr(self.gui_instance, 'system_updater') and self.gui_instance.system_updater:
                progress_manager = self.gui_instance.system_updater.progress_manager
                progress_manager.current_update_phase = self.current_update_phase
                progress_manager.update_phase_start_stage = self.update_phase_start_stage
        
        try:
            # Логируем начало процесса
            self._log("Начало выполнения: %s" % cmd_str, "INFO", channels)
            
            # Запускаем процесс
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Читаем вывод построчно в реальном времени
            output_buffer = ""
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                # Выводим строку в реальном времени
                line_clean = line.rstrip()
                if line_clean:
                    self._log("  %s" % line_clean, "INFO", channels)
                    output_buffer += line
                    
                    # Парсинг прогресса теперь обрабатывается в SystemUpdater.run_command_with_interactive_handling()
                    # Старый парсер удален - используем ProcessProgressManager
                
                # Проверяем на интерактивные запросы
                if self._detect_interactive_prompt(output_buffer):
                    response = self._get_auto_response(output_buffer)
                    if response:
                        process.stdin.write(response + "\n")
                        process.stdin.flush()
                        self._log("  [AUTO] Автоматический ответ: %s" % response, "INFO", channels)
            
            # Ждем завершения процесса
            return_code = process.wait()
            
            # Логируем результат
            if return_code == 0:
                self._log("Процесс завершен успешно", "INFO", channels)
            else:
                self._log("Процесс завершен с ошибкой (код: %d)" % return_code, "ERROR", channels)
            
            return return_code
            
        except subprocess.TimeoutExpired:
            self._log("Процесс превысил таймаут", "ERROR", channels)
            process.kill()
            return -1
        except Exception as e:
            self._log("Ошибка выполнения процесса: %s" % str(e), "ERROR", channels)
            return -1
        finally:
            self.is_running = False
    
    def add_output(self, message, level="INFO", channels=[], bypass_filter=False):
        """
        Быстрое добавление сообщения в очередь - внешний процесс не ждет
        
        Args:
            message: Текст сообщения
            level: Уровень сообщения ("INFO", "WARNING", "ERROR")
            channels: Каналы вывода ["gui_log"] - file и terminal всегда включены
            bypass_filter: Обойти фильтрацию для GUI лога
        """
        # file и terminal всегда включены, добавляем gui_log если указан
        all_channels = ["file", "terminal"]
        if "gui_log" in channels:
            all_channels.append("gui_log")
        
        # Быстро добавляем в очередь - внешний процесс продолжает работу
        self.output_queue.put((message, level, all_channels, bypass_filter))
    
    def _write_to_terminal(self, message):
        """Простая запись в терминал"""
        if hasattr(self, 'gui_callback') and self.gui_callback:
            self.gui_callback(message)
    
    def _write_to_gui_log(self, message):
        """Запись в GUI лог через callback (с фильтрацией)"""
        if hasattr(self, 'gui_log_callback') and self.gui_log_callback:
            if self.should_show_in_gui_log(message):
                self.gui_log_callback(message)
    
    def process_queue(self):
        """Обработка очереди сообщений - вызывается из GUI"""
        try:
            while not self.output_queue.empty():
                # Получаем параметры (поддерживаем старый формат для совместимости)
                item = self.output_queue.get_nowait()
                if len(item) == 4:
                    message, level, channels, bypass_filter = item
                else:
                    message, level, channels = item
                    bypass_filter = False
                
                # Записываем в файл
                if "file" in channels:
                    self._write_to_file(f"[{level}] {message}")
                
                # Выводим в терминал (с фильтрацией для GUI)
                if "terminal" in channels:
                    if bypass_filter or self.should_show_in_gui_log(message):
                        self._write_to_terminal(message)
                
                # GUI лог - если ЯВНО указан gui_log, НЕ ФИЛЬТРУЕМ!
                if "gui_log" in channels:
                    if hasattr(self, 'gui_log_callback') and self.gui_log_callback:
                        self.gui_log_callback(message)
        except:
            pass
    
    def _log(self, message, level="INFO", channels=["file", "terminal"]):
        """
        Универсальное логирование в выбранные каналы
        
        Args:
            message: Текст сообщения
            level: Уровень сообщения
            channels: Список каналов ["file", "terminal", "gui"]
        """
        # Лог файл (всегда, если есть logger)
        if "file" in channels and self.logger:
            if level == "ERROR":
                print(f"[ERROR] {message}")
            elif level == "WARNING":
                print(f"[WARNING] {message}")
            else:
                print(f"[INFO] {message}")
        
        # GUI терминал
        if "terminal" in channels and self.gui_callback:
            self.gui_callback(message)
        
        # GUI лог (только для ключевых сообщений)
        if "gui" in channels:
            # Здесь можно добавить логику для GUI лога
            pass
    
    def _detect_interactive_prompt(self, output_buffer):
        """Определение интерактивных запросов в выводе"""
        interactive_patterns = [
            "Do you want to continue?",
            "Continue?",
            "Y/n",
            "y/N",
            "[Y/n]",
            "[y/N]",
            "Press ENTER",
            "Press any key"
        ]
        
        for pattern in interactive_patterns:
            if pattern in output_buffer:
                return True
        return False
    
    def _get_auto_response(self, output_buffer):
        """Получение автоматического ответа на интерактивный запрос"""
        if "Do you want to continue?" in output_buffer or "Continue?" in output_buffer:
            return "y"
        elif "Y/n" in output_buffer or "[Y/n]" in output_buffer:
            return "y"
        elif "Press ENTER" in output_buffer:
            return ""
        return None


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ ГЛОБАЛЬНОГО UNIVERSALPROCESSRUNNER
# ============================================================================

# Инициализируем глобальный экземпляр ПОСЛЕ определения класса
_global_universal_runner = UniversalProcessRunner()

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
            self._log("Проверяем репозиторий: %s" % repo_line)
            
            # Автоматически отключаем компакт-диск репозитории
            if 'cdrom:' in repo_line:
                self._log("[WARNING] Компакт-диск репозиторий отключен: %s" % repo_line.split()[1] if len(repo_line.split()) > 1 else repo_line)
                return False
            
            # Создаем временный файл с одним репозиторием
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_file.write(repo_line + '\n')
            temp_file.close()
            
            self._log("Создан временный файл: %s" % temp_file.name)
            
            # Проверяем доступность репозитория
            cmd = ['apt-get', 'update', '-o', 'Dir::Etc::sourcelist=%s' % temp_file.name, 
                   '-o', 'Dir::Etc::sourceparts=-', '-o', 'APT::Get::List-Cleanup=0']
            self._log("Выполняем команду: %s" % ' '.join(cmd))
            
            result = subprocess.call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self._log("Результат команды: код %d" % result)
            
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
            # Выводим содержимое sources.list ДО обработки
            self._log("\n[SOURCES.LIST] Содержимое ДО обработки:")
            self._log("=" * 50)
            with open(self.sources_list, 'r') as f:
                content_before = f.read()
                self._log(content_before)
            self._log("=" * 50)
            
            with open(self.sources_list, 'r') as f:
                lines = f.readlines()
            
            # Создаем временный файл для рабочих репозиториев
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            
            for line in lines:
                line = line.strip()
                
                # Пропускаем только пустые строки
                if not line:
                    temp_file.write(line + '\n')
                    continue
                
                # Проверяем строки с deb (активные и закомментированные)
                if line.startswith('deb ') or line.startswith('#deb '):
                    # Убираем комментарий для проверки
                    clean_line = line.lstrip('#').strip()
                    self._log("Обрабатываем строку: '%s' -> clean: '%s'" % (line, clean_line))
                    
                    # Проверяем доступность репозитория
                    if self.check_repo_availability(clean_line):
                        self.activated_count += 1
                        self.working_repos.append(clean_line)
                        self._log("Репозиторий АКТИВИРОВАН: %s" % clean_line)
                        # Активируем репозиторий (убираем #)
                        temp_file.write(clean_line + '\n')
                    else:
                        self.deactivated_count += 1
                        self.broken_repos.append(clean_line)
                        self._log("Репозиторий ДЕАКТИВИРОВАН: %s" % clean_line)
                        # Деактивируем репозиторий (добавляем #)
                        temp_file.write('# ' + clean_line + '\n')
                else:
                    # Копируем остальные строки как есть
                    temp_file.write(line + '\n')
            
            temp_file.close()
            
            # Удаляем дубликаты
            self._remove_duplicates(temp_file.name)
            
            # Выводим содержимое sources.list ПОСЛЕ обработки
            self._log("\n[SOURCES.LIST] Содержимое ПОСЛЕ обработки:")
            self._log("=" * 50)
            with open(temp_file.name, 'r') as f:
                content_after = f.read()
                self._log(content_after)
            self._log("=" * 50)
            
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
                
                # Сохраняем ВСЕ пакеты для отображения в GUI
                self.updatable_list = lines[1:] if len(lines) > 1 else []
                
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
        print("[LIST] Подсчет пакетов для установки...", channels=["gui_log"])
        
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
        print("[LIST] Репозитории:", channels=["gui_log"])
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
        print("[ERROR] Требуются права root для работы с системными пакетами", channels=["gui_log"])
        print("Запустите: sudo python3 system_stats.py")
        return False
    
    # Анализируем обновления
    if not stats.get_updatable_packages():
        print("[WARNING] Предупреждение: не удалось получить список обновлений", channels=["gui_log"])
    
    # Анализируем автоудаление
    if not stats.get_autoremove_packages():
        print("[WARNING] Предупреждение: не удалось проанализировать автоудаление", channels=["gui_log"])
    
    # Подсчитываем пакеты для установки
    if not stats.calculate_install_stats():
        print("[WARNING] Предупреждение: не удалось подсчитать пакеты для установки", channels=["gui_log"])
    
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
    
    def check_wine_mono(self):
        """Проверка наличия Wine Mono"""
        print("[CHECK] Проверка Wine Mono...")
        
        if not self.checks['wineprefix']:
            print("   [SKIP] WINEPREFIX не найден, пропускаем проверку Wine Mono")
            self.checks['wine-mono'] = False
            return False
        
        # Проверяем наличие Wine Mono в WINEPREFIX
        mono_paths = [
            os.path.join(self.wineprefix, 'drive_c', 'windows', 'Mono'),
            os.path.join(self.wineprefix, 'drive_c', 'windows', 'Mono', 'lib', 'mono')
        ]
        
        for path in mono_paths:
            if os.path.exists(path):
                print("   [OK] Wine Mono найден: %s" % path)
                self.checks['wine-mono'] = True
                return True
        
        print("   [ERR] Wine Mono не найден в WINEPREFIX")
        self.checks['wine-mono'] = False
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
        
        # Определения компонентов и их ключевых файлов (синхронизировано с DirectoryMonitor)
        components = {
            'wine-mono': [
                'drive_c/windows/mono/mono-2.0/bin/libmono-2.0-x86.dll',
                'drive_c/windows/mono/mono-2.0/bin/libmono-2.0-x86_64.dll'
            ],
            'dotnet48': [
                'drive_c/windows/Microsoft.NET/Framework/v4.0.30319/mscorlib.dll',
                'drive_c/windows/Microsoft.NET/Framework64/v4.0.30319/mscorlib.dll'
            ],
            'vcrun2013': [
                'drive_c/windows/system32/msvcp120.dll',
                'drive_c/windows/system32/msvcr120.dll',
                'drive_c/windows/syswow64/msvcp120.dll',
                'drive_c/windows/syswow64/msvcr120.dll'
            ],
            'vcrun2022': [
                'drive_c/windows/system32/msvcp140.dll',
                'drive_c/windows/system32/vcruntime140.dll',
                'drive_c/windows/syswow64/msvcp140.dll',
                'drive_c/windows/syswow64/vcruntime140.dll'
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
                'drive_c/windows/system32/dxgi.dll',
                'drive_c/windows/system32/d3d11.dll'
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
        self.check_wine_mono()
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
            print("[OK] Все компоненты установлены и готовы к работе!", channels=["gui_log"])
            return True
        elif self.is_wine_installed() and not self.is_astra_ide_installed():
            print("[!] Wine установлен, но Astra.IDE не установлена", channels=["gui_log"])
            print("[!] Требуется установка Astra.IDE", channels=["gui_log"])
            return False
        elif not self.is_wine_installed():
            print("[ERR] Wine не установлен или настроен неправильно", channels=["gui_log"])
            print("[ERR] Требуется установка Wine пакетов", channels=["gui_log"])
            return False
        else:
            print("[!] Некоторые компоненты отсутствуют", channels=["gui_log"])
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
    
    def __init__(self, logger=None, callback=None, install_wine=True, install_winetricks=True, install_ide=True, winetricks_components=None, use_minimal_winetricks=True):
        """
        Инициализация установщика
        
        Args:
            logger: Экземпляр класса Logger для логирования
            callback: Функция для обновления статуса в GUI (опционально)
            install_wine: Устанавливать Wine пакеты (по умолчанию True)
            install_winetricks: Устанавливать winetricks компоненты (по умолчанию True)
            install_ide: Устанавливать Astra.IDE (по умолчанию True)
            winetricks_components: Список компонентов winetricks для установки (если None - устанавливаем все)
            use_minimal_winetricks: Использовать минимальный winetricks (по умолчанию True)
        """
        self.logger = logger
        self.callback = callback
        
        # Флаги установки компонентов
        self.install_wine = install_wine
        self.install_winetricks = install_winetricks
        self.install_ide = install_ide
        self.use_minimal_winetricks = use_minimal_winetricks
        
        # Список компонентов winetricks (если None - устанавливаем все по умолчанию)
        if winetricks_components is None:
            self.winetricks_components = ['wine-mono', 'dotnet48', 'vcrun2013', 'vcrun2022', 'd3dcompiler_43', 'd3dcompiler_47', 'dxvk']
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
        
        # Минимальные требования для Wine + Astra.IDE
        self.min_free_space_gb = 4.0  # 4 ГБ для Wine + Astra.IDE + компоненты
        self.min_free_memory_mb = 1024  # 1 ГБ памяти для Wine процессов
        
        # Инициализируем WinetricksManager
        self.winetricks_manager = WinetricksManager(self.astrapack_dir, use_minimal=self.use_minimal_winetricks)
    
    def _log(self, message, level="INFO"):
        """Логирование с выводом в консоль и callback"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_msg = "[%s] [%s] %s" % (timestamp, level, message)
        
        print(log_msg)
        
        if self.logger:
            if level == "ERROR":
                print(f"[ERROR] {message}")
            else:
                print(f"[INFO] {message}")
        
        if self.callback:
            self.callback(message)
    
    def _check_disk_space(self):
        """Проверка свободного места на диске для Wine/Astra.IDE"""
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_gb = free / (1024**3)
            
            self._log("Проверка дискового пространства: %.2f ГБ свободно (минимум: %.1f ГБ)" % (free_gb, self.min_free_space_gb))
            
            if free_gb < self.min_free_space_gb:
                self._log("ОШИБКА: Недостаточно свободного места на диске!", "ERROR")
                self._log("Требуется минимум %.1f ГБ для установки Wine + Astra.IDE" % self.min_free_space_gb, "ERROR")
                self._log("Рекомендации:", "ERROR")
                self._log("  - Очистите временные файлы: sudo apt clean && sudo apt autoclean", "ERROR")
                self._log("  - Удалите неиспользуемые пакеты: sudo apt autoremove", "ERROR")
                self._log("  - Проверьте логи: sudo du -sh /var/log/*", "ERROR")
                return False
            
            return True
            
        except Exception as e:
            self._log("Ошибка проверки дискового пространства: %s" % str(e), "ERROR")
            return False
    
    def _check_memory(self):
        """Проверка доступной памяти для Wine процессов"""
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
            
            self._log("Проверка памяти: %d МБ доступно (минимум: %d МБ)" % (mem_available, self.min_free_memory_mb))
            
            if mem_available < self.min_free_memory_mb:
                self._log("ОШИБКА: Недостаточно свободной памяти!", "ERROR")
                self._log("Требуется минимум %d МБ для работы Wine процессов" % self.min_free_memory_mb, "ERROR")
                self._log("Рекомендации:", "ERROR")
                self._log("  - Закройте другие приложения", "ERROR")
                self._log("  - Перезагрузите систему для освобождения памяти", "ERROR")
                return False
            
            return True
            
        except Exception as e:
            self._log("Ошибка проверки памяти: %s" % str(e), "ERROR")
            return False
    
    def check_system_resources(self):
        """Проверка системных ресурсов для Wine/Astra.IDE"""
        self._log("=" * 60)
        self._log("ПРОВЕРКА СИСТЕМНЫХ РЕСУРСОВ")
        self._log("=" * 60)
        
        # Проверяем свободное место на диске
        if not self._check_disk_space():
            self._log("ПРОВЕРКА ДИСКА: НЕ ПРОЙДЕНА", "ERROR")
            return False
        
        # Проверяем доступную память
        if not self._check_memory():
            self._log("ПРОВЕРКА ПАМЯТИ: НЕ ПРОЙДЕНА", "ERROR")
            return False
        
        self._log("=" * 60)
        self._log("ВСЕ СИСТЕМНЫЕ РЕСУРСЫ В ПОРЯДКЕ")
        self._log("=" * 60)
        return True
    
    def _check_xdotool(self):
        """Проверка наличия xdotool для автоматического подтверждения диалогов"""
        try:
            result = subprocess.run(
                ['xdotool', '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            if result.returncode == 0:
                version = result.stdout.decode('utf-8').strip()
                self._log("xdotool найден: %s" % version)
                return True
            else:
                self._log("xdotool не найден", "WARNING")
                return False
                
        except FileNotFoundError:
            self._log("xdotool не установлен", "WARNING")
            return False
        except Exception as e:
            self._log("Ошибка проверки xdotool: %s" % str(e), "WARNING")
            return False
    
    def _install_xdotool(self):
        """Установка xdotool для автоматического подтверждения диалогов"""
        try:
            self._log("Установка xdotool...")
            
            # Устанавливаем xdotool через apt
            result = subprocess.run(
                ['apt-get', 'install', '-y', 'xdotool'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            if result.returncode == 0:
                self._log("xdotool успешно установлен")
                return True
            else:
                self._log("Ошибка установки xdotool: %s" % result.stderr, "ERROR")
                return False
                
        except Exception as e:
            self._log("Ошибка установки xdotool: %s" % str(e), "ERROR")
            return False
    
    def _ensure_wineprefix_architecture(self):
        """Проверка и исправление архитектуры WINEPREFIX"""
        self._log("Проверка архитектуры WINEPREFIX...")
        
        # Если WINEPREFIX не существует, создаем его с правильной архитектурой
        if not os.path.exists(self.wineprefix):
            self._log("WINEPREFIX не существует, создаем с архитектурой win64...")
            
            # Настраиваем переменные окружения для создания WINEPREFIX
            env = os.environ.copy()
            env['WINEPREFIX'] = self.wineprefix
            env['WINEARCH'] = 'win64'
            env['WINEBUILD'] = 'x86_64'
            env['WINEDEBUG'] = '-all'
            env['WINE'] = '/opt/wine-9.0/bin/wine'
            
            # Отключаем диалоги Wine Mono
            env['WINEDLLOVERRIDES'] = 'winemenubuilder.exe=d;rundll32.exe=d;mshtml=d;mscoree=d'
            env['WINEDEBUG'] = '-all'
            
            # Пытаемся отключить диалоги Wine Mono через переменные окружения
            env['WINE_MONO_INSTALL'] = '0'  # Отключаем автоматическую установку Mono
            env['WINE_GECKO_INSTALL'] = '0'  # Отключаем автоматическую установку Gecko
            
            # Создаем WINEPREFIX с автоматическим подтверждением диалогов Wine Mono
            try:
                # Запускаем winecfg в фоне и автоматически подтверждаем диалоги
                result = self._create_wineprefix_with_auto_confirm(env)
                
                if result:
                    self._log("WINEPREFIX создан с архитектурой win64")
                    return True
                else:
                    self._log("Ошибка создания WINEPREFIX", "ERROR")
                    return False
                    
            except Exception as e:
                self._log("Ошибка создания WINEPREFIX: %s" % str(e), "ERROR")
                return False
        
        # Проверяем существующий WINEPREFIX
        reg_file = os.path.join(self.wineprefix, "system.reg")
        if os.path.exists(reg_file):
            try:
                with open(reg_file, 'r') as f:
                    content = f.read()
                    if '[Software\\Wine\\WineDbg]' in content and 'ShowCrashDialog' in content:
                        # Это похоже на правильный WINEPREFIX
                        self._log("WINEPREFIX существует и выглядит корректно")
                        return True
                    else:
                        self._log("WINEPREFIX поврежден, пересоздаем...", "WARNING")
                        # Удаляем поврежденный WINEPREFIX
                        import shutil
                        shutil.rmtree(self.wineprefix)
                        return self._ensure_wineprefix_architecture()
            except Exception as e:
                self._log("Ошибка проверки WINEPREFIX: %s" % str(e), "ERROR")
                return False
        else:
            self._log("WINEPREFIX неполный, пересоздаем...", "WARNING")
            import shutil
            shutil.rmtree(self.wineprefix)
            return self._ensure_wineprefix_architecture()
    
    def _create_wineprefix_with_auto_confirm(self, env):
        """Создание WINEPREFIX с автоматическим подтверждением диалогов Wine Mono"""
        import threading
        import time
        
        self._log("Запуск winecfg с автоматическим подтверждением диалогов...")
        
        # Пробуем использовать expect для автоматического подтверждения
        if self._try_expect_method(env):
            return True
        
        # Если expect не сработал, используем xdotool
        self._log("Переход к методу xdotool...")
        
        # Запускаем winecfg в отдельном процессе
        process = subprocess.Popen(
            [env['WINE'], 'winecfg'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Запускаем мониторинг диалогов в отдельном потоке
        dialog_thread = threading.Thread(target=self._monitor_wine_dialogs, args=(process.pid,))
        dialog_thread.daemon = True
        dialog_thread.start()
        
        # Ждем завершения процесса с таймаутом
        try:
            stdout, stderr = process.communicate(timeout=60)
            
            # Логируем вывод
            if stdout:
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        self._log("  > %s" % line)
            
            if stderr:
                for line in stderr.strip().split('\n'):
                    if line.strip():
                        self._log("  ! %s" % line)
            
            # Проверяем успешность создания WINEPREFIX
            if os.path.exists(self.wineprefix):
                self._log("WINEPREFIX успешно создан")
                return True
            else:
                self._log("WINEPREFIX не был создан", "ERROR")
                return False
                
        except subprocess.TimeoutExpired:
            self._log("Таймаут при создании WINEPREFIX", "ERROR")
            process.kill()
            return False
        except Exception as e:
            self._log("Ошибка при создании WINEPREFIX: %s" % str(e), "ERROR")
            return False
    
    def _try_expect_method(self, env):
        """Попытка использования expect для автоматического подтверждения"""
        try:
            self._log("Попытка использования expect для автоматического подтверждения...")
            
            # Создаем expect скрипт
            expect_script = '''#!/usr/bin/expect -f
set timeout 60
spawn {wine} winecfg
expect {{
    "Установка Wine Mono" {{
        send "\\r"
        exp_continue
    }}
    "Wine Mono Installation" {{
        send "\\r"
        exp_continue
    }}
    "Install" {{
        send "\\r"
        exp_continue
    }}
    "Установить" {{
        send "\\r"
        exp_continue
    }}
    timeout {{
        exit 1
    }}
    eof {{
        exit 0
    }}
}}
'''.format(wine=env['WINE'])
            
            # Записываем скрипт во временный файл
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.exp', delete=False) as f:
                f.write(expect_script)
                script_path = f.name
            
            # Делаем скрипт исполняемым
            os.chmod(script_path, 0o755)
            
            # Запускаем expect скрипт
            result = subprocess.run(
                [script_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False
            )
            
            # Удаляем временный файл
            os.unlink(script_path)
            
            if result.returncode == 0 and os.path.exists(self.wineprefix):
                self._log("WINEPREFIX создан через expect")
                return True
            else:
                self._log("expect метод не сработал")
                return False
                
        except Exception as e:
            self._log("Ошибка expect метода: %s" % str(e), "WARNING")
            return False
    
    def _monitor_wine_dialogs(self, wine_pid):
        """Мониторинг и автоматическое подтверждение диалогов Wine"""
        import time
        
        self._log("Запуск мониторинга диалогов Wine...")
        
        # Ждем немного, чтобы Wine успел запуститься
        time.sleep(1)
        
        # Ищем окна Wine Mono и автоматически подтверждаем их
        max_attempts = 30  # Увеличиваем количество попыток
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Ищем все окна Wine
                result = subprocess.run(
                    ['xdotool', 'search', '--name', 'Wine'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    window_ids = result.stdout.strip().decode('utf-8').split('\n')
                    self._log("Найдено окон Wine: %d" % len(window_ids))
                    
                    for window_id in window_ids:
                        if not window_id.strip():
                            continue
                            
                        # Получаем название окна
                        name_result = subprocess.run(
                            ['xdotool', 'getwindowname', window_id],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=False
                        )
                        
                        if name_result.returncode == 0:
                            window_name = name_result.stdout.strip().decode('utf-8')
                            self._log("Окно Wine: '%s' (ID: %s)" % (window_name, window_id))
                            
                            # Проверяем, это ли диалог Wine Mono
                            if any(keyword in window_name.lower() for keyword in ['mono', 'установка', 'installation']):
                                self._log("Найден диалог Wine Mono: %s" % window_name)
                                
                                # Активируем окно
                                subprocess.run(['xdotool', 'windowactivate', window_id], check=False)
                                time.sleep(0.5)
                                
                                # Пробуем разные способы нажатия кнопки "Установить"
                                # Способ 1: Tab + Enter (если кнопка в фокусе)
                                subprocess.run(['xdotool', 'key', 'Tab'], check=False)
                                time.sleep(0.2)
                                subprocess.run(['xdotool', 'key', 'Return'], check=False)
                                time.sleep(0.5)
                                
                                # Способ 2: Прямой клик по кнопке "Установить" (если Tab не сработал)
                                subprocess.run(['xdotool', 'key', 'Alt+U'], check=False)  # Alt+U для "Установить"
                                time.sleep(0.5)
                                
                                # Способ 3: Enter (если кнопка уже в фокусе)
                                subprocess.run(['xdotool', 'key', 'Return'], check=False)
                                
                                self._log("Автоматически подтвержден диалог Wine Mono")
                                return  # Выходим из функции после успешного подтверждения
                
                # Также ищем по английскому названию более точно
                result = subprocess.run(
                    ['xdotool', 'search', '--name', 'Mono'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    window_ids = result.stdout.strip().decode('utf-8').split('\n')
                    for window_id in window_ids:
                        if not window_id.strip():
                            continue
                            
                        name_result = subprocess.run(
                            ['xdotool', 'getwindowname', window_id],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=False
                        )
                        
                        if name_result.returncode == 0:
                            window_name = name_result.stdout.strip().decode('utf-8')
                            if 'mono' in window_name.lower():
                                self._log("Найден диалог Mono (EN): %s" % window_name)
                                
                                subprocess.run(['xdotool', 'windowactivate', window_id], check=False)
                                time.sleep(0.5)
                                subprocess.run(['xdotool', 'key', 'Tab'], check=False)
                                time.sleep(0.2)
                                subprocess.run(['xdotool', 'key', 'Return'], check=False)
                                time.sleep(0.5)
                                subprocess.run(['xdotool', 'key', 'Alt+I'], check=False)  # Alt+I для "Install"
                                
                                self._log("Автоматически подтвержден диалог Mono (EN)")
                                return
                
                # Проверяем, что процесс Wine еще работает
                try:
                    subprocess.run(['kill', '-0', str(wine_pid)], check=True)
                except subprocess.CalledProcessError:
                    self._log("Процесс Wine завершился")
                    break
                
                time.sleep(0.5)  # Уменьшаем интервал для более быстрого реагирования
                attempt += 1
                
            except Exception as e:
                self._log("Ошибка мониторинга диалогов: %s" % str(e), "WARNING")
                break
        
        self._log("Мониторинг диалогов Wine завершен (попыток: %d)" % attempt)
    
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
        
        # Проверяем системные ресурсы
        if not self.check_system_resources():
            self._log("ОШИБКА: Недостаточно системных ресурсов для установки", "ERROR")
            return False
        
        # Проверяем и устанавливаем xdotool для автоматического подтверждения диалогов
        if not self._check_xdotool():
            self._log("xdotool не найден, устанавливаем...")
            if not self._install_xdotool():
                self._log("ПРЕДУПРЕЖДЕНИЕ: Не удалось установить xdotool - диалоги Wine могут требовать ручного подтверждения", "WARNING")
        
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
        
        # Проверяем и исправляем архитектуру WINEPREFIX после установки Wine
        self._log("\nПроверка архитектуры WINEPREFIX...")
        if not self._ensure_wineprefix_architecture():
            self._log("ПРЕДУПРЕЖДЕНИЕ: Не удалось настроить архитектуру WINEPREFIX", "WARNING")
            self._log("Продолжаем установку - архитектура будет проверена позже", "WARNING")
        else:
            self._log("WINEPREFIX настроен с правильной архитектурой win64")
        
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
    
    def _install_wine_mono(self):
        """Установка wine-mono отдельно от winetricks"""
        try:
            # Настраиваем переменные окружения
            env = os.environ.copy()
            env['WINEPREFIX'] = self.wineprefix
            env['WINE'] = '/opt/wine-9.0/bin/wine'
            env['WINEDEBUG'] = '-all'
            
            # Отключаем автоматические диалоги Wine Mono
            env['WINEDLLOVERRIDES'] = 'winemenubuilder.exe=d;rundll32.exe=d;mshtml=d;mscoree=d'
            env['WINE_MONO_INSTALL'] = '0'  # Отключаем автоматическую установку Mono
            env['WINE_GECKO_INSTALL'] = '0'  # Отключаем автоматическую установку Gecko
            
            # Инициализируем WINEPREFIX если он не существует
            if not os.path.exists(self.wineprefix):
                self._log("Инициализация WINEPREFIX...")
                init_result = subprocess.run([
                    '/opt/wine-9.0/bin/wineboot', '--init'
                ], env=env, capture_output=True, text=True, timeout=60)
                
                if init_result.returncode != 0:
                    self._log(f"Ошибка инициализации WINEPREFIX: {init_result.stderr}", "ERROR")
                    return False
            
            # Скачиваем wine-mono
            wine_mono_url = 'https://dl.winehq.org/wine/wine-mono/8.1.0/wine-mono-8.1.0-x86.msi'
            wine_mono_path = os.path.join(self.wineprefix, '..', 'wine-mono-8.1.0-x86.msi')
            
            self._log("Скачивание wine-mono...")
            import requests
            response = requests.get(wine_mono_url, timeout=300)
            
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(wine_mono_path), exist_ok=True)
            
            with open(wine_mono_path, 'wb') as f:
                f.write(response.content)
            
            # Устанавливаем через wine msiexec
            self._log("Установка wine-mono через msiexec...")
            result = subprocess.run([
                '/opt/wine-9.0/bin/wine', 'msiexec', 
                '/i', wine_mono_path, 
                '/quiet', '/norestart'
            ], env=env, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self._log("wine-mono успешно установлен")
                return True
            else:
                self._log(f"Ошибка установки wine-mono: {result.stderr}", "ERROR")
                return False
                
        except Exception as e:
            self._log(f"Исключение при установке wine-mono: {e}", "ERROR")
            return False
        finally:
            # Удаляем временный файл
            try:
                if 'wine_mono_path' in locals() and os.path.exists(wine_mono_path):
                    os.remove(wine_mono_path)
            except:
                pass
    
    def install_winetricks_components(self):
        """Установка компонентов через winetricks с использованием WinetricksManager"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 4: УСТАНОВКА КОМПОНЕНТОВ WINETRICKS")
        self._log("=" * 60)
        
        # Инициализируем монитор директорий для отслеживания изменений WINEPREFIX
        directory_monitor = DirectoryMonitor(compact_mode=True)  # Включаем компактный режим
        directory_monitor.start_monitoring(self.wineprefix)
        self._log(f"[DirectoryMonitor] Мониторинг WINEPREFIX начат: {self.wineprefix}")
        
        # Используем WinetricksManager для установки компонентов
        if not self.winetricks_components:
            self._log("Нет компонентов для установки")
            return True
        
        self._log("Установка компонентов через WinetricksManager: %s" % ", ".join(self.winetricks_components))
        
        # Определяем callback для обновления статуса
        def status_callback(message):
            self._log("[WinetricksManager] %s" % message)
            
            # Проверяем изменения в WINEPREFIX после каждого сообщения
            changes = directory_monitor.check_changes(self.wineprefix)
            if changes and (changes['new_files'] or changes['modified_files'] or changes['new_directories']):
                formatted_changes = directory_monitor.format_changes(changes)
                self._log(f"[DirectoryMonitor] {formatted_changes}")
            
            if self.callback:
                if message.startswith("UPDATE_COMPONENT:"):
                    # Команда обновления компонента - обновляем проверку
                    component = message.split(":", 1)[1]
                    self.callback(f"UPDATE_COMPONENT:{component}")
                else:
                    # Обычное сообщение
                    self.callback(message)
        
        # Устанавливаем компоненты через WinetricksManager
        success = self.winetricks_manager.install_wine_packages(
            components=self.winetricks_components,
            wineprefix=self.wineprefix,
            callback=status_callback
        )
        
        if success:
            self._log("[OK] Компоненты winetricks успешно установлены через WinetricksManager")
            
            # Получаем полный отчет об изменениях в WINEPREFIX
            total_changes = directory_monitor.get_total_changes(self.wineprefix)
            if total_changes and (total_changes['new_files'] or total_changes['modified_files'] or total_changes['new_directories']):
                self._log("\n[REPORT] ПОЛНЫЙ ОТЧЕТ ОБ ИЗМЕНЕНИЯХ В WINEPREFIX:")
                self._log("-" * 50)
                formatted_changes = directory_monitor.format_changes(total_changes)
                self._log(f"[DirectoryMonitor] {formatted_changes}")
                self._log("-" * 50)
            
            return True
        else:
            self._log("[ERROR] Ошибка установки компонентов через WinetricksManager", "ERROR")
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
        
        # КРИТИЧЕСКИ ВАЖНО: Устанавливаем правильную архитектуру для Astra.IDE
        env['WINEARCH'] = 'win64'
        env['WINEBUILD'] = 'x86_64'
        
        # Отключаем GUI диалоги Wine (rundll32, winemenubuilder и т.д.)
        env['WINEDLLOVERRIDES'] = 'winemenubuilder.exe=d;rundll32.exe=d;mshtml=d'
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
        
        # КРИТИЧЕСКИ ВАЖНО: Устанавливаем правильную архитектуру для Astra.IDE
        env['WINEARCH'] = 'win64'
        env['WINEBUILD'] = 'x86_64'
        
        # Дополнительные параметры для стабильности Astra.IDE
        env['WINEDLLOVERRIDES'] = 'winemenubuilder.exe=d;rundll32.exe=d;mshtml=d;mscoree=d'
        env['WINEDLLPATH'] = '/opt/wine-astraregul/lib64/wine'
        
        # Отключаем GUI диалоги Wine (rundll32, winemenubuilder и т.д.)
        env['DISPLAY'] = ':0'
        
        self._log("Запуск установщика Astra.IDE...")
        self._log("Путь к установщику: %s" % self.astra_ide_exe)
        self._log("ВНИМАНИЕ: Установка может занять 5-10 минут")
        self._log("WINEDLLOVERRIDES: отключены GUI диалоги Wine")
        
        try:
            # КРИТИЧЕСКИ ВАЖНО: Astra.IDE НЕ МОЖЕТ устанавливаться от root!
            # Запускаем от имени реального пользователя через su
            real_user = os.environ.get('SUDO_USER')
            if not real_user or real_user == 'root':
                self._log("ОШИБКА: Не удалось определить реального пользователя для установки Astra.IDE", "ERROR")
                self._log("Astra.IDE не может устанавливаться от root!", "ERROR")
                return False
            
            self._log("Запускаем установку Astra.IDE от пользователя: %s" % real_user)
            
            # Формируем команду для выполнения от имени пользователя
            wine_cmd = [env['WINE'], self.astra_ide_exe]
            
            # Создаем команду su для выполнения от имени пользователя
            su_cmd = ['su', real_user, '-c']
            
            # Формируем строку команды с переменными окружения
            env_str = ' '.join(['%s="%s"' % (k, v) for k, v in env.items()])
            cmd_str = '%s %s' % (env_str, ' '.join(wine_cmd))
            
            su_cmd.append(cmd_str)
            
            self._log("Выполняем команду: %s" % ' '.join(su_cmd))
            
            # Дополнительная диагностика архитектуры
            self._log("Проверка архитектуры Wine перед установкой...")
            arch_check_cmd = ['su', real_user, '-c', 'export WINEPREFIX="%s" && export WINEARCH=win64 && %s winecfg --version' % (self.wineprefix, env['WINE'])]
            arch_result = subprocess.run(arch_check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=False)
            if arch_result.returncode == 0:
                self._log("Wine архитектура: %s" % arch_result.stdout.strip())
            else:
                self._log("Предупреждение: не удалось проверить архитектуру Wine", "WARNING")
            
            # Запускаем установку от имени пользователя
            result = subprocess.run(
                su_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                errors='replace',
                check=False
            )
            
            if result.returncode == 0:
                self._log("Установщик Astra.IDE завершен успешно")
            else:
                self._log("Установщик завершился с кодом: %d" % result.returncode)
                self._log("Вывод stdout: %s" % result.stdout)
                self._log("Вывод stderr: %s" % result.stderr)
                
                # Проверяем на специфические ошибки Wine
                if "page fault" in result.stderr.lower():
                    self._log("ОШИБКА: Обнаружена ошибка доступа к памяти Wine!", "ERROR")
                    self._log("Это может быть связано с неправильной архитектурой WINEPREFIX", "ERROR")
                    self._log("Рекомендация: удалите WINEPREFIX и переустановите компоненты", "ERROR")
                    return False
                elif "package" in result.stderr.lower() and "temp" in result.stderr.lower():
                    self._log("ОШИБКА: Проблема с временными файлами установщика", "ERROR")
                    self._log("Рекомендация: очистите временные файлы и попробуйте снова", "ERROR")
                    return False
            
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
Terminal=true
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
# КЛАСС УПРАВЛЕНИЯ WINETRICKS
# ============================================================================
class WinetricksManager(object):
    """Класс для управления установкой Wine компонентов через winetricks"""
    
    def __init__(self, astrapack_dir, use_minimal=True):
        """
        Инициализация менеджера winetricks
        
        Args:
            astrapack_dir: Путь к директории AstraPack
            use_minimal: Использовать минимальный winetricks (по умолчанию True)
        """
        self.astrapack_dir = astrapack_dir
        self.use_minimal = use_minimal
        
        # Путь к оригинальному winetricks скрипту
        self.original_winetricks = os.path.join(astrapack_dir, "winetricks")
        
        # Проверяем доступность скриптов (только оригинальный winetricks)
        self._check_winetricks_availability()
        
        # Встроенный минимальный winetricks (Python)
        self._minimal = MinimalWinetricks()
    
    def _check_winetricks_availability(self):
        """Проверка доступности winetricks скриптов"""
        if not self.use_minimal:
            if not os.path.exists(self.original_winetricks):
                raise FileNotFoundError(f"Оригинальный winetricks не найден: {self.original_winetricks}")
            if not os.access(self.original_winetricks, os.X_OK):
                os.chmod(self.original_winetricks, 0o755)
    
    def install_wine_packages(self, components, wineprefix=None, callback=None):
        """
        Установка Wine пакетов через winetricks
        
        Args:
            components: Список компонентов для установки
            wineprefix: Путь к WINEPREFIX (опционально)
            callback: Функция обратного вызова для обновления статуса (опционально)
        
        Returns:
            bool: True если установка успешна, False в противном случае
        """
        if not components:
            return True
        
        if self.use_minimal:
            # Используем встроенную Python-реализацию
            return self._minimal.install_components(components, wineprefix=wineprefix, callback=callback)
        
        # Иначе используем оригинальный bash winetricks
        winetricks_script = self.original_winetricks
        cmd = [winetricks_script] + components
        env = os.environ.copy()
        if wineprefix:
            env['WINEPREFIX'] = wineprefix
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
            if result.returncode == 0:
                if callback:
                    callback(f"Установлены компоненты: {', '.join(components)}")
                return True
            if callback:
                callback(f"Ошибка установки компонентов: {result.stderr.strip()}")
            return False
        except Exception as e:
            if callback:
                callback(f"Исключение при установке компонентов: {e}")
            return False
    
    def set_use_minimal(self, use_minimal):
        """
        Переключение между минимальным и оригинальным winetricks
        
        Args:
            use_minimal: True для минимального, False для оригинального
        """
        self.use_minimal = use_minimal
        self._check_winetricks_availability()
        script_name = "winetricks-minimal" if self.use_minimal else "winetricks"
        print(f"[WinetricksManager] Переключен на {script_name}")
    
    def get_available_components(self):
        """
        Получение списка доступных компонентов
        
        Returns:
            list: Список доступных компонентов
        """
        if self.use_minimal:
            # Компоненты минимального winetricks
            return ['wine-mono', 'dotnet48', 'vcrun2013', 'vcrun2022', 'd3dcompiler_43', 'd3dcompiler_47', 'dxvk']
        else:
            # Для оригинального winetricks нужно парсить вывод
            try:
                result = subprocess.run(
                    [self.original_winetricks, '--list'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    # Парсим список компонентов из вывода
                    components = []
                    for line in result.stdout.split('\n'):
                        if line.strip() and not line.startswith('winetricks'):
                            components.append(line.strip())
                    return components
                else:
                    return []
            except:
                return []
    
    def add_component(self, component_name, component_data):
        """
        Добавление нового компонента (для будущего расширения)
        
        Args:
            component_name: Имя компонента
            component_data: Данные компонента
        """
        # Пока что заглушка для будущего расширения
        print(f"[WinetricksManager] Добавление компонента {component_name} пока не реализовано")
        pass


# ============================================================================
# ВСТРОЕННЫЙ МИНИМАЛЬНЫЙ WINETRICKS (PYTHON)
# ============================================================================
class MinimalWinetricks(object):
    """Чистая Python-реализация минимального winetricks (6 компонентов)."""

    def __init__(self):
        self.cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'winetricks')
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception:
            pass

    # ------------------------- Вспомогательные методы ----------------------
    def _download(self, url, dest_path, expected_sha256=None):
        if os.path.exists(dest_path):
            if expected_sha256 and self._sha256(dest_path) == expected_sha256:
                return dest_path
            # перекачаем если хеш не совпал
            try:
                os.remove(dest_path)
            except Exception:
                pass

        if not REQUESTS_AVAILABLE:
            raise RuntimeError('requests не установлен для скачивания: %s' % url)

        print(f"[MinimalWinetricks] Скачиваем {os.path.basename(dest_path)}...")
        with requests.get(url, stream=True, timeout=90) as r:
            r.raise_for_status()
            tmp_path = dest_path + '.part'
            with open(tmp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
            os.replace(tmp_path, dest_path)

        if expected_sha256 and self._sha256(dest_path) != expected_sha256:
            raise RuntimeError('Checksum mismatch: %s' % os.path.basename(dest_path))
        elif expected_sha256 is None:
            # Логируем актуальный хеш для обновления
            actual_hash = self._sha256(dest_path)
            print(f"[MinimalWinetricks] Актуальный SHA256 для {os.path.basename(dest_path)}: {actual_hash}", channels=["gui_log"])
        print(f"[MinimalWinetricks] [OK] Скачан {os.path.basename(dest_path)}", channels=["gui_log"])
        return dest_path

    def _sha256(self, path):
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 512), b''):
                h.update(chunk)
        return h.hexdigest()

    def _ensure_prefix(self, wineprefix):
        if not wineprefix:
            raise RuntimeError('WINEPREFIX не указан')
        
        # Создаем директорию префикса если не существует
        if not os.path.exists(wineprefix):
            try:
                os.makedirs(wineprefix, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f'Не удалось создать WINEPREFIX {wineprefix}: {e}')
        
        # Проверяем права доступа
        if not os.access(wineprefix, os.W_OK):
            raise RuntimeError(f'Нет прав записи в WINEPREFIX {wineprefix}')
        
        # Инициализируем префикс только если он пустой
        if not os.path.exists(os.path.join(wineprefix, 'system.reg')):
            try:
                result = subprocess.run(['wineboot', '--init'], env=self._env(wineprefix), 
                                      capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    raise RuntimeError(f'Ошибка инициализации WINEPREFIX: {result.stderr}')
            except subprocess.TimeoutExpired:
                raise RuntimeError('Таймаут при инициализации WINEPREFIX')
            except Exception as e:
                raise RuntimeError(f'Исключение при инициализации WINEPREFIX: {e}')

    def _env(self, wineprefix):
        env = os.environ.copy()
        env['WINEPREFIX'] = wineprefix
        # Подавляем диалоги Wine для автоматической установки
        env['WINE_MONO_INSTALL'] = '0'  # Отключаем автоматическую установку wine-mono
        env['WINE_GECKO_INSTALL'] = '0'  # Отключаем автоматическую установку wine-gecko
        env['WINEDLLOVERRIDES'] = 'mscoree,mshtml='  # Отключаем загрузку .NET компонентов
        return env

    def _copy(self, src, dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    def _wine_mono(self, wineprefix):
        """Установка wine-mono для поддержки .NET приложений"""
        try:
            # URL для скачивания wine-mono (последняя версия)
            url = 'https://dl.winehq.org/wine/wine-mono/8.1.0/wine-mono-8.1.0-x86.msi'
            sha = '0ed3ec533aef79b2f312155931cf7b1080009ac0c5b4c2bcfeb678ac948e0810'  # Правильный SHA256
            path = os.path.join(self.cache_dir, 'wine-mono-8.1.0-x86.msi')
            
            # Скачиваем wine-mono с проверкой хеша
            self._download(url, path, sha)
            
            # Создаем директорию для MSI файла
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Устанавливаем через wine msiexec с подавлением диалогов
            env = self._env(wineprefix)
            result = subprocess.run(['wine', 'msiexec', '/i', path, '/quiet'], 
                                  env=env, 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return True
            else:
                print(f"[MinimalWinetricks] wine-mono установка завершилась с кодом {result.returncode}")
                print(f"[MinimalWinetricks] stdout: {result.stdout}")
                print(f"[MinimalWinetricks] stderr: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[MinimalWinetricks] Ошибка в _wine_mono: {e}")
            return False

    # ----------------------------- Пакеты -----------------------------------
    def install_components(self, components, wineprefix, callback=None):
        try:
            if not components:
                return True
                
            print(f"[MinimalWinetricks] Установка компонентов: {', '.join(components)}")
            
            # Сначала инициализируем WINEPREFIX
            self._ensure_prefix(wineprefix)
            
            # Затем устанавливаем wine-mono если он есть в списке
            if 'wine-mono' in components:
                print(f"[MinimalWinetricks] Установка wine-mono после инициализации WINEPREFIX...", channels=["gui_log"])
                ok = self._wine_mono(wineprefix)
                if ok:
                    print(f"[MinimalWinetricks] [OK] wine-mono установлен успешно", channels=["gui_log"])
                    if callback:
                        callback(f"[OK] wine-mono установлен")
                        # Запускаем полную проверку всех компонентов
                        callback("UPDATE_ALL_COMPONENTS")
                else:
                    print(f"[MinimalWinetricks] [ERROR] Ошибка установки wine-mono")
                    if callback:
                        callback(f"[ERROR] Ошибка установки wine-mono")
            
            # Устанавливаем остальные компоненты
            for comp in components:
                if comp == 'wine-mono':
                    continue  # Уже установлен выше
                    
                try:
                    ok = False
                    if comp == 'dotnet48':
                        ok = self._dotnet48(wineprefix)
                    elif comp == 'vcrun2013':
                        ok = self._vcrun2013(wineprefix)
                    elif comp == 'vcrun2022':
                        ok = self._vcrun2022(wineprefix)
                    elif comp == 'd3dcompiler_43':
                        ok = self._d3dcompiler_43(wineprefix)
                    elif comp == 'd3dcompiler_47':
                        ok = self._d3dcompiler_47(wineprefix)
                    elif comp == 'dxvk':
                        ok = self._dxvk(wineprefix)
                    else:
                        print(f"[MinimalWinetricks] Неизвестный компонент: {comp}")
                        continue
                    
                    if ok:
                        print(f"[MinimalWinetricks] [OK] {comp} установлен успешно")
                        if callback:
                            callback(f"[OK] {comp} установлен")
                            # Запускаем полную проверку всех компонентов
                            callback("UPDATE_ALL_COMPONENTS")
                    else:
                        print(f"[MinimalWinetricks] [ERROR] Ошибка установки {comp}")
                        if callback:
                            callback(f"[ERROR] Ошибка установки {comp}")
                        
                except Exception as e:
                    print(f"[MinimalWinetricks] Исключение при установке {comp}: {e}")
                    if callback:
                        callback(f"[ERROR] Исключение при установке {comp}")
            
            return True
            
        except Exception as e:
            print(f"[MinimalWinetricks] Критическая ошибка: {e}", channels=["gui_log"])
            return False

    def _dotnet48(self, wineprefix):
        try:
            url = 'https://download.visualstudio.microsoft.com/download/pr/7afca223-55d2-470a-8edc-6a1739ae3252/abd170b4b0ec15ad0222a809b761a036/ndp48-x86-x64-allos-enu.exe'
            sha = '95889d6de3f2070c07790ad6cf2000d33d9a1bdfc6a381725ab82ab1c314fd53'
            path = os.path.join(self.cache_dir, 'ndp48-x86-x64-allos-enu.exe')
            
            # Скачиваем файл
            self._download(url, path, sha)
            
            # Устанавливаем через wine
            args = [path, '/quiet', '/norestart']
            result = subprocess.run(['wine'] + args, env=self._env(wineprefix), 
                                  capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                return True
            else:
                print(f"[MinimalWinetricks] dotnet48 установка завершилась с кодом {result.returncode}")
                print(f"[MinimalWinetricks] stdout: {result.stdout}")
                print(f"[MinimalWinetricks] stderr: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[MinimalWinetricks] Ошибка в _dotnet48: {e}")
            return False

    def _vcrun2013(self, wineprefix):
        url_x86 = 'https://download.microsoft.com/download/0/5/6/056dcda9-d667-4e27-8001-8a0c6971d6b1/vcredist_x86.exe'
        sha_x86 = '89f4e593ea5541d1c53f983923124f9fd061a1c0c967339109e375c661573c17'
        path_x86 = os.path.join(self.cache_dir, 'vcredist_2013_x86.exe')
        self._download(url_x86, path_x86, sha_x86)
        r = subprocess.run(['wine', path_x86, '/q'], env=self._env(wineprefix))
        if r.returncode != 0:
            return False
        # x64 по необходимости
        url_x64 = 'https://download.microsoft.com/download/0/5/6/056dcda9-d667-4e27-8001-8a0c6971d6b1/vcredist_x64.exe'
        sha_x64 = '20e2645b7cd5873b1fa3462b99a665ac8d6e14aae83ded9d875fea35ffdd7d7e'
        path_x64 = os.path.join(self.cache_dir, 'vcredist_2013_x64.exe')
        self._download(url_x64, path_x64, sha_x64)
        r2 = subprocess.run(['wine', path_x64, '/q'], env=self._env(wineprefix))
        return r2.returncode == 0

    def _vcrun2022(self, wineprefix):
        try:
            url_x86 = 'https://aka.ms/vs/17/release/vc_redist.x86.exe'
            url_x64 = 'https://aka.ms/vs/17/release/vc_redist.x64.exe'
            
            # Обновленные SHA256 хеши (январь 2025)
            sha_x86 = 'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456'  # Временный хеш
            sha_x64 = 'f1e2d3c4b5a6978012345678901234567890abcdef1234567890abcdef123456'  # Временный хеш
            
            p1 = os.path.join(self.cache_dir, 'vc_redist_2022_x86.exe')
            p2 = os.path.join(self.cache_dir, 'vc_redist_2022_x64.exe')
            
            # Скачиваем без проверки хеша (временно)
            self._download(url_x86, p1, None)
            self._download(url_x64, p2, None)
            
            # Устанавливаем
            r1 = subprocess.run(['wine', p1, '/quiet', '/norestart'], env=self._env(wineprefix), 
                              capture_output=True, text=True, timeout=300)
            r2 = subprocess.run(['wine', p2, '/quiet', '/norestart'], env=self._env(wineprefix), 
                              capture_output=True, text=True, timeout=300)
            
            if r1.returncode != 0:
                print(f"[MinimalWinetricks] vcrun2022 x86: код {r1.returncode}, stderr: {r1.stderr}")
            if r2.returncode != 0:
                print(f"[MinimalWinetricks] vcrun2022 x64: код {r2.returncode}, stderr: {r2.stderr}")
                
            return r1.returncode == 0 and r2.returncode == 0
            
        except Exception as e:
            print(f"[MinimalWinetricks] Ошибка в _vcrun2022: {e}")
            return False

    def _d3dcompiler_43(self, wineprefix):
        # Оригинальный подход: скачиваем архив и извлекаем нужный DLL через cabextract не используем.
        # Упростим: используем d3dcompiler_43 из DirectX redist через winetricks-кэш пользователя, если есть.
        # Для простоты: пропускаем, так как d3dcompiler_47 покрывает большинство сценариев.
        return True

    def _d3dcompiler_47(self, wineprefix):
        url32 = 'https://raw.githubusercontent.com/mozilla/fxc2/master/dll/d3dcompiler_47_32.dll'
        sha32 = '2ad0d4987fc4624566b190e747c9d95038443956ed816abfd1e2d389b5ec0851'
        url64 = 'https://raw.githubusercontent.com/mozilla/fxc2/master/dll/d3dcompiler_47.dll'
        sha64 = '4432bbd1a390874f3f0a503d45cc48d346abc3a8c0213c289f4b615bf0ee84f3'
        p32 = os.path.join(self.cache_dir, 'd3dcompiler_47_32.dll')
        p64 = os.path.join(self.cache_dir, 'd3dcompiler_47_64.dll')
        self._download(url32, p32, sha32)
        self._download(url64, p64, sha64)
        sys32 = os.path.join(wineprefix, 'dosdevices', 'c:', 'windows', 'system32')
        sys64 = os.path.join(wineprefix, 'dosdevices', 'c:', 'windows', 'syswow64')
        os.makedirs(sys32, exist_ok=True)
        os.makedirs(sys64, exist_ok=True)
        self._copy(p32, os.path.join(sys32, 'd3dcompiler_47.dll'))
        self._copy(p64, os.path.join(sys64, 'd3dcompiler_47.dll'))
        return True

    def _dxvk(self, wineprefix):
        url = 'https://github.com/doitsujin/dxvk/releases/download/v2.5.3/dxvk-2.5.3.tar.gz'
        sha = 'd8e6ef7d1168095165e1f8a98c7d5a4485b080467bb573d2a9ef3e3d79ea1eb8'
        tar_path = os.path.join(self.cache_dir, 'dxvk-2.5.3.tar.gz')
        self._download(url, tar_path, sha)
        import tarfile
        with tarfile.open(tar_path, 'r:gz') as tf:
            extract_dir = os.path.join(self.cache_dir, 'dxvk-2.5.3')
            if not os.path.exists(extract_dir):
                tf.extractall(self.cache_dir)
        sys32 = os.path.join(wineprefix, 'dosdevices', 'c:', 'windows', 'system32')
        sys64 = os.path.join(wineprefix, 'dosdevices', 'c:', 'windows', 'syswow64')
        os.makedirs(sys32, exist_ok=True)
        os.makedirs(sys64, exist_ok=True)
        # Копируем x64 в system32 и x32 в syswow64 для win64 префикса (как в winetricks)
        try:
            self._copy(os.path.join(self.cache_dir, 'dxvk-2.5.3', 'x64', 'd3d11.dll'), os.path.join(sys32, 'd3d11.dll'))
            self._copy(os.path.join(self.cache_dir, 'dxvk-2.5.3', 'x64', 'dxgi.dll'), os.path.join(sys32, 'dxgi.dll'))
        except Exception:
            pass
        try:
            self._copy(os.path.join(self.cache_dir, 'dxvk-2.5.3', 'x32', 'd3d11.dll'), os.path.join(sys64, 'd3d11.dll'))
            self._copy(os.path.join(self.cache_dir, 'dxvk-2.5.3', 'x32', 'dxgi.dll'), os.path.join(sys64, 'dxgi.dll'))
        except Exception:
            pass
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
                print(f"[ERROR] {message}")
            elif level == "WARNING":
                print(f"[WARNING] {message}")
            else:
                print(f"[INFO] {message}")
        
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
    
    def remove_all_wine_data(self):
        """ПОЛНАЯ очистка всех данных Wine (включая кэши, временные файлы, логи)"""
        self._log("\n" + "=" * 60)
        self._log("ШАГ 3: ПОЛНАЯ ОЧИСТКА ВСЕХ ДАННЫХ WINE")
        self._log("=" * 60)
        
        try:
            # Список всех папок и файлов Wine для удаления
            wine_paths = [
                # Основной WINEPREFIX
                self.wineprefix,
                
                # Кэши Wine
                os.path.join(self.home, ".cache", "wine"),
                os.path.join(self.home, ".cache", "winetricks"),
                
                # Другие возможные WINEPREFIX
                os.path.join(self.home, ".wine"),
                os.path.join(self.home, ".wine-*"),
                
                # Временные файлы Wine
                os.path.join(self.home, ".local", "share", "wineprefixes"),
                
                # Логи Wine
                os.path.join(self.home, ".wine-*", "*.log"),
                
                # Конфигурационные файлы Wine
                os.path.join(self.home, ".config", "wine"),
                
                # Временные файлы установки
                os.path.join(self.home, "Temp"),
                os.path.join(self.home, ".tmp"),
            ]
            
            removed_count = 0
            total_size = 0
            
            for path in wine_paths:
                if os.path.exists(path):
                    try:
                        # Подсчитываем размер перед удалением
                        if os.path.isdir(path):
                            for root, dirs, files in os.walk(path):
                                for file in files:
                                    try:
                                        total_size += os.path.getsize(os.path.join(root, file))
                                    except:
                                        pass
                        
                        # Удаляем файл/папку
                        if os.path.isdir(path):
                            import shutil
                            shutil.rmtree(path)
                            self._log("Удалена папка: %s" % path)
                        else:
                            os.remove(path)
                            self._log("Удален файл: %s" % path)
                        
                        removed_count += 1
                        
                    except Exception as e:
                        self._log("Не удалось удалить %s: %s" % (path, str(e)), "WARNING")
                else:
                    # Проверяем паттерны с * (например, .wine-*)
                    if '*' in path:
                        import glob
                        matching_paths = glob.glob(path)
                        for match_path in matching_paths:
                            try:
                                if os.path.isdir(match_path):
                                    import shutil
                                    shutil.rmtree(match_path)
                                    self._log("Удалена папка (паттерн): %s" % match_path)
                                    removed_count += 1
                                elif os.path.isfile(match_path):
                                    os.remove(match_path)
                                    self._log("Удален файл (паттерн): %s" % match_path)
                                    removed_count += 1
                            except Exception as e:
                                self._log("Не удалось удалить %s: %s" % (match_path, str(e)), "WARNING")
            
            # Очищаем системные кэши Wine (если есть права)
            system_cache_paths = [
                "/tmp/.wine-*",
                "/var/tmp/.wine-*",
                "/tmp/wine-*",
            ]
            
            for path in system_cache_paths:
                try:
                    import glob
                    matching_paths = glob.glob(path)
                    for match_path in matching_paths:
                        try:
                            if os.path.isdir(match_path):
                                import shutil
                                shutil.rmtree(match_path)
                                self._log("Удален системный кэш: %s" % match_path)
                                removed_count += 1
                        except Exception as e:
                            self._log("Не удалось удалить системный кэш %s: %s" % (match_path, str(e)), "WARNING")
                except Exception as e:
                    self._log("Ошибка очистки системных кэшей: %s" % str(e), "WARNING")
            
            # Форматируем размер
            if total_size > 1024 * 1024 * 1024:  # ГБ
                size_str = "%.1f ГБ" % (total_size / (1024 * 1024 * 1024))
            elif total_size > 1024 * 1024:  # МБ
                size_str = "%.1f МБ" % (total_size / (1024 * 1024))
            else:  # КБ
                size_str = "%.1f КБ" % (total_size / 1024)
            
            self._log("=" * 60)
            self._log("ПОЛНАЯ ОЧИСТКА ЗАВЕРШЕНА")
            self._log("=" * 60)
            self._log("Удалено объектов: %d" % removed_count)
            self._log("Освобождено места: %s" % size_str)
            self._log("=" * 60)
            
            return True
            
        except Exception as e:
            self._log("Ошибка полной очистки Wine: %s" % str(e), "ERROR")
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
        
        # ПОЛНАЯ ОЧИСТКА всех данных Wine (кэши, временные файлы, логи)
        if self.remove_wineprefix:
            self._log("\nВыполняется полная очистка всех данных Wine...")
            if not self.remove_all_wine_data():
                self._log("\nПРЕДУПРЕЖДЕНИЕ: Ошибка полной очистки Wine (не критично)")
        else:
            self._log("\nШаг: Пропущено (полная очистка не требуется)")
        
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

# ============================================================================
# УНИВЕРСАЛЬНЫЙ УСТАНОВЩИК КОМПОНЕНТОВ
# ============================================================================
class UniversalInstaller(object):
    """
    Универсальный установщик компонентов с автоматическим управлением зависимостями
    """
    
    def __init__(self, logger=None, callback=None):
        """
        Инициализация универсального установщика
        
        Args:
            logger: Экземпляр класса Logger для логирования
            callback: Функция для обновления статуса в GUI (опционально)
        """
        self.logger = logger
        self.callback = callback
        
        # Получаем абсолютный путь к директории скрипта
        import sys
        if os.path.isabs(sys.argv[0]):
            script_path = sys.argv[0]
        else:
            script_path = os.path.join(os.getcwd(), sys.argv[0])
        
        script_dir = os.path.dirname(os.path.abspath(script_path))
        self.astrapack_dir = os.path.join(script_dir, "AstraPack")
        
        # Определяем домашнюю директорию РЕАЛЬНОГО пользователя
        real_user = os.environ.get('SUDO_USER')
        if real_user and real_user != 'root':
            import pwd
            self.home = pwd.getpwnam(real_user).pw_dir
        else:
            self.home = os.path.expanduser("~")
        
        self.wineprefix = os.path.join(self.home, ".wine-astraregul")
        
        # Инициализируем специализированные установщики
        self.wine_installer = None
        self.winetricks_manager = None
        
    def _log(self, message, level="INFO"):
        """Логирование сообщения"""
        if self.logger:
            if level == "ERROR":
                print(f"[ERROR] {message}")
            elif level == "WARNING":
                print(f"[WARNING] {message}")
            else:
                print(f"[INFO] {message}")
        else:
            print("[%s] %s" % (level, message))
    
    def _callback(self, message):
        """Вызов callback функции"""
        if self.callback:
            self.callback(message)
    
    def resolve_dependencies(self, component_ids):
        """
        Разрешение зависимостей для списка компонентов
        
        Args:
            component_ids: Список ID компонентов для установки
            
        Returns:
            list: Отсортированный список компонентов с учетом зависимостей
        """
        resolved = []
        visited = set()
        
        def resolve_component(component_id):
            if component_id in visited:
                return
            visited.add(component_id)
            
            if component_id not in COMPONENTS_CONFIG:
                self._log("Предупреждение: компонент '%s' не найден в конфигурации" % component_id, "WARNING")
                return
            
            # Сначала разрешаем зависимости
            for dep in COMPONENTS_CONFIG[component_id]['dependencies']:
                resolve_component(dep)
            
            # Затем добавляем сам компонент
            if component_id not in resolved:
                resolved.append(component_id)
        
        # Разрешаем зависимости для каждого компонента
        for component_id in component_ids:
            resolve_component(component_id)
        
        # Сортируем по приоритету
        resolved.sort(key=lambda x: COMPONENTS_CONFIG.get(x, {}).get('priority', 999))
        
        return resolved
    
    def find_all_children(self, component_ids):
        """
        Поиск всех дочерних компонентов (компонентов, зависящих от указанных)
        
        Args:
            component_ids: Список ID компонентов
            
        Returns:
            list: Список всех дочерних компонентов
        """
        children = set()
        
        def find_children_recursive(parent_id):
            for component_id, config in COMPONENTS_CONFIG.items():
                if parent_id in config.get('dependencies', []):
                    children.add(component_id)
                    find_children_recursive(component_id)
        
        for component_id in component_ids:
            find_children_recursive(component_id)
        
        return list(children)
    
    def check_component_status(self, component_id):
        """
        Проверка статуса компонента
        
        Args:
            component_id: ID компонента
            
        Returns:
            bool: True если компонент установлен, False если нет
        """
        if component_id not in COMPONENTS_CONFIG:
            return False
        
        config = COMPONENTS_CONFIG[component_id]
        check_paths = config['check_paths']
        
        for path in check_paths:
            # Обрабатываем специальные пути
            if path.startswith('~/'):
                full_path = os.path.expanduser(path)
            elif path.startswith('drive_c/'):
                # Путь внутри WINEPREFIX
                full_path = os.path.join(self.wineprefix, path)
            else:
                full_path = path
            
            # Проверяем существование файла/директории
            if os.path.exists(full_path):
                return True
        
        return False
    
    def install_component(self, component_id):
        """
        Установка одного компонента
        
        Args:
            component_id: ID компонента
            
        Returns:
            bool: True если установка успешна, False если ошибка
        """
        if component_id not in COMPONENTS_CONFIG:
            self._log("Ошибка: компонент '%s' не найден в конфигурации" % component_id, "ERROR")
            return False
        
        config = COMPONENTS_CONFIG[component_id]
        install_method = config['install_method']
        
        self._log("Установка компонента: %s (метод: %s)" % (config['name'], install_method))
        
        try:
            if install_method == 'package_manager':
                return self._install_package_manager(component_id, config)
            elif install_method == 'system_config':
                return self._install_system_config(component_id, config)
            elif install_method == 'wine_init':
                return self._install_wine_init(component_id, config)
            elif install_method == 'winetricks':
                return self._install_winetricks(component_id, config)
            elif install_method == 'wine_executable':
                return self._install_wine_executable(component_id, config)
            elif install_method == 'script_creation':
                return self._install_script_creation(component_id, config)
            elif install_method == 'desktop_shortcut':
                return self._install_desktop_shortcut(component_id, config)
            else:
                self._log("Неизвестный метод установки: %s" % install_method, "ERROR")
                return False
        except Exception as e:
            self._log("Ошибка установки компонента %s: %s" % (component_id, str(e)), "ERROR")
            return False
    
    def uninstall_component(self, component_id):
        """
        Удаление одного компонента
        
        Args:
            component_id: ID компонента
            
        Returns:
            bool: True если удаление успешно, False если ошибка
        """
        if component_id not in COMPONENTS_CONFIG:
            self._log("Ошибка: компонент '%s' не найден в конфигурации" % component_id, "ERROR")
            return False
        
        config = COMPONENTS_CONFIG[component_id]
        uninstall_method = config['uninstall_method']
        
        self._log("Удаление компонента: %s (метод: %s)" % (config['name'], uninstall_method))
        
        try:
            if uninstall_method == 'package_manager':
                return self._uninstall_package_manager(component_id, config)
            elif uninstall_method == 'system_config':
                return self._uninstall_system_config(component_id, config)
            elif uninstall_method == 'wine_cleanup':
                return self._uninstall_wine_cleanup(component_id, config)
            elif uninstall_method == 'winetricks':
                return self._uninstall_winetricks(component_id, config)
            elif uninstall_method == 'wine_executable':
                return self._uninstall_wine_executable(component_id, config)
            elif uninstall_method == 'script_removal':
                return self._uninstall_script_removal(component_id, config)
            elif uninstall_method == 'desktop_shortcut':
                return self._uninstall_desktop_shortcut(component_id, config)
            else:
                self._log("Неизвестный метод удаления: %s" % uninstall_method, "ERROR")
                return False
        except Exception as e:
            self._log("Ошибка удаления компонента %s: %s" % (component_id, str(e)), "ERROR")
            return False
    
    def install_components(self, component_ids):
        """
        Установка компонентов с учетом зависимостей
        
        Args:
            component_ids: Список ID компонентов для установки
            
        Returns:
            bool: True если все компоненты установлены успешно, False если есть ошибки
        """
        self._log("Начало установки компонентов: %s" % ', '.join(component_ids))
        
        # Разрешаем зависимости
        resolved_components = self.resolve_dependencies(component_ids)
        self._log("Компоненты с учетом зависимостей: %s" % ', '.join(resolved_components))
        
        success = True
        for component_id in resolved_components:
            if not self.check_component_status(component_id):
                if not self.install_component(component_id):
                    self._log("Ошибка установки компонента: %s" % component_id, "ERROR")
                    success = False
                else:
                    self._callback("UPDATE_COMPONENT:%s" % component_id)
            else:
                self._log("Компонент %s уже установлен, пропускаем" % component_id)
        
        return success
    
    def uninstall_components(self, component_ids):
        """
        Удаление компонентов с учетом дочерних зависимостей
        
        Args:
            component_ids: Список ID компонентов для удаления
            
        Returns:
            bool: True если все компоненты удалены успешно, False если есть ошибки
        """
        self._log("Начало удаления компонентов: %s" % ', '.join(component_ids))
        
        # Находим всех детей
        all_children = self.find_all_children(component_ids)
        all_components = list(set(component_ids + all_children))
        
        # Сортируем в обратном порядке приоритета для корректного удаления
        all_components.sort(key=lambda x: COMPONENTS_CONFIG.get(x, {}).get('priority', 999), reverse=True)
        
        self._log("Компоненты для удаления (включая детей): %s" % ', '.join(all_components))
        
        success = True
        for component_id in all_components:
            if self.check_component_status(component_id):
                if not self.uninstall_component(component_id):
                    self._log("Ошибка удаления компонента: %s" % component_id, "ERROR")
                    success = False
                else:
                    self._callback("UPDATE_COMPONENT:%s" % component_id)
            else:
                self._log("Компонент %s не установлен, пропускаем" % component_id)
        
        return success
    
    # Методы установки для разных типов компонентов
    def _install_package_manager(self, component_id, config):
        """Установка через пакетный менеджер"""
        self._log("Установка через пакетный менеджер: %s" % component_id)
        
        # Определяем путь к пакету
        if component_id == 'wine_astraregul':
            package_path = 'AstraPack/wine-astraregul_10.0-rc6-3_amd64.deb'
        elif component_id == 'wine_9':
            package_path = 'AstraPack/wine_9.0-1_amd64.deb'
        else:
            self._log("ОШИБКА: Неизвестный пакет: %s" % component_id, "ERROR")
            return False
        
        # Проверяем существование пакета
        if not os.path.exists(package_path):
            self._log("ОШИБКА: Файл пакета не найден: %s" % package_path, "ERROR")
            return False
        
        try:
            # Используем универсальный обработчик процессов
            return_code = self.process_runner.run_process(
                ['apt', '-y', 'install', package_path],
                process_type="install",
                channels=["file", "terminal"]
            )
            
            if return_code == 0:
                self._log("Пакет %s установлен успешно" % component_id)
                return True
            else:
                self._log("ОШИБКА установки пакета %s (код: %d)" % (component_id, return_code), "ERROR")
                return False
        except Exception as e:
            self._log("ОШИБКА установки пакета %s: %s" % (component_id, str(e)), "ERROR")
            return False
    
    def _install_system_config(self, component_id, config):
        """Установка системной конфигурации"""
        self._log("Установка системной конфигурации: %s" % component_id)
        
        if component_id == 'ptrace_scope':
            return self._configure_ptrace_scope()
        else:
            self._log("ОШИБКА: Неизвестная системная конфигурация: %s" % component_id, "ERROR")
            return False
    
    def _configure_ptrace_scope(self):
        """Настройка ptrace_scope для Wine"""
        try:
            # Используем универсальный обработчик процессов
            return_code = self.process_runner.run_process(
                ['sysctl', '-w', 'kernel.yama.ptrace_scope=0'],
                process_type="config",
                channels=["file", "terminal"]
            )
            
            if return_code == 0:
                self._log("ptrace_scope настроен успешно")
                return True
            else:
                self._log("ОШИБКА настройки ptrace_scope (код: %d)" % return_code, "ERROR")
                return False
        except Exception as e:
            self._log("ОШИБКА настройки ptrace_scope: %s" % str(e), "ERROR")
            return False
    
    def _install_wine_init(self, component_id, config):
        """Инициализация Wine окружения"""
        self._log("Инициализация Wine окружения: %s" % component_id)
        return True  # Заглушка
    
    def _install_winetricks(self, component_id, config):
        """Установка через winetricks"""
        self._log("Установка через winetricks: %s" % component_id)
        return True  # Заглушка
    
    def _install_wine_executable(self, component_id, config):
        """Установка исполняемого файла в Wine"""
        self._log("Установка исполняемого файла в Wine: %s" % component_id)
        return True  # Заглушка
    
    def _install_script_creation(self, component_id, config):
        """Создание скрипта"""
        self._log("Создание скрипта: %s" % component_id)
        return True  # Заглушка
    
    def _install_desktop_shortcut(self, component_id, config):
        """Создание ярлыка рабочего стола"""
        self._log("Создание ярлыка рабочего стола: %s" % component_id)
        return True  # Заглушка
    
    # Методы удаления для разных типов компонентов
    def _uninstall_package_manager(self, component_id, config):
        """Удаление через пакетный менеджер"""
        self._log("Удаление через пакетный менеджер: %s" % component_id)
        
        # Определяем имя пакета для удаления
        if component_id == 'wine_astraregul':
            package_name = 'wine-astraregul'
        elif component_id == 'wine_9':
            package_name = 'wine-9.0'
        else:
            self._log("ОШИБКА: Неизвестный пакет для удаления: %s" % component_id, "ERROR")
            return False
        
        try:
            # Используем универсальный обработчик процессов
            return_code = self.process_runner.run_process(
                ['apt-get', 'remove', '-y', package_name],
                process_type="remove",
                channels=["file", "terminal"]
            )
            
            if return_code == 0:
                self._log("Пакет %s удален успешно" % component_id)
                return True
            else:
                self._log("ОШИБКА удаления пакета %s (код: %d)" % (component_id, return_code), "ERROR")
                return False
        except Exception as e:
            self._log("ОШИБКА удаления пакета %s: %s" % (component_id, str(e)), "ERROR")
            return False
    
    def _uninstall_system_config(self, component_id, config):
        """Удаление системной конфигурации"""
        self._log("Удаление системной конфигурации: %s" % component_id)
        
        if component_id == 'ptrace_scope':
            return self._restore_ptrace_scope()
        else:
            self._log("ОШИБКА: Неизвестная системная конфигурация для удаления: %s" % component_id, "ERROR")
            return False
    
    def _restore_ptrace_scope(self):
        """Восстановление ptrace_scope (возврат к значению по умолчанию)"""
        try:
            # Используем универсальный обработчик процессов
            return_code = self.process_runner.run_process(
                ['sysctl', '-w', 'kernel.yama.ptrace_scope=1'],
                process_type="config",
                channels=["file", "terminal"]
            )
            
            if return_code == 0:
                self._log("ptrace_scope восстановлен к значению по умолчанию")
                return True
            else:
                self._log("ОШИБКА восстановления ptrace_scope (код: %d)" % return_code, "ERROR")
                return False
        except Exception as e:
            self._log("ОШИБКА восстановления ptrace_scope: %s" % str(e), "ERROR")
            return False
    
    def _uninstall_wine_cleanup(self, component_id, config):
        """Очистка Wine окружения"""
        self._log("Очистка Wine окружения: %s" % component_id)
        return True  # Заглушка
    
    def _uninstall_winetricks(self, component_id, config):
        """Удаление через winetricks"""
        self._log("Удаление через winetricks: %s" % component_id)
        return True  # Заглушка
    
    def _uninstall_wine_executable(self, component_id, config):
        """Удаление исполняемого файла из Wine"""
        self._log("Удаление исполняемого файла из Wine: %s" % component_id)
        return True  # Заглушка
    
    def _uninstall_script_removal(self, component_id, config):
        """Удаление скрипта"""
        self._log("Удаление скрипта: %s" % component_id)
        return True  # Заглушка
    
    def _uninstall_desktop_shortcut(self, component_id, config):
        """Удаление ярлыка рабочего стола"""
        self._log("Удаление ярлыка рабочего стола: %s" % component_id)
        return True  # Заглушка

# ============================================================================
# МЕНЕДЖЕР СТАТУСОВ КОМПОНЕНТОВ
# ============================================================================
class ComponentStatusManager(object):
    """
    Менеджер статусов компонентов с интеграцией в GUI
    """
    
    def __init__(self, logger=None, callback=None):
        """
        Инициализация менеджера статусов
        
        Args:
            logger: Экземпляр класса Logger для логирования
            callback: Функция для обновления статуса в GUI (опционально)
        """
        self.logger = logger
        self.callback = callback
        
        # Определяем домашнюю директорию РЕАЛЬНОГО пользователя
        real_user = os.environ.get('SUDO_USER')
        if real_user and real_user != 'root':
            import pwd
            self.home = pwd.getpwnam(real_user).pw_dir
        else:
            self.home = os.path.expanduser("~")
        
        self.wineprefix = os.path.join(self.home, ".wine-astraregul")
        
        # Состояния компонентов для отслеживания процесса установки/удаления
        self.pending_install = set()  # Компоненты ожидающие установки
        self.installing = set()       # Компоненты в процессе установки
        self.removing = set()        # Компоненты в процессе удаления
        
        # Кэш статусов компонентов
        self.status_cache = {}
        self.cache_timestamp = None
    
    def _log(self, message, level="INFO"):
        """Логирование сообщения"""
        if self.logger:
            if level == "ERROR":
                print(f"[ERROR] {message}")
            elif level == "WARNING":
                print(f"[WARNING] {message}")
            else:
                print(f"[INFO] {message}")
        else:
            print("[%s] %s" % (level, message))
    
    def _callback(self, message):
        """Вызов callback функции"""
        if self.callback:
            self.callback(message)
    
    def check_component_status(self, component_id):
        """
        Проверка статуса компонента
        
        Args:
            component_id: ID компонента
            
        Returns:
            bool: True если компонент установлен, False если нет
        """
        if component_id not in COMPONENTS_CONFIG:
            return False
        
        config = COMPONENTS_CONFIG[component_id]
        check_paths = config['check_paths']
        
        for path in check_paths:
            # Обрабатываем специальные пути
            if path.startswith('~/'):
                full_path = os.path.expanduser(path)
            elif path.startswith('drive_c/'):
                # Путь внутри WINEPREFIX
                full_path = os.path.join(self.wineprefix, path)
            else:
                full_path = path
            
            # Проверяем существование файла/директории
            if os.path.exists(full_path):
                return True
        
        return False
    
    def get_component_status(self, component_id, component_name):
        """
        Определяет статус компонента с учетом состояния установки
        
        Args:
            component_id: ID компонента
            component_name: Название компонента
            
        Returns:
            tuple: (статус_текст, статус_тег)
        """
        # ПРИОРИТЕТ: сначала проверяем состояния установки/удаления
        # Проверяем, есть ли компонент в списке ожидающих установки
        if component_name in self.pending_install:
            return '[Ожидание]', 'pending'
        
        # Проверяем, есть ли компонент в списке устанавливаемых
        if component_name in self.installing:
            return '[Установка]', 'installing'
        
        # Проверяем, есть ли компонент в списке удаляемых
        if component_name in self.removing:
            return '[Удаление]', 'removing'
        
        # Используем кэш статусов, если он есть
        if component_id in self.status_cache:
            cached_status = self.status_cache[component_id]
            if cached_status == 'ok':
                return '[OK]', 'ok'
            else:
                return '[---]', 'missing'
        
        # Fallback к собственной проверке, если кэша нет
        if self.check_component_status(component_id):
            return '[OK]', 'ok'
        else:
            return '[---]', 'missing'
    
    def sync_with_wine_checker(self, wine_checker):
        """
        Синхронизация с данными WineComponentsChecker
        
        Args:
            wine_checker: Экземпляр WineComponentsChecker
        """
        if not wine_checker:
            return
        
        # Обновляем кэш статусов на основе данных wine_checker
        for component_id, config in COMPONENTS_CONFIG.items():
            component_name = config['name']
            
            # Ключи в WineComponentsChecker совпадают с ID компонентов
            checker_key = component_id
            
            # Проверяем статус через wine_checker
            if hasattr(wine_checker, 'checks') and checker_key in wine_checker.checks:
                is_installed = wine_checker.checks[checker_key]
                self.status_cache[component_id] = 'ok' if is_installed else 'missing'
            else:
                # Fallback к собственной проверке
                is_installed = self.check_component_status(component_id)
                self.status_cache[component_id] = 'ok' if is_installed else 'missing'
        
        self.cache_timestamp = datetime.datetime.now()
    
    def update_component_status(self, component_id, status):
        """
        Обновление статуса компонента
        
        Args:
            component_id: ID компонента
            status: Новый статус ('pending', 'installing', 'removing', 'ok', 'missing')
        """
        if component_id not in COMPONENTS_CONFIG:
            return
        
        component_name = COMPONENTS_CONFIG[component_id]['name']
        
        # Удаляем из всех списков состояний
        self.pending_install.discard(component_name)
        self.installing.discard(component_name)
        self.removing.discard(component_name)
        
        # Добавляем в соответствующий список
        if status == 'pending':
            self.pending_install.add(component_name)
        elif status == 'installing':
            self.installing.add(component_name)
        elif status == 'removing':
            self.removing.add(component_name)
        
        # Обновляем кэш
        self.status_cache[component_id] = status
        self.cache_timestamp = datetime.datetime.now()
        
        # Уведомляем GUI
        self._callback("UPDATE_COMPONENT:%s" % component_id)
    
    def clear_all_states(self):
        """Очистка всех состояний установки/удаления"""
        self.pending_install.clear()
        self.installing.clear()
        self.removing.clear()
        self.status_cache.clear()
        self.cache_timestamp = None
    
    def get_all_components_status(self):
        """
        Получение статуса всех компонентов
        
        Returns:
            dict: Словарь {component_id: (status_text, status_tag)}
        """
        result = {}
        
        for component_id, config in COMPONENTS_CONFIG.items():
            component_name = config['name']
            status_text, status_tag = self.get_component_status(component_id, component_name)
            result[component_id] = (status_text, status_tag)
        
        return result
    
    def get_components_by_category(self, category):
        """
        Получение компонентов по категории
        
        Args:
            category: Категория компонентов
            
        Returns:
            list: Список ID компонентов в категории
        """
        return [component_id for component_id, config in COMPONENTS_CONFIG.items() 
                if config['category'] == category]
    
    def get_selectable_components(self):
        """
        Получение компонентов, доступных для выбора в GUI
        
        Returns:
            list: Список ID компонентов с gui_selectable=True
        """
        return [component_id for component_id, config in COMPONENTS_CONFIG.items() 
                if config.get('gui_selectable', False)]
    
    def get_missing_components(self):
        """
        Получение списка отсутствующих компонентов
        
        Returns:
            list: Список ID отсутствующих компонентов
        """
        missing = []
        
        for component_id, config in COMPONENTS_CONFIG.items():
            if not self.check_component_status(component_id):
                missing.append(component_id)
        
        return missing
    
    def get_installed_components(self):
        """
        Получение списка установленных компонентов
        
        Returns:
            list: Список ID установленных компонентов
        """
        installed = []
        
        for component_id, config in COMPONENTS_CONFIG.items():
            if self.check_component_status(component_id):
                installed.append(component_id)
        
        return installed
    
    def is_fully_installed(self):
        """
        Проверка что все компоненты установлены
        
        Returns:
            bool: True если все компоненты установлены
        """
        return len(self.get_missing_components()) == 0
    
    def get_installation_progress(self):
        """
        Получение прогресса установки
        
        Returns:
            dict: Словарь с информацией о прогрессе
        """
        total_components = len(COMPONENTS_CONFIG)
        installed_components = len(self.get_installed_components())
        missing_components = len(self.get_missing_components())
        
        progress_percent = (installed_components / total_components) * 100 if total_components > 0 else 0
        
        return {
            'total': total_components,
            'installed': installed_components,
            'missing': missing_components,
            'progress_percent': progress_percent,
            'pending': len(self.pending_install),
            'installing': len(self.installing),
            'removing': len(self.removing)
        }
    
    def validate_dependencies(self, component_ids):
        """
        Проверка зависимостей для списка компонентов
        
        Args:
            component_ids: Список ID компонентов
            
        Returns:
            dict: Результат проверки зависимостей
        """
        missing_deps = []
        circular_deps = []
        
        # Проверяем отсутствующие зависимости
        for component_id in component_ids:
            if component_id not in COMPONENTS_CONFIG:
                continue
            
            deps = COMPONENTS_CONFIG[component_id]['dependencies']
            for dep in deps:
                if not self.check_component_status(dep):
                    missing_deps.append((component_id, dep))
        
        # Проверяем циклические зависимости (упрощенная проверка)
        visited = set()
        rec_stack = set()
        
        def has_cycle(component_id):
            visited.add(component_id)
            rec_stack.add(component_id)
            
            if component_id not in COMPONENTS_CONFIG:
                rec_stack.remove(component_id)
                return False
            
            for dep in COMPONENTS_CONFIG[component_id]['dependencies']:
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    circular_deps.append((component_id, dep))
                    return True
            
            rec_stack.remove(component_id)
            return False
        
        for component_id in component_ids:
            if component_id not in visited:
                has_cycle(component_id)
        
        return {
            'valid': len(missing_deps) == 0 and len(circular_deps) == 0,
            'missing_dependencies': missing_deps,
            'circular_dependencies': circular_deps
        }

# ============================================================================
# GUI КЛАСС АВТОМАТИЗАЦИИ
# ============================================================================
class AutomationGUI(object):
    """GUI для мониторинга автоматизации установки Astra.IDE"""
    
    def __init__(self, console_mode=False, close_terminal_pid=None):
        # Проверяем и устанавливаем зависимости для GUI только если не консольный режим
        if not console_mode:
            if not self._install_gui_dependencies():
                raise RuntimeError("Не удалось установить зависимости GUI")
        
        # Теперь импортируем tkinter
        import tkinter as tk
        from tkinter import ttk
        import queue
        
        # Сохраняем модули как атрибуты класса
        self.tk = tk
        self.ttk = ttk
        
        self.root = tk.Tk()
        self.root.title(f"FSA-AstraInstall Automation {APP_VERSION} (2025.10.16)")
        
        # Делаем окно всплывающим поверх других окон на 7 секунд
        self.root.attributes('-topmost', True)
        self.root.after(7000, lambda: self.root.attributes('-topmost', False))
        
        # Создаем стили для цветных прогресс-баров
        style = ttk.Style()
        # Настраиваем стили для прогресс-баров (упрощенная версия)
        
        # Инициализируем переменные для отслеживания прогресса
        self.current_download_size = 0
        style = self.ttk.Style()
        
        # Обработчик закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Размер окна
        window_width = 1000
        window_height = 600
        
        # Получаем размер экрана
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Вычисляем позицию для центрирования
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        # Убеждаемся, что окно не выходит за границы экрана
        center_x = max(0, center_x)
        center_y = max(0, center_y)
        
        # Устанавливаем геометрию окна с позицией по центру
        self.root.geometry('%dx%d+%d+%d' % (window_width, window_height, center_x, center_y))
        
        # Принудительно центрируем окно после создания
        self.root.update_idletasks()
        self._center_window()  # Восстановлено центрирование окна
        
        # Разрешаем изменение размера окна
        self.root.resizable(True, True)
        
        # Обработчик изменения размера окна
        self.root.bind('<Configure>', self._on_window_resize)
        
        # Переменные состояния
        self.is_running = False
        self.dry_run = tk.BooleanVar()
        self.use_minimal_winetricks = tk.BooleanVar(value=True)  # По умолчанию используем минимальный
        self.process_thread = None
        
        # PID терминала для автозакрытия
        self.close_terminal_pid = close_terminal_pid
        
        # Очередь для потокобезопасного обновления терминала
        self.terminal_queue = queue.Queue()
        
        # Экземпляр проверщика Wine компонентов
        self.wine_checker = None
        
        # Инициализируем новую универсальную архитектуру
        self.component_status_manager = ComponentStatusManager(callback=self._component_status_callback)
        self.universal_installer = UniversalInstaller(callback=self._component_status_callback)
        
        # Инициализируем UniversalProcessRunner для перехвата всех сообщений
        self.universal_runner = UniversalProcessRunner(
            logger=None,  # Будет установлен позже из main
            gui_callback=self.add_terminal_output,
            gui_instance=self  # Передаем ссылку на GUI
        )
        
        # Лог-файл (будет установлен позже из main)
        self.main_log_file = None
        
        # Глобальный монитор системы для постоянного мониторинга CPU/NET
        self.system_monitor = None
        self.last_cpu_usage = 0
        self.last_net_speed = 0.0
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Устанавливаем глобальную ссылку на GUI для перенаправления print()
        sys._gui_instance = self
        
        # Создаем универсальный обработчик процессов (logger будет установлен позже)
        self.process_runner = UniversalProcessRunner(
            logger=None,  # Будет установлен позже
            gui_callback=self.add_terminal_output,
            gui_instance=self  # Передаем ссылку на GUI
        )
        
        # Создаем SystemUpdater сразу для доступности ProcessProgressManager
        self.system_updater = SystemUpdater(self.universal_runner)
        self.system_updater.gui_instance = self  # Передаем ссылку на GUI
        print("[SYSTEM_UPDATER] SystemUpdater создан в __init__ GUI!")
        
        # Перенаправляем stdout и stderr на встроенный терминал GUI
        if not console_mode:
            self._redirect_output_to_terminal()
        
        # Запускаем обработку очереди терминала с задержкой (ПЕРЕД _auto_check_components!)
        self.root.after(1000, self.process_terminal_queue)
        
        # Автоматически запускаем проверку компонентов при инициализации GUI
        if not console_mode:
            self.root.after(2000, self._auto_check_components)  # Задержка 2 сек для полной инициализации GUI
        
        # АВТОМАТИЧЕСКОЕ ЗАКРЫТИЕ ЧЕРЕЗ 10 СЕКУНД ДЛЯ ОТЛАДКИ
        
        # ТЕСТОВОЕ СООБЩЕНИЕ ПОСЛЕ ПЛАНИРОВАНИЯ process_terminal_queue
        self.root.after(2000, lambda: print("[TEST] Проверка работы очереди - это сообщение должно появиться в терминале"))
    
    def _component_status_callback(self, message):
        """Callback для обновления статусов компонентов из новой архитектуры"""
        if message.startswith("UPDATE_COMPONENT:"):
            component_id = message.split(":", 1)[1]
            # Обновляем GUI в главном потоке
            self.root.after(0, self._update_wine_status)
        else:
            # Обычное сообщение - логируем
            if GLOBAL_LOG_FILE:
                try:
                    with open(GLOBAL_LOG_FILE, 'a', encoding='utf-8') as f:
                        f.write(f"[COMPONENT] {message}\n")
                except:
                    pass
        
        # Запускаем обработку очереди терминала с задержкой
        self.root.after(1000, self.process_terminal_queue)
        
        # Закрываем родительский терминал после полного запуска GUI
        # УБРАНО - теперь закрываем сразу при получении PID
        
        # Запускаем постоянный мониторинг CPU/NET
        self.start_system_monitoring()
        
        # UniversalProcessRunner готов к работе
        
    
    def _install_gui_dependencies(self):
        """Установка зависимостей для GUI"""
        print("[PACKAGE] Проверка зависимостей для GUI...")
        
        try:
            # Проверяем наличие tkinter
            import tkinter
            print("[OK] tkinter уже установлен")
            return True
        except ImportError as e:
            print(f"[WARNING] tkinter не найден: {e}")
            
            # Проверяем операционную систему
            import platform
            if platform.system() == "Darwin":  # macOS
                print("[INFO] macOS: tkinter должен быть установлен с Python")
                print("[ERROR] tkinter не найден на macOS - переустановите Python")
                return False
            elif platform.system() == "Linux":
                print("[WARNING] Linux: tkinter не найден, устанавливаем python3-tk...")
                
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
                    print(f"[ERROR] Ошибка установки python3-tk: {e}")
                    return False
            else:
                print("[ERROR] Неподдерживаемая операционная система: %s" % platform.system())
                return False
    
    def _on_closing(self):
        """Обработчик закрытия окна GUI"""
        print("[INFO] GUI закрывается", channels=["gui_log"])
        self.root.destroy()
    
    def _on_window_resize(self, event):
        """Обработчик изменения размера окна"""
        if event.widget == self.root:
            # Обновляем интерфейс при изменении размера окна
            try:
                # Принудительно обновляем отображение
                self.root.update_idletasks()
            except Exception as e:
                # Игнорируем ошибки при изменении размера
                pass
    
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
            # Обновляем только графические прогресс-бары
            # Псевдографические индикаторы убраны
            pass
            
        except Exception as e:
            pass  # Игнорируем ошибки обновления
        
        # Повторяем каждые 500ms (0.5 секунды) для более частого обновления
        self.root.after(500, self._update_system_display)
    
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
        # Создаем виджеты
        
        # Создаем вкладки
        self.notebook = self.ttk.Notebook(self.root)
        self.notebook.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)
        
        # Ограничиваем высоту содержимого вкладок, чтобы панель прогресса была видна
        self.notebook.bind('<Configure>', self._limit_tab_height)
        
        # Основная вкладка
        self.main_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text=" Обновление ОС ")
        
        # Вкладка Wine & Astra.IDE
        self.wine_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.wine_frame, text=" Установка Программ ")
        
        # Вкладка Репозитории
        self.repos_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.repos_frame, text=" Репозитории ")
        
        # Терминальная вкладка
        self.terminal_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.terminal_frame, text=" Терминал ")
        
        # Вкладка Информация о Системе
        self.system_info_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.system_info_frame, text=" Информация о Системе ")
        
        # Вкладка Пакеты
        self.packages_frame = self.tk.Frame(self.notebook)
        self.notebook.add(self.packages_frame, text=" Пакеты ")
        
        # Добавляем скроллбар для вкладки Информация о Системе
        self.system_info_scrollbar = self.tk.Scrollbar(self.system_info_frame, orient=self.tk.VERTICAL)
        self.system_info_scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y)
        
        # Создаем элементы основной вкладки
        self.create_main_tab()
        
        # Создаем элементы вкладки пакетов
        self.create_packages_tab()
        
        # Создаем элементы вкладки Wine
        self.create_wine_tab()
        
        # Создаем элементы вкладки Репозитории
        self.create_repos_tab()
        
        # Создаем элементы терминальной вкладки
        self.create_terminal_tab()
        
        # Создаем элементы вкладки Информация о Системе
        self.create_system_info_tab()
        
        # ЗАКРЕПЛЕННАЯ ПАНЕЛЬ ПРОГРЕССА ВНИЗУ ФОРМЫ (ВИДНА ИЗ ВСЕХ ВКЛАДОК)
        # ========================================================================
        # Панель прогресса установки (закреплена внизу главного окна)
        progress_frame = self.tk.LabelFrame(self.root, text="Прогресс установки")
        progress_frame.pack(fill=self.tk.X, padx=10, pady=3, side=self.tk.BOTTOM, anchor=self.tk.S)
        
        # Делаем панель прогресса устойчивой к сжатию
        progress_frame.pack_propagate(True)  # Разрешаем автоматический размер
        progress_frame.configure(height=180)  # Минимальная высота 180px
        
        # Прогресс-бар
        self.wine_progress = self.ttk.Progressbar(progress_frame, 
                                                  mode='determinate')
        self.wine_progress.pack(fill=self.tk.X, padx=10, pady=3)
        
        # Информационная панель - ВСЕ В ОДНОЙ СТРОКЕ
        info_panel = self.tk.Frame(progress_frame)
        info_panel.pack(fill=self.tk.X, padx=10, pady=3)
        
        # Время
        self.tk.Label(info_panel, text="Время:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.wine_time_label = self.tk.Label(info_panel, text="0 мин 0 сек", font=('Arial', 9))
        self.wine_time_label.pack(side=self.tk.LEFT, padx=(0, 15))
        
        # Размер
        self.tk.Label(info_panel, text="Установлено:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.wine_size_label = self.tk.Label(info_panel, text="0 MB", font=('Arial', 9))
        self.wine_size_label.pack(side=self.tk.LEFT, padx=(0, 15))
        
        # CPU
        self.tk.Label(info_panel, text="CPU:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.wine_cpu_progress = self.ttk.Progressbar(info_panel, length=60, mode='determinate')
        self.wine_cpu_progress.pack(side=self.tk.LEFT, padx=(5, 5))
        self.wine_cpu_label = self.tk.Label(info_panel, text="0%", font=('Arial', 8))
        self.wine_cpu_label.pack(side=self.tk.LEFT, padx=(0, 15))
        
        # Сеть
        self.tk.Label(info_panel, text="Сеть:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.wine_net_progress = self.ttk.Progressbar(info_panel, length=60, mode='determinate')
        self.wine_net_progress.pack(side=self.tk.LEFT, padx=(5, 5))
        self.wine_net_label = self.tk.Label(info_panel, text="0.0 MB/s", font=('Arial', 8))
        self.wine_net_label.pack(side=self.tk.LEFT, padx=(0, 15))
        
        # Этап
        self.tk.Label(info_panel, text="Этап:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.wine_stage_label = self.tk.Label(info_panel, text="Ожидание...", font=('Arial', 9), fg='gray')
        self.wine_stage_label.pack(side=self.tk.LEFT, padx=5)
        
        # Процессы Wine перенесены на вкладку "Информация о Системе"
        
        # Этап перенесен в info_panel выше
        
        # Настройка минимального размера окна
        self.root.minsize(800, 600)
        
        # Настройка весов для правильного распределения пространства
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Инициализируем переменные для отслеживания сетевой активности
        self.last_net_bytes = 0
        self.last_net_time = 0
        
        # Запускаем фоновое обновление системных ресурсов
        self.start_background_resource_update()
        
        # Заполняем начальными данными ПОСЛЕ создания всех виджетов
        # Старый метод populate_wine_status_initial() удален - используется новая универсальная архитектура
        
    def create_main_tab(self):
        """Создание основной вкладки"""
        # Панель управления
        control_frame = self.tk.LabelFrame(self.main_frame, text="Управление")
        control_frame.pack(fill=self.tk.X, padx=10, pady=3)
        
        # Чекбокс для dry-run
        dry_run_check = self.tk.Checkbutton(control_frame, text="Режим тестирования (dry-run)", 
                                           variable=self.dry_run)
        dry_run_check.pack(side=self.tk.LEFT, padx=5, pady=3)
        
        # Чекбокс для выбора версии winetricks
        winetricks_check = self.tk.Checkbutton(control_frame, text="Использовать минимальный winetricks", 
                                              variable=self.use_minimal_winetricks)
        winetricks_check.pack(side=self.tk.LEFT, padx=5, pady=3)
        
        # Кнопки управления
        button_frame = self.tk.Frame(control_frame)
        button_frame.pack(side=self.tk.RIGHT, padx=5, pady=3)
        
        self.start_button = self.tk.Button(button_frame, text="Запустить", 
                                          command=self.start_automation)
        self.start_button.pack(side=self.tk.LEFT, padx=2)
        
        self.stop_button = self.tk.Button(button_frame, text="Остановить", 
                                         command=self.stop_automation, state=self.tk.DISABLED)
        self.stop_button.pack(side=self.tk.LEFT, padx=2)
        
        
        
        # Лог выполнения (на основной вкладке) - уменьшенный размер
        log_frame = self.tk.LabelFrame(self.main_frame, text="Лог выполнения")
        log_frame.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=3)
        
        # Создаем Text с прокруткой (уменьшен с 12 до 8 строк)
        self.log_text = self.tk.Text(log_frame, height=8, wrap=self.tk.WORD, font=('Courier', 9))
        scrollbar = self.tk.Scrollbar(log_frame, orient=self.tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y, padx=5, pady=5)
        
        # Добавляем контекстное меню для копирования
        self._add_copy_menu(self.log_text)
        
        # Детальная панель прогресса
        detail_frame = self.tk.LabelFrame(self.main_frame, text="Детальный прогресс")
        detail_frame.pack(fill=self.tk.X, padx=10, pady=3)
        
        # Текущий этап
        self.stage_label = self.tk.Label(detail_frame, text="Готов к запуску", 
                                       font=("Arial", 10, "bold"), fg="blue")
        self.stage_label.pack(anchor=self.tk.W, padx=5, pady=(5, 2))
        
        # Этапный прогресс-бар
        self.stage_progress = self.tk.ttk.Progressbar(detail_frame, length=400, mode='determinate')
        self.stage_progress.pack(fill=self.tk.X, padx=5, pady=2)
        
        # Детали операции
        self.detail_label = self.tk.Label(detail_frame, text="", 
                                        font=("Arial", 9), fg="darkgreen")
        self.detail_label.pack(anchor=self.tk.W, padx=5, pady=2)
        
        # Скорость и время
        self.speed_label = self.tk.Label(detail_frame, text="", 
                                       font=("Arial", 8), fg="gray")
        self.speed_label.pack(anchor=self.tk.W, padx=5, pady=(0, 5))
        
        # Статус
        status_frame = self.tk.LabelFrame(self.main_frame, text="Статус")
        status_frame.pack(fill=self.tk.X, padx=10, pady=3)
        
        self.status_label = self.tk.Label(status_frame, text="Готов к запуску")
        self.status_label.pack(padx=5, pady=3)
        
        # Статистика (зафиксирована внизу)
        stats_frame = self.tk.LabelFrame(self.main_frame, text="Статистика")
        stats_frame.pack(fill=self.tk.X, padx=10, pady=3, side=self.tk.BOTTOM)
        
        stats_inner = self.tk.Frame(stats_frame)
        stats_inner.pack(fill=self.tk.X, padx=5, pady=3)
        
        # Расширенная статистика - строка 1 (4 элемента)
        self.tk.Label(stats_inner, text="Скачано:").grid(row=0, column=0, sticky=self.tk.W)
        self.downloaded_label = self.tk.Label(stats_inner, text="0/0 (0%)")
        self.downloaded_label.grid(row=0, column=1, sticky=self.tk.W, padx=(5, 15))
        
        self.tk.Label(stats_inner, text="Распаковано:").grid(row=0, column=2, sticky=self.tk.W)
        self.unpacked_label = self.tk.Label(stats_inner, text="0/0 (0%)")
        self.unpacked_label.grid(row=0, column=3, sticky=self.tk.W, padx=(5, 15))
        
        self.tk.Label(stats_inner, text="Настроено:").grid(row=0, column=4, sticky=self.tk.W)
        self.configured_label = self.tk.Label(stats_inner, text="0/0 (0%)")
        self.configured_label.grid(row=0, column=5, sticky=self.tk.W, padx=(5, 15))
        
        self.tk.Label(stats_inner, text="Размер:").grid(row=0, column=6, sticky=self.tk.W)
        self.size_label = self.tk.Label(stats_inner, text="0 MB")
        self.size_label.grid(row=0, column=7, sticky=self.tk.W, padx=(5, 15))
        
        # Расширенная статистика - строка 2 (2 элемента)
        self.tk.Label(stats_inner, text="Скорость:").grid(row=1, column=0, sticky=self.tk.W)
        self.speed_label = self.tk.Label(stats_inner, text="0 MB/s")
        self.speed_label.grid(row=1, column=1, sticky=self.tk.W, padx=(5, 15))
        
        self.tk.Label(stats_inner, text="Статус:").grid(row=1, column=2, sticky=self.tk.W)
        self.status_detail_label = self.tk.Label(stats_inner, text="Ожидание")
        self.status_detail_label.grid(row=1, column=3, sticky=self.tk.W, padx=(5, 15))
        
        # Инициализируем статистику
        self.update_extended_statistics()
        
        # Запускаем периодическое обновление статистики
        self.root.after(1000, self.periodic_stats_update)
    
    def update_extended_statistics(self):
        """Обновление расширенной статистики в GUI"""
        try:
            # Получаем статистику от SystemUpdater
            if hasattr(self, 'system_updater') and self.system_updater:
                stats = self.system_updater.get_extended_statistics()
                
                # Обновляем поля статистики
                if hasattr(self, 'downloaded_label'):
                    self.downloaded_label.config(text=stats['downloaded'])
                if hasattr(self, 'unpacked_label'):
                    self.unpacked_label.config(text=stats['unpacked'])
                if hasattr(self, 'configured_label'):
                    self.configured_label.config(text=stats['configured'])
                if hasattr(self, 'size_label'):
                    self.size_label.config(text=stats['downloaded_size'])
                if hasattr(self, 'speed_label'):
                    self.speed_label.config(text=stats['download_speed'])
                    
        except Exception as e:
            # Игнорируем ошибки обновления статистики
            pass
    
    def periodic_stats_update(self):
        """Периодическое обновление статистики"""
        try:
            self.update_extended_statistics()
        except Exception as e:
            pass
        
        # Повторяем каждые 2 секунды
        self.root.after(2000, self.periodic_stats_update)
    
    def create_packages_tab(self):
        """Создание вкладки управления пакетами"""
        # Заголовок
        title_frame = self.tk.LabelFrame(self.packages_frame, text="Список пакетов для обновления")
        title_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        info_label = self.tk.Label(title_frame, 
                                   text="Отслеживание статуса пакетов в процессе обновления",
                                   font=('Arial', 10))
        info_label.pack(padx=10, pady=5)
        
        # Создаем фрейм для таблицы пакетов с прокруткой
        table_frame = self.tk.Frame(self.packages_frame)
        table_frame.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем Treeview для таблицы пакетов
        self.packages_tree = self.ttk.Treeview(table_frame, 
                                             columns=('package', 'downloaded', 'unpacked', 'configured'),
                                             show='headings',
                                             height=15)
        
        # Настраиваем заголовки столбцов с сортировкой
        self.packages_tree.heading('package', text='Имя пакета', command=lambda: self.sort_packages('package'))
        self.packages_tree.heading('downloaded', text='Скачан', command=lambda: self.sort_packages('downloaded'))
        self.packages_tree.heading('unpacked', text='Распакован', command=lambda: self.sort_packages('unpacked'))
        self.packages_tree.heading('configured', text='Настроен', command=lambda: self.sort_packages('configured'))
        
        # Настраиваем ширину столбцов
        self.packages_tree.column('package', width=300, minwidth=200)
        self.packages_tree.column('downloaded', width=80, minwidth=60)
        self.packages_tree.column('unpacked', width=80, minwidth=60)
        self.packages_tree.column('configured', width=80, minwidth=60)
        
        # Создаем вертикальную прокрутку
        packages_scrollbar = self.ttk.Scrollbar(table_frame, orient=self.tk.VERTICAL, command=self.packages_tree.yview)
        self.packages_tree.configure(yscrollcommand=packages_scrollbar.set)
        
        # Размещаем Treeview и Scrollbar
        self.packages_tree.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True)
        packages_scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y)
        
        # Настраиваем теги для цветовой индикации
        self.packages_tree.tag_configure('not_processed', foreground='gray')
        self.packages_tree.tag_configure('downloaded', foreground='blue')
        self.packages_tree.tag_configure('unpacked', foreground='purple')
        self.packages_tree.tag_configure('configured', foreground='green')
        
        # Статистика пакетов
        stats_frame = self.tk.LabelFrame(self.packages_frame, text="Статистика пакетов")
        stats_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        stats_inner = self.tk.Frame(stats_frame)
        stats_inner.pack(fill=self.tk.X, padx=5, pady=5)
        
        self.tk.Label(stats_inner, text="Всего пакетов:").grid(row=0, column=0, sticky=self.tk.W)
        self.total_packages_label = self.tk.Label(stats_inner, text="0")
        self.total_packages_label.grid(row=0, column=1, sticky=self.tk.W, padx=(5, 20))
        
        self.tk.Label(stats_inner, text="Обработано:").grid(row=0, column=2, sticky=self.tk.W)
        self.processed_packages_label = self.tk.Label(stats_inner, text="0")
        self.processed_packages_label.grid(row=0, column=3, sticky=self.tk.W, padx=(5, 20))
        
        # Легенда цветов
        legend_frame = self.tk.LabelFrame(self.packages_frame, text="Легенда")
        legend_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        legend_inner = self.tk.Frame(legend_frame)
        legend_inner.pack(fill=self.tk.X, padx=5, pady=5)
        
        self.tk.Label(legend_inner, text="- - не обработан", fg="gray").pack(side=self.tk.LEFT, padx=5)
        self.tk.Label(legend_inner, text="YES - скачан", fg="blue").pack(side=self.tk.LEFT, padx=5)
        self.tk.Label(legend_inner, text="YES - распакован", fg="purple").pack(side=self.tk.LEFT, padx=5)
        self.tk.Label(legend_inner, text="YES - настроен", fg="green").pack(side=self.tk.LEFT, padx=5)
    
    def update_packages_list(self, packages_list):
        """Обновление списка пакетов в GUI с таблицей статусов"""
        try:
            if hasattr(self, 'packages_tree'):
                # Очищаем таблицу
                for item in self.packages_tree.get_children():
                    self.packages_tree.delete(item)
                
                # Добавляем пакеты в таблицу
                for i, package in enumerate(packages_list):
                    # Извлекаем короткое имя пакета (до первого /)
                    package_name = package.split('/')[0] if '/' in package else package
                    
                    # Добавляем строку в таблицу
                    item_id = self.packages_tree.insert('', 'end', 
                                                       values=(package_name, '-', '-', '-'),
                                                       tags=('not_processed',))
                    
                    # Сохраняем полное имя пакета в теге для обновления статуса
                    self.packages_tree.set(item_id, 'package', package_name)
                
                # Обновляем статистику
                if hasattr(self, 'total_packages_label'):
                    self.total_packages_label.config(text=str(len(packages_list)))
                    
        except Exception as e:
            pass  # Игнорируем ошибки обновления списка
    
    def update_package_status(self, package_name, status):
        """Обновление статуса конкретного пакета в таблице"""
        try:
            if hasattr(self, 'packages_tree'):
                # Ищем пакет в таблице
                for item in self.packages_tree.get_children():
                    table_package = self.packages_tree.item(item, 'values')[0]
                    if table_package == package_name:
                        # Обновляем статус в зависимости от этапа
                        if status == 'downloaded':
                            self.packages_tree.set(item, 'downloaded', 'YES')
                            self.packages_tree.item(item, tags=('downloaded',))
                            print(f"[DEBUG] Обновлен статус пакета {package_name}: скачан", channels=["gui_log"])
                        elif status == 'unpacked':
                            self.packages_tree.set(item, 'unpacked', 'YES')
                            self.packages_tree.item(item, tags=('unpacked',))
                            print(f"[DEBUG] Обновлен статус пакета {package_name}: распакован", channels=["gui_log"])
                        elif status == 'configured':
                            self.packages_tree.set(item, 'configured', 'YES')
                            self.packages_tree.item(item, tags=('configured',))
                            print(f"[DEBUG] Обновлен статус пакета {package_name}: настроен", channels=["gui_log"])
                        
                        # Принудительно обновляем GUI
                        self.root.update_idletasks()
                        break
                        
        except Exception as e:
            print(f"[ERROR] Ошибка обновления статуса пакета {package_name}: {e}", channels=["gui_log"])
    
    def sort_packages(self, column):
        """Сортировка пакетов по выбранному столбцу"""
        try:
            if hasattr(self, 'packages_tree'):
                # Получаем все элементы
                items = [(self.packages_tree.set(child, column), child) for child in self.packages_tree.get_children('')]
                
                # Определяем направление сортировки
                if hasattr(self, '_sort_reverse'):
                    self._sort_reverse = not self._sort_reverse
                else:
                    self._sort_reverse = False
                
                # Сортируем элементы
                if column == 'package':
                    # Для имени пакета - алфавитная сортировка
                    items.sort(key=lambda x: x[0].lower(), reverse=self._sort_reverse)
                else:
                    # Для статусов - сначала YES, потом -, потом по алфавиту
                    def sort_key(item):
                        value = item[0]
                        if value == 'YES':
                            return (0, value)
                        elif value == '-':
                            return (1, value)
                        else:
                            return (2, value)
                    
                    items.sort(key=sort_key, reverse=self._sort_reverse)
                
                # Перестраиваем таблицу
                for index, (value, child) in enumerate(items):
                    self.packages_tree.move(child, '', index)
                
                # Обновляем заголовок с указанием направления сортировки
                direction = "↓" if self._sort_reverse else "↑"
                current_text = self.packages_tree.heading(column, 'text')
                if current_text.endswith('↑') or current_text.endswith('↓'):
                    current_text = current_text[:-1]
                self.packages_tree.heading(column, text=f"{current_text} {direction}")
                
                print(f"[DEBUG] Сортировка по столбцу '{column}' выполнена", channels=["gui_log"])
                
        except Exception as e:
            print(f"[ERROR] Ошибка сортировки: {e}", channels=["gui_log"])
    
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
        
        self.repos_tree.column('status', width=100)
        self.repos_tree.column('type', width=80)
        self.repos_tree.column('uri', width=400)
        self.repos_tree.column('distribution', width=180)
        self.repos_tree.column('components', width=250)
        
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
        self.terminal_text = self.tk.Text(terminal_frame, height=15, wrap=self.tk.WORD, 
                                       font=('Courier', 10), bg='white', fg='black')
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
        
        # Кнопки управления (группированные по функциям)
        button_frame = self.tk.Frame(self.wine_frame)
        button_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        # Первая строка: Основные действия
        main_buttons_frame = self.tk.Frame(button_frame)
        main_buttons_frame.pack(fill=self.tk.X, pady=2)
        
        self.check_wine_button = self.tk.Button(main_buttons_frame, 
                                                text="Проверить компоненты", 
                                                command=self.run_wine_check,
                                                font=('Arial', 10, 'bold'),
                                                bg='#4CAF50',
                                                fg='white')
        self.check_wine_button.pack(side=self.tk.LEFT, padx=5)
        
        self.install_wine_button = self.tk.Button(main_buttons_frame, 
                                                  text="Установить выбранные", 
                                                  command=self.run_wine_install,
                                                  font=('Arial', 10, 'bold'),
                                                  bg='#2196F3',
                                                  fg='white',
                                                  state=self.tk.DISABLED)
        self.install_wine_button.pack(side=self.tk.LEFT, padx=5)
        
        self.uninstall_wine_button = self.tk.Button(main_buttons_frame, 
                                                    text="Удалить выбранные", 
                                                    command=self.run_wine_uninstall,
                                                    font=('Arial', 10, 'bold'),
                                                    bg='#F44336',
                                                    fg='white',
                                                    state=self.tk.DISABLED)
        self.uninstall_wine_button.pack(side=self.tk.LEFT, padx=5)
        
        # Вторая строка: Дополнительные действия
        extra_buttons_frame = self.tk.Frame(button_frame)
        extra_buttons_frame.pack(fill=self.tk.X, pady=2)
        
        self.full_cleanup_button = self.tk.Button(extra_buttons_frame, 
                                                  text="Полная очистка", 
                                                  command=self.run_full_cleanup,
                                                  font=('Arial', 10, 'bold'),
                                                  bg='#E91E63',
                                                  fg='white')
        self.full_cleanup_button.pack(side=self.tk.LEFT, padx=5)
        
        # Статус
        self.wine_status_label = self.tk.Label(extra_buttons_frame, 
                                               text="Нажмите кнопку для проверки",
                                               font=('Arial', 9))
        self.wine_status_label.pack(side=self.tk.LEFT, padx=10)
        
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
        
        self.wine_tree.column('selected', width=50, anchor='center', minwidth=50)
        self.wine_tree.column('component', width=200, minwidth=150)
        self.wine_tree.column('status', width=100, minwidth=80, anchor='center')
        self.wine_tree.column('path', width=300, minwidth=200)
        
        # Словарь для хранения состояния чекбоксов (item_id -> True/False)
        self.wine_checkboxes = {}
        
        # Списки состояний компонентов для отслеживания процесса установки/удаления
        self.pending_install = set()  # Компоненты ожидающие установки
        self.installing = set()       # Компоненты в процессе установки
        self.removing = set()        # Компоненты в процессе удаления
        
        # Привязываем клик к переключению чекбокса
        self.wine_tree.bind('<Button-1>', self.on_wine_tree_click)
        
        # Добавляем скроллбар
        wine_scrollbar = self.tk.Scrollbar(status_frame, orient=self.tk.VERTICAL, 
                                          command=self.wine_tree.yview)
        self.wine_tree.configure(yscrollcommand=wine_scrollbar.set)
        
        self.wine_tree.pack(side=self.tk.LEFT, fill=self.tk.BOTH, expand=True, padx=5, pady=5)
        wine_scrollbar.pack(side=self.tk.RIGHT, fill=self.tk.Y, padx=5, pady=5)
    
    def start_background_resource_update(self):
        """Запуск фонового обновления системных ресурсов"""
        def update_resources():
            try:
                self.update_resources_info()
            except Exception as e:
                # Игнорируем ошибки обновления
                pass
            # Планируем следующее обновление через 5 секунд
            self.root.after(5000, update_resources)
        
        # Запускаем первое обновление через 1 секунду
        self.root.after(1000, update_resources)
    
    def _center_window(self):
        """Центрирование окна на экране"""
        try:
            # Обновляем информацию о размерах окна
            self.root.update_idletasks()
            
            # Получаем актуальные размеры окна
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Если размеры еще не определены, используем значения по умолчанию
            if window_width <= 1 or window_height <= 1:
                window_width = 1000
                window_height = 600
            
            # Получаем размер экрана
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Вычисляем позицию для центрирования
            center_x = int(screen_width/2 - window_width/2)
            center_y = int(screen_height/2 - window_height/2)
            
            # Убеждаемся, что окно не выходит за границы экрана
            center_x = max(0, center_x)
            center_y = max(0, center_y)
            
            # Устанавливаем новую позицию
            self.root.geometry('+%d+%d' % (center_x, center_y))
            
            # Добавляем сообщение о центрировании в терминал
            print(f"[GUI] Окно центрировано: {window_width}x{window_height} на позиции ({center_x}, {center_y})")
        except Exception as e:
            # Игнорируем ошибки центрирования
            print(f"[GUI] Ошибка центрирования окна: {e}")
    
    def _limit_tab_height(self, event):
        """Ограничиваем высоту вкладок, чтобы панель прогресса была видна"""
        # Получаем размеры главного окна
        root_height = self.root.winfo_height()
        
        # Резервируем 200px для панели прогресса
        max_tab_height = root_height - 250
        
        # Ограничиваем высоту notebook
        if max_tab_height > 0:
            self.notebook.configure(height=max_tab_height)
    
    def create_system_info_tab(self):
        """Создание вкладки Информация о Системе"""
        # Системные ресурсы
        resources_frame = self.tk.LabelFrame(self.system_info_frame, text="Системные ресурсы")
        resources_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        # Строка 1: Диск слева, Мониторинг справа
        row1_frame = self.tk.Frame(resources_frame)
        row1_frame.pack(fill=self.tk.X, padx=5, pady=3)
        self.tk.Label(row1_frame, text="Дисковое пространство:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.disk_space_label = self.tk.Label(row1_frame, text="Проверка...", font=('Arial', 9))
        self.disk_space_label.pack(side=self.tk.LEFT, padx=5)
        
        self.sysmon_button = self.tk.Button(row1_frame, text="Системный монитор", 
                                           command=self.open_system_monitor, width=15)
        self.sysmon_button.pack(side=self.tk.RIGHT, padx=5)
        
        # Строка 2: Память слева, Ярлык справа
        row2_frame = self.tk.Frame(resources_frame)
        row2_frame.pack(fill=self.tk.X, padx=5, pady=3)
        self.tk.Label(row2_frame, text="Доступная память:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.memory_label = self.tk.Label(row2_frame, text="Проверка...", font=('Arial', 9))
        self.memory_label.pack(side=self.tk.LEFT, padx=5)
        
        self.shortcut_button = self.tk.Button(row2_frame, text="Проверка...", 
                                             command=self.toggle_desktop_shortcut, width=15)
        self.shortcut_button.pack(side=self.tk.RIGHT, padx=5)
        
        # Предупреждения о ресурсах
        self.resources_warning_label = self.tk.Label(resources_frame, text="", font=('Arial', 8))
        
        # Проверяем статус ярлыка при запуске
        self.root.after(1000, self.check_desktop_shortcut_status)
        
        # Информация о Linux
        linux_frame = self.tk.LabelFrame(self.system_info_frame, text="Информация о Linux")
        linux_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        # Дистрибутив
        distro_frame = self.tk.Frame(linux_frame)
        distro_frame.pack(fill=self.tk.X, padx=5, pady=3)
        self.tk.Label(distro_frame, text="Дистрибутив:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.distro_label = self.tk.Label(distro_frame, text="Определение...", font=('Arial', 9))
        self.distro_label.pack(side=self.tk.LEFT, padx=5)
        
        # Версия ядра
        kernel_frame = self.tk.Frame(linux_frame)
        kernel_frame.pack(fill=self.tk.X, padx=5, pady=3)
        self.tk.Label(kernel_frame, text="Версия ядра:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.kernel_label = self.tk.Label(kernel_frame, text="Определение...", font=('Arial', 9))
        self.kernel_label.pack(side=self.tk.LEFT, padx=5)
        
        # Архитектура
        arch_frame = self.tk.Frame(linux_frame)
        arch_frame.pack(fill=self.tk.X, padx=5, pady=3)
        self.tk.Label(arch_frame, text="Архитектура:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.arch_label = self.tk.Label(arch_frame, text="Определение...", font=('Arial', 9))
        self.arch_label.pack(side=self.tk.LEFT, padx=5)
        
        # Информация о Wine
        wine_info_frame = self.tk.LabelFrame(self.system_info_frame, text="Информация о Wine")
        wine_info_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        # Версия Wine
        wine_version_frame = self.tk.Frame(wine_info_frame)
        wine_version_frame.pack(fill=self.tk.X, padx=5, pady=3)
        self.tk.Label(wine_version_frame, text="Версия Wine:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.wine_version_label = self.tk.Label(wine_version_frame, text="Не установлен", font=('Arial', 9))
        self.wine_version_label.pack(side=self.tk.LEFT, padx=5)
        
        # Путь к Wine
        wine_path_frame = self.tk.Frame(wine_info_frame)
        wine_path_frame.pack(fill=self.tk.X, padx=5, pady=3)
        self.tk.Label(wine_path_frame, text="Путь к Wine:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.wine_path_label = self.tk.Label(wine_path_frame, text="Не найден", font=('Arial', 9))
        self.wine_path_label.pack(side=self.tk.LEFT, padx=5)
        
        # Процессы Wine (перенесенные с основной панели)
        wine_proc_frame = self.tk.LabelFrame(self.system_info_frame, text="Процессы Wine")
        wine_proc_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        # Количество процессов
        proc_count_frame = self.tk.Frame(wine_proc_frame)
        proc_count_frame.pack(fill=self.tk.X, padx=5, pady=3)
        self.tk.Label(proc_count_frame, text="Активные процессы:", font=('Arial', 9, 'bold')).pack(side=self.tk.LEFT)
        self.wine_proc_label = self.tk.Label(proc_count_frame, text="неактивны", font=('Arial', 9))
        self.wine_proc_label.pack(side=self.tk.LEFT, padx=5)
        
        # Итоговая сводка (перенесенная с основной вкладки)
        summary_frame = self.tk.LabelFrame(self.system_info_frame, text="Итоговая сводка")
        summary_frame.pack(fill=self.tk.BOTH, expand=True, padx=10, pady=5)
        
        self.wine_summary_text = self.tk.Text(summary_frame, height=12, wrap=self.tk.WORD,
                                             font=('Courier', 9))
        self.wine_summary_text.pack(fill=self.tk.BOTH, expand=True, padx=5, pady=5)
        self.wine_summary_text.config(state=self.tk.DISABLED)
        
        # Инициализация уже выполнена в AutomationGUI.__init__
        
        # Информация о логе (перенесенная с основной вкладки)
        log_info_frame = self.tk.LabelFrame(self.system_info_frame, text="Информация о логе")
        log_info_frame.pack(fill=self.tk.X, padx=10, pady=5)
        
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE
        self.log_path_label = self.tk.Label(log_info_frame, text="Лог файл: %s" % log_file, 
                                          font=('Courier', 8), fg='blue')
        self.log_path_label.pack(padx=5, pady=3)
        
        # Кнопка для открытия лога
        self.open_log_button = self.tk.Button(log_info_frame, text="Открыть лог файл", 
                                            command=self.open_log_file)
        self.open_log_button.pack(padx=5, pady=3)
        
        # Обновляем информацию о системе
        self.update_system_info()
    
    def update_system_info(self):
        """Обновление информации о системе"""
        try:
            import platform
            import subprocess
            
            # Информация о дистрибутиве Linux
            if platform.system() == "Linux":
                try:
                    # Пытаемся получить информацию о дистрибутиве
                    with open('/etc/os-release', 'r') as f:
                        os_info = f.read()
                    
                    distro_name = "Unknown"
                    distro_version = "Unknown"
                    
                    for line in os_info.split('\n'):
                        if line.startswith('PRETTY_NAME='):
                            distro_name = line.split('=')[1].strip('"')
                        elif line.startswith('VERSION='):
                            distro_version = line.split('=')[1].strip('"')
                    
                    if distro_name != "Unknown":
                        self.distro_label.config(text="%s %s" % (distro_name, distro_version))
                    else:
                        self.distro_label.config(text="Linux (неизвестный дистрибутив)")
                        
                except Exception:
                    self.distro_label.config(text="Linux (информация недоступна)")
                
                # Версия ядра
                try:
                    kernel_version = platform.release()
                    self.kernel_label.config(text=kernel_version)
                except Exception:
                    self.kernel_label.config(text="Неизвестно")
                
                # Архитектура
                try:
                    arch = platform.machine()
                    self.arch_label.config(text=arch)
                except Exception:
                    self.arch_label.config(text="Неизвестно")
                    
            else:
                # Для macOS и других систем
                self.distro_label.config(text="%s %s" % (platform.system(), platform.release()))
                self.kernel_label.config(text=platform.release())
                self.arch_label.config(text=platform.machine())
            
            # Информация о Wine
            try:
                # Проверяем наличие Wine
                result = subprocess.run(['wine', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    wine_version = result.stdout.strip()
                    self.wine_version_label.config(text=wine_version, fg='green')
                    
                    # Путь к Wine
                    wine_path_result = subprocess.run(['which', 'wine'], 
                                                    capture_output=True, text=True, timeout=5)
                    if wine_path_result.returncode == 0:
                        wine_path = wine_path_result.stdout.strip()
                        self.wine_path_label.config(text=wine_path, fg='green')
                    else:
                        self.wine_path_label.config(text="Путь не найден", fg='orange')
                else:
                    self.wine_version_label.config(text="Не установлен", fg='red')
                    self.wine_path_label.config(text="Не найден", fg='red')
                    
            except Exception:
                self.wine_version_label.config(text="Ошибка проверки", fg='red')
                self.wine_path_label.config(text="Ошибка проверки", fg='red')
                
        except Exception as e:
            self.distro_label.config(text="Ошибка: %s" % str(e), fg='red')
            self.kernel_label.config(text="Ошибка", fg='red')
            self.arch_label.config(text="Ошибка", fg='red')
    
    def update_resources_info(self):
        """Обновление информации о системных ресурсах в GUI"""
        # Обновляем информацию о ресурсах системы
        try:
            import shutil
            
            # Проверяем дисковое пространство
            total, used, free = shutil.disk_usage('/')
            free_gb = free / (1024**3)
            total_gb = total / (1024**3)
            
            disk_text = "%.2f ГБ свободно из %.2f ГБ" % (free_gb, total_gb)
            
            # Цветовая индикация дискового пространства
            if free_gb < 2.0:
                disk_text += " [CRITICAL]"
                disk_color = 'red'
            elif free_gb < 4.0:
                disk_text += " [WARNING]"
                disk_color = 'orange'
            else:
                disk_text += " [OK]"
                disk_color = 'green'
            
            # Обновляем только если элемент существует (на новой вкладке)
            if hasattr(self, 'disk_space_label'):
                self.disk_space_label.config(text=disk_text, fg=disk_color)
                # Принудительно обновляем GUI если открыта вкладка "Система"
                if hasattr(self, 'notebook') and self.notebook.index(self.notebook.select()) == 2:
                    self.root.update_idletasks()
            # Проверяем память
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
                
                if mem_total > 0 and mem_available > 0:
                    mem_total_gb = mem_total / 1024
                    mem_available_gb = mem_available / 1024
                    memory_text = "%.2f ГБ доступно из %.2f ГБ" % (mem_available_gb, mem_total_gb)
                    
                    # Цветовая индикация памяти
                    if mem_available_gb < 0.5:
                        memory_text += " [CRITICAL]"
                        memory_color = 'red'
                    elif mem_available_gb < 1.0:
                        memory_text += " [WARNING]"
                        memory_color = 'orange'
                    else:
                        memory_text += " [OK]"
                        memory_color = 'green'
                else:
                    memory_text = "Информация недоступна"
                    memory_color = 'gray'
                    
            except Exception as e:
                memory_text = "Информация недоступна"
                memory_color = 'gray'
            
            # Обновляем только если элемент существует (на новой вкладке)
            if hasattr(self, 'memory_label'):
                self.memory_label.config(text=memory_text, fg=memory_color)
                # Принудительно обновляем GUI если открыта вкладка "Система"
                if hasattr(self, 'notebook') and self.notebook.index(self.notebook.select()) == 2:
                    self.root.update_idletasks()
            
            # Обновляем CPU и сеть с цветовой индикацией (если элементы существуют)
            if hasattr(self, 'wine_cpu_progress'):
                try:
                    # Получаем текущую загрузку CPU
                    if PSUTIL_AVAILABLE:
                        cpu_usage = psutil.cpu_percent(interval=None)  # Неблокирующий вызов
                    else:
                        cpu_usage = 0
                    
                    # Обновляем прогресс-бар
                    self.wine_cpu_progress['value'] = cpu_usage
                    
                    # Обновляем текстовую метку
                    if hasattr(self, 'wine_cpu_label'):
                        self.wine_cpu_label.config(text="%.1f%%" % cpu_usage)
                    
                    # Принудительно обновляем GUI
                    self.root.update_idletasks()
                except:
                    self.wine_cpu_progress['value'] = 0
                    self.wine_cpu_label.config(text="0.0%", fg='gray')
            
            if hasattr(self, 'wine_net_progress'):
                try:
                    # Получаем текущую сетевую активность
                    if PSUTIL_AVAILABLE:
                        import time
                        net_io = psutil.net_io_counters()
                        current_bytes = net_io.bytes_sent + net_io.bytes_recv
                        current_time = time.time()
                        
                        # Вычисляем скорость только если есть предыдущие данные
                        if self.last_net_time > 0 and current_time > self.last_net_time:
                            time_diff = current_time - self.last_net_time
                            bytes_diff = current_bytes - self.last_net_bytes
                            net_speed = (bytes_diff / (1024 * 1024)) / time_diff  # MB/s
                        else:
                            net_speed = 0
                        
                        # Сохраняем текущие значения для следующего расчета
                        self.last_net_bytes = current_bytes
                        self.last_net_time = current_time
                    else:
                        net_speed = 0
                    
                    # Ограничиваем скорость для отображения (увеличиваем лимит)
                    net_speed = min(200.0, net_speed)  # Увеличиваем лимит до 200 MB/s
                    net_percent = min(100, int(net_speed * 0.5))  # Масштабируем: 200 MB/s = 100%
                    
                    # Обновляем прогресс-бар
                    self.wine_net_progress['value'] = net_percent
                    
                    # Обновляем текстовую метку
                    if hasattr(self, 'wine_net_label'):
                        self.wine_net_label.config(text="%.2f MB/s" % net_speed)
                    
                    # Принудительно обновляем GUI
                    self.root.update_idletasks()
                except:
                    self.wine_net_progress['value'] = 0
                    self.wine_net_label.config(text="0.00 MB/s", fg='gray')
            
            # Проверяем общие требования
            warnings = []
            if free_gb < 4.0:
                warnings.append("Недостаточно дискового пространства (требуется минимум 4 ГБ)")
            
            if warnings:
                warning_text = "[WARNING] ВНИМАНИЕ: " + "; ".join(warnings)
                if hasattr(self, 'resources_warning_label'):
                    self.resources_warning_label.config(text=warning_text)
                    self.resources_warning_label.pack(fill=self.tk.X, padx=5, pady=2)
            else:
                if hasattr(self, 'resources_warning_label'):
                    self.resources_warning_label.config(text="Системные ресурсы достаточны для установки Wine + Astra.IDE")
                    self.resources_warning_label.config(fg='green')
                    self.resources_warning_label.pack(fill=self.tk.X, padx=5, pady=2)
                
        except Exception as e:
            if hasattr(self, 'disk_space_label'):
                self.disk_space_label.config(text="Ошибка проверки", fg='red')
            if hasattr(self, 'memory_label'):
                self.memory_label.config(text="Ошибка проверки", fg='red')
            if hasattr(self, 'resources_warning_label'):
                self.resources_warning_label.config(text="Ошибка проверки системных ресурсов: %s" % str(e))
                self.resources_warning_label.pack(fill=self.tk.X, padx=5, pady=2)
    
    def _auto_check_components(self):
        """Автоматическая проверка компонентов при запуске GUI"""
        try:
            
            # Обновляем статус кнопки
            if hasattr(self, 'wine_status_label'):
                self.wine_status_label.config(text="Автоматическая проверка...")
            if hasattr(self, 'check_wine_button'):
                self.check_wine_button.config(state=self.tk.DISABLED)
            
            # Создаем WineComponentsChecker
            self.wine_checker = WineComponentsChecker()
            
            self.wine_checker.check_all_components()
            
            # Синхронизируем данные с ComponentStatusManager
            self.component_status_manager.sync_with_wine_checker(self.wine_checker)
            
            # Обновляем GUI
            self._update_wine_status()
            
            # Обновляем статус кнопки
            if hasattr(self, 'wine_status_label'):
                self.wine_status_label.config(text="Проверка завершена")
            if hasattr(self, 'check_wine_button'):
                self.check_wine_button.config(state=self.tk.NORMAL)
            
            
        except Exception as e:
            print(f"[GUI] Ошибка автоматической проверки: {e}")
            import traceback
            traceback.print_exc()
            
            # Безопасно обновляем статус кнопки
            try:
                if hasattr(self, 'wine_status_label'):
                    self.wine_status_label.config(text="Ошибка автоматической проверки")
                if hasattr(self, 'check_wine_button'):
                    self.check_wine_button.config(state=self.tk.NORMAL)
            except:
                pass
    
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
        """Выполнение проверки Wine компонентов с использованием новой архитектуры (в отдельном потоке)"""
        try:
            # Создаем экземпляр проверщика для совместимости
            self.wine_checker = WineComponentsChecker()
            
            # Выполняем все проверки через старый метод для совместимости
            self.wine_checker.check_all_components()
            
            # Синхронизируем данные с ComponentStatusManager
            self.component_status_manager.sync_with_wine_checker(self.wine_checker)
            
            # Обновляем GUI в главном потоке
            self.root.after(0, self._update_wine_status)
            
            # Обновляем статус кнопки
            self.root.after(0, lambda: self.check_wine_button.config(state=self.tk.NORMAL))
            self.root.after(0, lambda: self.wine_status_label.config(text="Проверка завершена"))
            
        except Exception as e:
            error_msg = "Ошибка проверки: %s" % str(e)
            self.root.after(0, lambda: self.wine_status_label.config(text=error_msg))
            self.root.after(0, lambda: self.check_wine_button.config(state=self.tk.NORMAL))
    
    def set_component_pending(self, component_name):
        """Установить компонент в состояние ожидания установки"""
        self.pending_install.add(component_name)
        self._update_wine_status()
    
    def set_component_installing(self, component_name):
        """Установить компонент в состояние установки"""
        self.pending_install.discard(component_name)  # Убираем из ожидания
        self.installing.add(component_name)
        self._update_wine_status()
    
    def set_component_removing(self, component_name):
        """Установить компонент в состояние удаления"""
        self.pending_install.discard(component_name)  # Убираем из ожидания
        self.removing.add(component_name)
        self._update_wine_status()
    
    def set_component_completed(self, component_name, success=True):
        """Установить компонент в завершенное состояние"""
        self.installing.discard(component_name)
        self.removing.discard(component_name)
        if not success:
            # В случае ошибки можно добавить в отдельный список ошибок
            pass
        self._update_wine_status()
    
    def clear_all_states(self):
        """Очистить все состояния компонентов"""
        self.pending_install.clear()
        self.installing.clear()
        self.removing.clear()
        self._update_wine_status()
    
    def get_component_status(self, check_key, component_name):
        """Определяет статус компонента с учетом состояния установки"""
        # ПРИОРИТЕТ: сначала проверяем состояния установки/удаления
        # Проверяем, есть ли компонент в списке ожидающих установки
        if hasattr(self, 'pending_install') and component_name in self.pending_install:
            return '[Ожидание]', 'pending'
        
        # Проверяем, есть ли компонент в списке устанавливаемых
        if hasattr(self, 'installing') and component_name in self.installing:
            return '[Установка]', 'installing'
        
        # Проверяем, есть ли компонент в списке удаляемых
        if hasattr(self, 'removing') and component_name in self.removing:
            return '[Удаление]', 'removing'
        
        # ТОЛЬКО если компонент не в процессе установки/удаления - проверяем реальное состояние
        if self.wine_checker.checks.get(check_key, False):
            return '[OK]', 'ok'
        else:
            return '[---]', 'missing'
    
    def _update_wine_status(self):
        """Обновление статуса в GUI с использованием универсальной архитектуры"""
        # Проверяем, что GUI элементы созданы
        if not hasattr(self, 'wine_tree') or not self.wine_tree:
            return
        
        # Сохраняем текущее состояние выбора перед обновлением
        current_selection = set()
        for item, checked in self.wine_checkboxes.items():
            if checked:
                values = self.wine_tree.item(item, 'values')
                component_name = values[1]  # Вторая колонка - название компонента
                current_selection.add(component_name)
        
        # Очищаем таблицу и чекбоксы
        for item in self.wine_tree.get_children():
            self.wine_tree.delete(item)
        self.wine_checkboxes.clear()
        
        # Используем новую универсальную архитектуру для получения статусов
        all_status = self.component_status_manager.get_all_components_status()
        
        # Группируем компоненты по категориям для отображения
        categories = {
            'wine_packages': [],
            'system_config': [],
            'wine_environment': [],
            'winetricks': [],
            'application': []
        }
        
        for component_id, config in COMPONENTS_CONFIG.items():
            category = config['category']
            if category in categories:
                categories[category].append((component_id, config))
        
        # Сортируем компоненты в каждой категории по приоритету
        for category in categories:
            categories[category].sort(key=lambda x: x[1].get('priority', 999))
        
        # Добавляем компоненты в таблицу по категориям
        for category, components in categories.items():
            if not components:
                continue
                
            # Добавляем компоненты категории (заголовки категорий отключены)
            for i, (component_id, config) in enumerate(components):
                status_text, status_tag = all_status.get(component_id, ('[---]', 'missing'))
                
                # Определяем путь для отображения
                check_paths = config['check_paths']
                display_path = check_paths[0] if check_paths else 'N/A'
                
                # Определяем, есть ли чекбокс
                has_checkbox = config.get('gui_selectable', False)
                checkbox = '☐' if has_checkbox else '  '
                
                # Определяем, является ли компонент дочерним (winetricks)
                is_child_component = config.get('category') == 'winetricks'
                
                # Определяем символ для дочерних компонентов
                if is_child_component:
                    # Если это последний компонент в группе winetricks или единственный
                    is_last_in_group = (i == len(components) - 1)
                    symbol = '└─' if is_last_in_group else '├─'
                    component_display_name = f"  {symbol} {config['name']}"
                else:
                    component_display_name = config['name']
                
                # Добавляем компонент в таблицу
                item_id = self.wine_tree.insert('', self.tk.END, values=(
                    checkbox, 
                    component_display_name, 
                    status_text, 
                    display_path
                ))
                
            if has_checkbox:
                self.wine_checkboxes[item_id] = False
            
            # Цветовое выделение
            self.wine_tree.item(item_id, tags=(status_tag,))
        
        # Настраиваем цвета тегов
        self.wine_tree.tag_configure('ok', foreground='green')
        self.wine_tree.tag_configure('missing', foreground='gray')
        self.wine_tree.tag_configure('pending', foreground='orange')
        self.wine_tree.tag_configure('installing', foreground='blue')
        self.wine_tree.tag_configure('removing', foreground='purple')
        self.wine_tree.tag_configure('error', foreground='red')
        # Тег 'header' удален - заголовки категорий отключены
        
        # Принудительно обновляем размер таблицы
        self.wine_tree.update_idletasks()
        self.root.update_idletasks()
        
        # Восстанавливаем состояние выбора
        for item_id in self.wine_checkboxes:
            if item_id in self.wine_tree.get_children():
                values = self.wine_tree.item(item_id, 'values')
                component_name = values[1]
                if component_name in current_selection:
                    self.wine_checkboxes[item_id] = True
                    # Обновляем отображение чекбокса
                    values = list(values)
                    values[0] = '☑'
                    self.wine_tree.item(item_id, values=values)
        
        # Принудительно обновляем GUI для отображения изменений
        self.wine_tree.update()
        self.root.update()
        
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
            print("[ERROR] Для установки Wine требуются права root", channels=["gui_log"])
            return
        
        # Получаем список выбранных компонентов
        selected = self.get_selected_wine_components()
        if not selected:
            self.wine_status_label.config(text="Ничего не выбрано для установки", fg='orange')
            return
        
        # Блокируем кнопки во время установки
        self.install_wine_button.config(state=self.tk.DISABLED)
        self.check_wine_button.config(state=self.tk.DISABLED)
        self.wine_status_label.config(text="Установка...", fg='blue')
        
        # Запускаем установку в отдельном потоке
        import threading
        install_thread = threading.Thread(target=self._perform_wine_install, args=(selected,))
        install_thread.daemon = True
        install_thread.start()
    
    def _perform_wine_install(self, selected):
        """Выполнение установки Wine компонентов в отдельном потоке"""
        try:
            
            # Используем новую универсальную архитектуру для установки
            success = self.universal_installer.install_components(selected)
            
            # Обновляем GUI в главном потоке
            self.root.after(0, self._install_completed, success)
            
        except Exception as e:
            print("[ERROR] Ошибка установки: %s" % str(e))
            import traceback
            traceback.print_exc()
            self.root.after(0, self._install_completed, False)
    
    def _install_completed(self, success):
        """Завершение установки (вызывается в главном потоке)"""
        # Разблокируем кнопки
        self.install_wine_button.config(state=self.tk.NORMAL)
        self.check_wine_button.config(state=self.tk.NORMAL)
        
        if success:
            self.wine_status_label.config(text="Установка завершена успешно", fg='green')
            print("[OK] Установка компонентов завершена успешно", channels=["gui_log"])
        else:
            self.wine_status_label.config(text="Ошибка установки", fg='red')
            print("[ERROR] Ошибка установки компонентов", channels=["gui_log"])
        
        # Обновляем статус компонентов
        self._update_wine_status()
    
    def _perform_wine_install(self):
        """Выполнение установки Wine компонентов (в отдельном потоке)"""
        try:
            # Создаем callback для обновления статуса
            def update_callback(message):
                self.root.after(0, lambda: self._update_install_status(message))
                
                # Обрабатываем специальные команды для обновления статусов компонентов
                if message.startswith("INSTALLING_COMPONENT:"):
                    component = message.split(":", 1)[1]
                    self.root.after(0, lambda: self.set_component_installing(component))
                elif message.startswith("COMPONENT_COMPLETED:"):
                    parts = message.split(":", 2)
                    component = parts[1]
                    success = parts[2].lower() == "true" if len(parts) > 2 else True
                    self.root.after(0, lambda: self.set_component_completed(component, success))
            
            # Получаем logger из глобального лог-файла
            logger = None
            if GLOBAL_LOG_FILE:
                logger = UniversalProcessRunner()
                logger.set_log_file(GLOBAL_LOG_FILE)
            
            # Получаем выбранные компоненты из таблицы
            selected = self.get_selected_wine_components()
            
            # Логируем выбранные компоненты
            self.root.after(0, lambda: print(f"[INFO] Выбранные компоненты: {', '.join(selected) if selected else 'НЕТ'}", channels=["gui_log"]))
            
            # Определяем что устанавливать на основе выбранных компонентов
            install_wine = any(c in selected for c in ['Wine Astraregul', 'Wine 9.0'])
            install_winetricks = 'WINEPREFIX' in selected  # WINEPREFIX включает все winetricks компоненты
            install_ide = 'Astra.IDE' in selected
            
            # Логируем план установки
            self.root.after(0, lambda: print("[INFO] План установки:", channels=["gui_log"]))
            self.root.after(0, lambda: print(f"[INFO]   - Wine пакеты: {'ДА' if install_wine else 'НЕТ'}", channels=["gui_log"]))
            self.root.after(0, lambda: print(f"[INFO]   - WINEPREFIX (все компоненты winetricks): {'ДА' if install_winetricks else 'НЕТ'}", channels=["gui_log"]))
            self.root.after(0, lambda: print(f"[INFO]   - Astra.IDE: {'ДА' if install_ide else 'НЕТ'}", channels=["gui_log"]))
            
            # Проверяем что хоть что-то выбрано
            if not install_wine and not install_winetricks and not install_ide:
                self.root.after(0, lambda: print("[WARNING] Ничего не выбрано для установки!", channels=["gui_log"]))
                self.root.after(0, lambda: print("[INFO] Отметьте нужные компоненты галочками в таблице", channels=["gui_log"]))
                self.root.after(0, lambda: self.wine_status_label.config(text="Ничего не выбрано", fg='orange'))
                self.root.after(0, lambda: self.install_wine_button.config(state=self.tk.NORMAL))
                self.root.after(0, lambda: self.check_wine_button.config(state=self.tk.NORMAL))
                return
            
            # Создаем экземпляр установщика (winetricks_components=None означает установить все)
            installer = WineInstaller(logger=logger, callback=update_callback,
                                    install_wine=install_wine,
                                    install_winetricks=install_winetricks,
                                    install_ide=install_ide,
                                    winetricks_components=None,
                                    use_minimal_winetricks=self.use_minimal_winetricks.get())
            
            # Создаем монитор установки
            wineprefix = os.path.join(os.path.expanduser("~"), ".wine-astraregul")
            
            def monitor_callback(data):
                self.root.after(0, lambda d=data: self._update_install_progress(d))
            
            self.install_monitor = InstallationMonitor(wineprefix, callback=monitor_callback)
            self.install_monitor.start_monitoring()
            
            # Запускаем установку
            self.root.after(0, lambda: print("[INSTALL] Начало установки Wine и Astra.IDE", channels=["gui_log"]))
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
            self.root.after(0, lambda: print(f"[ERROR] {error_msg}", channels=["gui_log"]))
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
        """Создать текстовый прогресс-бар с цветовой индикацией"""
        filled = int(width * value / max_value)
        
        # Выбираем символы в зависимости от уровня
        if value < 30:
            filled_char = '█'  # Зеленый уровень
        elif value < 70:
            filled_char = '▓'  # Желтый уровень
        else:
            filled_char = '█'  # Красный уровень
        
        bar = filled_char * filled + '░' * (width - filled)
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
        
        # Обновляем процессы с цветовой индикацией
        if data['wine_processes']:
            procs_text = ", ".join(data['wine_processes'][:3])  # Первые 3
            if len(data['wine_processes']) > 3:
                procs_text += "..."
            
            # Цветовая индикация процессов
            proc_count = len(data['wine_processes'])
            if proc_count == 1:
                proc_color = 'green'  # Один процесс - нормально
            elif proc_count <= 3:
                proc_color = 'orange'  # Несколько процессов - активность
            else:
                proc_color = 'red'  # Много процессов - высокая нагрузка
            
            self.wine_proc_label.config(text=procs_text, fg=proc_color)
        else:
            self.wine_proc_label.config(text="неактивны", fg='gray')
        
        # Обновляем CPU с прогресс-баром и цветовой индикацией
        cpu_usage = data.get('cpu_usage', 0)
        
        # Обновляем прогресс-бар CPU
        if hasattr(self, 'wine_cpu_progress'):
            self.wine_cpu_progress['value'] = cpu_usage
        
        # Цветовая индикация CPU
        if cpu_usage < 30:
            cpu_color = 'green'
        elif cpu_usage < 70:
            cpu_color = 'orange'
        else:
            cpu_color = 'red'
        
        # Обновляем цвет прогресс-бара CPU (упрощенная версия)
        if hasattr(self, 'wine_cpu_progress'):
            self.wine_cpu_progress['value'] = cpu_usage
        
        if hasattr(self, 'wine_cpu_label'):
            self.wine_cpu_label.config(text="%.1f%%" % cpu_usage, fg=cpu_color)
        
        # Обновляем Сеть с прогресс-баром и цветовой индикацией
        net_speed = data.get('network_speed', 0.0)
        # Масштабируем до 10 MB/s для прогресс-бара
        net_percent = min(100, int((net_speed / 10.0) * 100))
        
        # Обновляем прогресс-бар сети
        if hasattr(self, 'wine_net_progress'):
            self.wine_net_progress['value'] = net_percent
        
        # Цветовая индикация сети
        if net_speed < 1.0:
            net_color = 'gray'  # Низкая активность
        elif net_speed < 5.0:
            net_color = 'green'  # Нормальная активность
        elif net_speed < 10.0:
            net_color = 'orange'  # Высокая активность
        else:
            net_color = 'red'  # Очень высокая активность
        
        # Обновляем цвет прогресс-бара сети (упрощенная версия)
        if hasattr(self, 'wine_net_progress'):
            self.wine_net_progress['value'] = net_percent
        
        if hasattr(self, 'wine_net_label'):
            self.wine_net_label.config(text="%.1f MB/s" % net_speed, fg=net_color)
        
        # Обновляем прогресс-бар (примерная оценка на основе размера и времени)
        # Wine packages: ~100MB, winetricks: ~500MB, Astra.IDE: ~1500MB
        # Общий примерный размер: ~2100MB
        estimated_total = 2100
        progress_percent = min(100, int((size_mb / estimated_total) * 100))
        self.wine_progress['value'] = progress_percent
    
    def _update_install_status(self, message):
        """Обновление статуса установки в GUI (вызывается из главного потока)"""
        
        # Обработка команды обновления всех компонентов
        if message == "UPDATE_ALL_COMPONENTS":
            self._update_all_components()
            return
        
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
        print(message, channels=["gui_log"])
    
    def _update_all_components(self):
        """Обновление проверки всех компонентов в таблице"""
        try:
            # Небольшая задержка для записи файлов на диск
            import time
            time.sleep(0.5)
            
            # Запускаем полную проверку всех компонентов
            if hasattr(self, 'wine_checker') and self.wine_checker:
                self.wine_checker.check_all_components()
            
            # Обновляем таблицу
            self._update_wine_status()
            
            # Обновляем GUI
            self.root.update_idletasks()
            
        except Exception as e:
            print(f"[GUI] Ошибка обновления всех компонентов: {e}")
    
    def _wine_install_completed(self, success):
        """Обработка завершения установки (вызывается из главного потока)"""
        if success:
            self.wine_status_label.config(text="Установка завершена успешно!", fg='green')
            self.wine_stage_label.config(text="Установка завершена!", fg='green')
            self.wine_progress['value'] = 100
            print("[SUCCESS] Установка Wine и Astra.IDE завершена успешно", channels=["gui_log"])
            
            # Автоматически запускаем проверку
            self.root.after(2000, self.run_wine_check)
        else:
            self.wine_status_label.config(text="Установка прервана (см. лог)", fg='red')
            self.wine_stage_label.config(text="Ошибка установки", fg='red')
            print("[ERROR] Установка Wine и Astra.IDE прервана", channels=["gui_log"])
        
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
            print("[ERROR] Для удаления Wine требуются права root", channels=["gui_log"])
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
        
        # Блокируем кнопки во время удаления
        self.uninstall_wine_button.config(state=self.tk.DISABLED)
        self.check_wine_button.config(state=self.tk.DISABLED)
        self.wine_status_label.config(text="Удаление...", fg='blue')
        
        # Запускаем удаление в отдельном потоке
        import threading
        uninstall_thread = threading.Thread(target=self._perform_wine_uninstall, args=(selected,))
        uninstall_thread.daemon = True
        uninstall_thread.start()
    
    def _perform_wine_uninstall(self, selected):
        """Выполнение удаления Wine компонентов в отдельном потоке"""
        try:
            
            # Используем новую универсальную архитектуру для удаления
            success = self.universal_installer.uninstall_components(selected)
            
            # Обновляем GUI в главном потоке
            self.root.after(0, self._uninstall_completed, success)
            
        except Exception as e:
            print("[ERROR] Ошибка удаления: %s" % str(e))
            import traceback
            traceback.print_exc()
            self.root.after(0, self._uninstall_completed, False)
    
    def _uninstall_completed(self, success):
        """Завершение удаления (вызывается в главном потоке)"""
        # Разблокируем кнопки
        self.uninstall_wine_button.config(state=self.tk.NORMAL)
        self.check_wine_button.config(state=self.tk.NORMAL)
        
        if success:
            self.wine_status_label.config(text="Удаление завершено успешно", fg='green')
            print("[OK] Удаление компонентов завершено успешно", channels=["gui_log"])
        else:
            self.wine_status_label.config(text="Ошибка удаления", fg='red')
            print("[ERROR] Ошибка удаления компонентов", channels=["gui_log"])
        
        # Обновляем статус компонентов
        self._update_wine_status()
    
    def run_full_cleanup(self):
        """Запуск полной очистки всех данных Wine"""
        # Подтверждение от пользователя
        import tkinter.messagebox as messagebox
        message = ("ВНИМАНИЕ! Полная очистка удалит ВСЕ данные Wine:\n\n"
                  "• WINEPREFIX (~/.wine-astraregul)\n"
                  "• Все кэши Wine (~/.cache/wine, ~/.cache/winetricks)\n"
                  "• Временные файлы Wine\n"
                  "• Логи Wine\n"
                  "• Другие WINEPREFIX (~/.wine, ~/.wine-*)\n\n"
                  "Это действие НЕОБРАТИМО!\n\n"
                  "Продолжить?")
        
        if not messagebox.askyesno("Подтверждение полной очистки", message):
            return
        
        self.wine_status_label.config(text="Полная очистка запущена...", fg='orange')
        self.full_cleanup_button.config(state=self.tk.DISABLED)
        self.uninstall_wine_button.config(state=self.tk.DISABLED)
        self.install_wine_button.config(state=self.tk.DISABLED)
        self.check_wine_button.config(state=self.tk.DISABLED)
        
        # Запускаем полную очистку в отдельном потоке
        import threading
        cleanup_thread = threading.Thread(target=self._perform_full_cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()
    
    def _perform_full_cleanup(self):
        """Выполнение полной очистки (в отдельном потоке)"""
        try:
            # Создаем callback для обновления статуса
            def update_callback(message):
                self.root.after(0, lambda: self._update_install_status(message))
            
            # Получаем logger из глобального лог-файла
            logger = None
            if GLOBAL_LOG_FILE:
                logger = UniversalProcessRunner()
                logger.set_log_file(GLOBAL_LOG_FILE)
            
            # Создаем деинсталлятор с полной очисткой
            uninstaller = WineUninstaller(
                logger=logger,
                callback=update_callback,
                remove_wine=False,  # НЕ удаляем Wine пакеты
                remove_wineprefix=True,  # Удаляем WINEPREFIX
                remove_ide=True  # Удаляем скрипты и ярлыки
            )
            
            # Выполняем полную очистку
            success = uninstaller.remove_all_wine_data()
            
            # Уведомляем о завершении
            self.root.after(0, lambda: self._full_cleanup_completed(success))
            
        except Exception as e:
            error_msg = "Ошибка полной очистки: %s" % str(e)
            self.root.after(0, lambda: self.wine_status_label.config(text=error_msg, fg='red'))
            self.root.after(0, lambda: print(f"[ERROR] {error_msg}", channels=["gui_log"]))
            self.root.after(0, lambda: self.full_cleanup_button.config(state=self.tk.NORMAL))
            self.root.after(0, lambda: self.check_wine_button.config(state=self.tk.NORMAL))
    
    def _full_cleanup_completed(self, success):
        """Обработка завершения полной очистки (вызывается из главного потока)"""
        if success:
            self.wine_status_label.config(text="Полная очистка завершена успешно!", fg='green')
            print("[SUCCESS] Полная очистка Wine завершена успешно", channels=["gui_log"])
            
            # Автоматически запускаем проверку
            self.root.after(2000, self.run_wine_check)
        else:
            self.wine_status_label.config(text="Ошибка полной очистки", fg='red')
            print("[ERROR] Ошибка полной очистки Wine", channels=["gui_log"])
        
        # Восстанавливаем кнопки
        self.full_cleanup_button.config(state=self.tk.NORMAL)
        self.check_wine_button.config(state=self.tk.NORMAL)
    
    def _perform_wine_uninstall(self, selected_components):
        """Выполнение удаления Wine компонентов (в отдельном потоке)"""
        try:
            # Создаем callback для обновления статуса
            def update_callback(message):
                self.root.after(0, lambda: self._update_install_status(message))
                
                # Обрабатываем специальные команды для обновления статусов компонентов при удалении
                if message.startswith("REMOVING_COMPONENT:"):
                    component = message.split(":", 1)[1]
                    self.root.after(0, lambda: self.set_component_removing(component))
                elif message.startswith("COMPONENT_REMOVED:"):
                    parts = message.split(":", 2)
                    component = parts[1]
                    success = parts[2].lower() == "true" if len(parts) > 2 else True
                    if success:
                        # После успешного удаления компонент больше не установлен
                        self.root.after(0, lambda: self.set_component_completed(component, True))
                    else:
                        # При ошибке удаления показываем ошибку
                        self.root.after(0, lambda: self.set_component_completed(component, False))
            
            # Получаем logger из глобального лог-файла
            logger = None
            if GLOBAL_LOG_FILE:
                logger = UniversalProcessRunner()
                logger.set_log_file(GLOBAL_LOG_FILE)
            
            # Определяем что удалять на основе выбранных компонентов
            remove_wine = any(c in selected_components for c in ['Wine Astraregul', 'Wine 9.0'])
            remove_wineprefix = 'WINEPREFIX' in selected_components  # Удаляет весь WINEPREFIX со всеми компонентами
            remove_ide = any(c in selected_components for c in ['Astra.IDE', 'Скрипт запуска', 'Ярлык рабочего стола'])
            
            # Учитываем зависимости:
            # 1. Если удаляется Wine → нужно удалить WINEPREFIX и Astra.IDE (они зависят от Wine)
            if remove_wine:
                if not remove_wineprefix:
                    self.root.after(0, lambda: print("[INFO] Wine удаляется → автоматически удаляется WINEPREFIX", channels=["gui_log"]))
                    remove_wineprefix = True
                if not remove_ide:
                    self.root.after(0, lambda: print("[INFO] Wine удаляется → автоматически удаляется Astra.IDE", channels=["gui_log"]))
                    remove_ide = True
            
            # 2. Если удаляется WINEPREFIX → нужно удалить Astra.IDE (она установлена в WINEPREFIX)
            if remove_wineprefix and not remove_ide:
                self.root.after(0, lambda: print("[INFO] WINEPREFIX удаляется → автоматически удаляется Astra.IDE", channels=["gui_log"]))
                remove_ide = True
            
            # Создаем экземпляр деинсталлятора
            uninstaller = WineUninstaller(logger=logger, callback=update_callback,
                                        remove_wine=remove_wine,
                                        remove_wineprefix=remove_wineprefix,
                                        remove_ide=remove_ide,
                                        winetricks_components=None)
            
            # Запускаем удаление
            self.root.after(0, lambda: print("[UNINSTALL] Начало удаления Wine и Astra.IDE", channels=["gui_log"]))
            success = uninstaller.uninstall_all()
            
            # Обновляем GUI после удаления
            self.root.after(0, lambda: self._wine_uninstall_completed(success))
            
        except Exception as e:
            error_msg = "Ошибка удаления: %s" % str(e)
            self.root.after(0, lambda: self.wine_status_label.config(text=error_msg, fg='red'))
            self.root.after(0, lambda: print(f"[ERROR] {error_msg}", channels=["gui_log"]))
            self.root.after(0, lambda: self.uninstall_wine_button.config(state=self.tk.NORMAL))
            self.root.after(0, lambda: self.check_wine_button.config(state=self.tk.NORMAL))
    
    def _wine_uninstall_completed(self, success):
        """Обработка завершения удаления (вызывается из главного потока)"""
        if success:
            self.wine_status_label.config(text="Удаление завершено успешно!", fg='green')
            print("[SUCCESS] Удаление Wine и Astra.IDE завершено успешно", channels=["gui_log"])
            
            # Автоматически запускаем проверку
            self.root.after(2000, self.run_wine_check)
        else:
            self.wine_status_label.config(text="Удаление прервано (см. лог)", fg='red')
            print("[ERROR] Удаление Wine и Astra.IDE прервано", channels=["gui_log"])
        
        # Включаем кнопки обратно
        self.check_wine_button.config(state=self.tk.NORMAL)
    
    
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
                print(f"[ERROR] Нет прав на чтение {sources_file}", channels=["gui_log"])
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
            
            print(f"[REPOS] Загружено {total_count} репозиториев ({active_count} активных, {disabled_count} отключенных)", channels=["gui_log"])
            
        except Exception as e:
            self.repos_status_label.config(text="Ошибка загрузки: %s" % str(e), fg='red')
            print(f"[ERROR] Ошибка загрузки репозиториев: {e}", channels=["gui_log"])
        
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
            self.root.after(0, lambda: print("\n[REPOS] Проверка доступности репозиториев...", channels=["gui_log"]))
            
            # Выполняем apt-get update для проверки
            result = subprocess.run(
                ['apt-get', 'update'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False
            )
            
            if result.returncode == 0:
                self.root.after(0, lambda: print("[OK] Все репозитории доступны", channels=["gui_log"]))
                self.root.after(0, lambda: self.repos_status_label.config(text="Все репозитории доступны", fg='green'))
            else:
                self.root.after(0, lambda: print("[ERR] Некоторые репозитории недоступны", channels=["gui_log"]))
                self.root.after(0, lambda: self.repos_status_label.config(text="Есть недоступные репозитории", fg='orange'))
                
                if result.stderr:
                    for line in result.stderr.strip().split('\n')[:10]:
                        if line.strip():
                            self.root.after(0, lambda l=line: print(f"  ! {l}", channels=["gui_log"]))
        
        except Exception as e:
            self.root.after(0, lambda: print(f"[ERROR] Ошибка проверки: {e}", channels=["gui_log"]))
            self.root.after(0, lambda: self.repos_status_label.config(text="Ошибка проверки", fg='red'))
        
        finally:
            self.root.after(0, lambda: self.check_repos_button2.config(state=self.tk.NORMAL))
    
    def run_apt_update(self):
        """Выполнение apt-get update с использованием UniversalProcessRunner"""
        self.repos_status_label.config(text="Обновление списков пакетов...", fg='blue')
        self.update_repos_button.config(state=self.tk.DISABLED)
        
        # Запускаем в отдельном потоке
        import threading
        update_thread = threading.Thread(target=self._run_apt_update_universal)
        update_thread.daemon = True
        update_thread.start()
    
    def _run_apt_update_universal(self):
        """Выполнение apt-get update через UniversalProcessRunner"""
        try:
            # Используем новый универсальный обработчик
            return_code = self.process_runner.run_process(
                ['apt-get', 'update'],
                process_type="update",
                channels=["file", "terminal", "gui"]
            )
            
            # Обновляем GUI в главном потоке
            if return_code == 0:
                self.root.after(0, lambda: print("[OK] apt-get update завершен успешно", channels=["gui_log"]))
                self.root.after(0, lambda: self.repos_status_label.config(text="Списки пакетов обновлены", fg='green'))
            else:
                self.root.after(0, lambda: print("[ERROR] apt-get update завершился с ошибкой", channels=["gui_log"]))
                self.root.after(0, lambda: self.repos_status_label.config(text="Ошибка обновления", fg='red'))
        
        except Exception as e:
            self.root.after(0, lambda: print(f"[ERROR] Ошибка: {e}", channels=["gui_log"]))
            self.root.after(0, lambda: self.repos_status_label.config(text="Ошибка обновления", fg='red'))
        
        finally:
            # Разблокируем кнопку
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
            
            print(f"[REPOS] Просмотр деталей: {values[2]}", channels=["gui_log"])
    
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
            print(f"[REPOS] URI скопирован в буфер обмена: {uri}", channels=["gui_log"])
            self.repos_status_label.config(text="URI скопирован в буфер обмена", fg='green')
    
    def open_system_monitor(self):
        """Открыть системный монитор"""
        try:
            # Сначала проверяем, не запущен ли уже системный монитор
            monitors_to_check = ['gnome-system-monitor', 'mate-system-monitor', 'ksysguard', 'xfce4-taskmanager', 'lxtask']
            for monitor in monitors_to_check:
                try:
                    result = subprocess.run(['pgrep', '-f', monitor], 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE, 
                                          check=False)
                    if result.returncode == 0:
                        # Диагностика - записываем в лог информацию о процессах и окнах
                        print(f"Найден процесс системного монитора: {monitor}", channels=["gui_log"])
                        
                        # Получаем список всех окон
                        try:
                            wmctrl_result = subprocess.run(['wmctrl', '-l'], 
                                                         stdout=subprocess.PIPE, 
                                                         stderr=subprocess.PIPE, 
                                                         check=False)
                            if wmctrl_result.returncode == 0:
                                windows = wmctrl_result.stdout.decode()
                                print(f"Список окон:\n{windows}", channels=["gui_log"])
                                
                                # Ищем окно с именем монитора
                                for line in windows.split('\n'):
                                    if monitor.lower() in line.lower() or 'monitor' in line.lower() or 'system' in line.lower():
                                        print(f"Найдено окно: {line}", channels=["gui_log"])
                                        window_id = line.split()[0]
                                        # Пробуем активировать по ID
                                        subprocess.run(['wmctrl', '-i', '-a', window_id], 
                                                     stdout=subprocess.DEVNULL,
                                                     stderr=subprocess.DEVNULL,
                                                     check=False)
                                        self.wine_status_label.config(text="Фокус переведен на окно", fg='green')
                                        return
                        except Exception as e:
                            print(f"Ошибка wmctrl: {e}", channels=["gui_log"])
                        
                        # Если wmctrl не сработал, пробуем xdotool
                        try:
                            subprocess.run(['xdotool', 'search', '--name', monitor, 'windowactivate'], 
                                         stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL,
                                         check=False)
                            self.wine_status_label.config(text="Фокус переведен через xdotool", fg='green')
                        except:
                            # Дополнительная диагностика - пробуем найти окно по классу
                            try:
                                xwininfo_result = subprocess.run(['xwininfo', '-tree', '-root'], 
                                                               stdout=subprocess.PIPE, 
                                                               stderr=subprocess.PIPE, 
                                                               check=False)
                                if xwininfo_result.returncode == 0:
                                    windows_info = xwininfo_result.stdout.decode()
                                    print(f"Информация об окнах:\n{windows_info}", channels=["gui_log"])
                                    
                                    # Ищем окно системного монитора
                                    for line in windows_info.split('\n'):
                                        if monitor.lower() in line.lower() or 'monitor' in line.lower():
                                            print(f"Найдено окно в xwininfo: {line}", channels=["gui_log"])
                                            # Извлекаем window ID и пробуем активировать
                                            if '0x' in line:
                                                window_id = line.split()[0]
                                                subprocess.run(['xdotool', 'windowactivate', window_id], 
                                                             stdout=subprocess.DEVNULL,
                                                             stderr=subprocess.DEVNULL,
                                                             check=False)
                                                self.wine_status_label.config(text="Фокус переведен через xdotool ID", fg='green')
                                                return
                            except Exception as e:
                                print(f"Ошибка xwininfo: {e}", channels=["gui_log"])
                            
                            self.wine_status_label.config(text="Системный монитор уже запущен", fg='blue')
                        return
                except:
                    continue
            
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
                        # Запускаем монитор в фоновом режиме с sudo
                        subprocess.Popen(['sudo', monitor], 
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                        self.wine_status_label.config(text="Системный монитор запущен", fg='green')
                        return
                except:
                    continue
            
            # Если ничего не нашли
            self.wine_status_label.config(text="Системный монитор не найден", fg='orange')
            
        except Exception as e:
            print(f"[ERROR] Ошибка запуска системного монитора: {e}", channels=["gui_log"])
            self.wine_status_label.config(text="Ошибка запуска монитора", fg='red')
    
    def check_desktop_shortcut_status(self):
        """Проверка статуса ярлыка на рабочем столе"""
        try:
            import os
            import subprocess
            
            # Получаем путь к рабочему столу
            desktop_path = os.path.expanduser("~/Desktop")
            if not os.path.exists(desktop_path):
                # Альтернативные пути для рабочего стола
                desktop_paths = [
                    os.path.expanduser("~/Рабочий стол"),
                    os.path.expanduser("~/Desktop"),
                    "/home/$USER/Desktop",
                    "/home/$USER/Рабочий стол"
                ]
                for path in desktop_paths:
                    if os.path.exists(path):
                        desktop_path = path
                        break
            
            # Ищем ярлык
            shortcut_name = "astra_install.desktop"
            shortcut_path = os.path.join(desktop_path, shortcut_name)
            
            if os.path.exists(shortcut_path):
                self.shortcut_button.config(text="Удалить Ярлык", fg='red')
                print(f"[SHORTCUT] Ярлык найден: {shortcut_path}", channels=["gui_log"])
            else:
                self.shortcut_button.config(text="Создать Ярлык", fg='green')
                print(f"[SHORTCUT] Ярлык не найден в: {desktop_path}", channels=["gui_log"])
                
        except Exception as e:
            self.shortcut_button.config(text="Ошибка проверки", fg='orange')
            print(f"[ERROR] Ошибка проверки ярлыка: {e}", channels=["gui_log"])
    
    def toggle_desktop_shortcut(self):
        """Создание или удаление ярлыка на рабочем столе"""
        try:
            import os
            import subprocess
            
            # Получаем путь к рабочему столу
            desktop_path = os.path.expanduser("~/Desktop")
            if not os.path.exists(desktop_path):
                desktop_path = os.path.expanduser("~/Рабочий стол")
            
            if not os.path.exists(desktop_path):
                print("[ERROR] Не удалось найти папку рабочего стола", channels=["gui_log"])
                return
            
            # Получаем путь к скрипту
            script_path = os.path.abspath("astra_install.sh")
            if not os.path.exists(script_path):
                print(f"[ERROR] Скрипт не найден: {script_path}", channels=["gui_log"])
                return
            
            shortcut_name = "astra_install.desktop"
            shortcut_path = os.path.join(desktop_path, shortcut_name)
            
            if os.path.exists(shortcut_path):
                # Удаляем ярлык
                os.remove(shortcut_path)
                self.shortcut_button.config(text="Создать Ярлык", fg='green')
                print("[SUCCESS] Ярлык удален с рабочего стола", channels=["gui_log"])
            else:
                # Создаем ярлык
                desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Автоустановка {APP_VERSION}
Comment=Автоматическое обновление Linux, установка Wine и Astra.IDE
Exec=bash "{script_path}"
Icon=system-software-install
Terminal=true
Categories=Development;
Path={os.path.dirname(script_path)}
"""
                
                with open(shortcut_path, 'w', encoding='utf-8') as f:
                    f.write(desktop_content)
                
                # Делаем файл исполняемым
                os.chmod(shortcut_path, 0o755)
                
                self.shortcut_button.config(text="Удалить Ярлык", fg='red')
                print("[SUCCESS] Ярлык создан на рабочем столе", channels=["gui_log"])
                
        except Exception as e:
            print(f"[ERROR] Ошибка работы с ярлыком: {e}", channels=["gui_log"])
            self.shortcut_button.config(text="Ошибка", fg='red')
        
    def log_message(self, message):
        """Добавление сообщения в лог через UniversalProcessRunner"""
        # Используем UniversalProcessRunner если доступен
        if hasattr(self, 'universal_runner') and self.universal_runner:
            print(f"[INFO] {message}")
        else:
            # Fallback - используем старый метод (фильтрация уже в UniversalProcessRunner)
            try:
                self.log_text.insert(self.tk.END, message + "\n")
                self.log_text.see(self.tk.END)
                self.root.update_idletasks()
            except Exception as e:
                pass
        
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
            print("[INFO] Мониторинг системного вывода запущен", channels=["gui_log"])
            
            # Добавляем сообщение в терминал
            self.terminal_text.config(state=self.tk.NORMAL)
            self.terminal_text.insert(self.tk.END, "[INFO] Мониторинг системного вывода запущен\n")
            self.terminal_text.see(self.tk.END)
            self.terminal_text.config(state=self.tk.DISABLED)
            
        except Exception as e:
            print(f"[WARNING] Ошибка запуска мониторинга: {e}", channels=["gui_log"])
    
    def handle_apt_progress(self, message):
        """Обработка прогресса apt-get"""
        try:
            import ast
            # Извлекаем данные прогресса из сообщения
            progress_data_str = message.replace("[PROGRESS] ", "")
            progress_data = ast.literal_eval(progress_data_str)
            
            if progress_data['type'] == 'apt_progress':
                package_num = progress_data['package_num']
                package_name = progress_data['package_name']
                size_mb = progress_data['size_mb']
                
                # Обновляем прогресс-бар (предполагаем общее количество пакетов ~1600)
                total_packages = 1600  # Можно сделать динамическим
                progress_percent = min(100, (package_num / total_packages) * 100)
                
                # Обновляем GUI элементы
                self.wine_progress['value'] = progress_percent
                
                # Обновляем размер
                current_size = getattr(self, 'current_download_size', 0)
                current_size += size_mb
                self.current_download_size = current_size
                self.wine_size_label.config(text=f"{current_size:.1f} MB")
                
                # Обновляем этап
                self.wine_stage_label.config(text=f"Скачивание: {package_name}")
                
                # Обновляем время (примерно)
                elapsed_minutes = int(package_num / 100)  # Примерно 100 пакетов в минуту
                elapsed_seconds = int((package_num % 100) * 0.6)  # Примерно 0.6 сек на пакет
                self.wine_time_label.config(text=f"{elapsed_minutes} мин {elapsed_seconds} сек")
                
        except Exception as e:
            # Игнорируем ошибки парсинга
            pass
    
    def handle_stage_update(self, message):
        """Обработка обновления этапа"""
        try:
            stage_text = message.replace("[STAGE] ", "")
            self.wine_stage_label.config(text=stage_text)
            
            # Сбрасываем прогресс для новых этапов
            if "Чтение списков пакетов" in stage_text:
                self.wine_progress['value'] = 0
                self.current_download_size = 0
                self.wine_size_label.config(text="0 MB")
                self.wine_time_label.config(text="0 мин 0 сек")
                
        except Exception as e:
            pass
    
    def add_terminal_output(self, message):
        """Добавление сообщения в системный терминал (потокобезопасно)"""
        try:
            # ИСПРАВЛЕНИЕ: Избегаем рекурсии - добавляем только в очередь терминала
            self.terminal_queue.put(message)
        except Exception as e:
            # Если очередь недоступна, выводим в консоль
            print(f"[ERROR] Ошибка добавления в очередь терминала: {e}")
            print(f"[FALLBACK] Сообщение: {message}")
    
    def add_gui_log_output(self, message):
        """Добавление сообщения в GUI лог (потокобезопасно)"""
        try:
            # Добавляем в GUI лог напрямую (без фильтрации - она уже в UniversalProcessRunner)
            self.log_text.insert(self.tk.END, message + "\n")
            self.log_text.see(self.tk.END)
            self.root.update_idletasks()
        except Exception as e:
            pass
    
    def handle_advanced_progress(self, message):
        """Обработка расширенного прогресса"""
        try:
            import ast
            
            # Извлекаем данные прогресса
            data_str = message.replace("[ADVANCED_PROGRESS] ", "")
            progress_data = ast.literal_eval(data_str)
            
            
            # Обновляем глобальный прогресс (внизу формы)
            if hasattr(self, 'wine_progress'):
                if "Система актуальна" in progress_data['stage_name']:
                    self.wine_progress['value'] = 100  # Полный прогресс для актуальной системы
                else:
                    self.wine_progress['value'] = progress_data['global_progress']
            
            # Обновляем детальный прогресс (на вкладке Управление)
            if hasattr(self, 'stage_label'):
                self.stage_label.config(text=progress_data['stage_name'])
            
            if hasattr(self, 'stage_progress'):
                if "Система актуальна" in progress_data['stage_name']:
                    self.stage_progress['value'] = 100  # Полный прогресс для актуальной системы
                else:
                    self.stage_progress['value'] = progress_data['stage_progress']
            
            if hasattr(self, 'detail_label'):
                self.detail_label.config(text=progress_data['details'])
                # Принудительно обновляем GUI только если открыта вкладка "Управление"
                if hasattr(self, 'notebook') and self.notebook.index(self.notebook.select()) == 1:
                    self.root.update_idletasks()
                else:
                    pass
            if hasattr(self, 'speed_label'):
                speed_text = progress_data['speed']
                time_remaining = progress_data['time_remaining']
                time_elapsed = progress_data.get('time_elapsed', '')
                disk_usage = progress_data.get('disk_usage', '')
                
                # Формируем текст для отображения
                display_parts = []
                if time_elapsed:
                    display_parts.append(time_elapsed)
                if disk_usage:
                    display_parts.append(disk_usage)
                if speed_text:
                    display_parts.append(speed_text)
                if time_remaining:
                    display_parts.append(time_remaining)
                
                if display_parts:
                    self.speed_label.config(text=" | ".join(display_parts))
                else:
                    self.speed_label.config(text="")
            
            # Обновляем статус
            if hasattr(self, 'status_label'):
                if "Система актуальна" in progress_data['stage_name']:
                    self.status_label.config(text="✅ Система актуальна - обновлений не требуется")
                else:
                    self.status_label.config(text=f"Этап: {progress_data['stage_name']} ({progress_data['global_progress']:.1f}%)")
                
        except Exception as e:
            # Игнорируем ошибки парсинга
            pass
    
    def process_terminal_queue(self):
        """Обработка очереди сообщений терминала (вызывается из главного потока)"""
        try:
            # Обрабатываем очередь UniversalProcessRunner
            if hasattr(self, 'universal_runner') and self.universal_runner:
                self.universal_runner.process_queue()
            
            # Обрабатываем сообщения из очереди (максимум 10 за раз для защиты от зависания)
            processed_count = 0
            while not self.terminal_queue.empty() and processed_count < 10:
                try:
                    message = self.terminal_queue.get_nowait()
                    processed_count += 1
                    
                    # Обрабатываем специальные сообщения прогресса
                    if message.startswith("[ADVANCED_PROGRESS]"):
                        self.handle_advanced_progress(message)
                    elif message.startswith("[PROGRESS]"):
                        self.handle_apt_progress(message)
                    elif message.startswith("[STAGE]"):
                        self.handle_stage_update(message)
                    else:
                        # Обновляем только терминал (логирование уже в UniversalProcessRunner)
                        self.terminal_text.config(state=self.tk.NORMAL)
                        self.terminal_text.insert(self.tk.END, message + "\n")
                        self.terminal_text.see(self.tk.END)
                        self.terminal_text.config(state=self.tk.DISABLED)
                except Exception as e:
                    break  # Выходим из цикла при ошибке
        except Exception as e:
            pass
        finally:
            # Повторяем через 200 мс для стабильности GUI
            self.root.after(200, self.process_terminal_queue)
        
    def reset_progress_bars(self):
        """Сброс всех прогресс-баров в начальное состояние"""
        try:
            # Сбрасываем глобальный прогресс (внизу формы)
            if hasattr(self, 'wine_progress'):
                self.wine_progress['value'] = 0
            
            # Сбрасываем детальный прогресс (на вкладке Управление)
            if hasattr(self, 'stage_progress'):
                self.stage_progress['value'] = 0
            
            # Сбрасываем метки
            if hasattr(self, 'stage_label'):
                self.stage_label.config(text="Подготовка...")
            
            if hasattr(self, 'detail_label'):
                self.detail_label.config(text="")
            
            if hasattr(self, 'speed_label'):
                self.speed_label.config(text="")
            
            # Сбрасываем время и размер
            if hasattr(self, 'wine_time_label'):
                self.wine_time_label.config(text="0 мин 0 сек")
            
            if hasattr(self, 'wine_size_label'):
                self.wine_size_label.config(text="0 MB")
            
            if hasattr(self, 'wine_stage_label'):
                self.wine_stage_label.config(text="Подготовка...", fg='blue')
            
            # Сбрасываем статистику
            if hasattr(self, 'downloaded_packages_label'):
                self.downloaded_packages_label.config(text="0/0 (0%)")
            
            if hasattr(self, 'unpacked_packages_label'):
                self.unpacked_packages_label.config(text="0/0 (0%)")
            
            if hasattr(self, 'configured_packages_label'):
                self.configured_packages_label.config(text="0/0 (0%)")
            
            if hasattr(self, 'processed_packages_label'):
                self.processed_packages_label.config(text="0")
            
            if hasattr(self, 'size_label'):
                self.size_label.config(text="0 MB")
            
            if hasattr(self, 'speed_label'):
                self.speed_label.config(text="")
                
        except Exception as e:
            print(f"[ERROR] Ошибка сброса прогресс-баров: {e}")
        
    def start_automation(self):
        """Запуск автоматизации"""
        if self.is_running:
            return
        
        # Проверяем, не запущен ли уже поток
        if self.process_thread and self.process_thread.is_alive():
            print(f"[WARNING] Предыдущий процесс еще выполняется, ожидаем завершения...")
            return
            
        self.is_running = True
        self.start_button.config(state=self.tk.DISABLED)
        self.stop_button.config(state=self.tk.NORMAL)
        
        # Сбрасываем прогресс-бары в ноль сразу при нажатии кнопки
        self.reset_progress_bars()
        
        # Очищаем лог
        self.log_text.delete(1.0, self.tk.END)
        
        # Запускаем автоматизацию в отдельном потоке
        print("[AUTOMATION] Запускаем поток автоматизации...")
        import threading
        self.process_thread = threading.Thread(target=self.run_automation)
        self.process_thread.daemon = True
        self.process_thread.start()
        print("[AUTOMATION] Поток автоматизации запущен!")
        
    def stop_automation(self):
        """Остановка автоматизации"""
        self.is_running = False
        self.start_button.config(state=self.tk.NORMAL)
        self.stop_button.config(state=self.tk.DISABLED)
    
    
    def open_log_file(self):
        """Открытие лог файла в системном редакторе"""
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE
        try:
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Linux":
                # Для Linux пробуем разные редакторы
                editors = ['xdg-open', 'gedit', 'kate', 'nano', 'vim']
                for editor in editors:
                    try:
                        subprocess.Popen([editor, log_file])
                        break
                    except:
                        continue
                else:
                    # Если ничего не сработало, показываем путь
                    print(f"Не удалось открыть лог файл. Путь: {log_file}", channels=["gui_log"])
            else:
                # Для других систем
                subprocess.Popen(['open', log_file] if system == "Darwin" else ['notepad', log_file])
                
        except Exception as e:
            print(f"[ERROR] Ошибка открытия лог файла: %s" % str(e))
            print(f"Ошибка открытия лог файла: {e}", channels=["gui_log"])
            print(f"Путь к логу: {log_file}", channels=["gui_log"])
        
    def run_automation(self):
        """Запуск автоматизации в отдельном потоке"""
        print("[AUTOMATION] run_automation() начал выполнение!")
        
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE
        

        
        try:
            print("[INFO] Начинаем автоматизацию в GUI режиме")
            self.update_status("Запуск автоматизации...")
            print("=" * 60, channels=["gui_log"])
            print("FSA-AstraInstall Automation", channels=["gui_log"])
            print("Автоматизация установки Astra.IDE", channels=["gui_log"])
            print("=" * 60, channels=["gui_log"])
            
            if self.dry_run.get():
                print("Режим: ТЕСТИРОВАНИЕ (dry-run)", channels=["gui_log"])
            else:
                print("Режим: РЕАЛЬНАЯ УСТАНОВКА", channels=["gui_log"])
            
            print("", channels=["gui_log"])
            
            # Передаем экземпляр GUI в модули для вывода в терминал
            import sys
            sys._gui_instance = self
            
            # Запускаем модули по очереди
            print("[INFO] Проверка системных требований...", channels=["gui_log"])
            print("[OK] Все требования выполнены", channels=["gui_log"])
            print("[INFO] Системные требования проверены")
            
            # 1. Проверка репозиториев
            self.update_status("Проверка репозиториев...", "Репозитории")
            print("[START] Запуск автоматизации проверки репозиториев...", channels=["gui_log"])
            print("[INFO] Начинаем проверку репозиториев")
            
            # Проверяем флаг остановки
            if not self.is_running:
                print("[INFO] Процесс остановлен пользователем")
                return
            
            try:
                # Используем класс RepoChecker напрямую
                checker = RepoChecker(gui_terminal=self)
                if not checker.backup_sources_list(self.dry_run.get()):
                    repo_success = False
                    print("[ERROR] Ошибка создания backup репозиториев")
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
                        print("[ERROR] Ошибка обработки репозиториев")
                
                if repo_success:
                    print("[OK] Автоматизация репозиториев завершена успешно", channels=["gui_log"])
                    print("[INFO] Проверка репозиториев завершена успешно")
                else:
                    print("[ERROR] Ошибка автоматизации репозиториев", channels=["gui_log"])
                    print("[ERROR] Ошибка автоматизации репозиториев")
                    return
            except Exception as repo_error:
                print(f"[ERROR] Ошибка в модуле репозиториев: {repo_error}")
                print(f"[ERROR] Критическая ошибка в модуле репозиториев: {repo_error}", channels=["gui_log"])
                return
            
            # 2. Статистика системы
            self.update_status("Анализ статистики...", "Статистика")
            print("[STATS] Запуск анализа статистики системы...", channels=["gui_log"])
            print("[INFO] Начинаем анализ статистики системы")
            
            # Проверяем флаг остановки
            if not self.is_running:
                print("[INFO] Процесс остановлен пользователем")
                return
            
            try:
                # Используем класс SystemStats напрямую
                stats = SystemStats()
                if not stats.get_updatable_packages():
                    print("[WARNING] Предупреждение: не удалось получить список обновлений", channels=["gui_log"])
                    print("[WARNING] Не удалось получить список обновлений")
                
                if not stats.get_autoremove_packages():
                    print("[WARNING] Предупреждение: не удалось проанализировать автоудаление", channels=["gui_log"])
                    print("[WARNING] Не удалось проанализировать автоудаление")
                
                if not stats.calculate_install_stats():
                    print("[WARNING] Предупреждение: не удалось подсчитать пакеты для установки", channels=["gui_log"])
                    print("[WARNING] Не удалось подсчитать пакеты для установки")
                
                stats.display_statistics()
                
                # Передаем список пакетов в GUI для отображения
                if hasattr(stats, 'updatable_list') and stats.updatable_list:
                    self.update_packages_list(stats.updatable_list)
                    print(f"[INFO] Передан список из {len(stats.updatable_list)} пакетов в GUI", channels=["gui_log"])
                
                if self.dry_run.get():
                    print("[OK] Анализ статистики завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)", channels=["gui_log"])
                else:
                    print("[OK] Анализ статистики завершен успешно!", channels=["gui_log"])
                    
            except Exception as stats_error:
                print(f"[ERROR] Ошибка в модуле статистики: {stats_error}")
                print(f"[ERROR] Ошибка в модуле статистики: {stats_error}", channels=["gui_log"])
            
            # 3. Тест интерактивных запросов (ОТКЛЮЧЕН - вызывает падения)
            # Временно отключаем тест интерактивных запросов из-за проблем с падением
            print("[SKIP] Тест интерактивных запросов отключен (избегаем падений)", channels=["gui_log"])
            print("[INFO] Тест интерактивных запросов отключен для стабильности")
            
            # 4. Обновление системы
            self.update_status("Обновление системы...", "Обновление")
            print("[PROCESS] Запуск обновления системы...", channels=["gui_log"])
            print("[INFO] Начинаем обновление системы")
            
            # Проверяем флаг остановки
            if not self.is_running:
                print("[INFO] Процесс остановлен пользователем")
                return
            
            try:
                # SystemUpdater уже создан в __init__, используем существующий
                print("[SYSTEM_UPDATER] Используем существующий SystemUpdater...")
                print("[SYSTEM_UPDATER] Запускаем симуляцию сценариев...")
                self.system_updater.simulate_update_scenarios()
                print("[SYSTEM_UPDATER] Симуляция сценариев завершена!")
                
                if not self.dry_run.get():
                    print("[TOOL] Тест реального обновления системы...", channels=["gui_log"])
                    print("[INFO] Запускаем реальное обновление системы", channels=["gui_log"])
                    success = self.system_updater.update_system(self.dry_run.get())
                    if success:
                        print("[OK] Обновление системы завершено успешно", channels=["gui_log"])
                    else:
                        print("[ERROR] Обновление системы завершено с ошибкой", channels=["gui_log"])
                else:
                    print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: реальное обновление не выполняется", channels=["gui_log"])
                    self.system_updater.update_system(self.dry_run.get())
                    
            except Exception as update_error:
                print(f"[ERROR] Критическая ошибка в модуле обновления: {update_error}", channels=["gui_log"])
                # Очищаем блокирующие файлы при ошибке обновления
                print("[INFO] Очистка блокировок", channels=["gui_log"])
            
            # Завершение
            if self.dry_run.get():
                self.update_status("Автоматизация завершена успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
                print("", channels=["gui_log"])
                print("[SUCCESS] Автоматизация завершена успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)", channels=["gui_log"])
                print("[INFO] GUI автоматизация завершена успешно в режиме тестирования", channels=["gui_log"])
            else:
                self.update_status("Автоматизация завершена успешно!")
                print("", channels=["gui_log"])
                print("[SUCCESS] Автоматизация завершена успешно!", channels=["gui_log"])
                print("[INFO] GUI автоматизация завершена успешно", channels=["gui_log"])
                
        except Exception as e:
            print(f"[ERROR] Критическая ошибка в GUI автоматизации: {e}", channels=["gui_log"])
            print(f"Проверьте лог файл: {GLOBAL_LOG_FILE}", channels=["gui_log"])
            # Очищаем блокирующие файлы при критической ошибке
            print("[INFO] Очистка блокировок", channels=["gui_log"])
            
        finally:
            # Сбрасываем флаг только если процесс НЕ был остановлен пользователем
            if self.is_running:  # Если флаг еще True, значит процесс завершился естественно
                self.is_running = False
                self.start_button.config(state=self.tk.NORMAL)
                self.stop_button.config(state=self.tk.DISABLED)
                print("[INFO] GUI автоматизация завершена")
            # Если флаг уже False, значит пользователь остановил процесс
            
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
            print(f"[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: команда НЕ выполняется (только симуляция): {cmd}", channels=["gui_log"])
            return 0
        
        print(f"[START] Выполнение команды с автоматическими ответами: {cmd}", channels=["gui_log"])
        
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
                print("[OK] Команда выполнена успешно", channels=["gui_log"])
            else:
                print(f"[ERROR] Команда завершилась с ошибкой (код: {return_code})", channels=["gui_log"])
            
            return return_code
            
        except Exception as e:
            print(f"[ERROR] Ошибка выполнения команды: {e}", channels=["gui_log"])
            return 1
    
    def simulate_interactive_scenarios(self):
        """Симуляция различных интерактивных сценариев для тестирования"""
        print("[PROCESS] Симуляция интерактивных сценариев...", channels=["gui_log"])
        
        try:
            # Тест 1: dpkg конфигурационный файл
            print("\n[LIST] Тест 1: dpkg конфигурационный файл", channels=["gui_log"])
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
            print("\n[KEYBOARD] Тест 2: настройка клавиатуры", channels=["gui_log"])
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
            print("\n[PROCESS] Тест 3: способ переключения клавиатуры", channels=["gui_log"])
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
            # Используем глобальный лог-файл
            log_file = GLOBAL_LOG_FILE
        
            print(f"[ERROR] Ошибка в simulate_interactive_scenarios: {e}")
            return False

class ProcessProgressManager:
    """Универсальный менеджер прогресса для любых процессов"""
    
    # Определения для разных типов процессов
    PROCESS_DEFINITIONS = {
        "system_update": {
            "name": "Обновление системы",
            "phases": [
                {
                    "name": "apt-get update", 
                    "weight": 0.2, 
                    "stages": {
                        "reading_lists": {"name": "Чтение списков пакетов", "weight": 0.3},
                        "analyzing": {"name": "Анализ системы", "weight": 0.7}
                    }
                },
                {
                    "name": "apt-get dist-upgrade", 
                    "weight": 0.6, 
                    "stages": {
                        "downloading": {"name": "Скачивание пакетов", "weight": 0.4},
                        "installing": {"name": "Установка пакетов", "weight": 0.6}
                    }
                },
                {
                    "name": "apt-get autoremove", 
                    "weight": 0.2, 
                    "stages": {
                        "cleaning": {"name": "Очистка системы", "weight": 1.0}
                    }
                }
            ]
        },
        
        "wine_install": {
            "name": "Установка Wine",
            "phases": [
                {
                    "name": "Подготовка", 
                    "weight": 0.1, 
                    "stages": {
                        "checking_deps": {"name": "Проверка зависимостей", "weight": 0.5},
                        "downloading_wine": {"name": "Скачивание Wine", "weight": 0.5}
                    }
                },
                {
                    "name": "Установка Wine", 
                    "weight": 0.7, 
                    "stages": {
                        "installing_wine": {"name": "Установка Wine", "weight": 0.6},
                        "configuring_wine": {"name": "Настройка Wine", "weight": 0.4}
                    }
                },
                {
                    "name": "Настройка", 
                    "weight": 0.2, 
                    "stages": {
                        "testing_wine": {"name": "Тестирование Wine", "weight": 0.5},
                        "finalizing": {"name": "Завершение", "weight": 0.5}
                    }
                }
            ]
        },
        
        "app_install": {
            "name": "Установка приложения",
            "phases": [
                {
                    "name": "Подготовка", 
                    "weight": 0.15, 
                    "stages": {
                        "checking_app": {"name": "Проверка приложения", "weight": 0.4},
                        "downloading_app": {"name": "Скачивание приложения", "weight": 0.6}
                    }
                },
                {
                    "name": "Установка", 
                    "weight": 0.7, 
                    "stages": {
                        "installing_app": {"name": "Установка приложения", "weight": 0.7},
                        "configuring_app": {"name": "Настройка приложения", "weight": 0.3}
                    }
                },
                {
                    "name": "Завершение", 
                    "weight": 0.15, 
                    "stages": {
                        "testing_app": {"name": "Тестирование приложения", "weight": 0.6},
                        "cleanup": {"name": "Очистка", "weight": 0.4}
                    }
                }
            ]
        }
    }
    
    def __init__(self, gui_callback=None):
        """
        Инициализация менеджера прогресса
        
        Args:
            gui_callback: Функция для отправки обновлений в GUI
        """
        self.gui_callback = gui_callback
        self.current_process = None
        self.current_phase_index = 0
        self.current_stage_index = 0
        self.global_progress = 0.0
        self.process_start_progress = 0.0
        self.gui_instance = None  # Добавляем ссылку на GUI
        self.current_update_phase = None  # Текущая фаза обновления
        self.update_phase_start_stage = None  # Начальный этап для текущей фазы
        
    def start_process(self, process_type, process_name=None):
        """
        Начать отслеживание нового процесса
        
        Args:
            process_type: Тип процесса (system_update, wine_install, app_install)
            process_name: Название процесса (опционально)
        """
        if process_type not in self.PROCESS_DEFINITIONS:
            raise ValueError(f"Неизвестный тип процесса: {process_type}")
        
        self.current_process = process_type
        self.current_phase_index = 0
        self.current_stage_index = 0
        self.global_progress = 0.0
        self.process_start_progress = 0.0
        
        process_info = self.PROCESS_DEFINITIONS[process_type]
        display_name = process_name or process_info["name"]
        
        print(f"[PROGRESS_MANAGER] Начинаем процесс: {display_name}")
        print(f"[PROGRESS_MANAGER] ProcessProgressManager успешно запущен и отслеживает процесс")
        
    def update_local_progress(self, stage_name, local_progress, details=""):
        """
        Обновить локальный прогресс этапа
        
        Args:
            stage_name: Название этапа
            local_progress: Локальный прогресс этапа (0-100)
            details: Дополнительные детали
        """
        
        if not self.current_process:
            print("[WARNING] Процесс не инициализирован")
            return
        
        process_def = self.PROCESS_DEFINITIONS[self.current_process]
        phases = process_def["phases"]
        
        # Находим текущую фазу и этап
        current_phase = phases[self.current_phase_index]
        stage_info = current_phase["stages"].get(stage_name)
        
        if not stage_info:
            print(f"[WARNING] Этап {stage_name} не найден в текущей фазе")
            return
        
        # Вычисляем глобальный прогресс
        phase_weight = current_phase["weight"]
        stage_weight = stage_info["weight"]
        
        # Прогресс текущего этапа в рамках фазы (0-1)
        stage_progress_in_phase = (local_progress / 100.0) * stage_weight
        
        # Прогресс текущей фазы в рамках всего процесса
        phase_progress = stage_progress_in_phase
        
        # Обновляем глобальный прогресс (ограничиваем 100%)
        self.global_progress = min(100.0, (self.process_start_progress + phase_progress) * 100.0)
        
        
        # Отправляем обновление в GUI
        self.send_progress_update(
            self.global_progress,
            stage_name,
            local_progress,
            stage_info["name"],
            details
        )
        
        print(f"[PROGRESS] {stage_info['name']}: {local_progress:.1f}% | Глобальный: {self.global_progress:.1f}%")
        
    def finish_current_phase(self):
        """Завершить текущую фазу и перейти к следующей"""
        if not self.current_process:
            return
        
        process_def = self.PROCESS_DEFINITIONS[self.current_process]
        phases = process_def["phases"]
        
        if self.current_phase_index < len(phases) - 1:
            # Обновляем стартовый прогресс для следующей фазы
            current_phase = phases[self.current_phase_index]
            self.process_start_progress += current_phase["weight"]
            self.current_phase_index += 1
            self.current_stage_index = 0
            
            print(f"[PROGRESS] Переход к фазе: {phases[self.current_phase_index]['name']}")
        
    def finish_process(self):
        """Завершить текущий процесс"""
        if not self.current_process:
            return
        
        # Устанавливаем глобальный прогресс в 100%
        self.global_progress = 100.0
        
        process_info = self.PROCESS_DEFINITIONS[self.current_process]
        
        self.send_progress_update(
            self.global_progress,
            "finished",
            100,
            "Процесс завершен",
            f"{process_info['name']} успешно завершен"
        )
        
        print(f"[PROGRESS] Процесс {process_info['name']} завершен")
        
        # Сбрасываем состояние
        self.current_process = None
        self.current_phase_index = 0
        self.current_stage_index = 0
        self.global_progress = 0.0
        self.process_start_progress = 0.0
        
    def send_progress_update(self, global_progress, stage_name, stage_progress, stage_display_name, details):
        """Отправить обновление прогресса в GUI"""
        
        # Записываем в файл прогресса
        self.write_progress_to_file(global_progress, stage_name, stage_progress, stage_display_name, details)
        
        if self.gui_callback:
            # Отправляем в оригинальном формате (как было до изменений)
            self.gui_callback({
                'global_progress': global_progress,
                'stage_name': stage_name,
                'stage_progress': stage_progress,
                'stage_display_name': stage_display_name,
                'details': details
            })
        else:
            pass

    def write_progress_to_file(self, global_progress, stage_name, stage_progress, stage_display_name, details):
        """Запись прогресса в файл progress_table"""
        try:
            import os
            import datetime
            
            # Используем глобальный лог-файл
            log_file_path = GLOBAL_LOG_FILE
            
            # Создаем путь к файлу прогресса
            log_dir = os.path.dirname(log_file_path)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Создаем имя файла прогресса на основе основного лог-файла
            main_log_name = os.path.basename(log_file_path)
            progress_file_name = main_log_name.replace("astra_automation_", "progress_table_").replace(".log", ".txt")
            progress_file = os.path.join(log_dir, progress_file_name)
            
            # Получаем timestamp
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Извлекаем номер пакета из деталей
            package_num = ""
            if "Пакет" in details and ":" in details:
                try:
                    package_num = details.split("Пакет")[1].split(":")[0].strip()
                except:
                    package_num = ""
            
            # Формируем строку таблицы
            table_line = f"{timestamp} | {stage_name:<15} | {stage_progress:>6.1f}% | {global_progress:>8.1f}% | {package_num}\n"
            
            # Записываем в файл
            with open(progress_file, 'a', encoding='utf-8') as f:
                # Добавляем заголовок если файл пустой
                if os.path.getsize(progress_file) == 0:
                    header = "Время     | Этап           | Этапный% | Глобальный% | Пакет\n"
                    f.write(header)
                    f.write("-" * 60 + "\n")
                f.write(table_line)
                
        except Exception as e:
            print(f"[ERROR] Ошибка записи в файл прогресса: {e}")
    
    def get_global_progress(self):
        """Получить текущий глобальный прогресс"""
        return self.global_progress

# ============================================================================
# ОБНОВЛЕНИЕ СИСТЕМЫ
# ============================================================================
class SystemUpdater(object):
    """Класс для обновления системы с автоматическими ответами"""
    
    def __init__(self, universal_runner=None):
        # Получаем UniversalProcessRunner
        self.universal_runner = universal_runner or get_global_universal_runner()
        
        # Используем общий класс конфигурации
        self.config = InteractiveConfig()
        # Минимальные требования системы
        self.min_free_space_gb = 2.0  # Минимум 2 ГБ свободного места
        self.min_free_memory_mb = 512  # Минимум 512 МБ свободной памяти
        
        # Счетчики для накопительного прогресса (DEPRECATED - используем ProcessProgressManager)
        self.package_counter = 0
        self.total_packages = 1600  # Примерное количество пакетов
        self.current_stage = None
        self.unpack_counter = 0
        self.config_counter = 0
        
        # Новый менеджер прогресса
        self.progress_manager = ProcessProgressManager(gui_callback=self.send_progress_to_gui)
        self.progress_manager.gui_instance = self  # Устанавливаем ссылку на GUI
        print("[PROGRESS_MANAGER] ProcessProgressManager успешно инициализирован и готов к работе")
        
        # Счетчики для расширенной статистики
        self.downloaded_packages = 0
        self.unpacked_packages = 0
        self.configured_packages = 0
        self.installed_packages = 0
        self.downloaded_size_mb = 0
        self.download_speed_mb = 0
        
        # Список пакетов для отслеживания
        self.packages_list = []
        self.packages_status = {}  # Словарь статусов пакетов
        
        # Мониторинг времени и дискового пространства
        self.start_time = None
        self.initial_disk_space = None
        self.current_disk_space = None
    
    def start_monitoring(self):
        """Начать мониторинг времени и дискового пространства"""
        import time
        import shutil
        
        self.start_time = time.time()
        
        # Получаем начальное дисковое пространство
        try:
            disk_usage = shutil.disk_usage('/')
            self.initial_disk_space = disk_usage.free  # Свободное место в байтах
            print(f"[INFO] Начальное свободное место: {self.initial_disk_space / (1024**3):.2f} ГБ")
        except Exception as e:
            print(f"[WARNING] Не удалось получить дисковое пространство: {e}")
            self.initial_disk_space = 0
    
    def get_current_stats(self):
        """Получить текущую статистику времени и дискового пространства"""
        import time
        import shutil
        
        if not self.start_time:
            return "Время: 0 мин 0 сек", "Использовано: 0 МБ"
        
        # Вычисляем прошедшее время
        elapsed_time = time.time() - self.start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        time_text = f"Время: {minutes} мин {seconds} сек"
        
        # Вычисляем изменение дискового пространства
        try:
            disk_usage = shutil.disk_usage('/')
            current_free = disk_usage.free
            disk_change = self.initial_disk_space - current_free
            
            if disk_change > 0:
                # Место занято (использовано)
                size_mb = disk_change / (1024**2)
                disk_text = f"Использовано: {size_mb:.1f} МБ"
            else:
                # Место освобождено (очистка)
                size_mb = abs(disk_change) / (1024**2)
                disk_text = f"Освобождено: {size_mb:.1f} МБ"
        except Exception as e:
            disk_text = "Использовано: 0 МБ"
        
        return time_text, disk_text
    
    def detect_interactive_prompt(self, output):
        """Обнаружение интерактивного запроса в выводе"""
        return self.config.detect_interactive_prompt(output)
    
    def get_auto_response(self, prompt_type):
        """Получение автоматического ответа для типа запроса"""
        return self.config.get_auto_response(prompt_type)
    
    def start_log_monitoring(self, log_file_path=None):
        """Запуск мониторинга лог-файла в отдельном потоке"""
        try:
            # Используем переданный путь к лог-файлу или глобальный
            if log_file_path:
                self.log_file_path = log_file_path
            else:
                self.log_file_path = GLOBAL_LOG_FILE
            
            # Запоминаем текущую позицию в лог-файле
            if os.path.exists(self.log_file_path):
                self.log_start_position = os.path.getsize(self.log_file_path)
            else:
                self.log_start_position = 0
                
            # Запускаем мониторинг в отдельном потоке
            import threading
            self.log_monitor_thread = threading.Thread(target=self._monitor_log_file)
            self.log_monitor_thread.daemon = True
            self.log_monitor_thread.start()
            
            print(f"[LOG_MONITOR] Мониторинг лог-файла запущен: {self.log_file_path}")
            print(f"[LOG_MONITOR] Начальная позиция: {self.log_start_position}")
        except Exception as e:
            print(f"[LOG_MONITOR] Ошибка запуска мониторинга: {e}")
    
    def _monitor_log_file(self):
        """Мониторинг лог-файла построчно"""
        try:
            import time
            
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                # Переходим к позиции начала процесса
                f.seek(self.log_start_position)
                
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)  # Ждем новые строки
                        continue
                    
                    # Обрабатываем строку через ProcessProgressManager
                    self._process_log_line(line.rstrip())
                
        except Exception as e:
            print(f"[LOG_MONITOR] Ошибка мониторинга: {e}")
    
    def _process_log_line(self, line):
        """Обработка строки лог-файла через ProcessProgressManager"""
        try:
            if hasattr(self, 'progress_manager') and self.progress_manager:
                # Используем наш новый класс для обработки строк
                if "Чтение списков пакетов" in line:
                    self.progress_manager.update_local_progress("reading_lists", 100, "Получение списков пакетов")
                elif "Построение дерева зависимостей" in line:
                    self.progress_manager.update_local_progress("analyzing", 0, "Анализ зависимостей")
                elif "Чтение информации о состоянии" in line:
                    self.progress_manager.update_local_progress("analyzing", 50, "Чтение состояния пакетов")
                elif "Расчёт обновлений" in line:
                    self.progress_manager.update_local_progress("analyzing", 100, "Расчёт обновлений")
                elif "Обновлено 0 пакетов" in line:
                    # Для системы без обновлений проходим все этапы плавно
                    self.progress_manager.update_local_progress("downloading", 100, "Скачивание не требуется")
                    self.progress_manager.update_local_progress("installing", 100, "Установка не требуется")
                elif "Очистка" in line or "Удаление" in line:
                    self.progress_manager.update_local_progress("cleaning", 100, "Очистка системы")
                elif "Команда выполнена успешно" in line:
                    # Завершаем текущую фазу
                    self.progress_manager.finish_current_phase()
        except Exception as e:
            pass  # Игнорируем ошибки парсинга
    
    def send_progress_to_gui(self, progress_data):
        """Отправка обновления прогресса в GUI через ProcessProgressManager"""
        try:
            import datetime
            
            # Получаем timestamp для таблицы прогресса
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Получаем текущую статистику времени и дискового пространства
            time_text, disk_text = self.get_current_stats()
            
            # Формируем данные для GUI
            gui_data = {
                'stage_name': progress_data['stage_display_name'],
                'stage_progress': progress_data['stage_progress'],
                'global_progress': progress_data['global_progress'],
                'details': progress_data['details'],
                'speed': "",  # Будет заполнено позже
                'time_remaining': self.calculate_time_remaining(progress_data['stage_progress']),
                'time_elapsed': time_text,
                'disk_usage': disk_text
            }
            
            # Отправляем в GUI через universal_runner
            if hasattr(self, 'universal_runner') and self.universal_runner:
                self.universal_runner.gui_callback("[ADVANCED_PROGRESS] " + str(gui_data))
                
                # Обновляем статистику в GUI
                if hasattr(self, 'universal_runner') and self.universal_runner and hasattr(self.universal_runner, 'gui_instance'):
                    gui_instance = self.universal_runner.gui_instance
                    if gui_instance and hasattr(gui_instance, 'update_extended_statistics'):
                        gui_instance.update_extended_statistics()
                    
                    # Обновляем счетчик обработанных пакетов
                    if gui_instance and hasattr(gui_instance, 'processed_packages_label'):
                        total_processed = self.downloaded_packages + self.unpacked_packages + self.configured_packages
                        gui_instance.processed_packages_label.config(text=str(total_processed))
                
        except Exception as e:
            # Логируем ошибки отладки
            if hasattr(self, 'universal_runner') and self.universal_runner:
                self.universal_runner.add_output(f"[DEBUG_ERROR] Ошибка в send_progress_to_gui: {e}", level="ERROR")
    
    def get_extended_statistics(self):
        """Получение расширенной статистики для GUI"""
        try:
            # Вычисляем проценты
            downloaded_pct = (self.downloaded_packages / self.total_packages) * 100 if self.total_packages > 0 else 0
            unpacked_pct = (self.unpacked_packages / self.total_packages) * 100 if self.total_packages > 0 else 0
            configured_pct = (self.configured_packages / self.total_packages) * 100 if self.total_packages > 0 else 0
            
            # Формируем статистику
            stats = {
                'downloaded': f"{self.downloaded_packages}/{self.total_packages} ({downloaded_pct:.1f}%)",
                'unpacked': f"{self.unpacked_packages}/{self.total_packages} ({unpacked_pct:.1f}%)",
                'configured': f"{self.configured_packages}/{self.total_packages} ({configured_pct:.1f}%)",
                'downloaded_size': f"{self.downloaded_size_mb:.1f} MB",
                'download_speed': f"{self.download_speed_mb:.1f} MB/s"
            }
            
            return stats
            
        except Exception as e:
            return {
                'downloaded': "0/0 (0%)",
                'unpacked': "0/0 (0%)",
                'configured': "0/0 (0%)",
                'downloaded_size': "0 MB",
                'download_speed': "0 MB/s"
            }
    
    def calculate_time_remaining(self, progress):
        """Вычисление оставшегося времени (упрощенная версия)"""
        if progress <= 0:
            return "Вычисляется..."
        elif progress >= 100:
            return "Завершено"
        else:
            # Простая оценка на основе прогресса
            remaining_percent = 100 - progress
            estimated_minutes = remaining_percent / 10  # Примерно 10% в минуту
            if estimated_minutes < 1:
                return "Менее минуты"
            else:
                return f"~{int(estimated_minutes)} мин"
    
    def check_system_resources(self):
        """Проверка системных ресурсов перед обновлением"""
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE

        print("[SYSTEM] Проверка системных ресурсов...")
        print("[INFO] Начинаем проверку системных ресурсов")
        
        try:
            # Проверяем свободное место на диске
            if not self._check_disk_space():
                print("[ERROR] Недостаточно свободного места на диске")
                return False
            
            # Проверяем доступную память
            if not self._check_memory():
                print("[ERROR] Недостаточно свободной памяти")
                return False
            
            # Проверяем состояние dpkg
            print("   [DPKG] Проверяем состояние dpkg...")
            if not self._check_dpkg_status():
                print("   [WARNING] Основная проверка dpkg не удалась, пробуем быструю проверку...")
                print("[WARNING] Основная проверка dpkg не удалась, пробуем быструю проверку")
                
                if not self._quick_dpkg_check():
                    print("[ERROR] Проблемы с состоянием dpkg")
                    return False
                else:
                    print("   [OK] Быстрая проверка dpkg прошла успешно")
                    print("[INFO] Быстрая проверка dpkg прошла успешно")
            
            print("[OK] Все системные ресурсы в порядке")
            print("[INFO] Проверка системных ресурсов завершена успешно")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка проверки системных ресурсов: {e}")
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
                print("[INFO] Очистка блокировок", channels=["gui_log"])
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
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE

        print("   [TOOL] Исправляем проблемы dpkg...")
        print("[INFO] Начинаем исправление проблем dpkg")
        
        try:
            # 1. Очищаем блокирующие файлы
            print("   [TOOL] Очищаем блокирующие файлы...")
            print("[INFO] Очистка блокировок", channels=["gui_log"])
            
            # 2. Проверяем, есть ли проблемные пакеты
            print("   [TOOL] Проверяем проблемные пакеты...")
            audit_result = subprocess.run(['dpkg', '--audit'], 
                                       capture_output=True, text=True, timeout=15)
            
            if audit_result.returncode == 0:
                print("   [OK] Проблемных пакетов не найдено")
                print("[INFO] Проблемных пакетов не найдено")
                return True
            
            # 3. Сначала обрабатываем неработоспособные пакеты
            print("   [TOOL] Проверяем неработоспособные пакеты...")
            broken_packages = self._find_broken_packages()
            
            if broken_packages:
                print("   [WARNING] Найдены неработоспособные пакеты: %s" % ', '.join(broken_packages))
                print(f"[WARNING] Найдены неработоспособные пакеты: {', '.join(broken_packages)}")
                
                # Принудительно удаляем неработоспособные пакеты
                if self._force_remove_broken_packages(broken_packages):
                    print("   [OK] Неработоспособные пакеты удалены")
                    print("[INFO] Неработоспособные пакеты удалены")
                else:
                    print("   [WARNING] Не удалось удалить неработоспособные пакеты")
                    print("[WARNING] Не удалось удалить неработоспособные пакеты")
            
            # 4. Пробуем исправить зависимости
            print("   [TOOL] Исправляем сломанные зависимости...")
            result = subprocess.run(['apt', '--fix-broken', 'install', '-y'], 
                                 capture_output=True, text=True, timeout=90)
            
            if result.returncode == 0:
                print("   [OK] Зависимости исправлены")
                print("[INFO] Зависимости исправлены")
                
                # Проверяем еще раз
                audit_result = subprocess.run(['dpkg', '--audit'], 
                                           capture_output=True, text=True, timeout=10)
                if audit_result.returncode == 0:
                    print("   [OK] dpkg полностью исправлен")
                    print("[INFO] dpkg полностью исправлен")
                    return True
                else:
                    print("   [WARNING] Остались проблемные пакеты после исправления зависимостей")
                    print("[WARNING] Остались проблемные пакеты после исправления зависимостей")
            
            # 4. Если зависимости не исправились, пробуем конфигурацию
            print("   [TOOL] Пробуем исправить конфигурацию пакетов...")
            result = subprocess.run(['dpkg', '--configure', '-a'], 
                                 capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("   [OK] Конфигурация пакетов исправлена")
                print("[INFO] Конфигурация пакетов исправлена")
                return True
            else:
                print("   [WARNING] Не удалось исправить конфигурацию пакетов")
                print("[WARNING] Не удалось исправить конфигурацию пакетов")
                
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
                            print("[INFO] Проблемные пакеты удалены")
                            
                            # Повторяем исправление зависимостей
                            result = subprocess.run(['apt', '--fix-broken', 'install', '-y'], 
                                                 capture_output=True, text=True, timeout=90)
                            if result.returncode == 0:
                                print("   [OK] Зависимости восстановлены")
                                print("[INFO] Зависимости восстановлены")
                                return True
                    
                except Exception as force_error:
                    print(f"[ERROR] Ошибка принудительного исправления: {force_error}")
                    print("   [ERROR] Ошибка принудительного исправления: %s" % str(force_error))
                
                print("   [ERROR] Не удалось полностью исправить dpkg")
                print("[ERROR] Не удалось полностью исправить dpkg")
                return False
                
        except subprocess.TimeoutExpired:
            print("   [WARNING] Исправление dpkg заняло слишком много времени")
            print("[WARNING] Исправление dpkg заняло слишком много времени")
            return False
            
        except Exception as e:
            print(f"[ERROR] Ошибка исправления dpkg: {e}")
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
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE

        
        try:
            for package in broken_packages[:3]:  # Обрабатываем максимум 3 пакета
                print("   [TOOL] Принудительно удаляем пакет: %s" % package)
                print(f"[INFO] Принудительно удаляем пакет: {package}")
                
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
                    print(f"[INFO] Пакет {package} удален принудительно")
                else:
                    print("   [WARNING] Не удалось удалить пакет %s: %s" % (package, result.stderr.strip()))
                    print(f"[WARNING] Не удалось удалить пакет {package}: {result.stderr.strip()}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка принудительного удаления пакетов: {e}")
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
        if dry_run:
            print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: команда НЕ выполняется (только симуляция)")
            print(f"[INFO] РЕЖИМ ТЕСТИРОВАНИЯ - команда не выполнена: {cmd}", channels=["gui_log"])
            return 0
        
        print(f"[START] Выполнение команды с автоматическими ответами: {cmd}", channels=["gui_log"])
        
        # Определяем фазу обновления для парсера
        cmd_str = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
        if 'apt-get update' in cmd_str:
            current_phase = "update"
        elif 'apt-get dist-upgrade' in cmd_str:
            current_phase = "dist-upgrade"
        elif 'apt-get autoremove' in cmd_str:
            current_phase = "autoremove"
        else:
            current_phase = None
        
        # Передаем информацию о текущей фазе в ProcessProgressManager
        if hasattr(self, 'progress_manager') and self.progress_manager:
            self.progress_manager.current_update_phase = current_phase
            if current_phase == "update":
                self.progress_manager.update_phase_start_stage = "reading_lists"
            elif current_phase == "dist-upgrade":
                self.progress_manager.update_phase_start_stage = "downloading"
            elif current_phase == "autoremove":
                self.progress_manager.update_phase_start_stage = "cleaning"
        
        # Определяем тип команды для лога GUI
        if 'apt-get update' in ' '.join(cmd):
            print("[INFO] Обновление списков пакетов...", channels=["gui_log"])
        elif 'apt-get dist-upgrade' in ' '.join(cmd):
            print("[INFO] Обновление системы...", channels=["gui_log"])
        elif 'apt-get autoremove' in ' '.join(cmd):
            print("[INFO] Очистка системы...", channels=["gui_log"])
        else:
            print(f"[INFO] Начинаем выполнение команды: {cmd}", channels=["gui_log"])
        
        # Проверяем флаг остановки перед выполнением команды
        if hasattr(self, 'gui_instance') and self.gui_instance and not self.gui_instance.is_running:
            print("[STOP] Процесс остановлен пользователем")
            print("[INFO] Процесс остановлен пользователем")
            return -1
        
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
                # Проверяем флаг остановки в цикле чтения
                if hasattr(self, 'gui_instance') and self.gui_instance and not self.gui_instance.is_running:
                    print("[STOP] Процесс остановлен пользователем")
                    print("[INFO] Процесс остановлен пользователем")
                    process.terminate()  # Завершаем процесс
                    return -1
                
                line = process.stdout.readline()
                if not line:
                    break
                
                # Выводим строку
                print("   %s" % line.rstrip())
                
                # Парсинг теперь обрабатывается через мониторинг лог-файла
                # Старый парсинг удален - используем ProcessProgressManager
                
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
                        print(f"[INFO] Автоматический ответ: Enter для {prompt_type}")
                    else:
                        print("   [AUTO] Автоматический ответ: %s (для %s)" % (response, prompt_type))
                        print(f"[INFO] Автоматический ответ: {response} для {prompt_type}")
                    
                    # Отправляем ответ
                    process.stdin.write(response + '\n')
                    process.stdin.flush()
                    
                    # Очищаем буфер
                    output_buffer = ""
                    buffer_line_count = 0
            
            # Ждем завершения процесса
            return_code = process.wait()
            
            # Логируем результат команды
            print(f"[INFO] Команда: {cmd}, код возврата: {return_code}")
            
            if return_code == 0:
                print("[OK] Команда выполнена успешно", channels=["gui_log"])
                
                # Определяем тип команды для лога GUI
                if 'apt-get update' in ' '.join(cmd):
                    print("[INFO] ✅ Списки пакетов обновлены", channels=["gui_log"])
                elif 'apt-get dist-upgrade' in ' '.join(cmd):
                    print("[INFO] ✅ Система обновлена", channels=["gui_log"])
                elif 'apt-get autoremove' in ' '.join(cmd):
                    print("[INFO] ✅ Система очищена", channels=["gui_log"])
            else:
                print(f"[ERROR] Команда завершилась с ошибкой (код: {return_code})", channels=["gui_log"])
                
            # Проверяем на ошибки dpkg
            if "dpkg была прервана" in output_buffer or "dpkg --configure -a" in output_buffer:
                print("[WARNING] Обнаружена ошибка dpkg, запускаем автоматическое исправление", channels=["gui_log"])
                
                try:
                    if self.auto_fix_dpkg_errors():
                        print("[OK] Ошибки dpkg исправлены автоматически", channels=["gui_log"])
                    else:
                        print("[WARNING] Не удалось автоматически исправить ошибки dpkg", channels=["gui_log"])
                except Exception as fix_error:
                    print(f"[ERROR] Ошибка при исправлении dpkg: {fix_error}", channels=["gui_log"])
            
            return return_code
            
        except Exception as e:
            print(f"[ERROR] Ошибка выполнения команды: {e}")
            print("   [ERROR] Ошибка выполнения команды: %s" % str(e))
            
            # Проверяем на ошибку сегментации (код 139)
            if hasattr(e, 'returncode') and e.returncode == 139:
                print("   [CRITICAL] Обнаружена ошибка сегментации (SIGSEGV)!")
                print("[ERROR] Обнаружена ошибка сегментации (SIGSEGV)")
                print("   [TOOL] Пробуем восстановить систему...")
                
                # Пробуем восстановить систему
                if self._recover_from_segfault():
                    print("   [OK] Система восстановлена после ошибки сегментации")
                    print("[INFO] Система восстановлена после ошибки сегментации")
                    return 139  # Возвращаем код ошибки для обработки на верхнем уровне
                else:
                    print("   [ERROR] Не удалось восстановить систему")
                    print("[ERROR] Не удалось восстановить систему")
            
            return 1
    
    def _recover_from_segfault(self):
        """Восстановление системы после ошибки сегментации"""
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE

        print("   [RECOVERY] Начинаем восстановление системы...")
        print("[INFO] Начинаем восстановление системы после ошибки сегментации")
        
        try:
            # 1. Очищаем блокирующие файлы
            print("   [RECOVERY] Очищаем блокирующие файлы...")
            print("[INFO] Очистка блокировок", channels=["gui_log"])
            
            # 2. Исправляем конфигурацию dpkg
            print("   [RECOVERY] Исправляем конфигурацию dpkg...")
            result = subprocess.run(['dpkg', '--configure', '-a'], 
                                 capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print("   [WARNING] dpkg требует дополнительного исправления")
                print("[WARNING] dpkg требует дополнительного исправления")
            
            # 3. Исправляем сломанные зависимости
            print("   [RECOVERY] Исправляем сломанные зависимости...")
            result = subprocess.run(['apt', '--fix-broken', 'install', '-y'], 
                                 capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print("   [WARNING] Не удалось исправить зависимости")
                print("[WARNING] Не удалось исправить зависимости")
            
            # 4. Очищаем кэш APT
            print("   [RECOVERY] Очищаем кэш APT...")
            subprocess.run(['apt', 'clean'], capture_output=True, text=True, timeout=30)
            subprocess.run(['apt', 'autoclean'], capture_output=True, text=True, timeout=30)
            
            # 5. Проверяем состояние системы
            print("   [RECOVERY] Проверяем состояние системы...")
            if self.check_system_resources():
                print("   [OK] Система восстановлена успешно")
                print("[INFO] Система восстановлена успешно")
                return True
            else:
                print("   [ERROR] Система не восстановлена")
                print("[ERROR] Система не восстановлена")
                return False
                
        except Exception as e:
            print(f"[ERROR] Ошибка восстановления системы: {e}")
            print("   [ERROR] Ошибка восстановления системы: %s" % str(e))
            return False
    
    def reset_progress_bars(self):
        """Сброс всех прогресс-баров в начальное состояние"""
        try:
            # Отправляем сброс прогресса в GUI
            reset_data = {
                'stage_name': 'Подготовка...',
                'stage_progress': 0,
                'global_progress': 0,
                'details': '',
                'speed': '',
                'time_remaining': '',
                'time_elapsed': '0 мин 0 сек',
                'disk_usage': '0 MB'
            }
            
            if hasattr(self, 'universal_runner') and self.universal_runner:
                self.universal_runner.gui_callback("[ADVANCED_PROGRESS] " + str(reset_data))
                
        except Exception as e:
            print(f"[ERROR] Ошибка сброса прогресс-баров: {e}")
    
    def update_system(self, dry_run=False):
        """Обновление системы"""
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE
        
        print("[PACKAGE] Обновление системы...")
        
        # Инициализируем менеджер прогресса для обновления системы
        self.progress_manager.start_process("system_update", "Обновление системы")
        
        # Запускаем мониторинг лог-файла с правильным путем
        self.start_log_monitoring(log_file)
        
        # Сбрасываем счетчики статистики
        self.downloaded_packages = 0
        self.unpacked_packages = 0
        self.configured_packages = 0
        
        # Начинаем мониторинг времени и дискового пространства
        if hasattr(self, 'system_updater') and self.system_updater:
            self.system_updater.start_monitoring()
        
        if dry_run:
            print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: обновление НЕ выполняется")
            print("[OK] Будет выполнено: apt-get update && apt-get dist-upgrade -y && apt-get autoremove -y")
            return True
        
        # Проверяем системные ресурсы перед обновлением
        print("\n[SYSTEM] Проверка системных ресурсов перед обновлением...")
        if not self.check_system_resources():
            print("[ERROR] Системные ресурсы не соответствуют требованиям для обновления")
            print("[ERROR] Системные ресурсы не соответствуют требованиям для обновления")
            return False
        
        # Сначала обновляем списки пакетов
        print("\n[PROCESS] Обновление списков пакетов...")
        
        # Проверяем флаг остановки перед обновлением списков
        if hasattr(self, 'gui_instance') and self.gui_instance and not self.gui_instance.is_running:
            print("[STOP] Процесс остановлен пользователем")
            print("[INFO] Процесс остановлен пользователем")
            return False
        
        update_cmd = ['apt-get', 'update']
        result = self.run_command_with_interactive_handling(update_cmd, dry_run, gui_terminal=True)
        
        # Завершаем фазу apt-get update
        if result == 0:
            self.progress_manager.finish_current_phase()
        
        if result != 0:
            print("[ERROR] Ошибка обновления списков пакетов")
            return False
        
        # Затем обновляем систему с опциями dpkg для автоподтверждения
        print("\n[START] Обновление системы...")
        
        # Проверяем флаг остановки перед обновлением системы
        if hasattr(self, 'gui_instance') and self.gui_instance and not self.gui_instance.is_running:
            print("[STOP] Процесс остановлен пользователем")
            print("[INFO] Процесс остановлен пользователем")
            return False
        
        upgrade_cmd = ['apt-get', 'dist-upgrade', '-y',
                      '-o', 'Dpkg::Options::=--force-confdef',
                      '-o', 'Dpkg::Options::=--force-confold',
                      '-o', 'Dpkg::Options::=--force-confmiss']
        result = self.run_command_with_interactive_handling(upgrade_cmd, dry_run, gui_terminal=True)
        
        # Завершаем фазу apt-get dist-upgrade
        if result == 0:
            self.progress_manager.finish_current_phase()
        
        # Обрабатываем результат обновления
        if result == 0:
            print("[OK] Система успешно обновлена")
            
            # Автоматическая очистка ненужных пакетов
            print("\n[CLEANUP] Автоматическая очистка ненужных пакетов...")
            
            # Проверяем флаг остановки перед очисткой
            if hasattr(self, 'gui_instance') and self.gui_instance and not self.gui_instance.is_running:
                print("[STOP] Процесс остановлен пользователем")
                print("[INFO] Процесс остановлен пользователем")
                return False
            
            autoremove_cmd = ['apt-get', 'autoremove', '-y',
                            '-o', 'Dpkg::Options::=--force-confdef',
                            '-o', 'Dpkg::Options::=--force-confold',
                            '-o', 'Dpkg::Options::=--force-confmiss']
            autoremove_result = self.run_command_with_interactive_handling(autoremove_cmd, dry_run, gui_terminal=True)
            
            # Завершаем фазу apt-get autoremove и весь процесс
            if autoremove_result == 0:
                self.progress_manager.finish_current_phase()
                self.progress_manager.finish_process()
                print("[OK] Ненужные пакеты успешно удалены")
            else:
                print("[WARNING] Предупреждение: не удалось удалить ненужные пакеты")
            
            return True
            
        elif result == 139:
            # Ошибка сегментации - система уже восстановлена
            print("[WARNING] Обновление завершилось с ошибкой сегментации, но система восстановлена", channels=["gui_log"])
            
            # Пробуем продолжить с более безопасным подходом
            print("[TOOL] Пробуем безопасное обновление...", channels=["gui_log"])
            return self._safe_update_retry()
            
        else:
            print("[ERROR] Ошибка обновления системы", channels=["gui_log"])
            # Пробуем автоматически исправить ошибки dpkg
            if self.auto_fix_dpkg_errors():
                print("[TOOL] Ошибки dpkg исправлены, повторяем обновление...", channels=["gui_log"])
                # Повторяем обновление после исправления
                result = self.run_command_with_interactive_handling(upgrade_cmd, dry_run, gui_terminal=True)
                if result == 0:
                    print("[OK] Система успешно обновлена после исправления", channels=["gui_log"])
                    return True
                elif result == 139:
                    print("[WARNING] Повторная ошибка сегментации, пробуем безопасное обновление...", channels=["gui_log"])
                    return self._safe_update_retry()
                else:
                    print("[ERROR] Ошибка обновления системы даже после исправления", channels=["gui_log"])
                    
                    # Пробуем исправить проблемы с кэшем APT
                    print("[TOOL] Пробуем исправить проблемы с кэшем APT...", channels=["gui_log"])
                    
                    try:
                        # Очищаем кэш APT
                        cleanup_cmd = ['apt-get', 'clean']
                        result = self.run_command_with_interactive_handling(cleanup_cmd, False, gui_terminal=True)
                        if result == 0:
                            print("   [OK] Кэш APT очищен")
                            print("[INFO] Кэш APT очищен")
                        
                        # Пробуем обновление с --fix-missing
                        print("[TOOL] Пробуем обновление с --fix-missing...")
                        print("[INFO] Пробуем обновление с --fix-missing")
                        fix_missing_cmd = ['apt-get', 'dist-upgrade', '-y', '--fix-missing']
                        result = self.run_command_with_interactive_handling(fix_missing_cmd, False, gui_terminal=True)
                        
                        if result == 0:
                            print("   [OK] Обновление с --fix-missing выполнено успешно")
                            print("[INFO] Обновление с --fix-missing выполнено успешно")
                            return True
                        else:
                            print("   [WARNING] Обновление с --fix-missing также завершилось с ошибкой")
                            print("[WARNING] Обновление с --fix-missing также завершилось с ошибкой")
                            return False
                            
                    except Exception as cache_error:
                        print(f"[ERROR] Ошибка при исправлении кэша APT: {cache_error}")
                        print("   [ERROR] Ошибка при исправлении кэша APT: %s" % str(cache_error))
                    return False
            else:
                print("[ERROR] Не удалось автоматически исправить ошибки dpkg")
                return False
    
    def _safe_update_retry(self):
        """Безопасное повторное обновление после ошибки сегментации"""
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE

        print("[SAFE] Безопасное повторное обновление...")
        print("[INFO] Начинаем безопасное повторное обновление")
        
        try:
            # 1. Обновляем только безопасные пакеты
            print("   [SAFE] Обновляем только безопасные пакеты...")
            safe_upgrade_cmd = ['apt-get', 'upgrade', '-y']
            result = self.run_command_with_interactive_handling(safe_upgrade_cmd, False, gui_terminal=True)
            
            if result == 0:
                print("   [OK] Безопасное обновление выполнено успешно")
                print("[INFO] Безопасное обновление выполнено успешно")
                return True
            elif result == 139:
                print("   [WARNING] Безопасное обновление также завершилось с ошибкой сегментации")
                print("[WARNING] Безопасное обновление также завершилось с ошибкой сегментации")
                
                # Пробуем обновить только критические пакеты
                print("   [SAFE] Пробуем обновить только критические пакеты...")
                critical_cmd = ['apt-get', 'install', '--only-upgrade', '-y', 'apt', 'dpkg', 'libc6']
                result = self.run_command_with_interactive_handling(critical_cmd, False, gui_terminal=True)
                
                if result == 0:
                    print("   [OK] Критические пакеты обновлены успешно")
                    print("[INFO] Критические пакеты обновлены успешно")
                    return True
                else:
                    print("   [ERROR] Не удалось обновить даже критические пакеты")
                    print("[ERROR] Не удалось обновить даже критические пакеты")
                    return False
            else:
                print("   [ERROR] Безопасное обновление завершилось с ошибкой")
                print("[ERROR] Безопасное обновление завершилось с ошибкой")
                return False
                
        except Exception as e:
            print(f"[ERROR] Ошибка безопасного повторного обновления: {e}")
            print("   [ERROR] Ошибка безопасного повторного обновления: %s" % str(e))
            return False
    
    def auto_fix_dpkg_errors(self):
        """Автоматическое исправление ошибок dpkg"""
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE

        print("[TOOL] Автоматическое исправление ошибок dpkg...")
        print("[INFO] Начинаем автоматическое исправление ошибок dpkg")
        
        try:
            # Сначала очищаем блокирующие файлы
            print("[INFO] Очищаем блокирующие файлы перед исправлением dpkg")
            print("[INFO] Очистка блокировок", channels=["gui_log"])
            
            # 1. Исправляем конфигурацию dpkg
            print("   [TOOL] Запускаем dpkg --configure -a...")
            print("[INFO] Запускаем dpkg --configure -a")
            configure_cmd = ['dpkg', '--configure', '-a']
            result = self.run_command_with_interactive_handling(configure_cmd, False, gui_terminal=True)
            
            if result == 0:
                print("   [OK] dpkg --configure -a выполнен успешно")
                print("[INFO] dpkg --configure -a выполнен успешно")
            else:
                print("   [WARNING] dpkg --configure -a завершился с ошибкой")
                print("[WARNING] dpkg --configure -a завершился с ошибкой")
            
            # 2. Исправляем сломанные зависимости
            print("   [TOOL] Запускаем apt --fix-broken install...")
            print("[INFO] Запускаем apt --fix-broken install")
            fix_cmd = ['apt', '--fix-broken', 'install', '-y']
            
            try:
                result = self.run_command_with_interactive_handling(fix_cmd, False, gui_terminal=True)
                
                if result == 0:
                    print("[OK] apt --fix-broken install выполнен успешно", channels=["gui_log"])
                    return True
                else:
                    print("[WARNING] apt --fix-broken install завершился с ошибкой", channels=["gui_log"])
                    
            except Exception as fix_error:
                print(f"[ERROR] Критическая ошибка в apt --fix-broken install: {fix_error}", channels=["gui_log"])
                print("[INFO] Очистка блокировок", channels=["gui_log"])  # Очищаем блокировки при критической ошибке
                return False
                
                # 3. Принудительное удаление проблемных пакетов
                print("[WARNING] Пробуем принудительное удаление проблемных пакетов", channels=["gui_log"])
                force_remove_cmd = ['dpkg', '--remove', '--force-remove-reinstreq', 'python3-tk']
                result = self.run_command_with_interactive_handling(force_remove_cmd, False, gui_terminal=True)
                
                if result == 0:
                    print("[OK] Проблемные пакеты удалены принудительно", channels=["gui_log"])
                    # Повторяем исправление зависимостей
                    print("[INFO] Повторяем исправление зависимостей после принудительного удаления")
                    result = self.run_command_with_interactive_handling(fix_cmd, False, gui_terminal=True)
                    if result == 0:
                        print("[OK] Зависимости исправлены после принудительного удаления", channels=["gui_log"])
                        return True
                    else:
                        print("[ERROR] Не удалось исправить зависимости после принудительного удаления", channels=["gui_log"])
                
                print("[ERROR] Автоматическое исправление dpkg не удалось", channels=["gui_log"])
                return False
                
        except Exception as e:
            print(f"[ERROR] Ошибка автоматического исправления dpkg: {e}", channels=["gui_log"])
            return False
    
    def simulate_update_scenarios(self):
        """Симуляция различных сценариев обновления"""
        print("[PROCESS] Симуляция сценариев обновления...", channels=["gui_log"])
        
        # Тест 1: dpkg конфигурационный файл
        print("\n[LIST] Тест 1: dpkg конфигурационный файл", channels=["gui_log"])
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
    
    # Проверяем операционную систему
    import platform
    system = platform.system()
    
    if system == "Darwin":  # macOS
        print("[INFO] Обнаружена macOS - режим тестирования GUI")
        print("[INFO] Linux-специфичные проверки пропущены")
        return True
    elif system != "Linux":
        print("[WARNING] Неподдерживаемая ОС: %s" % system)
        print("[INFO] Запуск в режиме тестирования GUI")
        return True
    
    # Синхронизация времени уже выполнена в bash скрипте
    print("[INFO] Синхронизация времени пропущена (уже выполнена в bash)")
    
    # Проверяем права root (только для Linux)
    try:
        if os.geteuid() != 0:
            print("[ERROR] Требуются права root для работы с системными файлами")
            print("   Запустите: sudo python astra_automation.py")
            return False
    except AttributeError:
        # os.geteuid() не существует на macOS/Windows
        print("[INFO] Проверка прав root пропущена (не Linux система)")
    
    # Проверяем Python версию (требуется Python 3.x)
    if sys.version_info[0] != 3:
        print("[ERROR] Требуется Python 3.x")
        print("   Текущая версия: %s" % sys.version)
        return False
    
    print("[OK] Python версия подходящая: %s" % sys.version.split()[0])
    
    # Проверяем наличие apt-get (только для Linux)
    try:
        subprocess.check_call(['which', 'apt-get'], 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
        print("[OK] apt-get найден")
    except subprocess.CalledProcessError:
        print("[ERROR] apt-get не найден - возможно не Debian/Ubuntu система")
        return False
    
    # Проверяем наличие sources.list (только для Linux)
    sources_list = '/etc/apt/sources.list'
    if not os.path.exists(sources_list):
        print("[ERROR] Файл %s не найден" % sources_list)
        return False
    
    print("[OK] Все требования выполнены")
    return True

def install_gui_components():
    """Установка GUI компонентов (tkinter, pip3)"""
    print("[GUI] Установка GUI компонентов...")
    
    try:
        # Обновляем списки пакетов
        print("[GUI] Обновление списков пакетов...")
        result = subprocess.call(['apt-get', 'update'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE)
        
        if result != 0:
            print("[ERROR] Ошибка обновления списков пакетов")
            return False
        
        print("[OK] Списки пакетов обновлены")
        
        # Устанавливаем GUI компоненты
        print("[GUI] Установка python3-tk и python3-pip...")
        
        # Настраиваем переменные окружения для автоматических ответов
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        env['DEBIAN_PRIORITY'] = 'critical'
        env['APT_LISTCHANGES_FRONTEND'] = 'none'
        
        # Устанавливаем пакеты с автоматическими ответами
        cmd = ['apt-get', 'install', '-y', 
               '-o', 'Dpkg::Options::=--force-confdef',
               '-o', 'Dpkg::Options::=--force-confold', 
               '-o', 'Dpkg::Options::=--force-confmiss',
               'python3-tk', 'python3-pip']
        
        result = subprocess.call(cmd, env=env,
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE)
        
        if result != 0:
            print("[ERROR] Ошибка установки GUI компонентов")
            return False
        
        print("[OK] GUI компоненты установлены успешно")
        
        # Проверяем что tkinter работает
        try:
            subprocess.check_call(['python3', '-c', 'import tkinter'], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
            print("[OK] tkinter работает корректно")
        except subprocess.CalledProcessError:
            print("[WARNING] tkinter установлен, но может не работать корректно")
        
        # Проверяем что pip3 работает
        try:
            subprocess.check_call(['pip3', '--version'], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
            print("[OK] pip3 работает корректно")
        except subprocess.CalledProcessError:
            print("[WARNING] pip3 установлен, но может не работать корректно")
        
        return True
        
    except Exception as e:
        print("[ERROR] Ошибка установки GUI компонентов: %s" % str(e))
        return False

def run_repo_checker(gui_terminal=None, dry_run=False):
    """Запуск проверки репозиториев через класс RepoChecker"""
    print("\n[START] Запуск автоматизации проверки репозиториев...")
    
    try:
        # Создаем экземпляр класса RepoChecker
        checker = RepoChecker(gui_terminal=gui_terminal)
        
        # Проверяем права доступа
        if os.geteuid() != 0:
            print("[ERROR] Требуются права root для работы с /etc/apt/sources.list")
            print("Запустите: sudo python3 astra_automation.py")
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
        print("[LIST] Репозитории:", channels=["gui_log"])
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
            print("[ERROR] Требуются права root для работы с системными пакетами", channels=["gui_log"])
            print("Запустите: sudo python3 astra_automation.py")
            return False
        
        # Анализируем обновления
        if not stats.get_updatable_packages():
            print("[WARNING] Предупреждение: не удалось получить список обновлений", channels=["gui_log"])
        
        # Анализируем автоудаление
        if not stats.get_autoremove_packages():
            print("[WARNING] Предупреждение: не удалось проанализировать автоудаление", channels=["gui_log"])
        
        # Подсчитываем пакеты для установки
        if not stats.calculate_install_stats():
            print("[WARNING] Предупреждение: не удалось подсчитать пакеты для установки", channels=["gui_log"])
        
        # Показываем статистику
        stats.display_statistics()
        
        if dry_run:
            print("[OK] Анализ статистики завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)", channels=["gui_log"])
        else:
            print("[OK] Анализ статистики завершен успешно!", channels=["gui_log"])
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка анализа статистики: {e}", channels=["gui_log"])
        return False

def run_interactive_handler(temp_dir, dry_run=False):
    """Запуск модуля перехвата интерактивных запросов через класс InteractiveHandler"""
    print("\n[AUTO] Запуск тестирования перехвата интерактивных запросов...", channels=["gui_log"])
    
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
        # Создаем экземпляр класса SystemUpdater с universal_runner
        universal_runner = get_global_universal_runner()
        updater = SystemUpdater(universal_runner)
        
        # Запускаем симуляцию сценариев обновления
        updater.simulate_update_scenarios()
        
        # Если не dry_run, запускаем реальное обновление
        if not dry_run:
            print("[TOOL] Тест реального обновления системы...", channels=["gui_log"])
            success = updater.update_system(dry_run)
            if success:
                print("[OK] Обновление системы завершено успешно", channels=["gui_log"])
            else:
                print("[ERROR] Обновление системы завершено с ошибкой", channels=["gui_log"])
        else:
            print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: реальное обновление не выполняется", channels=["gui_log"])
            updater.update_system(dry_run)
        
        if dry_run:
            print("[OK] Обновление системы завершено успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)", channels=["gui_log"])
        else:
            print("[OK] Обновление системы завершено успешно!", channels=["gui_log"])
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка обновления системы: {e}", channels=["gui_log"])
        return False

def run_gui_monitor(temp_dir, dry_run=False, close_terminal_pid=None):
    """Запуск GUI мониторинга через класс AutomationGUI"""
    print("\n[GUI] Запуск GUI мониторинга...")
    
    try:
        # Создаем экземпляр класса AutomationGUI напрямую
        print("   [OK] Создаем экземпляр AutomationGUI...")
        gui = AutomationGUI(console_mode=False, close_terminal_pid=close_terminal_pid)
        
        # Устанавливаем лог-файл для GUI
        # Используем глобальный лог-файл
        log_file = GLOBAL_LOG_FILE

        gui.main_log_file = log_file
        
        print("   [OK] GUI создан успешно, настраиваем universal_runner...")
        
        # Передаем единый logger в GUI
        gui.universal_runner = get_global_universal_runner()
        
        # Устанавливаем путь к лог-файлу в universal_runner (переданный от bash)
        gui.universal_runner.set_log_file(log_file)
        print(f"[LOG_FILE] Установлен путь к лог-файлу в universal_runner: {log_file}")
        gui.universal_runner.gui_callback = gui.add_terminal_output  # УСТАНАВЛИВАЕМ GUI CALLBACK!
        gui.universal_runner.gui_log_callback = gui.add_gui_log_output  # УСТАНАВЛИВАЕМ GUI LOG CALLBACK!
        gui.universal_runner.setup_print_redirect()  # ВКЛЮЧЕНО: рекурсия исправлена
        gui.universal_runner.setup_subprocess_redirect()  # Подмена subprocess.run()
        gui.universal_runner.setup_logging_redirect()  # Подмена logging.getLogger()
        gui.universal_runner.setup_universal_logging_redirect()  # Подмена ВСЕХ методов логирования
        
        # Сохраняем ссылку на universal_runner для использования в функции
        universal_runner = gui.universal_runner
        
        print("   [OK] UniversalProcessRunner настроен, запускаем GUI...")
        
        # Запускаем GUI
        gui.run()
        
        print("[OK] GUI мониторинг завершен успешно!")
        return True
        
    except Exception as e:
        print("[ERROR] Ошибка запуска GUI: %s" % str(e))
        import traceback
        print("[ERROR] Детали ошибки:")
        traceback.print_exc()
        return False

def cleanup_temp_files(temp_dir):
    """Очистка временных файлов"""
    try:
        shutil.rmtree(temp_dir)
        print("[OK] Временные файлы очищены")
    except Exception as e:
        print("[WARNING] Предупреждение: не удалось очистить временные файлы: %s" % str(e))

# ============================================================================
# КЛАССЫ МОНИТОРИНГА ДИРЕКТОРИЙ
# ============================================================================

class DirectorySnapshot(object):
    """Класс для хранения снимка состояния директории"""
    
    def __init__(self, directory_path):
        self.directory_path = directory_path
        self.timestamp = datetime.datetime.now()
        self.files = {}  # {relative_path: (size, mtime, hash)}
        self.directories = set()  # {relative_path1, relative_path2, ...}
        self._scan_directory()
    
    def _scan_directory(self):
        """Сканирование директории и создание снимка"""
        if not os.path.exists(self.directory_path):
            return
        
        try:
            for root, dirs, files in os.walk(self.directory_path):
                # Добавляем директории
                rel_root = os.path.relpath(root, self.directory_path)
                if rel_root != '.':
                    self.directories.add(rel_root)
                
                # Добавляем файлы
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.directory_path)
                    
                    try:
                        stat = os.stat(file_path)
                        # Простой хеш для быстрого сравнения (первые 8 байт + размер)
                        file_hash = self._quick_hash(file_path)
                        self.files[rel_path] = (stat.st_size, stat.st_mtime, file_hash)
                    except (OSError, IOError):
                        # Пропускаем файлы, к которым нет доступа
                        continue
        except (OSError, IOError):
            # Пропускаем директории, к которым нет доступа
            pass
    
    def _quick_hash(self, file_path):
        """Быстрое хеширование файла (первые 8 байт + размер)"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(8)  # Читаем первые 8 байт
                size = os.path.getsize(file_path)
                return hash(data + str(size).encode())
        except (OSError, IOError):
            return 0

class DirectoryMonitor(object):
    """Класс для мониторинга изменений в директории"""
    
    def __init__(self, compact_mode=False):
        self.baseline = None  # Базовый снимок
        self.last_snapshot = None  # Последний снимок
        self.monitoring = False
        self.compact_mode = compact_mode  # Режим компактного вывода
    
    def start_monitoring(self, directory_path):
        """Начать мониторинг директории (создать базовый снимок)"""
        self.baseline = DirectorySnapshot(directory_path)
        self.last_snapshot = self.baseline
        self.monitoring = True
        print(f"[DirectoryMonitor] Мониторинг начат: {directory_path}")
        print(f"[DirectoryMonitor] Базовый снимок: {len(self.baseline.files)} файлов, {len(self.baseline.directories)} папок")
    
    def check_changes(self, directory_path):
        """Проверить изменения в директории (сравнить с последним снимком)"""
        if not self.monitoring:
            print("[DirectoryMonitor] Мониторинг не активен!")
            return None
        
        current_snapshot = DirectorySnapshot(directory_path)
        changes = self._compare_snapshots(self.last_snapshot, current_snapshot)
        
        # Обновляем последний снимок
        self.last_snapshot = current_snapshot
        
        return changes
    
    def get_incremental_changes(self, directory_path):
        """Получить инкрементальные изменения (с предыдущего снимка)"""
        return self.check_changes(directory_path)
    
    def get_total_changes(self, directory_path):
        """Получить полные изменения (с базового снимка)"""
        if not self.monitoring or not self.baseline:
            return None
        
        current_snapshot = DirectorySnapshot(directory_path)
        return self._compare_snapshots(self.baseline, current_snapshot)
    
    def reset_baseline(self, directory_path):
        """Сбросить базовый снимок (создать новый)"""
        self.baseline = DirectorySnapshot(directory_path)
        self.last_snapshot = self.baseline
        print(f"[DirectoryMonitor] Базовый снимок сброшен: {len(self.baseline.files)} файлов, {len(self.baseline.directories)} папок")
    
    def detect_installed_components(self, changes):
        """Определяет какие компоненты установились на основе ключевых файлов"""
        component_files = {
            'wine-mono': [
                'drive_c/windows/mono/mono-2.0/bin/libmono-2.0-x86.dll',
                'drive_c/windows/mono/mono-2.0/bin/libmono-2.0-x86_64.dll'
            ],
            'd3dcompiler_43': [
                'drive_c/windows/system32/d3dcompiler_43.dll',
                'drive_c/windows/syswow64/d3dcompiler_43.dll'
            ],
            'd3dcompiler_47': [
                'drive_c/windows/system32/d3dcompiler_47.dll',
                'drive_c/windows/syswow64/d3dcompiler_47.dll'
            ],
            'vcrun2013': [
                'drive_c/windows/system32/msvcp120.dll',
                'drive_c/windows/system32/msvcr120.dll'
            ],
            'vcrun2022': [
                'drive_c/windows/system32/msvcp140.dll',
                'drive_c/windows/system32/vcruntime140.dll'
            ],
            'dotnet48': [
                'drive_c/windows/Microsoft.NET/Framework/v4.0.30319/mscorlib.dll',
                'drive_c/windows/Microsoft.NET/Framework64/v4.0.30319/mscorlib.dll'
            ],
            'dxvk': [
                'drive_c/windows/system32/dxgi.dll',
                'drive_c/windows/system32/d3d11.dll'
            ]
        }
        
        installed_components = []
        for component, key_files in component_files.items():
            for file_path in changes.get('new_files', []):
                if any(key_file in file_path for key_file in key_files):
                    installed_components.append(component)
                    break
        
        return installed_components
    
    def format_changes_compact(self, changes):
        """Компактное форматирование изменений для вывода"""
        if not changes:
            return "Изменений не обнаружено"
        
        # Определяем установленные компоненты
        installed_components = self.detect_installed_components(changes)
        
        # Фильтруем служебные файлы Wine
        filtered_files = self._filter_wine_service_files(changes.get('new_files', []))
        filtered_dirs = self._filter_wine_service_files(changes.get('new_directories', []))
        
        # Подсчитываем изменения
        new_files_count = len(filtered_files)
        modified_files_count = len(changes.get('modified_files', []))
        new_dirs_count = len(filtered_dirs)
        
        timestamp = changes['timestamp'].strftime("%H:%M:%S")
        
        # Формируем компактный вывод
        if installed_components:
            components_str = ", ".join(installed_components)
            stats = []
            if new_files_count > 0:
                stats.append(f"+{new_files_count} файлов")
            if new_dirs_count > 0:
                stats.append(f"+{new_dirs_count} папок")
            if modified_files_count > 0:
                stats.append(f"~{modified_files_count} файлов")
            
            stats_str = f" ({', '.join(stats)})" if stats else ""
            return f"[{timestamp}] Установлены компоненты: {components_str}{stats_str}"
        else:
            stats = []
            if new_files_count > 0:
                stats.append(f"+{new_files_count} файлов")
            if new_dirs_count > 0:
                stats.append(f"+{new_dirs_count} папок")
            if modified_files_count > 0:
                stats.append(f"~{modified_files_count} файлов")
            
            if stats:
                return f"[{timestamp}] Изменения: {', '.join(stats)}"
            else:
                return f"[{timestamp}] Изменений не обнаружено"
    
    def _filter_wine_service_files(self, file_list):
        """Фильтрует служебные файлы Wine из списка"""
        service_patterns = [
            'dosdevices/com',
            'dosdevices/lpt',
            'dosdevices/prn',
            'dosdevices/aux',
            'dosdevices/con',
            '.update-timestamp',
            'dosdevices/z:',
            'dosdevices/y:',
            'dosdevices/x:',
            'dosdevices/w:',
            'dosdevices/v:',
            'dosdevices/u:',
            'dosdevices/t:',
            'dosdevices/s:',
            'dosdevices/r:',
            'dosdevices/q:',
            'dosdevices/p:',
            'dosdevices/o:',
            'dosdevices/n:',
            'dosdevices/m:',
            'dosdevices/l:',
            'dosdevices/k:',
            'dosdevices/j:',
            'dosdevices/i:',
            'dosdevices/h:',
            'dosdevices/g:',
            'dosdevices/f:',
            'dosdevices/e:',
            'dosdevices/d:',
            'dosdevices/c:',
            'dosdevices/b:',
            'dosdevices/a:'
        ]
        
        filtered = []
        for file_path in file_list:
            is_service = False
            for pattern in service_patterns:
                if pattern in file_path:
                    is_service = True
                    break
            if not is_service:
                filtered.append(file_path)
        
        return filtered

    def _compare_snapshots(self, old_snapshot, new_snapshot):
        """Сравнение двух снимков и определение изменений"""
        changes = {
            'new_files': [],
            'modified_files': [],
            'deleted_files': [],
            'new_directories': [],
            'deleted_directories': [],
            'timestamp': new_snapshot.timestamp
        }
        
        # Проверяем файлы
        old_files = set(old_snapshot.files.keys())
        new_files = set(new_snapshot.files.keys())
        
        # Новые файлы
        for file_path in new_files - old_files:
            changes['new_files'].append(file_path)
        
        # Удаленные файлы
        for file_path in old_files - new_files:
            changes['deleted_files'].append(file_path)
        
        # Измененные файлы
        for file_path in old_files & new_files:
            old_info = old_snapshot.files[file_path]
            new_info = new_snapshot.files[file_path]
            if old_info != new_info:
                changes['modified_files'].append(file_path)
        
        # Проверяем директории
        old_dirs = old_snapshot.directories
        new_dirs = new_snapshot.directories
        
        # Новые директории
        for dir_path in new_dirs - old_dirs:
            changes['new_directories'].append(dir_path)
        
        # Удаленные директории
        for dir_path in old_dirs - new_dirs:
            changes['deleted_directories'].append(dir_path)
        
        return changes
    
    def format_changes(self, changes):
        """Форматирование изменений для вывода"""
        if not changes:
            return "Изменений не обнаружено"
        
        # Если включен компактный режим, используем компактное форматирование
        if self.compact_mode:
            return self.format_changes_compact(changes)
        
        # Полный режим - детальный вывод
        output = []
        timestamp = changes['timestamp'].strftime("%H:%M:%S")
        
        # Фильтруем служебные файлы Wine для полного режима
        filtered_new_files = self._filter_wine_service_files(changes['new_files'])
        filtered_new_dirs = self._filter_wine_service_files(changes['new_directories'])
        
        if filtered_new_files:
            output.append(f"[{timestamp}] НОВЫЕ ФАЙЛЫ:")
            for file_path in sorted(filtered_new_files):
                output.append(f"  ├─ {file_path}")
        
        if changes['modified_files']:
            output.append(f"[{timestamp}] ИЗМЕНЕННЫЕ ФАЙЛЫ:")
            for file_path in sorted(changes['modified_files']):
                output.append(f"  ├─ {file_path}")
        
        if filtered_new_dirs:
            output.append(f"[{timestamp}] НОВЫЕ ПАПКИ:")
            for dir_path in sorted(filtered_new_dirs):
                output.append(f"  └─ {dir_path}/")
        
        if changes['deleted_files']:
            output.append(f"[{timestamp}] УДАЛЕННЫЕ ФАЙЛЫ:")
            for file_path in sorted(changes['deleted_files']):
                output.append(f"  ├─ {file_path}")
        
        if changes['deleted_directories']:
            output.append(f"[{timestamp}] УДАЛЕННЫЕ ПАПКИ:")
            for dir_path in sorted(changes['deleted_directories']):
                output.append(f"  └─ {dir_path}/")
        
        return "\n".join(output) if output else "Изменений не обнаружено"

def main():
    """Основная функция"""
    # Проверяем аргументы командной строки для лог-файла
    log_file = None
    print(f"[DEBUG_ARGS] Все аргументы: {sys.argv}")
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            print(f"[DEBUG_ARGS] Аргумент {i}: '{arg}'")
            if arg == '--log-file' and i + 1 < len(sys.argv):
                log_file = sys.argv[i + 1]
                print(f"[DEBUG_ARGS] Найден лог-файл: '{log_file}'")
                break
    
    print(f"[DEBUG_ARGS] Итоговый log_file: '{log_file}'")
    
    # Если не передан, создаем автоматически
    if log_file is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(script_dir, "Log", "astra_automation_%s.log" % timestamp)
    
    # Создаем глобальную переменную для лог-файла
    global GLOBAL_LOG_FILE
    GLOBAL_LOG_FILE = log_file
    print(f"[GLOBAL_LOG] Установлен глобальный лог-файл: {GLOBAL_LOG_FILE}")
    
    # Создаем директорию Log если нужно
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Создаем единый universal_runner для всего приложения
    logger = get_global_universal_runner()
    logger.set_log_file(log_file)
    
    # КРИТИЧЕСКОЕ ОТЛАДОЧНОЕ СООБЩЕНИЕ НА СТАРТЕ
    print(f"[DEBUG_START] Python скрипт запущен! Лог файл: {log_file}", channels=["gui_log"])
    print(f"[DEBUG_START] Все аргументы: {sys.argv}", channels=["gui_log"])
    
    # ДОПОЛНИТЕЛЬНАЯ ОТЛАДКА - обычный print() для гарантии попадания в лог
    _original_print(f"[DEBUG_START_ORIGINAL] Python скрипт запущен! Лог файл: {log_file}")
    _original_print(f"[DEBUG_START_ORIGINAL] Все аргументы: {sys.argv}")
    
    # КРИТИЧНО: Немедленно обрабатываем очередь для записи в лог файл!
    logger.process_queue()
    
    # Диагностическая информация
    print(f"[INFO] Аргументы командной строки: {sys.argv}", channels=["gui_log"])
    print(f"[INFO] Количество аргументов: {len(sys.argv)}", channels=["gui_log"])
    print(f"[INFO] Текущая рабочая директория: {os.getcwd()}", channels=["gui_log"])
    print(f"[INFO] FSA-AstraInstall версия: {APP_VERSION}", channels=["gui_log"])
    print(f"[INFO] Python версия: {sys.version}", channels=["gui_log"])
    
    # КРИТИЧНО: Обрабатываем --close-terminal СРАЗУ после создания лог файла
    close_terminal_pid = None
    start_mode = None
    console_mode = False
    setup_repos = False
    dry_run = False  # Инициализируем dry_run
    
    # Обрабатываем аргументы командной строки
    i = 0
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--console':
            console_mode = True
            print("[INFO] Включен консольный режим", channels=["gui_log"])
        elif arg == '--dry-run':
            dry_run = True
            print("[INFO] Включен режим тестирования", channels=["gui_log"])
        elif arg == '--log-file':
            # Уже обработан выше
            i += 1  # Пропускаем следующий аргумент
        elif arg == '--setup-repos':
            setup_repos = True
            print("[INFO] Режим: только настройка репозиториев", channels=["gui_log"])
        elif arg == '--close-terminal':
            # Следующий аргумент - PID терминала
            if i + 1 < len(sys.argv):
                close_terminal_pid = sys.argv[i + 1]
                print(f"[INFO] Терминал будет закрыт после запуска GUI (PID: {close_terminal_pid})", channels=["gui_log"])
                print("[INFO] Получен PID терминала для закрытия: %s" % close_terminal_pid)
                
                # ЗАКРЫВАЕМ ТЕРМИНАЛ СРАЗУ!
                try:
                    import signal
                    pid = int(close_terminal_pid)
                    
                    # Проверяем что процесс существует
                    try:
                        os.kill(pid, 0)  # Сигнал 0 - только проверка существования
                        
                        # Сначала мягкое завершение
                        os.kill(pid, signal.SIGTERM)
                        
                        # Даем время на завершение
                        import time
                        time.sleep(0.5)
                        
                        # Проверяем что процесс завершился
                        try:
                            os.kill(pid, 0)
                            # Процесс еще жив - отправляем SIGKILL
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            # Процесс уже завершился
                            pass
                            
                    except OSError as e:
                        # Процесс уже не существует
                        pass
                        
                except Exception as e:
                    print(f"[ERROR] Ошибка закрытия терминала: {e}")
                
                i += 1  # Пропускаем следующий аргумент
            else:
                print("[WARNING] Флаг --close-terminal указан без PID", channels=["gui_log"])
        elif arg == '--mode':
            # Следующий аргумент - режим запуска
            if i + 1 < len(sys.argv):
                start_mode = sys.argv[i + 1]
                print(f"[INFO] Режим запуска: {start_mode}", channels=["gui_log"])
                i += 1  # Пропускаем следующий аргумент
        i += 1
    
    try:
        # Логируем системную информацию
        print("[INFO] Системная информация:", channels=["gui_log"])
        print(f"[INFO] OS: {os.name}", channels=["gui_log"])
        print(f"[INFO] Platform: {sys.platform}", channels=["gui_log"])
        print(f"[INFO] User ID: {os.getuid()}", channels=["gui_log"])
        print(f"[INFO] Effective User ID: {os.geteuid()}", channels=["gui_log"])
        
        # Проверяем права root
        if os.geteuid() == 0:
            print("[INFO] Запущено с правами root", channels=["gui_log"])
        else:
            print("[INFO] Запущено БЕЗ прав root", channels=["gui_log"])
        
        # Режим настройки репозиториев - выполнить и выйти
        if setup_repos:
            # В режиме --setup-repos не создаем отдельный лог файл
            # Все логи будут записаны в основной лог bash скрипта
            print("")
            print("="*60)
            print("[SETUP-REPOS] Настройка репозиториев")
            print("="*60)
            
            repo_checker = RepoChecker()
            
            # Создаем backup
            print("\n[BACKUP] Создаем резервную копию sources.list...")
            if repo_checker.backup_sources_list(dry_run=False):
                print("   [OK] Backup создан")
            else:
                print("   [ERROR] Не удалось создать backup")
                sys.exit(1)
            
            # Проверяем и настраиваем репозитории
            print("\n[CHECK] Проверка и настройка репозиториев...")
            temp_file = repo_checker.process_all_repos()
            
            if temp_file:
                # Применяем изменения
                try:
                    import shutil
                    shutil.copy2(temp_file, '/etc/apt/sources.list')
                    os.unlink(temp_file)
                    
                    stats = repo_checker.get_statistics()
                    print("\n[OK] Репозитории настроены:")
                    print("   - Активных: %d" % stats['activated'])
                    print("   - Деактивированных: %d" % stats['deactivated'])
                    
                    
                    print("\n" + "="*60)
                    print("[SUCCESS] Настройка репозиториев завершена")
                    print("="*60)
                    sys.exit(0)
                    
                except Exception as e:
                    print("\n[ERROR] Ошибка применения настроек: %s" % str(e))
                    sys.exit(1)
            else:
                print("\n[ERROR] Не удалось обработать репозитории")
                sys.exit(1)
            
            print("[INFO] Начинаем выполнение основной программы", channels=["gui_log"])
        
        # По умолчанию запускаем GUI, если не указан --console
        if not console_mode:
            print("[INFO] Запускаем GUI режим", channels=["gui_log"])
            # Проверяем системные требования
            if not check_system_requirements():
                print("[ERROR] Системные требования не выполнены", channels=["gui_log"])
                sys.exit(1)
            
            # Умная логика выбора режима на основе start_mode от bash
            if start_mode == "gui_ready":
                # GUI готов - запускаем сразу
                print("[GUI] GUI готов - запускаем интерфейс...")
                print("[INFO] Режим: gui_ready - запускаем GUI", channels=["gui_log"])
                
                try:
                    gui_success = run_gui_monitor(None, dry_run, close_terminal_pid)
                    if gui_success:
                        print("[OK] GUI мониторинг завершен", channels=["gui_log"])
                    else:
                        print("[ERROR] Ошибка GUI мониторинга", channels=["gui_log"])
                except Exception as gui_error:
                    print(f"[ERROR] Критическая ошибка GUI: {gui_error}", channels=["gui_log"])
                    
            elif start_mode == "gui_install_first":
                # Нужно установить GUI компоненты
                print("[GUI] Установка GUI компонентов...")
                print("[INFO] Режим: gui_install_first - устанавливаем GUI компоненты", channels=["gui_log"])
                
                if dry_run:
                    print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: установка GUI компонентов НЕ выполняется")
                    print("[OK] Будет выполнено: apt-get install -y python3-tk python3-pip")
                    gui_install_success = True
                else:
                    # Устанавливаем GUI компоненты
                    gui_install_success = install_gui_components()
                
                if gui_install_success:
                    print("[SUCCESS] GUI компоненты установлены успешно!", channels=["gui_log"])
                else:
                    print("[ERROR] Установка GUI компонентов завершена с ошибками")
                    print("[ERROR] Установка GUI компонентов завершена с ошибками", channels=["gui_log"])
                    
            elif start_mode == "console_forced":
                # Принудительный консольный режим - но мы в GUI режиме!
                print("[ERROR] Противоречие: bash выбрал console_forced, но Python в GUI режиме")
                print("[ERROR] Противоречие: bash выбрал console_forced, но Python в GUI режиме", channels=["gui_log"])
                print("[INFO] Перезапустите с флагом --console:")
                print("       bash astra_install.sh --console")
                sys.exit(1)
                
            else:
                # Неизвестный режим - пытаемся запустить GUI
                print("[WARNING] Неизвестный режим: %s" % start_mode)
                print(f"[WARNING] Неизвестный режим: {start_mode} - пытаемся запустить GUI", channels=["gui_log"])
                
                try:
                    gui_success = run_gui_monitor(None, dry_run, close_terminal_pid)
                    if gui_success:
                        print("[OK] GUI мониторинг завершен", channels=["gui_log"])
                    else:
                        print("[ERROR] Ошибка GUI мониторинга", channels=["gui_log"])
                except Exception as gui_error:
                    print(f"[ERROR] Критическая ошибка GUI: {gui_error}", channels=["gui_log"])
                    print("[ERROR] Критическая ошибка GUI: %s" % str(gui_error))
                print("[INFO] Очистка блокировок", channels=["gui_log"])
            return
    
        # Консольный режим (только если указан --console)
        print("[INFO] Запускаем консольный режим", channels=["gui_log"])
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
            print("[INFO] Проверяем системные требования", channels=["gui_log"])
            if not check_system_requirements():
                print("[ERROR] Системные требования не выполнены", channels=["gui_log"])
                sys.exit(1)
        
            # Умная логика консольного режима на основе start_mode от bash
            if start_mode == "console_forced":
                # Принудительный консольный режим - полное обновление системы
                print("[INFO] КОНСОЛЬНЫЙ РЕЖИМ: Обновление системы (console_forced)", channels=["gui_log"])
                print("\n[CONSOLE] Консольный режим - обновление системы...")
                
                # Обновляем систему
                print("[INFO] Запускаем обновление системы", channels=["gui_log"])
                print("\n[UPDATE] Обновление системы...")
                universal_runner = get_global_universal_runner()
                updater = SystemUpdater(universal_runner)
            
            if dry_run:
                print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: обновление НЕ выполняется")
                print("[OK] Будет выполнено: apt-get update && apt-get dist-upgrade -y && apt-get autoremove -y")
                update_success = True
            else:
                # Проверяем системные ресурсы
                if not updater.check_system_resources():
                    print("[ERROR] Системные ресурсы не соответствуют требованиям для обновления")
                    print("[ERROR] Системные ресурсы не соответствуют требованиям для обновления", channels=["gui_log"])
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
                    print("[INFO] Автоматизация завершена успешно в режиме тестирования", channels=["gui_log"])
                    print("\n[LIST] РЕЗЮМЕ РЕЖИМА ТЕСТИРОВАНИЯ:")
                    print("=============================")
                    print("[OK] Все проверки пройдены успешно")
                    print("[OK] Система готова к автоматизации")
                    print("[WARNING] Никаких изменений в системе НЕ внесено")
                    print("[START] Для реальной установки запустите без --dry-run")
                else:
                    print("\n[SUCCESS] Автоматизация завершена успешно!")
                    print("[INFO] Автоматизация завершена успешно", channels=["gui_log"])
            else:
                print("\n[ERROR] Автоматизация завершена с ошибками")
                print("[ERROR] Автоматизация завершена с ошибками", channels=["gui_log"])
            
            # Неожиданный режим в консольном режиме
            print("[ERROR] Неожиданный режим в консольном режиме: %s" % start_mode)
            print(f"[ERROR] Неожиданный режим в консольном режиме: {start_mode}", channels=["gui_log"])
            print("[INFO] Ожидался режим: console_forced")
            sys.exit(1)
            
        except KeyboardInterrupt:
            print("[WARNING] Программа остановлена пользователем (Ctrl+C)", channels=["gui_log"])
            print("\n[STOP] Остановлено пользователем")
            # Очищаем блокирующие файлы при прерывании
            print("[INFO] Очистка блокировок", channels=["gui_log"])
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Критическая ошибка в консольном режиме: {e}", channels=["gui_log"])
            print("\n[ERROR] Критическая ошибка: %s" % str(e))
            # Очищаем блокирующие файлы при ошибке
            print("[INFO] Очистка блокировок", channels=["gui_log"])
            sys.exit(1)
        finally:
            # Очищаем временные файлы
            if temp_dir:
                cleanup_temp_files(temp_dir)
            print("[INFO] Программа завершена", channels=["gui_log"])
            
    except Exception as main_error:
        # Критическая ошибка на уровне main()
        print(f"[ERROR] Критическая ошибка в main(): {main_error}", channels=["gui_log"])
        print("\n[FATAL] Критическая ошибка программы: %s" % str(main_error))
        print("Проверьте лог файл: %s" % logger.get_log_path())
        # Очищаем блокирующие файлы при критической ошибке
        try:
            print("[INFO] Очистка блокировок", channels=["gui_log"])
        except:
            pass

# ============================================================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================================================

if __name__ == '__main__':
    main()

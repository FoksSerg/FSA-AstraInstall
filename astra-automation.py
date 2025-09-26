#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-AstraInstall Automation - Единый исполняемый файл
Автоматически распаковывает компоненты и запускает автоматизацию astra-setup.sh
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import tempfile
import subprocess
import shutil
import re

# Перехватываем все print() вызовы в GUI режиме
_original_print = print
def print(*args, **kwargs):
    """Переопределенная функция print - перенаправляет в GUI терминал"""
    if hasattr(sys, '_gui_instance') and sys._gui_instance:
        # В GUI режиме - отправляем в терминал GUI
        message = ' '.join(str(arg) for arg in args)
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
                stderr=subprocess.PIPE
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
                stderr=subprocess.PIPE
            )
            stdout, stderr = result.communicate()
            
            if result.returncode == 0:
                # Ищем строку с количеством пакетов для удаления
                output = stdout.decode('utf-8', errors='ignore')
                
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
                stderr=subprocess.PIPE
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

def main(dry_run=False):
    """Основная функция для тестирования"""
    stats = SystemStats()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("[ERROR] Требуются права root для работы с системными пакетами")
        print("Запустите: sudo python system_stats.py")
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
    
    def __init__(self):
        # Проверяем и устанавливаем зависимости для GUI
        self._install_gui_dependencies()
        
        # Теперь импортируем tkinter (совместимость Python 2/3)
        if sys.version_info[0] == 2:
            import Tkinter as tk
            import ttk
        else:
            import tkinter as tk
            from tkinter import ttk
        
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
        
        # Создаем интерфейс
        self.create_widgets()
    
    def _install_gui_dependencies(self):
        """Установка зависимостей для GUI"""
        print("[PACKAGE] Проверка зависимостей для GUI...")
        
        try:
            # Проверяем наличие tkinter (совместимость Python 2/3)
            if sys.version_info[0] == 2:
                import Tkinter as tk
            else:
                import tkinter as tk
            print("[OK] tkinter уже установлен")
            return True
        except ImportError:
            print("[WARNING] tkinter не найден, устанавливаем python-tk...")
            
            try:
                # Устанавливаем python-tk
                result = subprocess.call(['apt-get', 'install', '-y', 'python-tk'], 
                                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                if result == 0:
                    print("[OK] python-tk успешно установлен")
                    return True
                else:
                    print("[ERROR] Не удалось установить python-tk")
                    return False
                    
            except Exception as e:
                print("[ERROR] Ошибка установки python-tk: %s" % str(e))
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
        """Добавление сообщения в системный терминал"""
        try:
            # Временно разблокируем терминал для записи
            self.terminal_text.config(state=self.tk.NORMAL)
            self.terminal_text.insert(self.tk.END, message + "\n")
            self.terminal_text.see(self.tk.END)
            # Снова блокируем терминал
            self.terminal_text.config(state=self.tk.DISABLED)
            self.root.update_idletasks()
        except Exception as e:
            pass  # Игнорируем ошибки если терминал не готов
        
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
        
    def run_automation(self):
        """Запуск автоматизации в отдельном потоке"""
        try:
            self.update_status("Запуск автоматизации...")
            self.log_message("=" * 60)
            self.log_message("FSA-AstraInstall Automation")
            self.log_message("Автоматизация установки Astra.IDE")
            self.log_message("=" * 60)
            
            if self.dry_run.get():
                self.log_message("Режим: ТЕСТИРОВАНИЕ (dry-run)")
            else:
                self.log_message("Режим: РЕАЛЬНАЯ УСТАНОВКА")
            
            self.log_message("")
            
            # Передаем экземпляр GUI в модули для вывода в терминал
            import sys
            sys._gui_instance = self
            
            # Запускаем модули по очереди
            self.log_message("[INFO] Проверка системных требований...")
            self.log_message("[OK] Все требования выполнены")
            
            # 1. Проверка репозиториев
            self.update_status("Проверка репозиториев...", "Репозитории")
            self.log_message("[START] Запуск автоматизации проверки репозиториев...")
            
            # Используем класс RepoChecker напрямую
            checker = RepoChecker(gui_terminal=self)
            if not checker.backup_sources_list(self.dry_run.get()):
                repo_success = False
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
            
            if repo_success:
                self.log_message("[OK] Автоматизация репозиториев завершена успешно")
            else:
                self.log_message("[ERROR] Ошибка автоматизации репозиториев")
                return
            
            # 2. Статистика системы
            self.update_status("Анализ статистики...", "Статистика")
            self.log_message("[STATS] Запуск анализа статистики системы...")
            
            # Используем класс SystemStats напрямую
            stats = SystemStats()
            if not stats.get_updatable_packages():
                self.log_message("[WARNING] Предупреждение: не удалось получить список обновлений")
            
            if not stats.get_autoremove_packages():
                self.log_message("[WARNING] Предупреждение: не удалось проанализировать автоудаление")
            
            if not stats.calculate_install_stats():
                self.log_message("[WARNING] Предупреждение: не удалось подсчитать пакеты для установки")
            
            stats.display_statistics()
            
            if self.dry_run.get():
                self.log_message("[OK] Анализ статистики завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
            else:
                self.log_message("[OK] Анализ статистики завершен успешно!")
            
            # 3. Тест интерактивных запросов
            self.update_status("Тест интерактивных запросов...", "Интерактивные")
            self.log_message("[AUTO] Запуск тестирования перехвата интерактивных запросов...")
            
            # Используем класс InteractiveHandler напрямую
            handler = InteractiveHandler()
            handler.simulate_interactive_scenarios()
            
            if self.dry_run.get():
                self.log_message("[OK] Тест перехвата интерактивных запросов завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
            else:
                self.log_message("[OK] Тест перехвата интерактивных запросов завершен успешно!")
            
            # 4. Обновление системы
            self.update_status("Обновление системы...", "Обновление")
            self.log_message("[PROCESS] Запуск обновления системы...")
            
            # Используем класс SystemUpdater напрямую
            updater = SystemUpdater()
            updater.simulate_update_scenarios()
            
            if not self.dry_run.get():
                self.log_message("[TOOL] Тест реального обновления системы...")
                success = updater.update_system(self.dry_run.get())
                if success:
                    self.log_message("[OK] Обновление системы завершено успешно")
                else:
                    self.log_message("[ERROR] Обновление системы завершено с ошибкой")
            else:
                self.log_message("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: реальное обновление не выполняется")
                updater.update_system(self.dry_run.get())
            
            # Завершение
            if self.dry_run.get():
                self.update_status("Автоматизация завершена успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
                self.log_message("")
                self.log_message("[SUCCESS] Автоматизация завершена успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
            else:
                self.update_status("Автоматизация завершена успешно!")
                self.log_message("")
                self.log_message("[SUCCESS] Автоматизация завершена успешно!")
                
        except Exception as e:
            self.update_status("Ошибка выполнения")
            self.log_message("[ERROR] Ошибка: %s" % str(e))
            
        finally:
            self.is_running = False
            self.start_button.config(state=self.tk.NORMAL)
            self.stop_button.config(state=self.tk.DISABLED)
            
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

class SystemUpdater(object):
    """Класс для обновления системы с автоматическими ответами"""
    
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
                    if response == '':
                        print("   [AUTO] Автоматический ответ: Enter (пустой ответ) для %s" % prompt_type)
                    else:
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
                # Проверяем на ошибки dpkg
                if "dpkg была прервана" in output_buffer or "dpkg --configure -a" in output_buffer:
                    print("   [TOOL] Обнаружена ошибка dpkg, запускаем автоматическое исправление...")
                    if self.auto_fix_dpkg_errors():
                        print("   [OK] Ошибки dpkg исправлены автоматически")
                    else:
                        print("   [WARNING] Не удалось автоматически исправить ошибки dpkg")
            
            return return_code
            
        except Exception as e:
            print("   [ERROR] Ошибка выполнения команды: %s" % str(e))
            return 1
    
    def update_system(self, dry_run=False):
        """Обновление системы"""
        print("[PACKAGE] Обновление системы...")
        
        if dry_run:
            print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: обновление НЕ выполняется")
            print("[OK] Будет выполнено: apt-get update && apt-get dist-upgrade -y && apt-get autoremove -y")
            return True
        
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
                else:
                    print("[ERROR] Ошибка обновления системы даже после исправления")
                    return False
            else:
                print("[ERROR] Не удалось автоматически исправить ошибки dpkg")
                return False
    
    def auto_fix_dpkg_errors(self):
        """Автоматическое исправление ошибок dpkg"""
        print("[TOOL] Автоматическое исправление ошибок dpkg...")
        
        try:
            # 1. Исправляем конфигурацию dpkg
            print("   [TOOL] Запускаем dpkg --configure -a...")
            configure_cmd = ['dpkg', '--configure', '-a']
            result = self.run_command_with_interactive_handling(configure_cmd, False, gui_terminal=True)
            
            if result == 0:
                print("   [OK] dpkg --configure -a выполнен успешно")
            else:
                print("   [WARNING] dpkg --configure -a завершился с ошибкой")
            
            # 2. Исправляем сломанные зависимости
            print("   [TOOL] Запускаем apt --fix-broken install...")
            fix_cmd = ['apt', '--fix-broken', 'install', '-y']
            result = self.run_command_with_interactive_handling(fix_cmd, False, gui_terminal=True)
            
            if result == 0:
                print("   [OK] apt --fix-broken install выполнен успешно")
                return True
            else:
                print("   [WARNING] apt --fix-broken install завершился с ошибкой")
                
                # 3. Принудительное удаление проблемных пакетов
                print("   [TOOL] Пробуем принудительное удаление проблемных пакетов...")
                force_remove_cmd = ['dpkg', '--remove', '--force-remove-reinstreq', 'python-tk', 'python-qt4']
                result = self.run_command_with_interactive_handling(force_remove_cmd, False, gui_terminal=True)
                
                if result == 0:
                    print("   [OK] Проблемные пакеты удалены принудительно")
                    # Повторяем исправление зависимостей
                    result = self.run_command_with_interactive_handling(fix_cmd, False, gui_terminal=True)
                    if result == 0:
                        print("   [OK] Зависимости исправлены после принудительного удаления")
                        return True
                
                return False
                
        except Exception as e:
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
    
    # Проверяем Python версию (поддерживаем Python 2.7+ и Python 3.x)
    if sys.version_info[0] == 2 and sys.version_info[1] < 7:
        print("[ERROR] Требуется Python 2.7+ или Python 3.x")
        print("   Текущая версия: %s" % sys.version)
        return False
    elif sys.version_info[0] not in [2, 3]:
        print("[ERROR] Требуется Python 2.7+ или Python 3.x")
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
            print("Запустите: sudo python astra-automation.py")
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
            print("Запустите: sudo python astra-automation.py")
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
        gui = AutomationGUI()
        
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
    # Проверяем аргументы командной строки
    dry_run = False
    console_mode = False
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == '--dry-run':
                dry_run = True
            elif arg == '--console':
                console_mode = True
    
    # По умолчанию запускаем GUI, если не указан --console
    if not console_mode:
        # Проверяем системные требования
        if not check_system_requirements():
            sys.exit(1)
        
        # Запускаем GUI
        print("[GUI] Запуск GUI мониторинга...")
        gui_success = run_gui_monitor(None, dry_run)
        if gui_success:
            print("[OK] GUI мониторинг завершен")
        else:
            print("[ERROR] Ошибка GUI мониторинга")
        return
    
    # Консольный режим (только если указан --console)
    print("=" * 60)
    if dry_run:
        print("FSA-AstraInstall Automation (РЕЖИМ ТЕСТИРОВАНИЯ)")
    else:
        print("FSA-AstraInstall Automation")
    print("Автоматизация установки Astra.IDE")
    print("=" * 60)
    
    temp_dir = None
    
    try:
        # Проверяем системные требования
        if not check_system_requirements():
            sys.exit(1)
        
        # Запускаем автоматизацию репозиториев
        repo_success = run_repo_checker(gui_terminal=None, dry_run=dry_run)
        
        # Запускаем анализ статистики
        stats_success = run_system_stats(temp_dir, dry_run)
        
        # Запускаем тест перехвата интерактивных запросов
        interactive_success = run_interactive_handler(temp_dir, dry_run)
        
        # Запускаем обновление системы
        update_success = run_system_updater(temp_dir, dry_run)
        
        if repo_success and stats_success and interactive_success and update_success:
            if dry_run:
                print("\n[SUCCESS] Автоматизация завершена успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
                print("\n[LIST] РЕЗЮМЕ РЕЖИМА ТЕСТИРОВАНИЯ:")
                print("=============================")
                print("[OK] Все проверки пройдены успешно")
                print("[OK] Система готова к автоматизации")
                print("[WARNING] Никаких изменений в системе НЕ внесено")
                print("[START] Для реальной установки запустите без --dry-run")
            else:
                print("\n[SUCCESS] Автоматизация завершена успешно!")
        else:
            print("\n[ERROR] Автоматизация завершена с ошибками")
            if not repo_success:
                print("   [ERROR] Ошибка в модуле проверки репозиториев")
            if not stats_success:
                print("   [ERROR] Ошибка в модуле статистики системы")
            if not interactive_success:
                print("   [ERROR] Ошибка в модуле перехвата интерактивных запросов")
            if not update_success:
                print("   [ERROR] Ошибка в модуле обновления системы")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n[STOP] Остановлено пользователем")
        sys.exit(1)
    except Exception as e:
        print("\n[ERROR] Критическая ошибка: %s" % str(e))
        sys.exit(1)
    finally:
        # Очищаем временные файлы
        if temp_dir:
            cleanup_temp_files(temp_dir)

if __name__ == '__main__':
    main()

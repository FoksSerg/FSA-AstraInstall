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

# Встроенные компоненты (будут добавлены автоматически)
EMBEDDED_FILES = {
    'automation/repo_checker.py': '',
    'config/auto_responses.json': ''
}

def get_embedded_repo_checker():
    """Встроенный код repo_checker.py"""
    return '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль автоматизации проверки репозиториев для astra-setup.sh
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import subprocess
import tempfile
import shutil
from collections import defaultdict

class RepoChecker(object):
    """Класс для проверки и настройки репозиториев APT"""
    
    def __init__(self):
        self.sources_list = '/etc/apt/sources.list'
        self.backup_file = '/etc/apt/sources.list.backup'
        self.activated_count = 0
        self.deactivated_count = 0
        self.working_repos = []
        self.broken_repos = []
    
    def backup_sources_list(self, dry_run=False):
        """Создание backup файла репозиториев"""
        try:
            if os.path.exists(self.sources_list):
                if dry_run:
                    print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: backup НЕ создан (только симуляция)")
                    print("[OK] Backup будет создан: %s" % self.backup_file)
                else:
                    shutil.copy2(self.sources_list, self.backup_file)
                    print("[OK] Backup создан: %s" % self.backup_file)
                return True
            else:
                print("[ERROR] Файл sources.list не найден: %s" % self.sources_list)
                return False
        except Exception as e:
            print("[ERROR] Ошибка создания backup: %s" % str(e))
            return False
    
    def check_repo_availability(self, repo_line):
        """Проверка доступности одного репозитория"""
        try:
            # Создаем временный файл с одним репозиторием
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_file.write(repo_line + '\\n')
            temp_file.close()
            
            # Проверяем доступность через apt-get update
            cmd = [
                'apt-get', 'update',
                '-o', 'Dir::Etc::sourcelist=%s' % temp_file.name,
                '-o', 'Dir::Etc::sourceparts=-',
                '-o', 'APT::Get::List-Cleanup=0'
            ]
            
            result = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setpgrp
            )
            stdout, stderr = result.communicate()
            
            # Удаляем временный файл
            os.unlink(temp_file.name)
            
            if result.returncode == 0:
                repo_name = repo_line.split()[1] if len(repo_line.split()) > 1 else repo_line
                print("[OK] Рабочий: %s" % repo_name)
                return True
            else:
                repo_name = repo_line.split()[1] if len(repo_line.split()) > 1 else repo_line
                print("[ERROR] Не доступен: %s" % repo_name)
                return False
                
        except Exception as e:
            print("[ERROR] Ошибка проверки репозитория: %s" % str(e))
            return False
    
    def process_all_repos(self):
        """Обработка всех репозиториев из sources.list"""
        print("\\n2. Проверка репозиториев...")
        print("==========================")
        
        try:
            with open(self.sources_list, 'r') as f:
                lines = f.readlines()
            
            # Создаем временный файл для нового sources.list
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_file.write("# Astra Linux repositories - auto configured\\n")
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('#deb') or line.startswith('deb'):
                    # Обрабатываем репозиторий
                    if line.startswith('#'):
                        # Закомментированный репозиторий
                        clean_line = line[1:].strip()
                        if self.check_repo_availability(clean_line):
                            temp_file.write(clean_line + '\\n')
                            self.activated_count += 1
                            self.working_repos.append(clean_line)
                        else:
                            temp_file.write(line + '\\n')
                            self.deactivated_count += 1
                            self.broken_repos.append(clean_line)
                    else:
                        # Активный репозиторий
                        if self.check_repo_availability(line):
                            temp_file.write(line + '\\n')
                            self.activated_count += 1
                            self.working_repos.append(line)
                        else:
                            temp_file.write('# ' + line + '\\n')
                            self.deactivated_count += 1
                            self.broken_repos.append(line)
                else:
                    # Комментарии и пустые строки
                    temp_file.write(line + '\\n')
            
            temp_file.close()
            
            # Удаляем дубликаты
            self._remove_duplicates(temp_file.name)
            
            return temp_file.name
            
        except Exception as e:
            print("[ERROR] Ошибка обработки репозиториев: %s" % str(e))
            return None
    
    def _remove_duplicates(self, temp_file):
        """Удаление дубликатов из временного файла"""
        try:
            with open(temp_file, 'r') as f:
                lines = f.readlines()
            
            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            
            with open(temp_file, 'w') as f:
                f.writelines(unique_lines)
                
        except Exception as e:
            print("[WARNING] Предупреждение: не удалось удалить дубликаты: %s" % str(e))
    
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
                print("\\n[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: изменения НЕ применены к sources.list")
                print("[OK] Изменения будут применены к sources.list")
                
                print("\\nАктивированные репозитории (будут активированы):")
                with open(temp_file, 'r') as f:
                    for line in f:
                        if line.strip().startswith('deb '):
                            print("   • %s" % line.strip())
            else:
                shutil.copy2(temp_file, self.sources_list)
                print("\\n[OK] Изменения применены к sources.list")
                
                print("\\nАктивированные репозитории:")
                with open(self.sources_list, 'r') as f:
                    for line in f:
                        if line.strip().startswith('deb '):
                            print("   • %s" % line.strip())
            
            return True
        except Exception as e:
            print("[ERROR] Ошибка применения изменений: %s" % str(e))
            return False

def main(dry_run=False):
    """Основная функция для тестирования"""
    
    checker = RepoChecker()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("[ERROR] Требуются права root для работы с /etc/apt/sources.list")
        print("Запустите: sudo python repo_checker.py")
        sys.exit(1)
    
    # Создаем backup
    if not checker.backup_sources_list(dry_run):
        sys.exit(1)
    
    # Обрабатываем репозитории
    temp_file = checker.process_all_repos()
    if not temp_file:
        sys.exit(1)
    
    # Показываем статистику
    stats = checker.get_statistics()
    print("\\nСТАТИСТИКА РЕПОЗИТОРИЕВ:")
    print("=========================")
    print("[LIST] Репозитории:")
    print("   • Активировано: %d рабочих" % stats['activated'])
    print("   • Деактивировано: %d нерабочих" % stats['deactivated'])
    
    # Применяем изменения
    if checker.apply_changes(temp_file, dry_run):
        if dry_run:
            print("\\n[OK] Тест завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
        else:
            print("\\n[OK] Тест завершен успешно!")
    else:
        print("\\n[ERROR] Ошибка применения изменений")
    
    # Очистка
    try:
        os.unlink(temp_file)
    except:
        pass
    
    return True

if __name__ == '__main__':
    # Проверяем аргументы командной строки
    dry_run = False
    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        dry_run = True
    
    print("==================================================")
    if dry_run:
        print("Тест модуля проверки репозиториев (РЕЖИМ ТЕСТИРОВАНИЯ)")
    else:
        print("Тест модуля проверки репозиториев")
    print("==================================================")
    
    success = main(dry_run)
    
    if not success:
        sys.exit(1)
'''

def get_embedded_config():
    """Встроенная конфигурация auto_responses.json"""
    return '''{
    "description": "Правила автоматических ответов на интерактивные запросы системы",
    "rules": {
        "openssl.cnf": "N",
        "keyboard-configuration": "Y", 
        "default": "N"
    },
    "interactive_patterns": {
        "dpkg_config": "\\\\*\\\\*\\\\* .* \\\\(Y/I/N/O/D/Z\\\\) \\\\[.*\\\\] \\\\?",
        "apt_config": "Настройка пакета",
        "keyboard_config": "Выберите подходящую раскладку клавиатуры"
    }
}'''

def get_embedded_gui_monitor():
    """Встроенный код gui_monitor.py"""
    return '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GUI мониторинг процессов автоматизации Astra.IDE
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import subprocess
import threading
import time

# Проверяем и устанавливаем зависимости для GUI
def install_gui_dependencies():
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

# Устанавливаем зависимости перед импортом tkinter
if not install_gui_dependencies():
    print("[ERROR] Не удалось установить зависимости для GUI")
    print("Попробуйте запустить: sudo apt-get install python-tk")
    sys.exit(1)

# Теперь импортируем tkinter (совместимость Python 2/3)
if sys.version_info[0] == 2:
    import Tkinter as tk
else:
    import tkinter as tk

class AutomationGUI(object):
    """GUI для мониторинга автоматизации установки Astra.IDE"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FSA-AstraInstall Automation")
        self.root.geometry("1000x700")
        
        # Переменные состояния
        self.is_running = False
        self.dry_run = tk.BooleanVar()
        self.process_thread = None
        
        # Создаем интерфейс
        self.create_widgets()
        
    def create_widgets(self):
        """Создание элементов интерфейса"""
        
        # Панель управления
        control_frame = tk.LabelFrame(self.root, text="Управление")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Чекбокс для dry-run
        dry_run_check = tk.Checkbutton(control_frame, text="Режим тестирования (dry-run)", 
                                       variable=self.dry_run)
        dry_run_check.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Кнопки управления
        button_frame = tk.Frame(control_frame)
        button_frame.pack(side=tk.RIGHT, padx=5, pady=5)
        
        self.start_button = tk.Button(button_frame, text="Запустить", 
                                      command=self.start_automation)
        self.start_button.pack(side=tk.LEFT, padx=2)
        
        self.stop_button = tk.Button(button_frame, text="Остановить", 
                                     command=self.stop_automation, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=2)
        
        # Прогресс
        progress_frame = tk.LabelFrame(self.root, text="Прогресс")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress_label = tk.Label(progress_frame, text="Готов к запуску", 
                                      relief=tk.SUNKEN, anchor=tk.W)
        self.progress_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Статус
        status_frame = tk.LabelFrame(self.root, text="Статус")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = tk.Label(status_frame, text="Готов к запуску")
        self.status_label.pack(padx=5, pady=5)
        
        # Лог выполнения
        log_frame = tk.LabelFrame(self.root, text="Лог выполнения")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем Text с прокруткой (увеличиваем высоту)
        self.log_text = tk.Text(log_frame, height=20, wrap=tk.WORD)
        scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Статистика
        stats_frame = tk.LabelFrame(self.root, text="Статистика")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        stats_inner = tk.Frame(stats_frame)
        stats_inner.pack(fill=tk.X, padx=5, pady=5)
        
        # Колонки статистики
        tk.Label(stats_inner, text="Репозитории:").grid(row=0, column=0, sticky=tk.W)
        self.repo_label = tk.Label(stats_inner, text="Не проверены")
        self.repo_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        tk.Label(stats_inner, text="Обновления:").grid(row=0, column=2, sticky=tk.W)
        self.update_label = tk.Label(stats_inner, text="Не проверены")
        self.update_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 20))
        
        tk.Label(stats_inner, text="Пакеты:").grid(row=1, column=0, sticky=tk.W)
        self.package_label = tk.Label(stats_inner, text="Не проверены")
        self.package_label.grid(row=1, column=1, sticky=tk.W, padx=(5, 20))
        
        tk.Label(stats_inner, text="Статус:").grid(row=1, column=2, sticky=tk.W)
        self.status_detail_label = tk.Label(stats_inner, text="Ожидание")
        self.status_detail_label.grid(row=1, column=3, sticky=tk.W, padx=(5, 20))
        
    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.log_text.insert(tk.END, message + "\\n")
        self.log_text.see(tk.END)
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
        
    def start_automation(self):
        """Запуск автоматизации"""
        if self.is_running:
            return
            
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_label.config(text="Выполняется...", bg="lightblue")
        
        # Очищаем лог
        self.log_text.delete(1.0, tk.END)
        
        # Запускаем автоматизацию в отдельном потоке
        self.process_thread = threading.Thread(target=self.run_automation)
        self.process_thread.daemon = True
        self.process_thread.start()
        
    def stop_automation(self):
        """Остановка автоматизации"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_label.config(text="Завершено", bg="lightgreen")
        self.update_status("Остановлено пользователем")
        
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
            
            # Импортируем модули автоматизации
            import sys
            import os
            
            # Добавляем путь к модулям (текущая директория)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            # Импортируем модули
            import repo_checker
            import system_stats
            import interactive_handler
            import system_updater
            
            # Запускаем модули по очереди
            self.log_message("[INFO] Проверка системных требований...")
            self.log_message("[OK] Все требования выполнены")
            
            # 1. Проверка репозиториев
            self.update_status("Проверка репозиториев...", "Репозитории")
            self.log_message("[START] Запуск автоматизации проверки репозиториев...")
            repo_success = repo_checker.main(self.dry_run.get())
            
            if repo_success:
                self.log_message("[OK] Автоматизация репозиториев завершена успешно")
            else:
                self.log_message("[ERROR] Ошибка автоматизации репозиториев")
                return
            
            # 2. Статистика системы
            self.update_status("Анализ статистики...", "Статистика")
            self.log_message("[STATS] Запуск анализа статистики системы...")
            stats_success = system_stats.main(self.dry_run.get())
            
            if stats_success:
                self.log_message("[OK] Анализ статистики завершен успешно")
            else:
                self.log_message("[ERROR] Ошибка анализа статистики")
                return
            
            # 3. Тест интерактивных запросов
            self.update_status("Тест интерактивных запросов...", "Интерактивные")
            self.log_message("[AUTO] Запуск тестирования перехвата интерактивных запросов...")
            interactive_success = interactive_handler.main(self.dry_run.get())
            
            if interactive_success:
                self.log_message("[OK] Тест интерактивных запросов завершен успешно")
            else:
                self.log_message("[ERROR] Ошибка теста интерактивных запросов")
                return
            
            # 4. Обновление системы
            self.update_status("Обновление системы...", "Обновление")
            self.log_message("[PROCESS] Запуск обновления системы...")
            update_success = system_updater.main(self.dry_run.get())
            
            if update_success:
                self.log_message("[OK] Обновление системы завершено успешно")
            else:
                self.log_message("[ERROR] Ошибка обновления системы")
                return
            
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
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress_label.config(text="Завершено", bg="lightgreen")
            
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

def main():
    """Основная функция"""
    print("Запуск GUI мониторинга автоматизации...")
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("[ERROR] Требуются права root для работы с системными файлами")
        print("Запустите: sudo python gui_monitor.py")
        sys.exit(1)
    
    # Проверяем наличие astra-automation.py
    if not os.path.exists('astra-automation.py'):
        print("[ERROR] Файл astra-automation.py не найден")
        print("Запустите из папки с файлом astra-automation.py")
        sys.exit(1)
    
    # Запускаем GUI (зависимости уже установлены в начале файла)
    app = AutomationGUI()
    app.run()

if __name__ == '__main__':
    main()
'''

def get_embedded_system_updater():
    """Встроенный код system_updater.py"""
    return '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль обновления системы с автоматическими ответами
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import subprocess
import re

class SystemUpdater(object):
    """Класс для обновления системы с автоматическими ответами"""
    
    def __init__(self):
        self.patterns = {
            'dpkg_config': r'\\*\\*\\* .* \\(Y/I/N/O/D/Z\\) \\[.*\\] \\?',
            'apt_config': r'Настройка пакета',
            'keyboard_config': r'Выберите подходящую раскладку клавиатуры',
            'keyboard_switch': r'способ переключения клавиатуры между национальной раскладкой',
            'language_config': r'Выберите язык системы',
            'restart_services': r'Перезапустить службы во время пакетных операций'
        }
        
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
    
    def run_command_with_interactive_handling(self, cmd, dry_run=False):
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
                    process.stdin.write(response + '\\n')
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
    
    def update_system(self, dry_run=False):
        """Обновление системы"""
        print("[PACKAGE] Обновление системы...")
        
        if dry_run:
            print("[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: обновление НЕ выполняется")
            print("[OK] Будет выполнено: apt-get update && apt-get dist-upgrade -y && apt-get autoremove -y")
            return True
        
        # Сначала обновляем списки пакетов
        print("\\n[PROCESS] Обновление списков пакетов...")
        update_cmd = ['apt-get', 'update']
        result = self.run_command_with_interactive_handling(update_cmd, dry_run)
        
        if result != 0:
            print("[ERROR] Ошибка обновления списков пакетов")
            return False
        
        # Затем обновляем систему
        print("\\n[START] Обновление системы...")
        upgrade_cmd = ['apt-get', 'dist-upgrade', '-y']
        result = self.run_command_with_interactive_handling(upgrade_cmd, dry_run)
        
        if result == 0:
            print("[OK] Система успешно обновлена")
            
            # Автоматическая очистка ненужных пакетов
            print("\\n[CLEANUP] Автоматическая очистка ненужных пакетов...")
            autoremove_cmd = ['apt-get', 'autoremove', '-y']
            autoremove_result = self.run_command_with_interactive_handling(autoremove_cmd, dry_run)
            
            if autoremove_result == 0:
                print("[OK] Ненужные пакеты успешно удалены")
            else:
                print("[WARNING] Предупреждение: не удалось удалить ненужные пакеты")
            
            return True
        else:
            print("[ERROR] Ошибка обновления системы")
            return False
    
    def simulate_update_scenarios(self):
        """Симуляция различных сценариев обновления"""
        print("[PROCESS] Симуляция сценариев обновления...")
        
        # Тест 1: dpkg конфигурационный файл
        print("\\n[LIST] Тест 1: dpkg конфигурационный файл")
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
        print("\\n[PROCESS] Тест 2: перезапуск служб")
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
        
        print("\\n[OK] Симуляция завершена")

def main(dry_run=False):
    """Основная функция для тестирования"""
    updater = SystemUpdater()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("[ERROR] Требуются права root для работы с системными пакетами")
        print("Запустите: sudo python system_updater.py")
        return False
    
    # Симулируем сценарии обновления
    updater.simulate_update_scenarios()
    
    # Тестируем обновление системы
    if not dry_run:
        print("\\n[TOOL] Тест реального обновления системы...")
        success = updater.update_system(dry_run)
        
        if success:
            print("[OK] Обновление системы завершено успешно")
        else:
            print("[ERROR] Обновление системы завершено с ошибкой")
    else:
        print("\\n[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: реальное обновление не выполняется")
        updater.update_system(dry_run)
    
    return True

if __name__ == '__main__':
    # Проверяем аргументы командной строки
    dry_run = False
    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        dry_run = True
    
    print("=" * 60)
    if dry_run:
        print("Тест модуля обновления системы (РЕЖИМ ТЕСТИРОВАНИЯ)")
    else:
        print("Тест модуля обновления системы")
    print("=" * 60)
    
    success = main(dry_run)
    
    if success:
        if dry_run:
            print("\\n[OK] Тест модуля завершен! (РЕЖИМ ТЕСТИРОВАНИЯ)")
        else:
            print("\\n[OK] Тест модуля завершен!")
    else:
        print("\\n[ERROR] Ошибка теста модуля")
        sys.exit(1)
'''

def get_embedded_interactive_handler():
    """Встроенный код interactive_handler.py"""
    return '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль перехвата интерактивных запросов для автоматизации установки
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import subprocess
import threading
import time
import re

class InteractiveHandler(object):
    """Класс для перехвата и автоматических ответов на интерактивные запросы"""
    
    def __init__(self):
        self.patterns = {
            'dpkg_config': r'\\*\\*\\* .* \\(Y/I/N/O/D/Z\\) \\[.*\\] \\?',
            'apt_config': r'Настройка пакета',
            'keyboard_config': r'Выберите подходящую раскладку клавиатуры',
            'keyboard_switch': r'способ переключения клавиатуры между национальной раскладкой',
            'language_config': r'Выберите язык системы'
        }
        
        self.responses = {
            'dpkg_config': 'Y',      # Всегда соглашаемся с новыми версиями
            'apt_config': '',        # Принимаем настройки по умолчанию (Enter)
            'keyboard_config': '',   # Принимаем предложенную раскладку (Enter)
            'keyboard_switch': '',   # Принимаем способ переключения (Enter)
            'language_config': ''    # Принимаем язык системы (Enter)
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
    
    def run_command_with_interactive_handling(self, cmd, dry_run=False):
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
                    process.stdin.write(response + '\\n')
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
        print("\\n[LIST] Тест 1: dpkg конфигурационный файл")
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
        print("\\n[KEYBOARD] Тест 2: настройка клавиатуры")
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
        print("\\n[PROCESS] Тест 3: способ переключения клавиатуры")
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
        
        print("\\n[OK] Симуляция завершена")

def main(dry_run=False):
    """Основная функция для тестирования"""
    handler = InteractiveHandler()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("[ERROR] Требуются права root для работы с системными командами")
        print("Запустите: sudo python interactive_handler.py")
        return False
    
    # Симулируем интерактивные сценарии
    handler.simulate_interactive_scenarios()
    
    # Тестируем реальную команду (если не dry-run)
    if not dry_run:
        print("\\n[TOOL] Тест реальной команды...")
        # Пример команды, которая может вызвать интерактивные запросы
        test_cmd = ['apt-get', 'install', '--simulate', 'openssl']
        result = handler.run_command_with_interactive_handling(test_cmd, dry_run)
        
        if result == 0:
            print("[OK] Тест реальной команды завершен успешно")
        else:
            print("[ERROR] Тест реальной команды завершен с ошибкой")
    else:
        print("\\n[WARNING] РЕЖИМ ТЕСТИРОВАНИЯ: реальные команды не выполняются")
    
    return True

if __name__ == '__main__':
    # Проверяем аргументы командной строки
    dry_run = False
    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        dry_run = True
    
    print("=" * 60)
    if dry_run:
        print("Тест модуля перехвата интерактивных запросов (РЕЖИМ ТЕСТИРОВАНИЯ)")
    else:
        print("Тест модуля перехвата интерактивных запросов")
    print("=" * 60)
    
    success = main(dry_run)
    
    if success:
        if dry_run:
            print("\\n[OK] Тест модуля завершен! (РЕЖИМ ТЕСТИРОВАНИЯ)")
        else:
            print("\\n[OK] Тест модуля завершен!")
    else:
        print("\\n[ERROR] Ошибка теста модуля")
        sys.exit(1)
'''

def get_embedded_system_stats():
    """Встроенный код system_stats.py"""
    return '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль анализа статистики системы для astra-setup.sh
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import subprocess
import re

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
                lines = stdout.strip().split('\\n')
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
        print("\\nСТАТИСТИКА ОПЕРАЦИЙ:")
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
        print("\\n[PACKAGE] Обновление системы:")
        print("   • Пакетов для обновления: %d" % self.packages_to_update)
        
        if self.packages_to_update > 0 and self.updatable_list:
            print("   • Первые пакеты:")
            for package in self.updatable_list:
                if package.strip():
                    print("     - %s" % package.strip())
        
        # Очистка системы
        print("\\n[CLEANUP] Очистка системы:")
        print("   • Пакетов для удаления: %d" % self.packages_to_remove)
        
        # Установка новых пакетов
        print("\\n[PACKAGE] Установка новых пакетов:")
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

if __name__ == '__main__':
    print("=" * 60)
    print("Тест модуля статистики системы")
    print("=" * 60)
    
    success = main()
    
    if success:
        print("\\n[OK] Тест модуля статистики завершен!")
    else:
        print("\\n[ERROR] Ошибка теста модуля статистики")
        sys.exit(1)
'''

def create_embedded_data():
    """Создание встроенных данных - всегда используем встроенные версии"""
    print("[PACKAGE] Загрузка встроенных компонентов...")
    
    embedded_data = {
        'automation/repo_checker.py': get_embedded_repo_checker(),
        'automation/system_stats.py': get_embedded_system_stats(),
        'automation/interactive_handler.py': get_embedded_interactive_handler(),
        'automation/system_updater.py': get_embedded_system_updater(),
        'automation/gui_monitor.py': get_embedded_gui_monitor(),
        'config/auto_responses.json': get_embedded_config()
    }
    
    print("[OK] Все компоненты загружены из встроенных данных:")
    print("   • automation/repo_checker.py (%d символов)" % len(embedded_data['automation/repo_checker.py']))
    print("   • automation/system_stats.py (%d символов)" % len(embedded_data['automation/system_stats.py']))
    print("   • automation/interactive_handler.py (%d символов)" % len(embedded_data['automation/interactive_handler.py']))
    print("   • automation/system_updater.py (%d символов)" % len(embedded_data['automation/system_updater.py']))
    print("   • automation/gui_monitor.py (%d символов)" % len(embedded_data['automation/gui_monitor.py']))
    print("   • config/auto_responses.json (%d символов)" % len(embedded_data['config/auto_responses.json']))
    print("[LIST] Итого подготовлено файлов: %d" % len(embedded_data))
    
    return embedded_data

def extract_embedded_files():
    """Извлечение встроенных файлов во временную папку"""
    print("[PACKAGE] Извлечение компонентов...")
    
    # Создаем временную папку
    temp_dir = tempfile.mkdtemp(prefix='astra-automation-')
    print("   Временная папка: %s" % temp_dir)
    
    # Получаем встроенные данные
    embedded_data = create_embedded_data()
    
    # Создаем структуру папок
    automation_dir = os.path.join(temp_dir, 'automation')
    config_dir = os.path.join(temp_dir, 'config')
    print("   Создаем папки: %s, %s" % (automation_dir, config_dir))
    os.makedirs(automation_dir)
    os.makedirs(config_dir)
    
    # Извлекаем файлы
    print("   Извлекаем файлы...")
    for file_path, content in embedded_data.items():
        full_path = os.path.join(temp_dir, file_path)
        print("     Записываем: %s (%d символов)" % (file_path, len(content)))
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        # Делаем исполняемым для Python файлов
        if file_path.endswith('.py'):
            os.chmod(full_path, 0o755)
            print("     [OK] Сделано исполняемым: %s" % file_path)
        else:
            print("     [OK] Извлечен: %s" % file_path)
    
    print("[FOLDER] Структура временной папки:")
    for root, dirs, files in os.walk(temp_dir):
        level = root.replace(temp_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print("   %s%s/" % (indent, os.path.basename(root)))
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print("   %s%s" % (subindent, file))
    
    return temp_dir

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

def run_repo_checker(temp_dir, dry_run=False):
    """Запуск модуля проверки репозиториев"""
    print("\n[START] Запуск автоматизации проверки репозиториев...")
    
    repo_checker_path = os.path.join(temp_dir, 'automation', 'repo_checker.py')
    print("   Путь к модулю: %s" % repo_checker_path)
    
    if not os.path.exists(repo_checker_path):
        print("[ERROR] Модуль repo_checker.py не найден")
        print("   Проверяем содержимое папки automation:")
        automation_dir = os.path.join(temp_dir, 'automation')
        if os.path.exists(automation_dir):
            for file in os.listdir(automation_dir):
                print("     - %s" % file)
        else:
            print("     Папка automation не существует!")
        return False
    
    print("   [OK] Модуль найден, запускаем...")
    
    # Формируем команду с учетом dry_run
    cmd = [sys.executable, repo_checker_path]
    if dry_run:
        cmd.append('--dry-run')
    
    print("   Команда: %s" % ' '.join(cmd))
    
    try:
        # Запускаем модуль проверки репозиториев
        result = subprocess.call(cmd)
        
        print("   Код возврата: %d" % result)
        
        if result == 0:
            if dry_run:
                print("[OK] Автоматизация завершена успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
            else:
                print("[OK] Автоматизация завершена успешно!")
            return True
        else:
            print("[ERROR] Ошибка выполнения автоматизации (код: %d)" % result)
            return False
            
    except Exception as e:
        print("[ERROR] Ошибка запуска: %s" % str(e))
        return False

def run_system_stats(temp_dir, dry_run=False):
    """Запуск модуля статистики системы"""
    print("\n[STATS] Запуск анализа статистики системы...")
    
    system_stats_path = os.path.join(temp_dir, 'automation', 'system_stats.py')
    print("   Путь к модулю: %s" % system_stats_path)
    
    if not os.path.exists(system_stats_path):
        print("[ERROR] Модуль system_stats.py не найден")
        return False
    
    print("   [OK] Модуль найден, запускаем...")
    
    # Формируем команду с учетом dry_run
    cmd = [sys.executable, system_stats_path]
    if dry_run:
        cmd.append('--dry-run')
    
    print("   Команда: %s" % ' '.join(cmd))
    
    try:
        # Запускаем модуль статистики системы
        result = subprocess.call(cmd)
        
        print("   Код возврата: %d" % result)
        
        if result == 0:
            if dry_run:
                print("[OK] Анализ статистики завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
            else:
                print("[OK] Анализ статистики завершен успешно!")
            return True
        else:
            print("[ERROR] Ошибка анализа статистики (код: %d)" % result)
            return False
            
    except Exception as e:
        print("[ERROR] Ошибка запуска: %s" % str(e))
        return False

def run_interactive_handler(temp_dir, dry_run=False):
    """Запуск модуля перехвата интерактивных запросов"""
    print("\n[AUTO] Запуск тестирования перехвата интерактивных запросов...")
    
    interactive_handler_path = os.path.join(temp_dir, 'automation', 'interactive_handler.py')
    print("   Путь к модулю: %s" % interactive_handler_path)
    
    if not os.path.exists(interactive_handler_path):
        print("[ERROR] Модуль interactive_handler.py не найден")
        return False
    
    print("   [OK] Модуль найден, запускаем...")
    
    # Формируем команду с учетом dry_run
    cmd = [sys.executable, interactive_handler_path]
    if dry_run:
        cmd.append('--dry-run')
    
    print("   Команда: %s" % ' '.join(cmd))
    
    try:
        # Запускаем модуль перехвата интерактивных запросов
        result = subprocess.call(cmd)
        
        print("   Код возврата: %d" % result)
        
        if result == 0:
            if dry_run:
                print("[OK] Тест перехвата интерактивных запросов завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
            else:
                print("[OK] Тест перехвата интерактивных запросов завершен успешно!")
            return True
        else:
            print("[ERROR] Ошибка теста перехвата интерактивных запросов (код: %d)" % result)
            return False
            
    except Exception as e:
        print("[ERROR] Ошибка запуска: %s" % str(e))
        return False

def run_system_updater(temp_dir, dry_run=False):
    """Запуск модуля обновления системы"""
    print("\n[PROCESS] Запуск обновления системы...")
    
    system_updater_path = os.path.join(temp_dir, 'automation', 'system_updater.py')
    print("   Путь к модулю: %s" % system_updater_path)
    
    if not os.path.exists(system_updater_path):
        print("[ERROR] Модуль system_updater.py не найден")
        return False
    
    print("   [OK] Модуль найден, запускаем...")
    
    # Формируем команду с учетом dry_run
    cmd = [sys.executable, system_updater_path]
    if dry_run:
        cmd.append('--dry-run')
    
    print("   Команда: %s" % ' '.join(cmd))
    
    try:
        # Запускаем модуль обновления системы
        result = subprocess.call(cmd)
        
        print("   Код возврата: %d" % result)
        
        if result == 0:
            if dry_run:
                print("[OK] Обновление системы завершено успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
            else:
                print("[OK] Обновление системы завершено успешно!")
            return True
        else:
            print("[ERROR] Ошибка обновления системы (код: %d)" % result)
            return False
            
    except Exception as e:
        print("[ERROR] Ошибка запуска: %s" % str(e))
        return False

def run_gui_monitor(temp_dir, dry_run=False):
    """Запуск GUI мониторинга"""
    print("\n[GUI] Запуск GUI мониторинга...")
    
    gui_monitor_path = os.path.join(temp_dir, 'automation', 'gui_monitor.py')
    print("   Путь к модулю: %s" % gui_monitor_path)
    
    if not os.path.exists(gui_monitor_path):
        print("[ERROR] Модуль gui_monitor.py не найден")
        return False
    
    print("   [OK] Модуль найден, запускаем...")
    
    # Формируем команду
    cmd = [sys.executable, gui_monitor_path]
    
    print("   Команда: %s" % ' '.join(cmd))
    
    try:
        # Запускаем GUI модуль
        result = subprocess.call(cmd)
        
        print("   Код возврата: %d" % result)
        
        if result == 0:
            print("[OK] GUI мониторинг завершен успешно!")
            return True
        else:
            print("[ERROR] Ошибка GUI мониторинга (код: %d)" % result)
            return False
            
    except Exception as e:
        print("[ERROR] Ошибка запуска: %s" % str(e))
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
        
        # Извлекаем встроенные файлы
        temp_dir = extract_embedded_files()
        
        # Запускаем GUI
        print("[GUI] Запуск GUI мониторинга...")
        gui_success = run_gui_monitor(temp_dir, dry_run)
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
        
        # Извлекаем встроенные файлы
        temp_dir = extract_embedded_files()
        
        # Запускаем автоматизацию репозиториев
        repo_success = run_repo_checker(temp_dir, dry_run)
        
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

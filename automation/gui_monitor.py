#!/usr/bin/env python
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
import Tkinter as tk
from Tkinter import ttk, scrolledtext

class AutomationGUI(object):
    """GUI для мониторинга автоматизации установки Astra.IDE"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FSA-AstraInstall Automation")
        self.root.geometry("800x600")
        
        # Переменные состояния
        self.is_running = False
        self.dry_run = tk.BooleanVar()
        self.process_thread = None
        
        # Создаем интерфейс
        self.create_widgets()
        
    def create_widgets(self):
        """Создание элементов интерфейса"""
        
        # Заголовок
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        title_label = ttk.Label(title_frame, text="FSA-AstraInstall Automation", 
                               font=("Arial", 16, "bold"))
        title_label.pack()
        
        subtitle_label = ttk.Label(title_frame, text="Автоматизация установки Astra.IDE")
        subtitle_label.pack()
        
        # Панель управления
        control_frame = ttk.LabelFrame(self.root, text="Управление")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Чекбокс для dry-run
        dry_run_check = ttk.Checkbutton(control_frame, text="Режим тестирования (dry-run)", 
                                       variable=self.dry_run)
        dry_run_check.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Кнопки управления
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.RIGHT, padx=5, pady=5)
        
        self.start_button = ttk.Button(button_frame, text="Запустить", 
                                      command=self.start_automation)
        self.start_button.pack(side=tk.LEFT, padx=2)
        
        self.stop_button = ttk.Button(button_frame, text="Остановить", 
                                     command=self.stop_automation, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=2)
        
        # Прогресс бар
        progress_frame = ttk.LabelFrame(self.root, text="Прогресс")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=5, pady=5)
        
        # Статус
        status_frame = ttk.LabelFrame(self.root, text="Статус")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Готов к запуску")
        self.status_label.pack(padx=5, pady=5)
        
        # Лог
        log_frame = ttk.LabelFrame(self.root, text="Лог выполнения")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Статистика
        stats_frame = ttk.LabelFrame(self.root, text="Статистика")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        stats_inner = ttk.Frame(stats_frame)
        stats_inner.pack(fill=tk.X, padx=5, pady=5)
        
        # Колонки статистики
        ttk.Label(stats_inner, text="Репозитории:").grid(row=0, column=0, sticky=tk.W)
        self.repo_label = ttk.Label(stats_inner, text="Не проверены")
        self.repo_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(stats_inner, text="Обновления:").grid(row=0, column=2, sticky=tk.W)
        self.update_label = ttk.Label(stats_inner, text="Не проверены")
        self.update_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(stats_inner, text="Пакеты:").grid(row=1, column=0, sticky=tk.W)
        self.package_label = ttk.Label(stats_inner, text="Не проверены")
        self.package_label.grid(row=1, column=1, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(stats_inner, text="Статус:").grid(row=1, column=2, sticky=tk.W)
        self.status_detail_label = ttk.Label(stats_inner, text="Ожидание")
        self.status_detail_label.grid(row=1, column=3, sticky=tk.W, padx=(5, 20))
        
    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.log_text.insert(tk.END, message + "\n")
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
        self.progress.start()
        
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
        self.progress.stop()
        self.update_status("Остановлено пользователем")
        
    def run_automation(self):
        """Запуск автоматизации в отдельном потоке"""
        try:
            self.update_status("Запуск автоматизации...")
            self.log_message("=" * 60)
            self.log_message("FSA-AstraInstall Automation")
            self.log_message("Автоматизация установки Astra.IDE")
            self.log_message("=" * 60)
            
            # Формируем команду
            cmd = ['python', 'astra-automation.py']
            if self.dry_run.get():
                cmd.append('--dry-run')
                self.log_message("Режим: ТЕСТИРОВАНИЕ (dry-run)")
            else:
                self.log_message("Режим: РЕАЛЬНАЯ УСТАНОВКА")
            
            self.log_message("Команда: %s" % ' '.join(cmd))
            self.log_message("")
            
            # Запускаем процесс
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Читаем вывод построчно
            while self.is_running:
                line = process.stdout.readline()
                if not line:
                    break
                    
                # Выводим строку в лог
                self.log_message(line.rstrip())
                
                # Парсим статус из вывода
                self.parse_status_from_output(line)
                
                # Обновляем интерфейс
                self.root.update_idletasks()
            
            # Ждем завершения процесса
            return_code = process.wait()
            
            if return_code == 0:
                self.update_status("Автоматизация завершена успешно!")
                self.log_message("")
                self.log_message("🎉 Автоматизация завершена успешно!")
            else:
                self.update_status("Автоматизация завершена с ошибками")
                self.log_message("")
                self.log_message("💥 Автоматизация завершена с ошибками")
                
        except Exception as e:
            self.update_status("Ошибка выполнения")
            self.log_message("❌ Ошибка: %s" % str(e))
            
        finally:
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress.stop()
            
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

def install_gui_dependencies():
    """Установка зависимостей для GUI"""
    print("📦 Проверка зависимостей для GUI...")
    
    try:
        # Проверяем наличие tkinter
        import Tkinter as tk
        print("✅ tkinter уже установлен")
        return True
    except ImportError:
        print("⚠️ tkinter не найден, устанавливаем python-tk...")
        
        try:
            # Устанавливаем python-tk
            result = subprocess.call(['apt-get', 'install', '-y', 'python-tk'], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if result == 0:
                print("✅ python-tk успешно установлен")
                return True
            else:
                print("❌ Не удалось установить python-tk")
                return False
                
        except Exception as e:
            print("❌ Ошибка установки python-tk: %s" % str(e))
            return False

def main():
    """Основная функция"""
    print("Запуск GUI мониторинга автоматизации...")
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("❌ Требуются права root для работы с системными файлами")
        print("Запустите: sudo python gui_monitor.py")
        sys.exit(1)
    
    # Проверяем наличие astra-automation.py
    if not os.path.exists('astra-automation.py'):
        print("❌ Файл astra-automation.py не найден")
        print("Запустите из папки с файлом astra-automation.py")
        sys.exit(1)
    
    # Устанавливаем зависимости для GUI
    if not install_gui_dependencies():
        print("❌ Не удалось установить зависимости для GUI")
        print("Попробуйте запустить: sudo apt-get install python-tk")
        sys.exit(1)
    
    # Запускаем GUI
    app = AutomationGUI()
    app.run()

if __name__ == '__main__':
    main()

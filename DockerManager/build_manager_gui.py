#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI приложение для управления Docker сборками
Версия: V2.7.143 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import subprocess
import os
import sys
import json
from pathlib import Path
from datetime import datetime

from .config import (
    REMOTE_SERVER, BUILD_PLATFORMS, PROJECTS, GUI_CONFIG,
    get_project_dir, get_dockmanager_dir
)
from .server_connection import test_connection, print_step, print_success, print_error
from .docker_manager import get_remote_images, check_remote_image_exists, remove_remote_image
from .file_manager import list_builds, download_build, check_unified_file
from .build_runner import build
from .logger import get_logger, setup_logger, get_log_file
import logging

class BuildManagerGUI:
    """GUI приложение для управления сборками"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(GUI_CONFIG["window_title"])
        self.root.geometry(GUI_CONFIG["window_size"])
        
        # Состояние
        self.current_project = "FSA-AstraInstall"
        self.current_platform = None
        self.build_process = None
        self.log_buffer = []
        
        # Файл настроек
        self.settings_file = get_dockmanager_dir() / ".build_manager_settings.json"
        
        # Лог файл
        self.log_file = None
        self.log_handler = None
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Настраиваем логирование для GUI (после создания виджетов)
        self.setup_gui_logging()
        
        # Загружаем настройки
        self.load_settings()
        
        # Загружаем начальные данные
        self.refresh_server_status()
        self.refresh_images()
        self.refresh_builds()
    
    def create_widgets(self):
        """Создание виджетов интерфейса"""
        # Создаем Notebook для вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладка 1: Настройки сервера
        self.create_settings_tab()
        
        # Вкладка 2: Docker образы
        self.create_images_tab()
        
        # Вкладка 3: Исходники
        self.create_sources_tab()
        
        # Вкладка 4: Сборка
        self.create_build_tab()
        
        # Вкладка 5: Результаты
        self.create_results_tab()
        
        # Вкладка 6: Лог сборки
        self.create_log_tab()
        
        # Вкладка 7: Лог работы
        self.create_work_log_tab()
    
    def create_settings_tab(self):
        """Вкладка настроек сервера"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Настройки сервера")
        
        # Поля ввода
        ttk.Label(frame, text="Сервер:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.server_host = tk.StringVar(value=f"{REMOTE_SERVER['user']}@{REMOTE_SERVER['host']}")
        ttk.Entry(frame, textvariable=self.server_host, width=40).grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(frame, text="Базовый путь:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.server_path = tk.StringVar(value=REMOTE_SERVER['base_path'])
        ttk.Entry(frame, textvariable=self.server_path, width=40).grid(row=1, column=1, padx=10, pady=5)
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Тест подключения", command=self.test_server_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Сохранить настройки", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        
        # Статус
        self.server_status = tk.StringVar(value="Не проверено")
        ttk.Label(frame, textvariable=self.server_status).grid(row=3, column=0, columnspan=2, pady=5)
    
    def create_images_tab(self):
        """Вкладка Docker образов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Docker образы")
        
        # Список образов
        ttk.Label(frame, text="Образы на сервере:").pack(anchor=tk.W, padx=10, pady=5)
        
        # Treeview для списка образов
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.images_tree = ttk.Treeview(tree_frame, columns=("size", "date"), show="tree headings", height=10)
        self.images_tree.heading("#0", text="Образ")
        self.images_tree.heading("size", text="Размер")
        self.images_tree.heading("date", text="Дата")
        self.images_tree.column("#0", width=300)
        self.images_tree.column("size", width=100)
        self.images_tree.column("date", width=150)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.images_tree.yview)
        self.images_tree.configure(yscrollcommand=scrollbar.set)
        
        self.images_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Обновить", command=self.refresh_images).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_image).pack(side=tk.LEFT, padx=5)
    
    def create_sources_tab(self):
        """Вкладка исходников"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Исходники")
        
        # Информация
        info_frame = ttk.LabelFrame(frame, text="Информация")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.sources_info = tk.StringVar(value="Проверка наличия объединенного файла...")
        ttk.Label(info_frame, textvariable=self.sources_info).pack(padx=10, pady=5)
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Проверить файл", command=self.check_unified_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Создать объединенный файл", command=self.generate_unified).pack(side=tk.LEFT, padx=5)
    
    def create_build_tab(self):
        """Вкладка сборки"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Сборка")
        
        # Выбор проекта
        ttk.Label(frame, text="Проект:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.build_project = tk.StringVar(value=self.current_project)
        project_combo = ttk.Combobox(frame, textvariable=self.build_project, 
                                    values=list(PROJECTS.keys()), state="readonly", width=30)
        project_combo.grid(row=0, column=1, padx=10, pady=5)
        project_combo.bind("<<ComboboxSelected>>", lambda e: setattr(self, 'current_project', self.build_project.get()))
        
        # Выбор платформы
        ttk.Label(frame, text="Платформа:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.build_platform = tk.StringVar()
        platform_combo = ttk.Combobox(frame, textvariable=self.build_platform,
                                      values=list(BUILD_PLATFORMS.keys()), state="readonly", width=30)
        platform_combo.grid(row=1, column=1, padx=10, pady=5)
        
        # Режим сборки
        self.build_remote = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Удаленная сборка (на сервере)", 
                        variable=self.build_remote).grid(row=2, column=0, columnspan=2, padx=10, pady=5)
        
        # Кнопка запуска
        ttk.Button(frame, text="Запустить сборку", command=self.start_build).grid(
            row=3, column=0, columnspan=2, pady=10
        )
        
        # Прогресс
        self.build_progress = ttk.Progressbar(frame, mode='indeterminate')
        self.build_progress.grid(row=4, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=5)
        
        # Статус
        self.build_status = tk.StringVar(value="Готов к сборке")
        ttk.Label(frame, textvariable=self.build_status).grid(row=5, column=0, columnspan=2, pady=5)
    
    def create_results_tab(self):
        """Вкладка результатов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Результаты")
        
        # Фильтры
        filter_frame = ttk.LabelFrame(frame, text="Фильтры")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="Проект:").grid(row=0, column=0, padx=5, pady=5)
        self.results_project = tk.StringVar(value=self.current_project)
        ttk.Combobox(filter_frame, textvariable=self.results_project,
                    values=list(PROJECTS.keys()), state="readonly", width=20).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Платформа:").grid(row=0, column=2, padx=5, pady=5)
        self.results_platform = tk.StringVar(value="Все")
        platform_values = ["Все"] + list(BUILD_PLATFORMS.keys())
        ttk.Combobox(filter_frame, textvariable=self.results_platform,
                    values=platform_values, state="readonly", width=20).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Button(filter_frame, text="Обновить", command=self.refresh_builds).grid(row=0, column=4, padx=5, pady=5)
        
        # Список результатов
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.results_tree = ttk.Treeview(results_frame, columns=("size", "date"), show="tree headings", height=15)
        self.results_tree.heading("#0", text="Файл")
        self.results_tree.heading("size", text="Размер")
        self.results_tree.heading("date", text="Дата")
        self.results_tree.column("#0", width=400)
        self.results_tree.column("size", width=100)
        self.results_tree.column("date", width=150)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Скачать", command=self.download_result).pack(side=tk.LEFT, padx=5)
    
    def create_log_tab(self):
        """Вкладка лога сборки"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Лог сборки")
        
        # Текстовое поле для лога
        self.log_text = scrolledtext.ScrolledText(frame, height=30, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Очистить", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Сохранить лог", command=self.save_log).pack(side=tk.LEFT, padx=5)
    
    # ============================================================================
    # МЕТОДЫ РАБОТЫ С СЕРВЕРОМ
    # ============================================================================
    
    def load_settings(self):
        """Загружает настройки из файла"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                # Обновляем значения в полях
                if 'server_host' in settings:
                    self.server_host.set(settings['server_host'])
                if 'server_path' in settings:
                    self.server_path.set(settings['server_path'])
                
                # Обновляем REMOTE_SERVER в config
                if 'server_host' in settings:
                    host_user = settings['server_host'].split('@')
                    if len(host_user) == 2:
                        REMOTE_SERVER['user'] = host_user[0]
                        REMOTE_SERVER['host'] = host_user[1]
                if 'server_path' in settings:
                    REMOTE_SERVER['base_path'] = settings['server_path']
                
                self.log("[OK] Настройки загружены из файла")
        except Exception as e:
            self.log(f"[WARNING] Не удалось загрузить настройки: {e}")
    
    def save_settings(self):
        """Сохраняет настройки в файл"""
        try:
            settings = {
                'server_host': self.server_host.get(),
                'server_path': self.server_path.get()
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            # Обновляем REMOTE_SERVER
            host_user = settings['server_host'].split('@')
            if len(host_user) == 2:
                REMOTE_SERVER['user'] = host_user[0]
                REMOTE_SERVER['host'] = host_user[1]
            REMOTE_SERVER['base_path'] = settings['server_path']
            
            self.log("[OK] Настройки сохранены")
            messagebox.showinfo("Успех", "Настройки сохранены")
        except Exception as e:
            self.log(f"[ERROR] Ошибка сохранения настроек: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}")
    
    def test_server_connection(self):
        """Тестирует подключение к серверу"""
        # Сначала обновляем настройки из полей
        host_user = self.server_host.get().split('@')
        if len(host_user) == 2:
            REMOTE_SERVER['user'] = host_user[0]
            REMOTE_SERVER['host'] = host_user[1]
        REMOTE_SERVER['base_path'] = self.server_path.get()
        
        self.server_status.set("Проверка...")
        self.root.update()
        
        def test():
            try:
                if test_connection():
                    self.server_status.set("✅ Подключено")
                    self.log("[OK] Подключение к серверу установлено")
                else:
                    self.server_status.set("❌ Не подключено")
                    self.log("[ERROR] Не удалось подключиться к серверу")
            except Exception as e:
                self.server_status.set(f"❌ Ошибка: {e}")
                self.log(f"[ERROR] Ошибка подключения: {e}")
            finally:
                self.root.after(0, lambda: self.root.update())
        
        threading.Thread(target=test, daemon=True).start()
    
    def refresh_server_status(self):
        """Обновляет статус сервера"""
        self.test_server_connection()
    
    # ============================================================================
    # МЕТОДЫ РАБОТЫ С ОБРАЗАМИ
    # ============================================================================
    
    def refresh_images(self):
        """Обновляет список образов"""
        # Очищаем дерево
        for item in self.images_tree.get_children():
            self.images_tree.delete(item)
        
        def load():
            try:
                images = get_remote_images()
                for image in images:
                    self.images_tree.insert("", tk.END, text=image, values=("", ""))
            except Exception as e:
                self.log(f"[ERROR] Ошибка загрузки образов: {e}")
        
        threading.Thread(target=load, daemon=True).start()
    
    def delete_image(self):
        """Удаляет выбранный образ"""
        selection = self.images_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите образ для удаления")
            return
        
        item = self.images_tree.item(selection[0])
        image_name = item['text']
        
        if messagebox.askyesno("Подтверждение", f"Удалить образ {image_name}?"):
            def delete():
                try:
                    if remove_remote_image(image_name):
                        self.log(f"[OK] Образ {image_name} удален")
                        self.refresh_images()
                    else:
                        self.log(f"[ERROR] Не удалось удалить образ {image_name}")
                except Exception as e:
                    self.log(f"[ERROR] Ошибка удаления: {e}")
            
            threading.Thread(target=delete, daemon=True).start()
    
    # ============================================================================
    # МЕТОДЫ РАБОТЫ С ИСХОДНИКАМИ
    # ============================================================================
    
    def check_unified_file(self):
        """Проверяет наличие объединенного файла"""
        if check_unified_file(self.current_project):
            self.sources_info.set("✅ Объединенный файл найден")
        else:
            self.sources_info.set("❌ Объединенный файл не найден")
    
    def generate_unified(self):
        """Генерирует объединенный файл"""
        self.log("[#] Генерация объединенного файла...")
        
        def generate():
            try:
                project_dir = get_project_dir()
                generate_script = project_dir / "Build" / "generate_unified.py"
                
                if not generate_script.exists():
                    self.log("[ERROR] Скрипт generate_unified.py не найден")
                    return
                
                result = subprocess.run(
                    [sys.executable, str(generate_script)],
                    capture_output=True,
                    text=True,
                    cwd=str(project_dir)
                )
                
                if result.returncode == 0:
                    self.log("[OK] Объединенный файл создан")
                    self.check_unified_file()
                else:
                    self.log(f"[ERROR] Ошибка: {result.stderr}")
            except Exception as e:
                self.log(f"[ERROR] Ошибка генерации: {e}")
        
        threading.Thread(target=generate, daemon=True).start()
    
    # ============================================================================
    # МЕТОДЫ РАБОТЫ СО СБОРКОЙ
    # ============================================================================
    
    def start_build(self):
        """Запускает сборку"""
        project = self.build_project.get()
        platform = self.build_platform.get()
        remote = self.build_remote.get()
        
        if not platform:
            messagebox.showwarning("Предупреждение", "Выберите платформу для сборки")
            return
        
        if not check_unified_file(project):
            if not messagebox.askyesno("Вопрос", 
                "Объединенный файл не найден. Создать его сейчас?"):
                return
            self.generate_unified()
            # Ждем немного
            import time
            time.sleep(2)
        
        self.build_status.set("Сборка запущена...")
        self.build_progress.start()
        self.log(f"[#] Запуск сборки: {project} для {platform} ({'удаленно' if remote else 'локально'})")
        
        def run_build():
            try:
                success = build(project, platform, remote=remote)
                if success:
                    self.log("[OK] Сборка завершена успешно")
                    self.build_status.set("✅ Сборка завершена успешно")
                    self.refresh_builds()
                else:
                    self.log("[ERROR] Сборка завершена с ошибками")
                    self.build_status.set("❌ Сборка завершена с ошибками")
            except Exception as e:
                self.log(f"[ERROR] Ошибка сборки: {e}")
                self.build_status.set(f"❌ Ошибка: {e}")
            finally:
                self.root.after(0, self.build_progress.stop)
        
        threading.Thread(target=run_build, daemon=True).start()
    
    # ============================================================================
    # МЕТОДЫ РАБОТЫ С РЕЗУЛЬТАТАМИ
    # ============================================================================
    
    def refresh_builds(self):
        """Обновляет список результатов"""
        # Очищаем дерево
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # TODO: Реализовать получение списка результатов с сервера
        self.log("[i] Обновление списка результатов...")
    
    def download_result(self):
        """Скачивает выбранный результат"""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите результат для скачивания")
            return
        
        # TODO: Реализовать скачивание
        self.log("[i] Скачивание результата...")
    
    # ============================================================================
    # МЕТОДЫ РАБОТЫ С ЛОГОМ
    # ============================================================================
    
    def log(self, message):
        """Добавляет сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # Ограничиваем размер лога
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > GUI_CONFIG["log_lines"]:
            self.log_text.delete("1.0", f"{len(lines) - GUI_CONFIG['log_lines']}.0")
    
    def clear_log(self):
        """Очищает лог"""
        self.log_text.delete("1.0", tk.END)
    
    def save_log(self):
        """Сохраняет лог в файл"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get("1.0", tk.END))
                self.log(f"[OK] Лог сохранен: {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить лог: {e}")
    
    def create_work_log_tab(self):
        """Вкладка лога работы (все операции)"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Лог работы")
        
        # Информация о лог файле
        info_frame = ttk.LabelFrame(frame, text="Информация")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.work_log_info = tk.StringVar(value="Лог файл не создан")
        ttk.Label(info_frame, textvariable=self.work_log_info).pack(padx=10, pady=5)
        
        # Текстовое поле для лога работы
        self.work_log_text = scrolledtext.ScrolledText(frame, height=30, wrap=tk.WORD, font=('Courier', 12))
        self.work_log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Обновить", command=self.refresh_work_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=self.clear_work_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Открыть лог файл", command=self.open_log_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Автообновление", command=self.toggle_auto_refresh).pack(side=tk.LEFT, padx=5)
        
        # Статус автообновления
        self.auto_refresh_enabled = False
        self.auto_refresh_label = tk.StringVar(value="Автообновление: выключено")
        ttk.Label(btn_frame, textvariable=self.auto_refresh_label).pack(side=tk.LEFT, padx=10)
    
    def setup_gui_logging(self):
        """Настраивает логирование с выводом в GUI"""
        try:
            # Инициализируем логгер один раз (если еще не инициализирован)
            logger, log_file = setup_logger("DockerManager", force_new=False)
            self.log_file = log_file
            
            # Если файл еще не установлен - получаем из глобальной переменной
            if self.log_file is None:
                self.log_file = get_log_file()
            
            # Обновляем информацию о лог файле
            if hasattr(self, 'work_log_info'):
                self.work_log_info.set(f"Лог файл: {log_file.name}")
            
            # Создаем кастомный handler для GUI
            class GUIHandler(logging.Handler):
                def __init__(self, text_widget, root):
                    super().__init__()
                    self.text_widget = text_widget
                    self.root = root
                    self.setFormatter(logging.Formatter(
                        '%(asctime)s [%(levelname)-8s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S'
                    ))
                
                def emit(self, record):
                    try:
                        msg = self.format(record) + '\n'
                        # Используем root.after для thread-safe обновления GUI
                        def update_gui():
                            try:
                                self.text_widget.insert(tk.END, msg)
                                self.text_widget.see(tk.END)
                                
                                # Ограничиваем размер (последние 10000 строк)
                                lines = self.text_widget.get("1.0", tk.END).split('\n')
                                if len(lines) > 10000:
                                    self.text_widget.delete("1.0", f"{len(lines) - 10000}.0")
                            except:
                                pass
                        
                        # Вызываем обновление GUI в главном потоке
                        self.root.after(0, update_gui)
                    except:
                        pass
            
            # Добавляем handler к корневому логгеру
            if hasattr(self, 'work_log_text'):
                self.log_handler = GUIHandler(self.work_log_text, self.root)
                self.log_handler.setLevel(logging.DEBUG)
                logger.addHandler(self.log_handler)
                
                # Также добавляем ко всем дочерним логгерам
                for name in ['DockerManager.ServerConnection', 'DockerManager.BuildRunner', 
                            'DockerManager.DockerManager', 'DockerManager.FileManager']:
                    child_logger = logging.getLogger(name)
                    child_logger.addHandler(self.log_handler)
            
            self.log(f"[OK] Логирование настроено: {log_file.name}")
        except Exception as e:
            print(f"[ERROR] Ошибка настройки логирования: {e}")
    
    def refresh_work_log(self):
        """Обновляет лог работы из файла"""
        if not self.log_file or not self.log_file.exists():
            self.work_log_text.delete("1.0", tk.END)
            self.work_log_text.insert(tk.END, "Лог файл не найден\n")
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.work_log_text.delete("1.0", tk.END)
            self.work_log_text.insert("1.0", content)
            self.work_log_text.see(tk.END)
            
            # Обновляем информацию
            size = self.log_file.stat().st_size / 1024  # KB
            self.work_log_info.set(f"Лог файл: {self.log_file.name} ({size:.1f} KB)")
        except Exception as e:
            self.work_log_text.insert(tk.END, f"Ошибка чтения лог файла: {e}\n")
    
    def clear_work_log(self):
        """Очищает лог работы в GUI (не удаляет файл)"""
        self.work_log_text.delete("1.0", tk.END)
    
    def open_log_file(self):
        """Открывает лог файл в системном редакторе"""
        if not self.log_file or not self.log_file.exists():
            messagebox.showwarning("Предупреждение", "Лог файл не найден")
            return
        
        import subprocess
        import platform as plat
        
        try:
            if plat.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(self.log_file)])
            elif plat.system() == 'Windows':
                subprocess.run(['notepad', str(self.log_file)])
            else:  # Linux
                subprocess.run(['xdg-open', str(self.log_file)])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
    
    def toggle_auto_refresh(self):
        """Включает/выключает автообновление лога"""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        
        if self.auto_refresh_enabled:
            self.auto_refresh_label.set("Автообновление: включено")
            self.start_auto_refresh()
        else:
            self.auto_refresh_label.set("Автообновление: выключено")
            self.stop_auto_refresh()
    
    def start_auto_refresh(self):
        """Запускает автообновление лога"""
        if self.auto_refresh_enabled:
            self.refresh_work_log()
            self.root.after(2000, self.start_auto_refresh)  # Обновление каждые 2 секунды
    
    def stop_auto_refresh(self):
        """Останавливает автообновление лога"""
        self.auto_refresh_enabled = False
    
    def run(self):
        """Запускает GUI"""
        # Обновляем информацию о лог файле после создания виджетов
        if self.log_file:
            self.work_log_info.set(f"Лог файл: {self.log_file.name}")
            # Загружаем начальный лог
            self.root.after(500, self.refresh_work_log)
        
        self.root.mainloop()


def main():
    """Главная функция"""
    app = BuildManagerGUI()
    app.run()


if __name__ == "__main__":
    main()


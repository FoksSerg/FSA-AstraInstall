#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI для CommitManager - Универсальный инструмент создания коммитов
Версия: V3.4.186 (2025.12.17)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from typing import Optional, Callable, Dict
from .config_manager import ConfigManager
from .project_config import ProjectConfig
from .commit_executor import CommitExecutor
from .commit_analyzer import CommitAnalyzer
from .test_environment import TestEnvironment
from .logger import CommitLogger, LoggingOutputCallback


class CommitManagerGUI:
    """Главный класс GUI для управления созданием коммитов"""
    
    def __init__(self):
        """Инициализация GUI"""
        self.root = tk.Tk()
        self.root.title("Создание коммита - Универсальный инструмент")
        self.root.geometry("1400x900")
        
        # Настройка стилей для увеличения шрифтов
        self.setup_styles()
        
        # Менеджер конфигураций
        self.config_manager = ConfigManager()
        
        # Текущий проект
        self.current_project_name = self.config_manager.get_current_project()
        self.current_project_config: Optional[ProjectConfig] = None
        
        # Исполнитель и анализатор
        self.executor: Optional[CommitExecutor] = None
        self.analyzer: Optional[CommitAnalyzer] = None
        self.test_env: Optional[TestEnvironment] = None
        self.logger: Optional[CommitLogger] = None
        
        # Состояние процесса
        self.process_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.is_paused = False
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Загружаем проект
        self.load_project()
        
        # Загружаем сохраненную геометрию
        self.load_window_geometry()
        
        # Если геометрия не загружена, центрируем окно
        if not self.config_manager.get_window_geometry():
            self.center_window()
        
        # Открываем окно поверх других
        self.show_window_on_top()
        
        # Привязываем обработчик закрытия окна для сохранения геометрии
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Привязываем обработчик изменения размера окна
        self.root.bind('<Configure>', self.on_window_configure)
    
    def setup_styles(self):
        """Настройка стилей для увеличения шрифтов"""
        style = ttk.Style()
        
        # Увеличиваем шрифты для кнопок
        style.configure('TButton', font=('Arial', 11))
        
        # Увеличиваем шрифты для чекбоксов
        style.configure('TCheckbutton', font=('Arial', 11))
        
        # Увеличиваем шрифты для LabelFrame
        style.configure('TLabelframe.Label', font=('Arial', 12, 'bold'))
        
        # Увеличиваем шрифты для вкладок
        style.configure('TNotebook.Tab', font=('Arial', 13))
    
    def create_widgets(self):
        """Создание виджетов интерфейса"""
        # Создаем Notebook для вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладка 1: Процесс
        self.create_process_tab()
        
        # Вкладка 2: Настройки проекта
        self.create_project_settings_tab()
        
        # Вкладка 3: Ключевые файлы
        self.create_key_files_tab()
        
        # Вкладка 4: История
        self.create_history_tab()
        
        # Вкладка 5: AI Анализ
        self.create_ai_tab()
    
    def create_process_tab(self):
        """Создание вкладки процесса"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Процесс")
        
        # Основной контейнер с тремя панелями
        self.main_paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Левая панель: Список шагов
        left_frame = ttk.LabelFrame(self.main_paned, text="Шаги")
        self.main_paned.add(left_frame, weight=1)
        
        # Список шагов
        steps_frame = ttk.Frame(left_frame)
        steps_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar_steps = ttk.Scrollbar(steps_frame)
        scrollbar_steps.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.steps_listbox = tk.Listbox(
            steps_frame,
            yscrollcommand=scrollbar_steps.set,
            font=('Courier', 15)
        )
        self.steps_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_steps.config(command=self.steps_listbox.yview)
        
        # Инициализируем список шагов
        self.init_steps_list()
        
        # Центральная панель: Вывод процесса
        center_frame = ttk.LabelFrame(self.main_paned, text="Процесс и вывод")
        self.main_paned.add(center_frame, weight=3)
        
        self.output_text = scrolledtext.ScrolledText(
            center_frame,
            wrap=tk.WORD,
            font=('Courier', 12),
            bg='white',
            fg='black',
            insertbackground='black'
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Фрейм для управления (внизу)
        control_frame = ttk.Frame(center_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)
        
        # Первая строка: Переключатель тестового режима
        test_mode_frame = ttk.Frame(control_frame)
        test_mode_frame.pack(fill=tk.X, pady=2)
        
        self.test_mode_var = tk.BooleanVar(value=False)  # По умолчанию выключен
        test_mode_check = ttk.Checkbutton(
            test_mode_frame,
            text="🧪 Тестовый режим (dry-run)",
            variable=self.test_mode_var,
            state=tk.NORMAL
        )
        test_mode_check.pack(side=tk.LEFT)
        
        self.full_test_mode_var = tk.BooleanVar(value=True)  # По умолчанию включен
        full_test_mode_check = ttk.Checkbutton(
            test_mode_frame,
            text="🔬 Полный тестовый режим",
            variable=self.full_test_mode_var,
            state=tk.NORMAL,
            command=self.on_full_test_mode_toggle
        )
        full_test_mode_check.pack(side=tk.LEFT, padx=5)
        
        self.use_persistent_test_dir_var = tk.BooleanVar(value=True)  # По умолчанию включен
        persistent_dir_check = ttk.Checkbutton(
            test_mode_frame,
            text="📁 Использовать CommitTest/",
            variable=self.use_persistent_test_dir_var,
            state=tk.NORMAL
        )
        persistent_dir_check.pack(side=tk.LEFT, padx=5)
        
        # Информация о тестовом режиме
        self.test_info_label = ttk.Label(
            test_mode_frame,
            text="(команды выводятся, файлы не изменяются)",
            foreground='gray',
            font=('Arial', 10)
        )
        self.test_info_label.pack(side=tk.LEFT, padx=5)
        
        # Вторая строка: Кнопки управления
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill=tk.X, pady=2)
        
        self.start_btn = ttk.Button(buttons_frame, text="▶ Старт", command=self.start_process)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_btn = ttk.Button(buttons_frame, text="⏸ Пауза", command=self.pause_process, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        self.resume_btn = ttk.Button(buttons_frame, text="▶▶ Продолжить", command=self.resume_process, state=tk.DISABLED)
        self.resume_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(buttons_frame, text="⏹ Стоп", command=self.stop_process, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Правая панель: Информация
        right_frame = ttk.LabelFrame(self.main_paned, text="Информация")
        self.main_paned.add(right_frame, weight=1)
        
        # Информация о проекте
        info_text = ttk.Label(right_frame, text="Проект:", font=('Arial', 12, 'bold'))
        info_text.pack(anchor=tk.W, padx=5, pady=2)
        
        self.project_label = ttk.Label(right_frame, text="Не выбран", foreground='gray', font=('Arial', 11))
        self.project_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # Версия
        version_text = ttk.Label(right_frame, text="Версия:", font=('Arial', 12, 'bold'))
        version_text.pack(anchor=tk.W, padx=5, pady=2)
        
        self.version_label = ttk.Label(right_frame, text="—", foreground='gray', font=('Arial', 11))
        self.version_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # Файлы
        files_text = ttk.Label(right_frame, text="Файлы:", font=('Arial', 12, 'bold'))
        files_text.pack(anchor=tk.W, padx=5, pady=2)
        
        files_frame = ttk.Frame(right_frame)
        files_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        scrollbar_files = ttk.Scrollbar(files_frame)
        scrollbar_files.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.files_listbox = tk.Listbox(
            files_frame,
            yscrollcommand=scrollbar_files.set,
            height=5,
            font=('Courier', 11)
        )
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_files.config(command=self.files_listbox.yview)
        
        # Прогресс
        progress_text = ttk.Label(right_frame, text="Прогресс:", font=('Arial', 12, 'bold'))
        progress_text.pack(anchor=tk.W, padx=5, pady=2)
        
        self.progress_var = tk.StringVar(value="0%")
        self.progress_label = ttk.Label(right_frame, textvariable=self.progress_var, font=('Arial', 11))
        self.progress_label.pack(anchor=tk.W, padx=5, pady=2)
        
        self.progress_bar = ttk.Progressbar(right_frame, mode='determinate', maximum=21)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=2)
    
    def init_steps_list(self):
        """Инициализация списка шагов"""
        steps = [
            "0. Проверка директории",
            "1. Определение измененных файлов",
            "2. Проверка реальных изменений",
            "3. Определение текущей версии",
            "4. Определение новой версии",
            "5. Сбор данных для анализа",
            "6. Анализ изменений",
            "7. Сохранение описания",
            "8. Проверка файла сообщения",
            "8.5. Пауза для просмотра",
            "9. Обновление дат и версий",
            "10. Проверка обновления дат",
            "11. Обновление версий в ключевых файлах",
            "11.5. Пересборка бинарных файлов",
            "12. Проверка обновления версий",
            "13. Добавление файлов в индекс",
            "13.5. Пауза перед коммитом",
            "14. Создание коммита",
            "15. Верификация коммита",
            "16. Очистка",
            "17. Проверка необходимости истории",
            "18. Создание истории",
            "19. Валидация истории",
            "20. Финальный отчёт"
        ]
        
        for step in steps:
            self.steps_listbox.insert(tk.END, f"⏳ {step}")
    
    def create_project_settings_tab(self):
        """Создание вкладки настроек проекта"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Настройки проекта")
        
        # TODO: Реализовать интерфейс настроек проекта
        ttk.Label(frame, text="Настройки проекта (в разработке)", font=('Arial', 14)).pack(pady=20)
    
    def create_key_files_tab(self):
        """Создание вкладки ключевых файлов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Ключевые файлы")
        
        # TODO: Реализовать интерфейс управления ключевыми файлами
        ttk.Label(frame, text="Управление ключевыми файлами (в разработке)", font=('Arial', 14)).pack(pady=20)
    
    def create_history_tab(self):
        """Создание вкладки истории"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="История")
        
        # TODO: Реализовать интерфейс настроек истории
        ttk.Label(frame, text="Настройки истории (в разработке)", font=('Arial', 14)).pack(pady=20)
    
    def create_ai_tab(self):
        """Создание вкладки AI анализа"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="AI Анализ")
        
        # TODO: Реализовать интерфейс настроек AI
        ttk.Label(frame, text="Настройки AI анализа (в разработке)", font=('Arial', 14)).pack(pady=20)
    
    def load_project(self):
        """Загрузка текущего проекта"""
        if self.current_project_name:
            self.current_project_config = self.config_manager.get_project_config(self.current_project_name)
            if self.current_project_config:
                self.project_label.config(text=self.current_project_name)
            else:
                # Создаем конфигурацию по умолчанию
                self.current_project_config = self.config_manager.create_default_fsa_config()
                self.config_manager.set_project_config(self.current_project_name, self.current_project_config)
        else:
            # Создаем конфигурацию по умолчанию для FSA-AstraInstall
            self.current_project_config = self.config_manager.create_default_fsa_config()
            self.current_project_name = self.current_project_config.name
            self.config_manager.set_project_config(self.current_project_name, self.current_project_config)
            self.config_manager.set_current_project(self.current_project_name)
            self.project_label.config(text=self.current_project_name)
    
    def output(self, message: str):
        """Вывод сообщения в текстовую область"""
        self.output_text.insert(tk.END, message + '\n')
        self.output_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_step_status(self, step_num: int, status: str):
        """Обновление статуса шага"""
        # status: 'pending', 'running', 'success', 'error', 'paused'
        icons = {
            'pending': '⏳',
            'running': '🔄',
            'success': '✓',
            'error': '✗',
            'paused': '⏸'
        }
        
        icon = icons.get(status, '⏳')
        
        if step_num < self.steps_listbox.size():
            step_text = self.steps_listbox.get(step_num)
            # Удаляем старый иконку и добавляем новую
            step_text = step_text.split(' ', 1)[-1] if ' ' in step_text else step_text
            self.steps_listbox.delete(step_num)
            self.steps_listbox.insert(step_num, f"{icon} {step_text}")
            self.steps_listbox.selection_clear(0, tk.END)
            self.steps_listbox.selection_set(step_num)
            self.steps_listbox.see(step_num)
    
    def start_process(self):
        """Запуск процесса создания коммита"""
        if not self.current_project_config:
            self.root.lift()
            self.root.focus_force()
            messagebox.showerror("Ошибка", "Проект не выбран", parent=self.root)
            return
        
        # Валидация конфигурации
        is_valid, error = self.current_project_config.validate()
        if not is_valid:
            self.root.lift()
            self.root.focus_force()
            messagebox.showerror("Ошибка конфигурации", error, parent=self.root)
            return
        
        self.is_running = True
        self.is_paused = False
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.resume_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Очищаем вывод
        self.output_text.delete(1.0, tk.END)
        
        # Запускаем процесс в отдельном потоке
        self.process_thread = threading.Thread(target=self.run_process, daemon=True)
        self.process_thread.start()
    
    def pause_process(self):
        """Пауза процесса"""
        self.is_paused = True
        self.pause_btn.config(state=tk.DISABLED)
        # Кнопка "Продолжить" активируется автоматически при паузе
        if hasattr(self, 'resume_btn'):
            self.resume_btn.config(state=tk.NORMAL)
    
    def resume_process(self):
        """Продолжение процесса после паузы"""
        self.is_paused = False
        # Также снимаем паузу в executor
        if hasattr(self, 'executor') and self.executor is not None and hasattr(self.executor, 'is_paused'):
            self.executor.is_paused = False
        self.resume_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.output("▶▶ Процесс продолжен")
    
    def stop_process(self):
        """Остановка процесса"""
        self.is_running = False
        self.is_paused = False
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.output("⏹ Процесс остановлен пользователем")
        
        # Очищаем тестовую среду если была создана
        if self.test_env:
            self.test_env.cleanup(keep=False)
            self.test_env = None
    
    def on_full_test_mode_toggle(self):
        """Обработчик переключения полного тестового режима"""
        if self.full_test_mode_var.get():
            # Если включен полный тестовый режим, отключаем обычный
            self.test_mode_var.set(False)
            use_persistent = self.use_persistent_test_dir_var.get()
            if use_persistent:
                self.test_info_label.config(text="(работа в CommitTest/, реальные файлы не изменяются)")
            else:
                self.test_info_label.config(text="(работа в временной директории, реальные файлы не изменяются)")
        else:
            self.test_info_label.config(text="(команды выводятся, файлы не изменяются)")
    
    def run_process(self):
        """Выполнение процесса создания коммита"""
        try:
            # Получаем режимы тестирования
            test_mode = self.test_mode_var.get()
            full_test_mode = self.full_test_mode_var.get()
            
            # Если полный тестовый режим, создаем тестовую среду
            test_env_dir = None
            if full_test_mode:
                use_persistent = self.use_persistent_test_dir_var.get()
                
                if use_persistent:
                    # Используем постоянную директорию CommitTest внутри проекта
                    from pathlib import Path
                    if self.current_project_config is None:
                        self.output("❌ Ошибка: Конфигурация проекта не выбрана")
                        messagebox.showerror("Ошибка", "Конфигурация проекта не выбрана", parent=self.root)
                        self.is_running = False
                        return
                    config_path = Path(self.current_project_config.path)
                    
                    # Проверяем, не является ли уже config_path директорией CommitTest
                    if config_path.name == "CommitTest":
                        # Если уже в CommitTest, используем его напрямую
                        test_commit_dir = config_path
                        self.output(f"🔬 Использование текущей тестовой директории: {test_commit_dir}")
                    else:
                        # Если это корень проекта, добавляем CommitTest
                        project_root = config_path
                        test_commit_dir = project_root / "CommitTest"
                        self.output(f"🔬 Использование постоянной тестовой директории: {test_commit_dir}")
                    
                    self.test_env = TestEnvironment(self.output, persistent_dir=str(test_commit_dir))
                else:
                    # Создаем временную директорию
                    self.output("🔬 Создание временной тестовой среды...")
                    self.test_env = TestEnvironment(self.output)
                
                if not self.test_env.setup():
                    self.output("❌ Ошибка: Не удалось создать тестовую среду")
                    messagebox.showerror("Ошибка", "Не удалось создать тестовую среду", parent=self.root)
                    self.is_running = False
                    return
                test_env_dir = self.test_env.get_temp_dir()
                self.output(f"✓ Тестовая среда готова: {test_env_dir}")
            
            # Создаем логгер - логи сохраняем ВНУТРИ проекта
            # Определяем правильную директорию для логов
            from pathlib import Path
            if self.current_project_config is None:
                self.output("❌ Ошибка: Конфигурация проекта не выбрана")
                messagebox.showerror("Ошибка", "Конфигурация проекта не выбрана", parent=self.root)
                self.is_running = False
                return
            project_root = Path(self.current_project_config.path)
            
            if test_env_dir:
                # Для тестовой среды логи сохраняем в CommitTest/Logs внутри проекта
                if Path(test_env_dir).name == 'CommitTest' or 'CommitTest' in str(test_env_dir):
                    # Это CommitTest - логи внутри проекта
                    log_dir = os.path.join(test_env_dir, 'Logs')
                else:
                    # Временная директория - логи в самой временной директории
                    log_dir = os.path.join(test_env_dir, 'Logs')
                project_dir = test_env_dir
            else:
                # Для реального проекта логи в проекте/Logs
                log_dir = os.path.join(project_root, 'Logs')
                project_dir = str(project_root)
            
            # Убеждаемся, что логи создаются внутри проекта
            self.logger = CommitLogger(project_dir, log_dir=log_dir)
            log_path = self.logger.get_log_file_path()
            self.output(f"📝 Логирование в файл: {log_path}")
            
            # Проверяем, что лог внутри проекта
            if not str(log_path).startswith(str(project_root)):
                self.output(f"⚠️ ВНИМАНИЕ: Лог создан вне проекта: {log_path}")
            
            # Создаем callback для одновременного вывода в GUI и в лог
            logging_callback = LoggingOutputCallback(self.output, self.logger)
            
            # Проверяем наличие конфигурации проекта
            if self.current_project_config is None:
                self.output("❌ Ошибка: Конфигурация проекта не выбрана")
                messagebox.showerror("Ошибка", "Конфигурация проекта не выбрана", parent=self.root)
                self.is_running = False
                return
            
            # Создаем исполнитель и анализатор с логированием
            self.executor = CommitExecutor(
                self.current_project_config,
                logging_callback,
                test_mode=test_mode,
                full_test_mode=full_test_mode,
                test_env_dir=test_env_dir
            )
            self.analyzer = CommitAnalyzer(self.current_project_config, logging_callback)
            
            # Выполняем шаги
            steps = [
                (0, self.executor.step_0_check_directory),
                (1, self.executor.step_1_determine_changed_files),
                (2, self.executor.step_2_check_real_changes),
                (3, self.executor.step_3_determine_current_version),
                (4, self.executor.step_4_determine_new_version),
                (5, self.executor.step_5_collect_analysis_data),
                (6, lambda: self.executor.step_6_analyze_changes(self.analyzer) if self.executor is not None else False),
                (7, self.executor.step_7_save_description),
                (8, self.executor.step_8_check_message_file),
                (8.5, self.executor.step_8_5_pause_for_review),
                (9, self.executor.step_9_update_dates_and_versions),
                (10, self.executor.step_10_verify_dates),
                (11, self.executor.step_11_update_key_files_versions),
                (11.5, self.executor.step_11_5_rebuild_binaries),
                (12, self.executor.step_12_verify_versions),
                (13, self.executor.step_13_add_files_to_index),
                (13.5, self.executor.step_13_5_pause_before_commit),
                (14, self.executor.step_14_create_commit),
                (15, self.executor.step_15_verify_commit),
                (16, self.executor.step_16_cleanup),
                (17, self.executor.step_17_check_history_needed),
                (18, self.executor.step_18_create_history),
                (19, self.executor.step_19_validate_history),
                (20, self.executor.step_20_final_report)
            ]
            
            commit_created = False  # Флаг успешного создания коммита
            
            for step_num, step_func in steps:
                if not self.is_running:
                    break
                
                # Обновляем статус шага
                self.root.after(0, lambda n=step_num: self.update_step_status(int(n), 'running'))
                
                # Выполняем шаг
                success = step_func()
                
                if not self.is_running:
                    break
                
                if success:
                    # Обновляем статус на успех
                    self.root.after(0, lambda n=step_num: self.update_step_status(int(n), 'success'))
                    
                    # Отмечаем успешное создание коммита
                    if step_num == 14:
                        commit_created = True
                    
                    # Проверяем паузу - синхронизируем флаг из executor
                    if step_num in [8.5, 13.5] or (hasattr(self.executor, 'is_paused') and self.executor.is_paused):
                        # Синхронизируем флаг паузы из executor в GUI
                        self.is_paused = True
                        self.root.after(0, lambda: self.update_step_status(int(step_num), 'paused'))
                        # Активируем кнопку "Продолжить" при паузе
                        self.root.after(0, lambda: self.resume_btn.config(state=tk.NORMAL))
                        self.root.after(0, lambda: self.pause_btn.config(state=tk.DISABLED))
                        self.output("⏸ ПАУЗА: Нажмите '▶▶ Продолжить' для продолжения процесса")
                        # Ждем снятия паузы пользователем (реальное ожидание)
                        while self.is_paused and self.is_running:
                            # Синхронизируем флаги - если executor снял паузу, снимаем и в GUI
                            if hasattr(self.executor, 'is_paused') and not self.executor.is_paused:
                                self.is_paused = False
                                break
                            threading.Event().wait(0.5)
                        # После снятия паузы снимаем флаг и в executor
                        if hasattr(self.executor, 'is_paused'):
                            self.executor.is_paused = False
                        # Деактивируем кнопку "Продолжить"
                        self.root.after(0, lambda: self.resume_btn.config(state=tk.DISABLED))
                        self.root.after(0, lambda: self.pause_btn.config(state=tk.NORMAL))
                        self.output("▶▶ Процесс продолжен")
                else:
                    # Обновляем статус на ошибку
                    self.root.after(0, lambda n=step_num: self.update_step_status(int(n), 'error'))
                    break
                
                # Обновляем прогресс
                progress = int((step_num / 20) * 100)
                self.root.after(0, lambda p=progress: self.progress_bar.config(value=p))
                self.root.after(0, lambda p=progress: self.progress_var.set(f"{p}%"))
            
                # Завершение
                if self.is_running:
                    self.root.after(0, lambda: self.progress_bar.config(value=100))
                    self.root.after(0, lambda: self.progress_var.set("100%"))
                    
                    # Процесс завершен
                    if commit_created:
                        self.output("✓ Коммит успешно создан")
                    else:
                        # Процесс завершен, но коммит не был создан (возможно, остановлен на паузе или ошибке)
                        self.output("ℹ️ Процесс завершен")
            
        except Exception as e:
            self.output(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            import traceback
            self.output(traceback.format_exc())
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.pause_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.resume_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            
            # Очищаем тестовую среду если была создана
            if self.test_env:
                self.output("🧹 Очистка тестовой среды...")
                self.test_env.cleanup(keep=False)
                self.test_env = None
                self.output("✓ Тестовая среда очищена")
            
            # Закрываем логгер
            if self.logger:
                log_file_path = self.logger.get_log_file_path()
                self.logger.close()
                self.logger = None
                self.output(f"📝 Лог сохранен: {log_file_path}")
    
    def load_window_geometry(self):
        """Загрузить сохраненную геометрию окна и позиции разделителей"""
        try:
            # Загружаем геометрию окна
            geometry = self.config_manager.get_window_geometry()
            if geometry:
                try:
                    self.root.geometry(geometry)
                except Exception:
                    # Если не удалось восстановить, используем значения по умолчанию
                    pass
            
            # Загружаем позиции разделителей PanedWindow
            paned_positions = self.config_manager.get_paned_positions()
            if paned_positions and hasattr(self, 'main_paned'):
                self.root.after(100, lambda: self.restore_paned_positions(paned_positions))
        except Exception as e:
            print(f"[GUI] Ошибка загрузки геометрии: {e}")
    
    def restore_paned_positions(self, positions: Dict[str, int]):
        """Восстановить позиции разделителей PanedWindow"""
        try:
            if hasattr(self, 'main_paned') and 'main_paned' in positions:
                # Восстанавливаем позицию разделителя
                # PanedWindow имеет метод sashpos для установки позиции
                pos = positions['main_paned']
                # Получаем количество панелей
                panes = self.main_paned.panes()
                if len(panes) >= 2:
                    # Устанавливаем позицию первого разделителя (между левой и центральной панелью)
                    try:
                        self.main_paned.sashpos(0, pos)
                    except Exception:
                        pass
                
                # Если есть второй разделитель (между центральной и правой панелью)
                if 'main_paned_2' in positions and len(panes) >= 3:
                    try:
                        pos2 = positions['main_paned_2']
                        self.main_paned.sashpos(1, pos2)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[GUI] Ошибка восстановления позиций разделителей: {e}")
    
    def save_window_geometry(self):
        """Сохранить текущую геометрию окна и позиции разделителей"""
        try:
            self.root.update_idletasks()
            geometry = self.root.geometry()
            
            # Сохраняем позиции разделителей PanedWindow
            paned_positions = {}
            if hasattr(self, 'main_paned'):
                try:
                    panes = self.main_paned.panes()
                    # Получаем позицию первого разделителя (между левой и центральной панелью)
                    if len(panes) >= 2:
                        pos = self.main_paned.sashpos(0)
                        paned_positions['main_paned'] = pos
                    
                    # Получаем позицию второго разделителя (между центральной и правой панелью)
                    if len(panes) >= 3:
                        pos2 = self.main_paned.sashpos(1)
                        paned_positions['main_paned_2'] = pos2
                except Exception:
                    pass
            
            # Сохраняем в конфигурацию
            self.config_manager.save_window_geometry(geometry, paned_positions)
        except Exception as e:
            print(f"[GUI] Ошибка сохранения геометрии: {e}")
    
    def on_window_configure(self, event):
        """Обработчик изменения размера/позиции окна"""
        # Сохраняем геометрию только если это изменение главного окна (не дочерних виджетов)
        if event.widget == self.root:
            # Сохраняем геометрию при изменении (с задержкой, чтобы не сохранять слишком часто)
            if hasattr(self, '_geometry_save_timer'):
                self.root.after_cancel(self._geometry_save_timer)
            self._geometry_save_timer = self.root.after(500, self.save_window_geometry)
    
    def on_closing(self):
        """Обработчик закрытия окна"""
        # Сохраняем геометрию перед закрытием
        self.save_window_geometry()
        self.root.destroy()
    
    def center_window(self):
        """Центрировать окно на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def show_window_on_top(self):
        """Показать окно поверх других окон на несколько секунд"""
        # Поднимаем окно наверх
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.update()
        
        # Через 5 секунд убираем флаг topmost
        self.root.after(5000, lambda: self.root.attributes('-topmost', False))
    
    
    def run(self):
        """Запуск GUI"""
        self.root.mainloop()


def main():
    """Главная функция"""
    app = CommitManagerGUI()
    app.run()


if __name__ == '__main__':
    main()

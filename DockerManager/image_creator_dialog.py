#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диалог создания Docker образов с редактированием компонентов
Версия: V3.1.161 (2025.12.04)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from pathlib import Path
import threading
import tempfile
import traceback

from .config import BUILD_PLATFORMS, get_dockerfiles_dir, get_incoming_path
from .docker_manager import (
    generate_dockerfile_from_config, get_local_base_images,
    build_remote_image, check_remote_image_exists
)
from .server_connection import scp_upload, execute_ssh_command, create_remote_directory
from .config import get_project_dir


class CreateImageDialog:
    """Диалог для создания Docker образа с редактированием компонентов"""
    
    def __init__(self, parent, log_callback=None):
        self.parent = parent
        self.log_callback = log_callback
        self.image_created = False
        self.config = {
            'base_image': 'debian:bookworm',
            'system_packages': [],
            'python_packages': [],
            'env_vars': [],
            'custom_commands': [],
            'pip_flags': '--break-system-packages'
        }
        
        # Создаем диалог
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Создать Docker образ")
        self.dialog.geometry("900x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        self.load_quick_templates()
        
    def log(self, message):
        """Логирование"""
        if self.log_callback:
            self.log_callback(message)
    
    def create_widgets(self):
        """Создает виджеты диалога"""
        # Основной контейнер с прокруткой
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Базовый образ
        base_frame = ttk.LabelFrame(main_frame, text="Базовый образ", padding=5)
        base_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(base_frame, text="Образ:").pack(side=tk.LEFT, padx=5)
        self.base_image_var = tk.StringVar(value="debian:bookworm")
        base_entry = ttk.Entry(base_frame, textvariable=self.base_image_var, width=40)
        base_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        base_entry.bind('<KeyRelease>', lambda e: self.update_preview())
        
        ttk.Button(base_frame, text="Быстрый выбор", 
                  command=self.quick_select_base).pack(side=tk.LEFT, padx=5)
        
        # Notebook для компонентов
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Вкладка: Системные пакеты
        self.system_frame = self.create_packages_frame(notebook, "Системные пакеты", "system")
        notebook.add(self.system_frame, text="Системные пакеты")
        
        # Вкладка: Python пакеты
        self.python_frame = self.create_packages_frame(notebook, "Python пакеты", "python")
        notebook.add(self.python_frame, text="Python пакеты")
        
        # Вкладка: Переменные окружения
        self.env_frame = self.create_env_frame(notebook)
        notebook.add(self.env_frame, text="Переменные окружения")
        
        # Вкладка: Кастомные команды
        self.commands_frame = self.create_commands_frame(notebook)
        notebook.add(self.commands_frame, text="Кастомные команды")
        
        # Вкладка: Предпросмотр Dockerfile
        preview_frame = ttk.Frame(notebook, padding=5)
        notebook.add(preview_frame, text="Предпросмотр Dockerfile")
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=15, wrap=tk.NONE)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        self.update_preview()
        
        # Имя образа
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(name_frame, text="Имя образа (repository:tag):").pack(side=tk.LEFT, padx=5)
        self.image_name_var = tk.StringVar(value="my-custom-image:latest")
        ttk.Entry(name_frame, textvariable=self.image_name_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="Отмена", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Создать образ", command=self.create_image).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Сохранить шаблон", command=self.save_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Загрузить шаблон", command=self.load_template).pack(side=tk.LEFT, padx=5)
    
    def create_packages_frame(self, parent, title, pkg_type):
        """Создает фрейм для пакетов (системных или Python)"""
        frame = ttk.Frame(parent, padding=5)
        
        # Список пакетов
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree = ttk.Treeview(list_frame, columns=("version", "actions"), show="tree headings", 
                           yscrollcommand=scrollbar.set, height=8)
        tree.heading("#0", text="Пакет")
        tree.heading("version", text="Версия")
        tree.heading("actions", text="Действия")
        tree.column("#0", width=200)
        tree.column("version", width=150)
        tree.column("actions", width=100)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=tree.yview)
        
        # Привязываем события
        def on_double_click(event):
            item = tree.selection()[0] if tree.selection() else None
            if item:
                self.edit_package(tree, item, pkg_type)
        
        def on_click(event):
            item = tree.identify_row(event.y)
            if item:
                column = tree.identify_column(event.x)
                if column == "#3":  # Колонка actions
                    # Определяем действие по позиции клика
                    x = event.x
                    item_bbox = tree.bbox(item, "#3")
                    if item_bbox:
                        # Простое определение: левая половина = редактировать, правая = удалить
                        if x < item_bbox[0] + item_bbox[2] / 2:
                            self.edit_package(tree, item, pkg_type)
                        else:
                            self.delete_item(tree, item, pkg_type)
        
        tree.bind('<Double-Button-1>', on_double_click)
        tree.bind('<Button-1>', on_click)
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        def add_package():
            name = simpledialog.askstring("Добавить пакет", "Имя пакета:")
            if name:
                version = simpledialog.askstring("Версия (опционально)", "Версия пакета (оставьте пустым для latest):")
                if version == "":
                    version = None
                self.add_package_item(tree, pkg_type, name, version)
        
        ttk.Button(btn_frame, text="+ Добавить пакет", command=add_package).pack(side=tk.LEFT, padx=5)
        
        def edit_selected():
            selection = tree.selection()
            if selection:
                self.edit_package(tree, selection[0], pkg_type)
            else:
                messagebox.showinfo("Информация", "Выберите пакет для редактирования")
        
        def delete_selected():
            selection = tree.selection()
            if selection:
                self.delete_item(tree, selection[0], pkg_type)
            else:
                messagebox.showinfo("Информация", "Выберите пакет для удаления")
        
        ttk.Button(btn_frame, text="✏️ Редактировать", command=edit_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Удалить", command=delete_selected).pack(side=tk.LEFT, padx=5)
        
        # Сохраняем ссылку на tree
        if pkg_type == "system":
            self.system_tree = tree
        else:
            self.python_tree = tree
        
        return frame
    
    def create_env_frame(self, parent):
        """Создает фрейм для переменных окружения"""
        frame = ttk.Frame(parent, padding=5)
        
        # Список переменных
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree = ttk.Treeview(list_frame, columns=("value", "actions"), show="tree headings",
                           yscrollcommand=scrollbar.set, height=8)
        tree.heading("#0", text="Ключ")
        tree.heading("value", text="Значение")
        tree.heading("actions", text="Действия")
        tree.column("#0", width=200)
        tree.column("value", width=200)
        tree.column("actions", width=100)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=tree.yview)
        
        # Привязываем события
        def on_double_click(event):
            item = tree.selection()[0] if tree.selection() else None
            if item:
                self.edit_env(item)
        
        tree.bind('<Double-Button-1>', on_double_click)
        
        self.env_tree = tree
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        def add_env():
            key = simpledialog.askstring("Добавить переменную", "Ключ:")
            if key:
                value = simpledialog.askstring("Значение", f"Значение для {key}:")
                if value is None:
                    value = ""
                self.add_env_item(key, value)
        
        ttk.Button(btn_frame, text="+ Добавить переменную", command=add_env).pack(side=tk.LEFT, padx=5)
        
        def edit_selected():
            selection = tree.selection()
            if selection:
                self.edit_env(selection[0])
            else:
                messagebox.showinfo("Информация", "Выберите переменную для редактирования")
        
        def delete_selected():
            selection = tree.selection()
            if selection:
                self.delete_item(tree, selection[0], "env")
            else:
                messagebox.showinfo("Информация", "Выберите переменную для удаления")
        
        ttk.Button(btn_frame, text="✏️ Редактировать", command=edit_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Удалить", command=delete_selected).pack(side=tk.LEFT, padx=5)
        
        return frame
    
    def create_commands_frame(self, parent):
        """Создает фрейм для кастомных команд"""
        frame = ttk.Frame(parent, padding=5)
        
        # Список команд
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree = ttk.Treeview(list_frame, columns=("actions",), show="tree headings",
                           yscrollcommand=scrollbar.set, height=8)
        tree.heading("#0", text="Команда")
        tree.heading("actions", text="Действия")
        tree.column("#0", width=500)
        tree.column("actions", width=100)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=tree.yview)
        
        # Привязываем события
        def on_double_click(event):
            item = tree.selection()[0] if tree.selection() else None
            if item:
                self.edit_command(item)
        
        tree.bind('<Double-Button-1>', on_double_click)
        
        self.commands_tree = tree
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        def add_command():
            cmd = simpledialog.askstring("Добавить команду", "Команда RUN:")
            if cmd:
                self.add_command_item(cmd)
        
        ttk.Button(btn_frame, text="+ Добавить команду", command=add_command).pack(side=tk.LEFT, padx=5)
        
        def edit_selected():
            selection = tree.selection()
            if selection:
                self.edit_command(selection[0])
            else:
                messagebox.showinfo("Информация", "Выберите команду для редактирования")
        
        def delete_selected():
            selection = tree.selection()
            if selection:
                self.delete_item(tree, selection[0], "command")
            else:
                messagebox.showinfo("Информация", "Выберите команду для удаления")
        
        ttk.Button(btn_frame, text="✏️ Редактировать", command=edit_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Удалить", command=delete_selected).pack(side=tk.LEFT, padx=5)
        
        return frame
    
    def add_package_item(self, tree, pkg_type, name, version=None, skip_config=False):
        """Добавляет пакет в список"""
        version_str = version if version else "latest"
        item_id = tree.insert("", tk.END, text=name, values=(version_str, "✏️ 🗑️"))
        
        # Привязываем события
        tree.item(item_id, tags=(pkg_type, item_id))
        
        # Сохраняем в конфигурацию только если не пропущено
        if not skip_config:
            pkg_data = {'name': name, 'version': version, 'enabled': True}
            if pkg_type == "system":
                self.config['system_packages'].append(pkg_data)
            else:
                self.config['python_packages'].append(pkg_data)
        
        self.update_preview()
    
    def add_env_item(self, key, value, skip_config=False):
        """Добавляет переменную окружения"""
        item_id = self.env_tree.insert("", tk.END, text=key, values=(value, "✏️ 🗑️"))
        self.env_tree.item(item_id, tags=("env", item_id))
        
        # Сохраняем в конфигурацию только если не пропущено
        if not skip_config:
            self.config['env_vars'].append({'key': key, 'value': value, 'enabled': True})
        
        self.update_preview()
    
    def add_command_item(self, command, skip_config=False):
        """Добавляет кастомную команду"""
        item_id = self.commands_tree.insert("", tk.END, text=command, values=("✏️ 🗑️",))
        self.commands_tree.item(item_id, tags=("command", item_id))
        
        # Сохраняем в конфигурацию только если не пропущено
        if not skip_config:
            self.config['custom_commands'].append({'command': command, 'enabled': True})
        
        self.update_preview()
    
    def edit_package(self, tree, item_id, pkg_type):
        """Редактирует пакет"""
        item = tree.item(item_id)
        current_name = item['text']
        current_version = item['values'][0] if item['values'] else "latest"
        if current_version == "latest":
            current_version = None
        
        new_name = simpledialog.askstring("Редактировать пакет", "Имя пакета:", initialvalue=current_name)
        if new_name:
            new_version = simpledialog.askstring("Версия", "Версия (оставьте пустым для latest):",
                                                initialvalue=current_version or "")
            if new_version == "":
                new_version = None
            
            # Обновляем в дереве
            version_str = new_version if new_version else "latest"
            tree.item(item_id, text=new_name, values=(version_str, ""))
            
            # Обновляем в конфигурации
            if pkg_type == "system":
                for pkg in self.config['system_packages']:
                    if pkg['name'] == current_name:
                        pkg['name'] = new_name
                        pkg['version'] = new_version
                        break
            else:
                for pkg in self.config['python_packages']:
                    if pkg['name'] == current_name:
                        pkg['name'] = new_name
                        pkg['version'] = new_version
                        break
            
            self.update_preview()
    
    def edit_env(self, item_id):
        """Редактирует переменную окружения"""
        item = self.env_tree.item(item_id)
        current_key = item['text']
        current_value = item['values'][0] if item['values'] else ""
        
        new_key = simpledialog.askstring("Редактировать переменную", "Ключ:", initialvalue=current_key)
        if new_key:
            new_value = simpledialog.askstring("Значение", f"Значение для {new_key}:", initialvalue=current_value)
            if new_value is None:
                new_value = ""
            
            # Обновляем в дереве
            self.env_tree.item(item_id, text=new_key, values=(new_value, ""))
            
            # Обновляем в конфигурации
            for env in self.config['env_vars']:
                if env['key'] == current_key:
                    env['key'] = new_key
                    env['value'] = new_value
                    break
            
            self.update_preview()
    
    def edit_command(self, item_id):
        """Редактирует кастомную команду"""
        item = self.commands_tree.item(item_id)
        current_cmd = item['text']
        
        new_cmd = simpledialog.askstring("Редактировать команду", "Команда RUN:", initialvalue=current_cmd)
        if new_cmd:
            # Обновляем в дереве
            self.commands_tree.item(item_id, text=new_cmd)
            
            # Обновляем в конфигурации
            for cmd in self.config['custom_commands']:
                if cmd['command'] == current_cmd:
                    cmd['command'] = new_cmd
                    break
            
            self.update_preview()
    
    def delete_item(self, tree, item_id, item_type):
        """Удаляет элемент из списка"""
        if not messagebox.askyesno("Подтверждение", "Удалить этот элемент?"):
            return
        
        item = tree.item(item_id)
        tree.delete(item_id)
        
        # Удаляем из конфигурации
        if item_type == "system":
            name = item['text']
            self.config['system_packages'] = [p for p in self.config['system_packages'] if p['name'] != name]
        elif item_type == "python":
            name = item['text']
            self.config['python_packages'] = [p for p in self.config['python_packages'] if p['name'] != name]
        elif item_type == "env":
            key = item['text']
            self.config['env_vars'] = [e for e in self.config['env_vars'] if e['key'] != key]
        elif item_type == "command":
            cmd = item['text']
            self.config['custom_commands'] = [c for c in self.config['custom_commands'] if c['command'] != cmd]
        
        self.update_preview()
    
    def update_preview(self):
        """Обновляет предпросмотр Dockerfile"""
        self.config['base_image'] = self.base_image_var.get()
        dockerfile = generate_dockerfile_from_config(self.config)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", dockerfile)
    
    def load_quick_templates(self):
        """Загружает быстрые шаблоны из BUILD_PLATFORMS"""
        # Можно добавить кнопки быстрого выбора
        pass
    
    def quick_select_base(self):
        """Быстрый выбор базового образа"""
        dialog = tk.Toplevel(self.dialog)
        dialog.title("Выбрать базовый образ")
        dialog.geometry("400x300")
        dialog.transient(self.dialog)
        
        # Предопределенные
        ttk.Label(dialog, text="Предопределенные:").pack(pady=5)
        for platform_id, platform in BUILD_PLATFORMS.items():
            btn = ttk.Button(dialog, 
                           text=f"{platform_id}: {platform['base_image']}",
                           command=lambda img=platform['base_image']: self.select_base_and_close(dialog, img))
            btn.pack(pady=2, padx=10, fill=tk.X)
        
        ttk.Separator(dialog, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Локальные образы
        ttk.Label(dialog, text="Локальные образы на сервере:").pack(pady=5)
        local_frame = ttk.Frame(dialog)
        local_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(local_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        local_list = tk.Listbox(local_frame, yscrollcommand=scrollbar.set)
        local_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=local_list.yview)
        
        def load_local():
            images = get_local_base_images()
            for img in images:
                local_list.insert(tk.END, img)
        
        threading.Thread(target=load_local, daemon=True).start()
        
        def on_select(event):
            selection = local_list.curselection()
            if selection:
                img = local_list.get(selection[0])
                self.select_base_and_close(dialog, img)
        
        local_list.bind('<Double-Button-1>', on_select)
        
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack(pady=5)
    
    def select_base_and_close(self, dialog, image):
        """Выбирает базовый образ и закрывает диалог"""
        self.base_image_var.set(image)
        dialog.destroy()
        self.update_preview()
    
    def save_template(self):
        """Сохраняет текущую конфигурацию как шаблон"""
        name = simpledialog.askstring("Сохранить шаблон", "Имя шаблона:")
        if name:
            # Сохраняем в файл
            templates_dir = get_dockerfiles_dir().parent / "templates"
            templates_dir.mkdir(exist_ok=True)
            template_file = templates_dir / f"{name}.json"
            
            import json
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Успех", f"Шаблон '{name}' сохранен")
    
    def load_template(self):
        """Загружает шаблон"""
        templates_dir = get_dockerfiles_dir().parent / "templates"
        if not templates_dir.exists():
            messagebox.showinfo("Информация", "Нет сохраненных шаблонов")
            return
        
        # Показываем список шаблонов
        templates = list(templates_dir.glob("*.json"))
        if not templates:
            messagebox.showinfo("Информация", "Нет сохраненных шаблонов")
            return
        
        dialog = tk.Toplevel(self.dialog)
        dialog.title("Загрузить шаблон")
        dialog.geometry("300x200")
        dialog.transient(self.dialog)
        
        ttk.Label(dialog, text="Выберите шаблон:").pack(pady=5)
        
        listbox = tk.Listbox(dialog)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for template in templates:
            listbox.insert(tk.END, template.stem)
        
        def load_selected():
            selection = listbox.curselection()
            if selection:
                template_name = listbox.get(selection[0])
                template_file = templates_dir / f"{template_name}.json"
                
                import json
                with open(template_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                
                # Обновляем UI
                self.base_image_var.set(self.config.get('base_image', 'debian:bookworm'))
                self.refresh_all_trees()
                dialog.destroy()
        
        ttk.Button(dialog, text="Загрузить", command=load_selected).pack(pady=5)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack()
    
    def refresh_all_trees(self):
        """Обновляет все деревья из конфигурации"""
        # Сохраняем конфигурацию перед очисткой
        import copy
        temp_config = copy.deepcopy(self.config)
        
        # Очищаем деревья
        for item in self.system_tree.get_children():
            self.system_tree.delete(item)
        for item in self.python_tree.get_children():
            self.python_tree.delete(item)
        for item in self.env_tree.get_children():
            self.env_tree.delete(item)
        for item in self.commands_tree.get_children():
            self.commands_tree.delete(item)
        
        # Очищаем конфигурацию перед загрузкой
        self.config['system_packages'] = []
        self.config['python_packages'] = []
        self.config['env_vars'] = []
        self.config['custom_commands'] = []
        
        # Загружаем из сохраненной конфигурации
        for pkg in temp_config.get('system_packages', []):
            if pkg.get('enabled', True):
                self.add_package_item(self.system_tree, "system", pkg['name'], 
                                    pkg.get('version'), skip_config=True)
                # Добавляем в конфигурацию
                self.config['system_packages'].append(pkg)
        
        for pkg in temp_config.get('python_packages', []):
            if pkg.get('enabled', True):
                self.add_package_item(self.python_tree, "python", pkg['name'], 
                                    pkg.get('version'), skip_config=True)
                # Добавляем в конфигурацию
                self.config['python_packages'].append(pkg)
        
        for env in temp_config.get('env_vars', []):
            if env.get('enabled', True):
                self.add_env_item(env['key'], env.get('value', ''), skip_config=True)
                # Добавляем в конфигурацию
                self.config['env_vars'].append(env)
        
        for cmd in temp_config.get('custom_commands', []):
            if cmd.get('enabled', True):
                self.add_command_item(cmd['command'], skip_config=True)
                # Добавляем в конфигурацию
                self.config['custom_commands'].append(cmd)
        
        self.update_preview()
    
    def create_image(self):
        """Создает образ на сервере"""
        image_name = self.image_name_var.get().strip()
        if not image_name or ':' not in image_name:
            messagebox.showerror("Ошибка", "Имя образа должно быть в формате repository:tag")
            return
        
        # Проверяем наличие компонентов
        has_components = any([
            self.config.get('system_packages'),
            self.config.get('python_packages'),
            self.config.get('env_vars'),
            self.config.get('custom_commands')
        ])
        
        if not has_components:
            if not messagebox.askyesno("Подтверждение", 
                                     "Нет настроенных компонентов. Создать образ только с базовым образом?"):
                return
        
        # Проверяем существование образа
        if check_remote_image_exists(image_name):
            if not messagebox.askyesno("Подтверждение", 
                                     f"Образ {image_name} уже существует. Пересобрать?"):
                return
        
        # Генерируем Dockerfile
        dockerfile_content = generate_dockerfile_from_config(self.config)
        
        # Сохраняем Dockerfile локально во временный файл
        temp_fd, temp_dockerfile_path = tempfile.mkstemp(suffix='.dockerfile', prefix='dockerfile_', text=True)
        try:
            with open(temp_fd, 'w', encoding='utf-8') as f:
                f.write(dockerfile_content)
            temp_dockerfile = Path(temp_dockerfile_path)
        except Exception as e:
            self.log(f"[ERROR] Не удалось создать временный файл: {e}")
            messagebox.showerror("Ошибка", f"Не удалось создать временный файл: {e}")
            return
        
        def build():
            try:
                self.log(f"[INFO] Создание образа {image_name}...")
                
                # Загружаем Dockerfile на сервер
                project = "FSA-AstraInstall"  # Можно сделать настраиваемым
                incoming_path = get_incoming_path(project)
                
                if not create_remote_directory(incoming_path):
                    error_msg = "Не удалось создать директорию на сервере"
                    self.log(f"[ERROR] {error_msg}")
                    self.dialog.after(0, lambda: messagebox.showerror("Ошибка", error_msg))
                    return
                
                # Имя файла Dockerfile на сервере
                dockerfile_name = f"Dockerfile.{image_name.replace(':', '_').replace('/', '_')}"
                remote_dockerfile_full = f"{incoming_path}/{dockerfile_name}"
                
                self.log(f"[INFO] Загрузка Dockerfile на сервер: {remote_dockerfile_full}")
                if not scp_upload(str(temp_dockerfile), remote_dockerfile_full):
                    error_msg = "Не удалось загрузить Dockerfile на сервер"
                    self.log(f"[ERROR] {error_msg}")
                    self.dialog.after(0, lambda: messagebox.showerror("Ошибка", error_msg))
                    return
                
                self.log(f"[INFO] Запуск сборки образа {image_name}...")
                # Собираем образ (используем относительный путь к Dockerfile от контекста)
                # Контекст = incoming_path, Dockerfile находится в этой же директории
                if build_remote_image(dockerfile_name, image_name, incoming_path, 
                                    platform="linux/amd64"):
                    success_msg = f"Образ {image_name} успешно создан"
                    self.log(f"[OK] {success_msg}")
                    self.image_created = True
                    self.dialog.after(0, lambda: messagebox.showinfo("Успех", success_msg))
                    self.dialog.after(0, self.dialog.destroy)
                else:
                    error_msg = f"Не удалось создать образ {image_name}"
                    self.log(f"[ERROR] {error_msg}")
                    self.dialog.after(0, lambda: messagebox.showerror("Ошибка", error_msg))
            except Exception as e:
                error_msg = f"Ошибка создания образа: {e}"
                error_details = traceback.format_exc()
                self.log(f"[ERROR] {error_msg}")
                self.log(f"[ERROR] Детали: {error_details}")
                self.dialog.after(0, lambda: messagebox.showerror("Ошибка", f"{error_msg}\n\nПроверьте логи для деталей."))
            finally:
                # Удаляем временный файл
                try:
                    if temp_dockerfile.exists():
                        temp_dockerfile.unlink()
                except Exception as e:
                    self.log(f"[WARNING] Не удалось удалить временный файл: {e}")
        
        # Запускаем сборку в отдельном потоке
        threading.Thread(target=build, daemon=True).start()


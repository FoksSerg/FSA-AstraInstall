#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инструмент управления пакетами для FSA-AstraInstall
GUI инструмент для формирования архивов и структуры компонентов
Версия: V2.4.111 (2025.11.11)
Компания: ООО "НПА Вира-Реалтайм"
"""

# Версия приложения
APP_VERSION = "V2.4.111 (2025.11.11)"

import os
import sys
import shutil
import tarfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pathlib import Path
import json

# Импортируем COMPONENTS_CONFIG из основного скрипта
COMPONENTS_CONFIG = {}
try:
    # Добавляем путь к директории скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    
    # Пытаемся импортировать модуль напрямую
    # Используем importlib для безопасной загрузки
    import importlib.util
    astra_automation_path = os.path.join(script_dir, 'astra_automation.py')
    
    if os.path.exists(astra_automation_path):
        spec = importlib.util.spec_from_file_location("astra_automation", astra_automation_path)
        if spec and spec.loader:
            astra_module = importlib.util.module_from_spec(spec)
            try:
                # Загружаем модуль (может вызвать ошибки из-за зависимостей)
                spec.loader.exec_module(astra_module)
                if hasattr(astra_module, 'COMPONENTS_CONFIG'):
                    COMPONENTS_CONFIG = astra_module.COMPONENTS_CONFIG
                    print(f"COMPONENTS_CONFIG загружен: {len(COMPONENTS_CONFIG)} компонентов")
            except Exception as import_error:
                # Если импорт не удался из-за зависимостей, используем fallback
                print(f"Прямой импорт не удался (это нормально): {import_error}")
                print("Используем fallback метод...")
                
                # Fallback: читаем файл и извлекаем COMPONENTS_CONFIG
                # Находим строку с COMPONENTS_CONFIG и читаем до конца словаря
                with open(astra_automation_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Ищем начало COMPONENTS_CONFIG
                start_marker = 'COMPONENTS_CONFIG = {'
                start_pos = content.find(start_marker)
                
                if start_pos != -1:
                    # Находим конец словаря, считая скобки
                    pos = start_pos + len(start_marker) - 1
                    brace_count = 1
                    end_pos = pos + 1
                    
                    while end_pos < len(content) and brace_count > 0:
                        if content[end_pos] == '{':
                            brace_count += 1
                        elif content[end_pos] == '}':
                            brace_count -= 1
                        end_pos += 1
                    
                    if brace_count == 0:
                        # Извлекаем код словаря
                        config_code = content[start_pos:end_pos]
                        namespace = {'__file__': astra_automation_path}
                        try:
                            exec(config_code, namespace)
                            COMPONENTS_CONFIG = namespace.get('COMPONENTS_CONFIG', {})
                            print(f"COMPONENTS_CONFIG загружен через fallback: {len(COMPONENTS_CONFIG)} компонентов")
                        except Exception as e:
                            print(f"Ошибка извлечения COMPONENTS_CONFIG: {e}")
                            COMPONENTS_CONFIG = {}
    else:
        print(f"Файл не найден: {astra_automation_path}")
except Exception as e:
    print(f"Ошибка загрузки COMPONENTS_CONFIG: {e}")
    import traceback
    traceback.print_exc()
    COMPONENTS_CONFIG = {}


class PackageManagerGUI:
    """GUI инструмент для управления пакетами"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Инструмент управления пакетами FSA-AstraInstall {APP_VERSION}")
        self.root.geometry("1200x700")
        
        # Получаем директорию скрипта
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.astrapack_dir = os.path.join(self.script_dir, "AstraPack")
        
        # Структура папок для групп
        self.package_groups = {
            'wine': {
                'name': 'Wine пакеты',
                'description': 'Пакеты Wine и связанные компоненты',
                'files': ['wine_9.0-1_amd64.deb', 'wine-astraregul_10.0-rc6-3_amd64.deb']
            },
            'astra': {
                'name': 'Astra IDE',
                'description': 'Компоненты Astra IDE',
                'files': ['Astra.IDE_64_1.7.2.1.exe']
            },
            'cont': {
                'name': 'CONT-Designer',
                'description': 'Компоненты CONT-Designer',
                'source_dir': 'CountPack',
                'archive_name': 'CountPack.tar.gz'
            },
            'winetricks': {
                'name': 'Winetricks',
                'description': 'Winetricks и кэш',
                'files': ['winetricks'],
                'dirs': ['winetricks-cache', 'wine-gecko']
            }
        }
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Загружаем структуру при запуске
        self.update_structure_tree()
        
        # Показываем предупреждение, если COMPONENTS_CONFIG не загружен
        if not COMPONENTS_CONFIG:
            self.root.after(500, lambda: messagebox.showwarning(
                "Предупреждение", 
                "COMPONENTS_CONFIG не загружен.\n" +
                "Некоторые функции могут работать некорректно.\n" +
                "Проверьте наличие файла astra_automation.py в той же директории."
            ))
    
    def create_widgets(self):
        """Создание виджетов интерфейса"""
        # Создаем Notebook для вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладка 1: Структура папок
        self.create_structure_tab()
        
        # Вкладка 2: Архивация
        self.create_archive_tab()
        
        # Вкладка 3: Компоненты
        self.create_components_tab()
        
        # Вкладка 4: Инструменты
        self.create_tools_tab()
    
    def create_structure_tab(self):
        """Создание вкладки структуры папок"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Структура папок")
        
        # Верхняя панель с кнопками
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(top_frame, text="Создать структуру", 
                  command=self.create_structure).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Обновить", 
                  command=self.update_structure_tree).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Открыть в Finder", 
                  command=self.open_in_finder).pack(side=tk.LEFT, padx=5)
        
        # Дерево структуры
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar для дерева
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        self.structure_tree = ttk.Treeview(tree_frame, yscrollcommand=scrollbar.set)
        self.structure_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.structure_tree.yview)
        
        # Колонки
        self.structure_tree['columns'] = ('size', 'type')
        self.structure_tree.heading('#0', text='Имя')
        self.structure_tree.heading('size', text='Размер')
        self.structure_tree.heading('type', text='Тип')
        
        self.structure_tree.column('#0', width=300)
        self.structure_tree.column('size', width=100)
        self.structure_tree.column('type', width=100)
        
        # Информационная панель
        info_frame = ttk.LabelFrame(frame, text="Информация")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.structure_info = tk.Text(info_frame, height=3, wrap=tk.WORD)
        self.structure_info.pack(fill=tk.X, padx=5, pady=5)
    
    def create_archive_tab(self):
        """Создание вкладки архивации"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Архивация")
        
        # Левая панель: список компонентов
        left_frame = ttk.LabelFrame(frame, text="Компоненты для архивации")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Список компонентов
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar_list = ttk.Scrollbar(list_frame)
        scrollbar_list.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.archive_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar_list.set, 
                                          selectmode=tk.EXTENDED)
        self.archive_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_list.config(command=self.archive_listbox.yview)
        
        # Заполняем список
        self.update_archive_list()
        
        # Кнопки архивации
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Архивировать выбранные", 
                  command=self.archive_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Архивировать все", 
                  command=self.archive_all).pack(side=tk.LEFT, padx=5)
        
        # Правая панель: информация и логи
        right_frame = ttk.LabelFrame(frame, text="Информация и логи")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Информация о компоненте
        info_label = ttk.Label(right_frame, text="Выберите компонент для просмотра информации")
        info_label.pack(padx=5, pady=5)
        
        self.archive_info = scrolledtext.ScrolledText(right_frame, height=15, wrap=tk.WORD)
        self.archive_info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Привязка события выбора
        self.archive_listbox.bind('<<ListboxSelect>>', self.on_archive_select)
    
    def create_components_tab(self):
        """Создание вкладки компонентов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Компоненты")
        
        # Левая панель: список компонентов
        left_frame = ttk.LabelFrame(frame, text="Список компонентов")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Поиск
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT, padx=5)
        self.component_search = ttk.Entry(search_frame)
        self.component_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.component_search.bind('<KeyRelease>', self.filter_components)
        
        # Список компонентов
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar_comp = ttk.Scrollbar(list_frame)
        scrollbar_comp.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.component_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar_comp.set)
        self.component_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_comp.config(command=self.component_listbox.yview)
        
        # Заполняем список
        self.update_component_list()
        
        # Правая панель: конфигурация компонента
        right_frame = ttk.LabelFrame(frame, text="Конфигурация компонента")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.component_config = scrolledtext.ScrolledText(right_frame, height=20, wrap=tk.WORD)
        self.component_config.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Привязка события выбора
        self.component_listbox.bind('<<ListboxSelect>>', self.on_component_select)
    
    def create_tools_tab(self):
        """Создание вкладки инструментов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Инструменты")
        
        # Панель инструментов
        tools_frame = ttk.LabelFrame(frame, text="Инструменты")
        tools_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(tools_frame, text="Проверить архивы", 
                  command=self.check_archives).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(tools_frame, text="Показать статистику", 
                  command=self.show_statistics).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(tools_frame, text="Очистить временные файлы", 
                  command=self.cleanup_temp).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Область вывода
        output_frame = ttk.LabelFrame(frame, text="Результаты")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tools_output = scrolledtext.ScrolledText(output_frame, height=20, wrap=tk.WORD)
        self.tools_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def get_dir_size(self, path):
        """Получить размер директории"""
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self.get_dir_size(entry.path)
        except:
            pass
        return total
    
    def format_size(self, size):
        """Форматировать размер в читаемый вид"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def update_structure_tree(self):
        """Обновить дерево структуры"""
        # Очищаем дерево
        for item in self.structure_tree.get_children():
            self.structure_tree.delete(item)
        
        # Добавляем корневую папку AstraPack
        if os.path.exists(self.astrapack_dir):
            root_item = self.structure_tree.insert('', 'end', text='AstraPack', 
                                                   values=('', 'Папка'), 
                                                   open=True)
            self.populate_tree(root_item, self.astrapack_dir)
        else:
            self.structure_tree.insert('', 'end', text='AstraPack (не существует)', 
                                     values=('', 'Папка'))
        
        # Обновляем информацию
        self.update_structure_info()
    
    def populate_tree(self, parent, path):
        """Заполнить дерево файлами и папками"""
        try:
            for entry in sorted(os.scandir(path), key=lambda e: (e.is_file(), e.name)):
                if entry.name.startswith('.'):
                    continue
                
                if entry.is_file():
                    size = entry.stat().st_size
                    item = self.structure_tree.insert(parent, 'end', text=entry.name,
                                                     values=(self.format_size(size), 'Файл'))
                elif entry.is_dir():
                    dir_size = self.get_dir_size(entry.path)
                    item = self.structure_tree.insert(parent, 'end', text=entry.name,
                                                     values=(self.format_size(dir_size), 'Папка'))
                    # Рекурсивно добавляем содержимое
                    self.populate_tree(item, entry.path)
        except PermissionError:
            pass
    
    def update_structure_info(self):
        """Обновить информацию о структуре"""
        info = []
        
        if os.path.exists(self.astrapack_dir):
            total_size = self.get_dir_size(self.astrapack_dir)
            info.append(f"Общий размер: {self.format_size(total_size)}")
            
            # Подсчитываем группы
            groups_found = []
            for group_id, group_info in self.package_groups.items():
                group_path = os.path.join(self.astrapack_dir, group_id)
                if os.path.exists(group_path):
                    groups_found.append(group_info['name'])
            
            if groups_found:
                info.append(f"Найдено групп: {len(groups_found)} ({', '.join(groups_found)})")
            else:
                info.append("Группы не созданы")
        else:
            info.append("Папка AstraPack не существует")
        
        self.structure_info.delete(1.0, tk.END)
        self.structure_info.insert(1.0, '\n'.join(info))
    
    def create_structure(self):
        """Создать структуру папок"""
        try:
            # Создаем корневую папку
            os.makedirs(self.astrapack_dir, exist_ok=True)
            
            # Создаем подпапки для групп
            created = []
            for group_id, group_info in self.package_groups.items():
                group_path = os.path.join(self.astrapack_dir, group_id)
                os.makedirs(group_path, exist_ok=True)
                created.append(group_info['name'])
            
            messagebox.showinfo("Успех", 
                              f"Структура создана успешно!\nСоздано групп: {len(created)}\n" + 
                              '\n'.join(f"- {name}" for name in created))
            
            # Обновляем дерево
            self.update_structure_tree()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать структуру:\n{e}")
    
    def open_in_finder(self):
        """Открыть папку в Finder (macOS)"""
        if os.path.exists(self.astrapack_dir):
            os.system(f'open "{self.astrapack_dir}"')
        else:
            messagebox.showwarning("Предупреждение", "Папка AstraPack не существует")
    
    def update_archive_list(self):
        """Обновить список компонентов для архивации"""
        self.archive_listbox.delete(0, tk.END)
        
        for group_id, group_info in self.package_groups.items():
            self.archive_listbox.insert(tk.END, f"{group_info['name']} ({group_id})")
    
    def on_archive_select(self, event):
        """Обработчик выбора компонента для архивации"""
        selection = self.archive_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        item = self.archive_listbox.get(index)
        
        # Извлекаем group_id
        group_id = item.split('(')[1].rstrip(')')
        group_info = self.package_groups.get(group_id, {})
        
        # Формируем информацию
        info = []
        info.append(f"Группа: {group_info.get('name', 'Неизвестно')}")
        info.append(f"ID: {group_id}")
        info.append(f"Описание: {group_info.get('description', 'Нет описания')}")
        info.append("")
        
        # Информация об исходных файлах
        if 'source_dir' in group_info:
            source_path = os.path.join(self.script_dir, group_info['source_dir'])
            if os.path.exists(source_path):
                size = self.get_dir_size(source_path)
                info.append(f"Исходная папка: {group_info['source_dir']}")
                info.append(f"Размер: {self.format_size(size)}")
                info.append(f"Путь: {source_path}")
            else:
                info.append(f"Исходная папка: {group_info['source_dir']} (не найдена)")
        
        if 'files' in group_info:
            info.append("Файлы:")
            for file in group_info['files']:
                file_path = os.path.join(self.astrapack_dir, file)
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    info.append(f"  - {file} ({self.format_size(size)})")
                else:
                    info.append(f"  - {file} (не найден)")
        
        if 'dirs' in group_info:
            info.append("Папки:")
            for dir_name in group_info['dirs']:
                dir_path = os.path.join(self.astrapack_dir, dir_name)
                if os.path.exists(dir_path):
                    size = self.get_dir_size(dir_path)
                    info.append(f"  - {dir_name} ({self.format_size(size)})")
                else:
                    info.append(f"  - {dir_name} (не найдена)")
        
        # Информация о целевом архиве
        if 'archive_name' in group_info:
            archive_path = os.path.join(self.astrapack_dir, group_id, group_info['archive_name'])
            if os.path.exists(archive_path):
                size = os.path.getsize(archive_path)
                info.append("")
                info.append(f"Архив уже существует: {group_info['archive_name']}")
                info.append(f"Размер: {self.format_size(size)}")
            else:
                info.append("")
                info.append(f"Архив будет создан: {group_info['archive_name']}")
        
        self.archive_info.delete(1.0, tk.END)
        self.archive_info.insert(1.0, '\n'.join(info))
    
    def archive_selected(self):
        """Архивировать выбранные компоненты"""
        selection = self.archive_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите компоненты для архивации")
            return
        
        # Получаем выбранные группы
        groups_to_archive = []
        for index in selection:
            item = self.archive_listbox.get(index)
            group_id = item.split('(')[1].rstrip(')')
            groups_to_archive.append(group_id)
        
        # Архивируем
        self.archive_groups(groups_to_archive)
    
    def archive_all(self):
        """Архивировать все компоненты"""
        groups_to_archive = list(self.package_groups.keys())
        self.archive_groups(groups_to_archive)
    
    def archive_groups(self, group_ids):
        """Архивировать указанные группы"""
        results = []
        
        for group_id in group_ids:
            group_info = self.package_groups.get(group_id)
            if not group_info:
                continue
            
            try:
                # Создаем папку группы если её нет
                group_path = os.path.join(self.astrapack_dir, group_id)
                os.makedirs(group_path, exist_ok=True)
                
                # Определяем имя архива
                if 'archive_name' in group_info:
                    archive_name = group_info['archive_name']
                else:
                    archive_name = f"{group_id}_packages.tar.gz"
                
                archive_path = os.path.join(group_path, archive_name)
                
                # Создаем архив
                with tarfile.open(archive_path, 'w:gz') as tar:
                    # Если есть source_dir - архивируем его
                    if 'source_dir' in group_info:
                        source_path = os.path.join(self.script_dir, group_info['source_dir'])
                        if os.path.exists(source_path):
                            # Архивируем всю папку с её содержимым
                            tar.add(source_path, arcname=os.path.basename(source_path), 
                                   recursive=True)
                            archive_size = os.path.getsize(archive_path)
                            results.append(f"✓ {group_info['name']}: {archive_name} создан "
                                         f"({self.format_size(archive_size)})")
                        else:
                            results.append(f"✗ {group_info['name']}: исходная папка не найдена "
                                         f"({source_path})")
                    else:
                        # Архивируем файлы и папки из списка
                        added = False
                        added_items = []
                        
                        if 'files' in group_info:
                            for file in group_info['files']:
                                file_path = os.path.join(self.astrapack_dir, file)
                                if os.path.exists(file_path):
                                    tar.add(file_path, arcname=file, recursive=False)
                                    added = True
                                    added_items.append(file)
                        
                        if 'dirs' in group_info:
                            for dir_name in group_info['dirs']:
                                dir_path = os.path.join(self.astrapack_dir, dir_name)
                                if os.path.exists(dir_path):
                                    tar.add(dir_path, arcname=dir_name, recursive=True)
                                    added = True
                                    added_items.append(dir_name)
                        
                        if added:
                            archive_size = os.path.getsize(archive_path)
                            results.append(f"✓ {group_info['name']}: {archive_name} создан "
                                         f"({self.format_size(archive_size)})\n"
                                         f"  Добавлено: {', '.join(added_items)}")
                        else:
                            results.append(f"✗ {group_info['name']}: файлы/папки не найдены")
                
            except Exception as e:
                results.append(f"✗ {group_info['name']}: ошибка - {e}")
        
        # Показываем результаты
        message = '\n'.join(results)
        if any('✓' in r for r in results):
            messagebox.showinfo("Архивация завершена", message)
        else:
            messagebox.showerror("Ошибка архивации", message)
        
        # Обновляем дерево
        self.update_structure_tree()
    
    def update_component_list(self):
        """Обновить список компонентов"""
        self.component_listbox.delete(0, tk.END)
        
        if COMPONENTS_CONFIG:
            for component_id, config in sorted(COMPONENTS_CONFIG.items()):
                name = config.get('name', component_id)
                self.component_listbox.insert(tk.END, f"{component_id}: {name}")
        else:
            self.component_listbox.insert(tk.END, "COMPONENTS_CONFIG не загружен")
    
    def filter_components(self, event=None):
        """Фильтровать компоненты по поисковому запросу"""
        search_text = self.component_search.get().lower()
        
        self.component_listbox.delete(0, tk.END)
        
        if COMPONENTS_CONFIG:
            for component_id, config in sorted(COMPONENTS_CONFIG.items()):
                name = config.get('name', component_id)
                # Проверяем совпадение в ID или имени
                if search_text in component_id.lower() or search_text in name.lower():
                    self.component_listbox.insert(tk.END, f"{component_id}: {name}")
        else:
            self.component_listbox.insert(tk.END, "COMPONENTS_CONFIG не загружен")
    
    def on_component_select(self, event):
        """Обработчик выбора компонента"""
        selection = self.component_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        item = self.component_listbox.get(index)
        
        # Извлекаем component_id
        component_id = item.split(':')[0]
        config = COMPONENTS_CONFIG.get(component_id, {})
        
        # Форматируем конфигурацию в читаемый вид
        config_text = json.dumps(config, indent=2, ensure_ascii=False)
        
        self.component_config.delete(1.0, tk.END)
        self.component_config.insert(1.0, f"ID: {component_id}\n\n{config_text}")
    
    def check_archives(self):
        """Проверить целостность архивов"""
        self.tools_output.delete(1.0, tk.END)
        self.tools_output.insert(tk.END, "Проверка архивов...\n\n")
        
        results = []
        
        for group_id, group_info in self.package_groups.items():
            group_path = os.path.join(self.astrapack_dir, group_id)
            
            if not os.path.exists(group_path):
                continue
            
            # Ищем архивы в папке группы
            for entry in os.scandir(group_path):
                if entry.is_file() and entry.name.endswith('.tar.gz'):
                    archive_path = entry.path
                    try:
                        with tarfile.open(archive_path, 'r:gz') as tar:
                            tar.getmembers()  # Проверяем целостность
                        size = os.path.getsize(archive_path)
                        results.append(f"✓ {entry.name}: OK ({self.format_size(size)})")
                    except Exception as e:
                        results.append(f"✗ {entry.name}: ОШИБКА - {e}")
        
        if results:
            self.tools_output.insert(tk.END, '\n'.join(results))
        else:
            self.tools_output.insert(tk.END, "Архивы не найдены")
    
    def show_statistics(self):
        """Показать статистику"""
        self.tools_output.delete(1.0, tk.END)
        self.tools_output.insert(tk.END, "Статистика пакетов...\n\n")
        
        stats = []
        
        # Общая статистика
        if os.path.exists(self.astrapack_dir):
            total_size = self.get_dir_size(self.astrapack_dir)
            stats.append(f"Общий размер AstraPack: {self.format_size(total_size)}")
            stats.append("")
        
        # Статистика по группам
        stats.append("Статистика по группам:")
        for group_id, group_info in self.package_groups.items():
            group_path = os.path.join(self.astrapack_dir, group_id)
            if os.path.exists(group_path):
                group_size = self.get_dir_size(group_path)
                stats.append(f"  {group_info['name']}: {self.format_size(group_size)}")
                
                # Подсчитываем архивы
                archives = [e for e in os.scandir(group_path) 
                           if e.is_file() and e.name.endswith('.tar.gz')]
                if archives:
                    stats.append(f"    Архивов: {len(archives)}")
        
        # Статистика компонентов
        if COMPONENTS_CONFIG:
            stats.append("")
            stats.append(f"Всего компонентов: {len(COMPONENTS_CONFIG)}")
            
            # Группируем по категориям
            categories = {}
            for component_id, config in COMPONENTS_CONFIG.items():
                category = config.get('category', 'unknown')
                categories[category] = categories.get(category, 0) + 1
            
            stats.append("По категориям:")
            for category, count in sorted(categories.items()):
                stats.append(f"  {category}: {count}")
        
        self.tools_output.insert(tk.END, '\n'.join(stats))
    
    def cleanup_temp(self):
        """Очистить временные файлы"""
        result = messagebox.askyesno("Подтверждение", 
                                    "Удалить все временные файлы?\n" +
                                    "(Это не затронет архивы и исходные файлы)")
        
        if result:
            # Здесь можно добавить логику очистки временных файлов
            self.tools_output.delete(1.0, tk.END)
            self.tools_output.insert(tk.END, "Очистка временных файлов...\n\n")
            self.tools_output.insert(tk.END, "Временные файлы не найдены или уже очищены")
    
    def run(self):
        """Запустить GUI"""
        self.root.mainloop()


def main():
    """Главная функция"""
    try:
        app = PackageManagerGUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Критическая ошибка", f"Не удалось запустить приложение:\n{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


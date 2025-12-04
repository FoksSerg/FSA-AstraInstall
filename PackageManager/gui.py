#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инструмент управления пакетами для FSA-AstraInstall
GUI инструмент для формирования архивов и структуры компонентов
Версия: V3.1.155 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

# Версия приложения
APP_VERSION = "V3.1.155 (2025.12.03)"

import os
import sys
import shutil
import tarfile
import threading
import subprocess
import time
import tempfile
import signal
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
from pathlib import Path
import json
from datetime import datetime

# Вспомогательные функции для работы с конфигурациями в архивах
def load_components_from_archives(astrapack_dir):
    """
    Загрузить конфигурации компонентов из всех архивов в AstraPack
    
    Args:
        astrapack_dir: Путь к директории AstraPack
    
    Returns:
        dict: Словарь {component_id: config} со всеми конфигурациями из архивов
        list: Список метаданных архивов
    """
    loaded_configs = {}
    archive_metadata = []
    
    if not os.path.exists(astrapack_dir):
        return loaded_configs, archive_metadata
    
    # Сканируем все архивы в AstraPack
    for root, dirs, files in os.walk(astrapack_dir):
        for file in files:
            if file.endswith('.tar.gz'):
                archive_path = os.path.join(root, file)
                try:
                    config_data = extract_config_from_archive(archive_path)
                    if config_data:
                        # Объединяем конфигурации (приоритет у более новых архивов)
                        components = config_data.get('components', {})
                        for comp_id, comp_config in components.items():
                            # Если компонент уже есть, проверяем дату создания
                            if comp_id in loaded_configs:
                                existing_meta = next(
                                    (m for m in archive_metadata if comp_id in m.get('components', [])),
                                    None
                                )
                                new_meta = config_data.get('metadata', {})
                                if existing_meta and new_meta.get('created', '') > existing_meta.get('created', ''):
                                    loaded_configs[comp_id] = comp_config
                            else:
                                loaded_configs[comp_id] = comp_config
                        
                        archive_metadata.append(config_data.get('metadata', {}))
                except Exception as e:
                    print(f"Ошибка загрузки конфигурации из {file}: {e}")
    
    return loaded_configs, archive_metadata

def extract_config_from_archive(archive_path):
    """
    Извлечь конфигурацию из архива без полной распаковки
    
    Args:
        archive_path: Путь к архиву .tar.gz
    
    Returns:
        dict: Конфигурация из архива или None
    """
    try:
        with tarfile.open(archive_path, 'r:gz') as tar:
            # Ищем файл конфигурации
            config_member = None
            for member in tar.getmembers():
                if member.name == '.components_config.json' or member.name.endswith('/.components_config.json'):
                    config_member = member
                    break
            
            if config_member:
                # Извлекаем только файл конфигурации
                config_file = tar.extractfile(config_member)
                if config_file:
                    config_data = json.loads(config_file.read().decode('utf-8'))
                    return config_data
    except Exception as e:
        print(f"Ошибка чтения архива {archive_path}: {e}")
    
    return None

def find_archive_for_component(component_id, astrapack_dir):
    """
    Найти архив, содержащий конфигурацию указанного компонента
    
    Args:
        component_id: ID компонента
        astrapack_dir: Путь к директории AstraPack
    
    Returns:
        str: Путь к архиву или None
    """
    if not os.path.exists(astrapack_dir):
        return None
    
    for root, dirs, files in os.walk(astrapack_dir):
        for file in files:
            if file.endswith('.tar.gz'):
                archive_path = os.path.join(root, file)
                config_data = extract_config_from_archive(archive_path)
                if config_data and component_id in config_data.get('components', {}):
                    return archive_path
    
    return None

def load_components_from_filesystem(components_dir):
    """
    Загрузить компоненты из файловой структуры (Components/)
    
    Args:
        components_dir: Путь к директории Components/
    
    Returns:
        dict: Словарь {component_id: {'config': config, 'path': path, 'archive_path': archive_path}}
    """
    components = {}
    
    if not os.path.exists(components_dir):
        return components
    
    # Сканируем все подпапки
    for item in os.listdir(components_dir):
        component_path = os.path.join(components_dir, item)
        
        if not os.path.isdir(component_path):
            continue
        
        # Ищем .component.json
        config_path = os.path.join(component_path, '.component.json')
        if not os.path.exists(config_path):
            continue
        
        try:
            # Загружаем конфигурацию
            with open(config_path, 'r', encoding='utf-8') as f:
                component_data = json.load(f)
            
            component_id = component_data.get('component_id')
            if not component_id:
                continue
            
            # Получаем путь к архиву
            archive_info = component_data.get('archive', {})
            archive_name = archive_info.get('archive_name')
            archive_path = None
            
            if archive_name:
                archive_path = os.path.join(component_path, archive_name)
                if not os.path.exists(archive_path):
                    archive_path = None
            
            # Сохраняем компонент
            components[component_id] = {
                'config': component_data.get('component', {}),
                'metadata': component_data.get('metadata', {}),
                'path': component_path,
                'archive_path': archive_path,
                'source': 'filesystem'
            }
            
        except Exception as e:
            print(f"Ошибка загрузки компонента {item}: {e}")
    
    return components

def load_bundles_from_filesystem(bundles_dir):
    """
    Загрузить сборки из файловой структуры (Bundles/)
    
    Args:
        bundles_dir: Путь к директории Bundles/
    
    Returns:
        dict: Словарь {bundle_id: {'config': config, 'components': components, 'path': path, 'archive_path': archive_path}}
    """
    bundles = {}
    
    if not os.path.exists(bundles_dir):
        return bundles
    
    # Сканируем все подпапки
    for item in os.listdir(bundles_dir):
        bundle_path = os.path.join(bundles_dir, item)
        
        if not os.path.isdir(bundle_path):
            continue
        
        # Ищем .bundle.json
        config_path = os.path.join(bundle_path, '.bundle.json')
        if not os.path.exists(config_path):
            continue
        
        try:
            # Загружаем конфигурацию
            with open(config_path, 'r', encoding='utf-8') as f:
                bundle_data = json.load(f)
            
            bundle_id = bundle_data.get('bundle_id')
            if not bundle_id:
                continue
            
            # Получаем путь к архиву
            archive_info = bundle_data.get('archive', {})
            archive_name = archive_info.get('archive_name')
            archive_path = None
            
            if archive_name:
                archive_path = os.path.join(bundle_path, archive_name)
                if not os.path.exists(archive_path):
                    archive_path = None
            
            # Сохраняем сборку
            bundles[bundle_id] = {
                'config': bundle_data.get('bundle', {}),
                'components': bundle_data.get('components', []),
                'dependencies': bundle_data.get('dependencies', {}),
                'install_order': bundle_data.get('install_order', []),
                'metadata': bundle_data.get('metadata', {}),
                'path': bundle_path,
                'archive_path': archive_path,
                'source': 'filesystem'
            }
            
        except Exception as e:
            print(f"Ошибка загрузки сборки {item}: {e}")
    
    return bundles

def build_file_tree(root_path, max_depth=10, current_depth=0):
    """
    Построить дерево файловой системы
    
    Args:
        root_path: Корневой путь
        max_depth: Максимальная глубина рекурсии
        current_depth: Текущая глубина
    
    Returns:
        dict: Структура дерева или None
    """
    if current_depth >= max_depth:
        return None
    
    if not os.path.exists(root_path):
        return None
    
    tree = {
        'name': os.path.basename(root_path) or root_path,
        'type': 'directory' if os.path.isdir(root_path) else 'file',
        'path': root_path,
        'children': []
    }
    
    if os.path.isdir(root_path):
        try:
            for item in sorted(os.listdir(root_path)):
                # Пропускаем скрытые файлы (кроме конфигурационных)
                if item.startswith('.') and item not in ['.component.json', '.bundle.json', '.astrapack_index.json']:
                    continue
                
                item_path = os.path.join(root_path, item)
                
                if os.path.isdir(item_path):
                    child_tree = build_file_tree(item_path, max_depth, current_depth + 1)
                    if child_tree:
                        tree['children'].append(child_tree)
                elif item.endswith('.tar.gz') or item in ['.component.json', '.bundle.json']:
                    try:
                        size = os.path.getsize(item_path) if os.path.exists(item_path) else 0
                        tree['children'].append({
                            'name': item,
                            'type': 'file',
                            'path': item_path,
                            'size': size
                        })
                    except (OSError, PermissionError):
                        pass
        except (PermissionError, OSError):
            pass
    
    return tree

def auto_detect_wine_templates(components_config):
    """
    Автоматически обнаружить все шаблоны Wine приложений
    
    Args:
        components_config: Словарь конфигураций компонентов
    
    Returns:
        list: Список ID шаблонов
        dict: Словарь {group_name: [template_ids]} для группировки
    """
    templates = []
    grouped_templates = {}
    
    for component_id, config in components_config.items():
        # Проверяем, является ли компонент шаблоном
        if config.get('template') == True and config.get('category') == 'wine_application_template':
            templates.append(component_id)
            
            # Проверяем наличие групп для группировки
            template_groups = config.get('template_groups', [])
            if template_groups:
                for group in template_groups:
                    if group not in grouped_templates:
                        grouped_templates[group] = []
                    grouped_templates[group].append(component_id)
    
    return templates, grouped_templates

def get_all_wineprefixes(components_config):
    """
    Получить список всех доступных wineprefix из конфигураций
    
    Args:
        components_config: Словарь конфигураций компонентов
    
    Returns:
        list: Список ID wineprefix
    """
    wineprefixes = []
    
    for component_id, config in components_config.items():
        # Ищем компоненты с категорией wine_environment (это wineprefix)
        if config.get('category') == 'wine_environment':
            # Проверяем наличие wineprefix_path или check_method == 'wineprefix'
            if config.get('wineprefix_path') or config.get('check_method') == 'wineprefix':
                wineprefixes.append(component_id)
    
    return wineprefixes

def auto_create_wine_template_packages(components_config):
    """
    Автоматически создать пакеты шаблонов Wine приложений
    
    Args:
        components_config: Словарь конфигураций компонентов (будет модифицирован)
    
    Returns:
        list: Список ID созданных пакетов
    """
    created_packages = []
    
    # Обнаруживаем шаблоны
    templates, grouped_templates = auto_detect_wine_templates(components_config)
    
    if not templates:
        return created_packages
    
    # Получаем список всех wineprefix
    wineprefixes = get_all_wineprefixes(components_config)
    
    # Создаем универсальный пакет со всеми шаблонами
    universal_package_id = 'wine-templates-universal-package'
    if universal_package_id not in components_config:
        universal_package = {
            'name': 'Пакет шаблонов Wine приложений',
            'category': 'package',
            'package_type': 'wine_templates',
            'package_templates': templates.copy(),
            'target_wineprefixes': wineprefixes.copy(),
            'auto_generated': True,
            'version': '1.0.0',
            'description': 'Универсальный набор шаблонов Wine приложений для установки в любую конфигурацию Wine',
            'sort_order': 0,
            'gui_selectable': True,
            'dependencies': []
        }
        components_config[universal_package_id] = universal_package
        created_packages.append(universal_package_id)
        print(f"Создан универсальный пакет шаблонов: {universal_package_id} ({len(templates)} шаблонов)")
    
    # Создаем специализированные пакеты по группам
    for group_name, group_templates in grouped_templates.items():
        if not group_templates:
            continue
        
        # Формируем ID пакета из имени группы
        package_id = f'wine-templates-{group_name}-package'
        
        # Пропускаем, если пакет уже существует
        if package_id in components_config:
            continue
        
        # Создаем пакет
        package = {
            'name': f'Wine приложения: {group_name.capitalize()}',
            'category': 'package',
            'package_type': 'wine_templates',
            'package_templates': group_templates.copy(),
            'target_wineprefixes': wineprefixes.copy(),
            'auto_generated': True,
            'package_category': group_name,
            'version': '1.0.0',
            'description': f'Набор шаблонов Wine приложений: {group_name}',
            'sort_order': 1,
            'gui_selectable': True,
            'dependencies': []
        }
        components_config[package_id] = package
        created_packages.append(package_id)
        print(f"Создан специализированный пакет: {package_id} ({len(group_templates)} шаблонов)")
    
    return created_packages

# Импортируем COMPONENTS_CONFIG из основного скрипта
# Приоритет: файловая структура > архивы > astra_automation.py
COMPONENTS_CONFIG = {}
COMPONENTS_DATA = {}  # Дополнительные данные о компонентах (пути, архивы)
BUNDLES_DATA = {}     # Данные о сборках

# Получаем путь к корню проекта (на уровень выше PackageManager/)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)  # Корень проекта
astrapack_dir = os.path.join(project_dir, "AstraPack")

# 1. НОВЫЙ СПОСОБ: Загрузка из файловой структуры (Components/)
components_dir = os.path.join(astrapack_dir, 'Components')
if os.path.exists(components_dir):
    try:
        filesystem_components = load_components_from_filesystem(components_dir)
        for component_id, component_data in filesystem_components.items():
            COMPONENTS_CONFIG[component_id] = component_data['config']
            COMPONENTS_DATA[component_id] = component_data
        print(f"Загружено {len(filesystem_components)} компонентов из файловой структуры")
    except Exception as e:
        print(f"Ошибка загрузки из файловой структуры: {e}")

# 2. СРЕДНИЙ СПОСОБ: Загрузка из архивов (существующий способ)
archive_configs = {}
try:
    archive_configs, archive_metadata = load_components_from_archives(astrapack_dir)
    # Добавляем только те компоненты, которых нет в файловой структуре
    added_from_archives = 0
    for comp_id, comp_config in archive_configs.items():
        if comp_id not in COMPONENTS_CONFIG:
            COMPONENTS_CONFIG[comp_id] = comp_config
            COMPONENTS_DATA[comp_id] = {'source': 'archive', 'config': comp_config}
            added_from_archives += 1
    if added_from_archives > 0:
        print(f"Загружено {added_from_archives} компонентов из архивов")
except Exception as e:
    print(f"Ошибка загрузки из архивов: {e}")
    archive_configs = {}

# 3. Загрузка сборок из файловой структуры
bundles_dir = os.path.join(astrapack_dir, 'Bundles')
if os.path.exists(bundles_dir):
    try:
        BUNDLES_DATA = load_bundles_from_filesystem(bundles_dir)
        print(f"Загружено {len(BUNDLES_DATA)} сборок из файловой структуры")
    except Exception as e:
        print(f"Ошибка загрузки сборок: {e}")

# 3. FALLBACK: Загрузка из astra_automation.py (старый способ, для обратной совместимости)
USE_LEGACY_FALLBACK = True  # Флаг для отключения fallback в будущем
if USE_LEGACY_FALLBACK:
    try:
        sys.path.insert(0, project_dir)
        import importlib.util
        astra_automation_path = os.path.join(project_dir, 'astra_automation.py')
        
        if os.path.exists(astra_automation_path):
            spec = importlib.util.spec_from_file_location("astra_automation", astra_automation_path)
            if spec and spec.loader:
                astra_module = importlib.util.module_from_spec(spec)
                try:
                    # Загружаем модуль (может вызвать ошибки из-за зависимостей)
                    spec.loader.exec_module(astra_module)
                    if hasattr(astra_module, 'COMPONENTS_CONFIG'):
                        astra_config = astra_module.COMPONENTS_CONFIG
                        # Добавляем только те компоненты, которых нет в новых способах
                        added_count = 0
                        for comp_id, comp_config in astra_config.items():
                            if comp_id not in COMPONENTS_CONFIG:
                                COMPONENTS_CONFIG[comp_id] = comp_config
                                COMPONENTS_DATA[comp_id] = {'source': 'astra_automation', 'config': comp_config}
                                added_count += 1
                        if added_count > 0:
                            print(f"⚠️  Загружено {added_count} компонентов из astra_automation.py (fallback)")
                            print(f"   Рекомендуется мигрировать эти компоненты в файловую структуру")
                    
                    # Автоматически создаем пакеты шаблонов Wine приложений
                    try:
                        created_packages = auto_create_wine_template_packages(COMPONENTS_CONFIG)
                        if created_packages:
                            print(f"Автоматически создано {len(created_packages)} пакетов шаблонов Wine")
                    except Exception as package_error:
                        print(f"Ошибка создания пакетов шаблонов: {package_error}")
                        import traceback
                        traceback.print_exc()
                except Exception as import_error:
                    # Если импорт не удался из-за зависимостей, используем fallback
                    print(f"Прямой импорт не удался (это нормально): {import_error}")
                    print("Используем fallback метод...")
                    
                    # Fallback: читаем файл и извлекаем COMPONENTS_CONFIG
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
                                astra_config = namespace.get('COMPONENTS_CONFIG', {})
                                # Добавляем только те компоненты, которых нет в новых способах
                                added_count = 0
                                for comp_id, comp_config in astra_config.items():
                                    if comp_id not in COMPONENTS_CONFIG:
                                        COMPONENTS_CONFIG[comp_id] = comp_config
                                        COMPONENTS_DATA[comp_id] = {'source': 'astra_automation', 'config': comp_config}
                                        added_count += 1
                                if added_count > 0:
                                    print(f"Добавлено {added_count} компонентов из astra_automation.py (fallback)")
                            except Exception as e:
                                print(f"Ошибка извлечения COMPONENTS_CONFIG: {e}")
        else:
            print(f"Файл не найден: {astra_automation_path}")
    except Exception as e:
        print(f"Ошибка загрузки COMPONENTS_CONFIG из astra_automation.py: {e}")

print(f"Итого загружено компонентов: {len(COMPONENTS_CONFIG)}")

# Автоматически создаем пакеты шаблонов Wine приложений после загрузки всех конфигураций
try:
    created_packages = auto_create_wine_template_packages(COMPONENTS_CONFIG)
    if created_packages:
        print(f"Автоматически создано {len(created_packages)} пакетов шаблонов Wine")
except Exception as package_error:
    print(f"Ошибка создания пакетов шаблонов: {package_error}")
    import traceback
    traceback.print_exc()

def get_component_field(component_id, field_name, default=None):
    """
    Получает значение поля компонента по ID
    
    Args:
        component_id: Строковый ID компонента
        field_name: Имя поля ('name', 'dependencies', 'sort_order', и т.д.)
        default: Значение по умолчанию, если поле не найдено
    
    Returns:
        Значение поля или default
    """
    if component_id not in COMPONENTS_CONFIG:
        return default
    return COMPONENTS_CONFIG[component_id].get(field_name, default)

def get_component_data(component_id):
    """
    Получает всю конфигурацию компонента по ID
    
    Args:
        component_id: Строковый ID компонента
    
    Returns:
        dict: Конфигурация компонента или None
    """
    return COMPONENTS_CONFIG.get(component_id)

# ============================================================================
# ФУНКЦИИ ВОРКЕРА ДЛЯ СОЗДАНИЯ АРХИВОВ В ОТДЕЛЬНОМ ПРОЦЕССЕ
# ============================================================================

def archive_worker_update_progress(progress_file, progress, status, current_file=None, elapsed=0):
    """Обновить файл прогресса (встроенная функция воркера)"""
    try:
        progress_data = {
            'progress': progress,
            'status': status,
            'current_file': current_file,
            'elapsed': elapsed,
            'timestamp': time.time()
        }
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Ошибка обновления прогресса: {e}", file=sys.stderr)

def archive_worker_create_archive(config_file, progress_file):
    """Создать архив на основе конфигурации (встроенная функция воркера)"""
    cancelled = [False]  # Используем список для изменения в обработчике сигнала
    
    def signal_handler(signum, frame):
        """Обработчик сигнала отмены"""
        cancelled[0] = True
        print(f"[INFO] Получен сигнал отмены", file=sys.stderr)
    
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Загружаем конфигурацию
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        archive_path = config['archive_path']
        items_to_archive = config['items_to_archive']
        temp_dir = config.get('temp_dir')
        group_id = config.get('group_id')
        group_name = config.get('group_name', 'Unknown')
        archive_name = config.get('archive_name')
        
        archive_worker_update_progress(progress_file, 0, "Начало архивации", None, 0)
        
        # Создаем временную директорию если не указана
        if not temp_dir:
            temp_dir = os.path.join(os.path.dirname(archive_path), '.temp_archive')
        
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Определяем общий корень для обрезки путей
            def find_common_root(paths):
                """Найти общий корень для списка путей"""
                if not paths:
                    return None
                
                # Нормализуем все пути
                normalized_paths = [os.path.normpath(p) for p in paths]
                
                # Находим общий префикс
                common = os.path.commonpath(normalized_paths) if len(normalized_paths) > 1 else os.path.dirname(normalized_paths[0])
                
                # Если общий путь - это сам элемент, берем родительскую директорию
                if common in normalized_paths:
                    common = os.path.dirname(common)
                
                return common
            
            # Собираем все пути для определения общего корня
            all_paths = [item_path for item_path, _ in items_to_archive if os.path.exists(item_path)]
            common_root = find_common_root(all_paths) if all_paths else None
            
            # Функция для обрезки корня из пути
            def strip_root(path, root):
                """Обрезать корень из пути"""
                if not root:
                    return path
                path_norm = os.path.normpath(path)
                root_norm = os.path.normpath(root)
                if path_norm.startswith(root_norm):
                    # Обрезаем корень + разделитель
                    relative = os.path.relpath(path_norm, root_norm)
                    return relative
                return os.path.basename(path)
            
            # Подготавливаем элементы для архивации
            total_items = len(items_to_archive)
            start_time = time.time()
            
            # Словарь для отслеживания созданных директорий (для пустых папок)
            created_dirs = set()
            
            for idx, (item_path, arcname) in enumerate(items_to_archive):
                if cancelled[0]:
                    archive_worker_update_progress(progress_file, 0, "Отменено пользователем", None, int(time.time() - start_time))
                    return False
                
                if os.path.exists(item_path):
                    # Обрезаем корень дерева из arcname если нужно
                    if common_root and os.path.isabs(item_path):
                        # Пересчитываем arcname с учетом обрезки корня
                        relative_path = strip_root(item_path, common_root)
                        if relative_path != os.path.basename(item_path):
                            arcname = relative_path
                    
                    target_path = os.path.join(temp_dir, arcname)
                    
                    # Создаем все родительские директории (включая пустые)
                    parent_dir = os.path.dirname(target_path)
                    if parent_dir and parent_dir != temp_dir:
                        # Создаем все промежуточные директории
                        parts = os.path.relpath(parent_dir, temp_dir).split(os.sep)
                        current_dir = temp_dir
                        for part in parts:
                            if part:
                                current_dir = os.path.join(current_dir, part)
                                if current_dir not in created_dirs:
                                    os.makedirs(current_dir, exist_ok=True)
                                    created_dirs.add(current_dir)
                    
                    # Удаляем существующий элемент если есть
                    if os.path.exists(target_path):
                        if os.path.isdir(target_path):
                            shutil.rmtree(target_path)
                        else:
                            os.remove(target_path)
                    
                    # Создаем символическую ссылку (быстро, не копирует данные)
                    try:
                        os.symlink(item_path, target_path)
                    except (OSError, AttributeError):
                        # Если симлинки не поддерживаются, копируем (медленнее)
                        if os.path.isdir(item_path):
                            # Копируем с сохранением структуры и пустых папок
                            def copy_tree_with_empty_dirs(src, dst):
                                """Копировать дерево включая пустые директории"""
                                os.makedirs(dst, exist_ok=True)
                                created_dirs.add(dst)
                                
                                try:
                                    for item in os.listdir(src):
                                        src_item = os.path.join(src, item)
                                        dst_item = os.path.join(dst, item)
                                        
                                        if os.path.isdir(src_item):
                                            copy_tree_with_empty_dirs(src_item, dst_item)
                                        else:
                                            shutil.copy2(src_item, dst_item)
                                except PermissionError:
                                    pass
                            
                            copy_tree_with_empty_dirs(item_path, target_path)
                        else:
                            shutil.copy2(item_path, target_path)
                    
                    # Обновляем прогресс подготовки (30% на подготовку)
                    prep_progress = ((idx + 1) / total_items) * 30
                    elapsed = int(time.time() - start_time)
                    archive_worker_update_progress(progress_file, prep_progress, 
                                                  f"Подготовка: {idx + 1}/{total_items}", 
                                                  os.path.basename(item_path), elapsed)
            
            # Создаем файл конфигурации компонентов для архива (если указан group_id)
            if group_id and 'components_config' in config:
                components_config = config['components_config']
                if components_config:
                    config_path = os.path.join(temp_dir, '.components_config.json')
                    config_data = {
                        'version': '1.0',
                        'components': components_config,
                        'metadata': {
                            'created': datetime.now().isoformat(),
                            'group_id': group_id,
                            'group_name': group_name,
                            'archive_name': archive_name or os.path.basename(archive_path),
                            'items_count': len(items_to_archive)
                        }
                    }
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # Проверяем отмену перед запуском tar
            if cancelled[0]:
                archive_worker_update_progress(progress_file, 0, "Отменено пользователем", None, int(time.time() - start_time))
                return False
            
            # Убеждаемся, что все пустые директории созданы в temp_dir
            # Проходим по всем созданным директориям и проверяем, что они существуют
            for created_dir in created_dirs:
                if not os.path.exists(created_dir):
                    os.makedirs(created_dir, exist_ok=True)
            
            # Строим команду tar из временной директории
            # Используем простой tar с точкой - он включает все файлы и директории (включая пустые)
            # Пустые директории будут включены, так как мы их явно создали выше
            tar_cmd = ['tar', '-czf', archive_path, '-C', temp_dir, '.']
            
            # Запускаем процесс tar
            process = subprocess.Popen(
                tar_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Мониторим прогресс
            tar_start_time = time.time()
            
            while process.poll() is None:
                if cancelled[0]:
                    process.terminate()
                    process.wait()
                    archive_worker_update_progress(progress_file, 0, "Отменено пользователем", None, int(time.time() - start_time))
                    return False
                
                # Обновляем прогресс архивации (30% подготовка + 70% архивация)
                elapsed = int(time.time() - start_time)
                tar_elapsed = time.time() - tar_start_time
                # Приблизительный прогресс на основе времени (предполагаем 30 секунд максимум для tar)
                estimated_progress = min(95, 30 + (tar_elapsed / 30) * 65)
                archive_worker_update_progress(progress_file, estimated_progress, 
                                              f"Архивация: {total_items} элементов", 
                                              None, elapsed)
                
                time.sleep(0.2)
            
            # Завершение
            return_code = process.wait()
            
            if return_code != 0:
                stderr = process.stderr.read().decode('utf-8', errors='ignore')
                archive_worker_update_progress(progress_file, 0, f"Ошибка: {stderr[:100]}", None, int(time.time() - start_time))
                return False
            
            # Финальное обновление
            archive_worker_update_progress(progress_file, 100, "Архивация завершена", None, int(time.time() - start_time))
            
            return True
            
        finally:
            # Удаляем временную директорию
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        archive_worker_update_progress(progress_file, 0, f"Ошибка: {str(e)}", None, 0)
        print(f"[ERROR] Ошибка создания архива: {e}", file=sys.stderr)
        return False

def archive_worker_main():
    """Главная функция воркера (для запуска через subprocess)"""
    if len(sys.argv) < 4 or sys.argv[1] != '--archive-worker':
        print("Использование: package_manager_gui.py --archive-worker <config_file> <progress_file>", file=sys.stderr)
        sys.exit(1)
    
    config_file = sys.argv[2]
    progress_file = sys.argv[3]
    
    if not os.path.exists(config_file):
        print(f"[ERROR] Файл конфигурации не найден: {config_file}", file=sys.stderr)
        sys.exit(1)
    
    success = archive_worker_create_archive(config_file, progress_file)
    sys.exit(0 if success else 1)

class PackageManagerGUI:
    """GUI инструмент для управления пакетами"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Инструмент управления пакетами FSA-AstraInstall {APP_VERSION}")
        self.root.geometry("1200x700")
        
        # Получаем директорию скрипта и корень проекта
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_dir = os.path.dirname(self.script_dir)  # Корень проекта
        self.astrapack_dir = os.path.join(self.project_dir, "AstraPack")
        
        # Список пользовательских файлов/папок для архивации
        self.custom_files = []
        
        # Пользовательские источники для элементов структуры архива
        # Формат: {group_id: {item_name: path}}
        self.custom_sources = {}
        
        # Исключенные элементы из архивации
        # Формат: {group_id: set(item_names)}
        self.excluded_items = {}
        
        # Дополнительные элементы для архивации (из других мест)
        # Формат: {group_id: [(item_path, arcname), ...]}
        self.additional_items = {}
        
        # Менеджер процессов архивации для параллельного выполнения
        self.active_archive_processes = {}  # {archive_path: {'process': process, 'progress_file': path, 'config_file': path, 'progress_window': window, 'temp_dir': path}}
        
        # Список файлов для компонента (для вкладки создания компонента)
        self.component_files = []
        
        # Список компонентов для сборки (для вкладки создания сборки)
        self.bundle_components = []
        
        # Текущий выбранный компонент для архивации
        self.current_group_id = None
        
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
        
        # Центрируем окно при открытии
        self.center_window()
        
        # Показываем окно поверх других на 3 секунды
        self.show_window_on_top()
        
        # Обновляем интерфейс для немедленного отображения
        self.root.update_idletasks()
        
        # Загружаем данные асинхронно для быстрого отображения окна
        # 1. Очищаем временные файлы в фоновом режиме
        self.root.after(50, self.cleanup_temp_files)
        
        # 2. Загружаем структуру дерева (быстро, без глубокого сканирования)
        self.root.after(100, self.update_structure_tree)
        
        # 3. Обновляем список компонентов (если загружен)
        if COMPONENTS_CONFIG:
            self.root.after(200, self.update_existing_components_list)
            # Обновляем дерево компонентов после списка
            self.root.after(300, self.update_component_tree)
        else:
            # Показываем предупреждение, если COMPONENTS_CONFIG не загружен
            self.root.after(500, lambda: messagebox.showwarning(
                "Предупреждение", 
                "COMPONENTS_CONFIG не загружен.\n" +
                "Некоторые функции могут работать некорректно.\n" +
                "Проверьте наличие файла astra_automation.py в той же директории."
            ))
    
    def get_group_folder_name(self, group_id):
        """Преобразовать group_id в имя папки с заглавной буквы"""
        folder_names = {
            'wine': 'Wine',
            'astra': 'Astra',
            'cont': 'Cont',
            'winetricks': 'Winetricks'
        }
        return folder_names.get(group_id, group_id.capitalize())
    
    def create_widgets(self):
        """Создание виджетов интерфейса"""
        # Создаем Notebook для вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладка 0: Обзор (новая, первая)
        self.create_explorer_tab()
        
        # Вкладка 1: Создание компонента
        self.create_component_creator_tab()
        
        # Вкладка 2: Компоненты
        self.create_components_tab()
        
        # Вкладка 3: Создание сборки
        self.create_bundle_creator_tab()
        
        # Вкладка 4: Структура папок
        self.create_structure_tab()
        
        # Вкладка 5: Архивация
        self.create_archive_tab()
        
        # Вкладка 6: Инструменты
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
        
        # Привязываем обработчик разворачивания для архивов
        self.structure_tree.bind('<<TreeviewOpen>>', self.on_tree_open)
        
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
        
        # Секция пользовательских файлов
        custom_frame = ttk.LabelFrame(left_frame, text="Дополнительные файлы/папки")
        custom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки добавления
        custom_buttons = ttk.Frame(custom_frame)
        custom_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(custom_buttons, text="Добавить файл", 
                  command=self.add_custom_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(custom_buttons, text="Добавить папку", 
                  command=self.add_custom_dir).pack(side=tk.LEFT, padx=2)
        ttk.Button(custom_buttons, text="Удалить", 
                  command=self.remove_custom_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(custom_buttons, text="Очистить", 
                  command=self.clear_custom_items).pack(side=tk.LEFT, padx=2)
        
        # Список пользовательских файлов
        custom_list_frame = ttk.Frame(custom_frame)
        custom_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar_custom = ttk.Scrollbar(custom_list_frame)
        scrollbar_custom.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.custom_listbox = tk.Listbox(custom_list_frame, yscrollcommand=scrollbar_custom.set,
                                         selectmode=tk.SINGLE)
        self.custom_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_custom.config(command=self.custom_listbox.yview)
        
        # Правая панель: структура архива
        right_frame = ttk.LabelFrame(frame, text="Структура архива")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Информация о компоненте
        info_label = ttk.Label(right_frame, text="Выберите компонент для просмотра структуры")
        info_label.pack(padx=5, pady=5)
        
        # Дерево структуры архива
        tree_frame = ttk.Frame(right_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar_tree = ttk.Scrollbar(tree_frame)
        scrollbar_tree.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.archive_structure_tree = ttk.Treeview(tree_frame, yscrollcommand=scrollbar_tree.set,
                                                   columns=('source', 'status'), show='tree headings')
        self.archive_structure_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_tree.config(command=self.archive_structure_tree.yview)
        
        # Настройка колонок
        self.archive_structure_tree.heading('#0', text='Элемент')
        self.archive_structure_tree.heading('source', text='Источник')
        self.archive_structure_tree.heading('status', text='Статус')
        
        self.archive_structure_tree.column('#0', width=200)
        self.archive_structure_tree.column('source', width=300)
        self.archive_structure_tree.column('status', width=150)
        
        # Кнопки управления элементами структуры
        structure_buttons = ttk.Frame(right_frame)
        structure_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(structure_buttons, text="Исключить выбранные", 
                  command=self.exclude_selected_items).pack(side=tk.LEFT, padx=2)
        ttk.Button(structure_buttons, text="Включить выбранные", 
                  command=self.include_selected_items).pack(side=tk.LEFT, padx=2)
        ttk.Button(structure_buttons, text="Включить все", 
                  command=self.include_all_items).pack(side=tk.LEFT, padx=2)
        ttk.Button(structure_buttons, text="Добавить элемент", 
                  command=self.add_structure_item).pack(side=tk.LEFT, padx=2)
        
        # Привязка события выбора
        self.archive_listbox.bind('<<ListboxSelect>>', self.on_archive_select)
        
        # Привязка двойного клика для указания источника
        self.archive_structure_tree.bind('<Double-1>', self.on_structure_item_double_click)
        
        # Привязка правого клика для контекстного меню
        self.archive_structure_tree.bind('<Button-3>', self.on_structure_item_right_click)
    
    def create_components_tab(self):
        """Создание вкладки компонентов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Компоненты")
        
        # Создаем PanedWindow для разделения панелей с возможностью изменения размера
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Левая панель: дерево компонентов
        left_frame = ttk.LabelFrame(paned, text="Дерево компонентов")
        left_frame.pack_propagate(False)  # Отключаем автоматическое изменение размера
        paned.add(left_frame, weight=1)
        
        # Настраиваем заполнение для левой панели
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        # Поиск и кнопки управления
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT, padx=5)
        self.component_search = ttk.Entry(search_frame)
        self.component_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.component_search.bind('<KeyRelease>', self.filter_components)
        
        # Кнопки управления деревом
        button_frame = ttk.Frame(search_frame)
        button_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Развернуть все", 
                  command=self.expand_all_components).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Свернуть все", 
                  command=self.collapse_all_components).pack(side=tk.LEFT, padx=2)
        
        # Treeview вместо Listbox
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar_comp = ttk.Scrollbar(tree_frame)
        scrollbar_comp.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Создаем Treeview с колонками
        columns = ('category', 'status')
        self.component_tree = ttk.Treeview(
            tree_frame, 
            columns=columns, 
            show='tree headings',  # Показываем дерево с заголовками
            yscrollcommand=scrollbar_comp.set
        )
        self.component_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_comp.config(command=self.component_tree.yview)
        
        # Настройка колонок
        self.component_tree.heading('#0', text='Компонент')
        self.component_tree.heading('category', text='Категория')
        self.component_tree.heading('status', text='Статус')
        
        self.component_tree.column('#0', width=300, minwidth=200)
        self.component_tree.column('category', width=150, minwidth=100)
        self.component_tree.column('status', width=120, minwidth=80, anchor='center')
        
        # Словарь для соответствия item_id -> component_id
        self.component_tree_item_to_id = {}
        
        # Заполняем дерево асинхронно (будет вызвано после инициализации в __init__)
        # self.update_component_tree() - вызывается в __init__ через after()
        
        # Фрейм с кнопками управления компонентами (под деревом)
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Кнопка создания нового компонента
        ttk.Button(control_frame, text="Создать новый", 
                  command=self.create_new_component).pack(side=tk.LEFT, padx=2)
        
        # Кнопка отмены последнего действия
        self.undo_button = ttk.Button(control_frame, text="Отменить", 
                                      command=self.undo_last_action,
                                      state=tk.DISABLED)
        self.undo_button.pack(side=tk.LEFT, padx=2)
        
        # Кнопки перемещения компонентов
        move_frame = ttk.Frame(control_frame)
        move_frame.pack(side=tk.LEFT, padx=10)
        
        self.move_up_button = ttk.Button(move_frame, text="↑ Вверх", 
                                         command=self.move_component_up,
                                         state=tk.DISABLED)
        self.move_up_button.pack(side=tk.LEFT, padx=2)
        
        self.move_down_button = ttk.Button(move_frame, text="↓ Вниз", 
                                          command=self.move_component_down,
                                          state=tk.DISABLED)
        self.move_down_button.pack(side=tk.LEFT, padx=2)
        
        # Правая панель: конфигурация компонента
        right_frame = ttk.LabelFrame(paned, text="Конфигурация компонента")
        right_frame.pack_propagate(False)  # Отключаем автоматическое изменение размера
        paned.add(right_frame, weight=1)
        
        # Настраиваем заполнение для правой панели
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        
        # ID компонента
        id_frame = ttk.Frame(right_frame)
        id_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(id_frame, text="ID компонента:", font=('TkDefaultFont', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        self.component_id_label = ttk.Label(id_frame, text="", font=('TkDefaultFont', 10))
        self.component_id_label.pack(side=tk.LEFT, padx=5)
        
        # Прокручиваемая область для полей
        config_canvas_frame = ttk.Frame(right_frame)
        config_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas для прокрутки
        config_canvas = tk.Canvas(config_canvas_frame)
        config_scrollbar = ttk.Scrollbar(config_canvas_frame, orient="vertical", command=config_canvas.yview)
        self.config_scrollable_frame = ttk.Frame(config_canvas)
        
        self.config_scrollable_frame.bind(
            "<Configure>",
            lambda e: config_canvas.configure(scrollregion=config_canvas.bbox("all"))
        )
        
        # Создаем окно в canvas с настройкой растягивания
        canvas_window = config_canvas.create_window((0, 0), window=self.config_scrollable_frame, anchor="nw")
        config_canvas.configure(yscrollcommand=config_scrollbar.set)
        
        # Сохраняем ссылку на canvas_window для последующего обновления
        self.component_config_canvas_window = canvas_window
        
        # Функция для обновления ширины окна в canvas при изменении размера
        def configure_canvas_window(event):
            canvas_width = event.width
            if canvas_width > 1:
                config_canvas.itemconfig(canvas_window, width=canvas_width)
        
        config_canvas.bind('<Configure>', configure_canvas_window)
        
        config_canvas.pack(side="left", fill="both", expand=True)
        config_scrollbar.pack(side="right", fill="y")
        
        # Привязываем прокрутку колесиком мыши (поддержка разных платформ)
        def _on_mousewheel(event):
            # Для Windows и Linux
            if event.delta:
                config_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            # Для macOS
            else:
                config_canvas.yview_scroll(int(-1*event.delta), "units")
        
        # Поддержка разных событий для разных платформ
        if sys.platform == "darwin":  # macOS
            config_canvas.bind_all("<Button-4>", lambda e: config_canvas.yview_scroll(-1, "units"))
            config_canvas.bind_all("<Button-5>", lambda e: config_canvas.yview_scroll(1, "units"))
        else:  # Windows и Linux
            config_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Сохраняем ссылки
        self.component_config_canvas = config_canvas
        self.component_config_frame = self.config_scrollable_frame
        self.current_component_id = None
        self.component_config_fields = {}  # Словарь для хранения виджетов полей
        
        # Кнопки управления
        save_frame = ttk.Frame(right_frame)
        save_frame.pack(fill=tk.X, padx=5, pady=5)
        self.save_config_button = ttk.Button(save_frame, text="Сохранить изменения", 
                                             command=self.save_component_config,
                                             state=tk.DISABLED)
        self.save_config_button.pack(side=tk.LEFT, padx=5)
        
        self.delete_component_button = ttk.Button(save_frame, text="Удалить компонент", 
                                                  command=self.delete_component,
                                                  state=tk.DISABLED)
        self.delete_component_button.pack(side=tk.LEFT, padx=5)
        
        # Привязка события выбора
        self.component_tree.bind('<<TreeviewSelect>>', self.on_component_select)
        
        # Привязка контекстного меню (поддержка разных платформ)
        if sys.platform == "darwin":  # macOS
            # На macOS используем Control+Click или Button-2
            self.component_tree.bind('<Button-2>', self.on_component_right_click)
            self.component_tree.bind('<Control-Button-1>', self.on_component_right_click)
        else:  # Windows и Linux
            self.component_tree.bind('<Button-3>', self.on_component_right_click)
        
        # Привязка событий Drag and Drop для связывания компонентов
        self.drag_start_item = None
        self.drag_start_time = 0
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_highlight_item = None  # Элемент, на который наведен курсор при перетаскивании
        self.drag_original_tags = {}  # Словарь для хранения оригинальных тегов элементов
        self.component_tree.bind('<ButtonPress-1>', self.on_drag_start)
        self.component_tree.bind('<B1-Motion>', self.on_drag_motion)
        self.component_tree.bind('<ButtonRelease-1>', self.on_drag_release)
        
        # Система отмены действий (undo)
        self.undo_history = []  # История изменений для отмены
        self.max_undo_history = 50  # Максимальное количество действий в истории
    
    def create_bundle_creator_tab(self):
        """Создание вкладки для создания сборок"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Создать сборку")
        
        # Создаем PanedWindow для разделения панелей
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Левая панель: информация о сборке и выбор компонентов
        left_frame = ttk.LabelFrame(paned, text="Информация о сборке")
        left_frame.pack_propagate(False)
        paned.add(left_frame, weight=1)
        
        # Основная информация
        info_frame = ttk.Frame(left_frame)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # ID сборки
        id_frame = ttk.Frame(info_frame)
        id_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(id_frame, text="ID сборки:").pack(side=tk.LEFT, padx=5)
        self.new_bundle_id = tk.StringVar()
        ttk.Entry(id_frame, textvariable=self.new_bundle_id, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Название сборки
        name_frame = ttk.Frame(info_frame)
        name_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(name_frame, text="Название:").pack(side=tk.LEFT, padx=5)
        self.new_bundle_name = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.new_bundle_name, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Версия сборки
        version_frame = ttk.Frame(info_frame)
        version_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(version_frame, text="Версия:").pack(side=tk.LEFT, padx=5)
        self.new_bundle_version = tk.StringVar(value='1.0.0')
        ttk.Entry(version_frame, textvariable=self.new_bundle_version, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Описание
        desc_frame = ttk.Frame(info_frame)
        desc_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(desc_frame, text="Описание:").pack(side=tk.LEFT, padx=5)
        self.new_bundle_description = tk.StringVar()
        ttk.Entry(desc_frame, textvariable=self.new_bundle_description, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Список выбранных компонентов
        components_frame = ttk.LabelFrame(left_frame, text="Выбранные компоненты")
        components_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки управления компонентами
        comp_buttons = ttk.Frame(components_frame)
        comp_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(comp_buttons, text="Добавить компонент", 
                  command=self.add_component_to_bundle).pack(side=tk.LEFT, padx=2)
        ttk.Button(comp_buttons, text="Удалить", 
                  command=self.remove_component_from_bundle).pack(side=tk.LEFT, padx=2)
        ttk.Button(comp_buttons, text="Разрешить зависимости", 
                  command=self.resolve_bundle_dependencies).pack(side=tk.LEFT, padx=2)
        
        # Список компонентов
        comp_list_frame = ttk.Frame(components_frame)
        comp_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar_comp = ttk.Scrollbar(comp_list_frame)
        scrollbar_comp.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.bundle_components_tree = ttk.Treeview(
            comp_list_frame,
            columns=('archive', 'deps'),
            yscrollcommand=scrollbar_comp.set,
            show='tree headings'
        )
        self.bundle_components_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_comp.config(command=self.bundle_components_tree.yview)
        
        self.bundle_components_tree.heading('#0', text='Компонент')
        self.bundle_components_tree.heading('archive', text='Архив')
        self.bundle_components_tree.heading('deps', text='Зависимости')
        
        # Словарь для хранения component_id элементов дерева
        self.bundle_tree_component_ids = {}  # {item_id: component_id}
        
        # Список компонентов для сборки
        self.bundle_components = []  # Список component_id
        
        # Правая панель: доступные компоненты
        right_frame = ttk.LabelFrame(paned, text="Доступные компоненты")
        right_frame.pack_propagate(False)
        paned.add(right_frame, weight=1)
        
        # Поиск
        search_frame = ttk.Frame(right_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT, padx=5)
        self.bundle_component_search = ttk.Entry(search_frame)
        self.bundle_component_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.bundle_component_search.bind('<KeyRelease>', self.filter_bundle_components)
        
        # Список доступных компонентов
        avail_list_frame = ttk.Frame(right_frame)
        avail_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar_avail = ttk.Scrollbar(avail_list_frame)
        scrollbar_avail.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.available_components_listbox = tk.Listbox(
            avail_list_frame,
            yscrollcommand=scrollbar_avail.set,
            selectmode=tk.EXTENDED
        )
        self.available_components_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_avail.config(command=self.available_components_listbox.yview)
        
        # Заполняем список доступных компонентов
        self.update_available_components_list()
        
        # Нижняя панель: кнопки действий
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(action_frame, text="Создать сборку", 
                  command=self.create_new_bundle_from_ui).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Создать архив сборки", 
                  command=self.create_bundle_archive).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Очистить форму", 
                  command=self.clear_bundle_form).pack(side=tk.LEFT, padx=5)
    
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
        
        # Область вывода
        output_frame = ttk.LabelFrame(frame, text="Результаты")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tools_output = scrolledtext.ScrolledText(output_frame, height=20, wrap=tk.WORD)
        self.tools_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_explorer_tab(self):
        """Создание вкладки обзора файловой системы"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Обзор")
        
        # Верхняя панель: выбор корневой папки
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="Корневая папка:").pack(side=tk.LEFT, padx=5)
        self.explorer_root_path = tk.StringVar(value=self.astrapack_dir)
        self.explorer_path_entry = ttk.Entry(top_frame, textvariable=self.explorer_root_path, width=50)
        self.explorer_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(top_frame, text="Обзор...", 
                  command=self.select_explorer_root_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Обновить", 
                  command=self.refresh_explorer).pack(side=tk.LEFT, padx=5)
        
        # Основная область: дерево файловой системы
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar для дерева
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview для обзора
        self.explorer_tree = ttk.Treeview(
            tree_frame,
            columns=('type', 'size', 'status'),
            yscrollcommand=scrollbar.set,
            show='tree headings'
        )
        self.explorer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.explorer_tree.yview)
        
        # Настройка колонок
        self.explorer_tree.heading('#0', text='Имя')
        self.explorer_tree.heading('type', text='Тип')
        self.explorer_tree.heading('size', text='Размер')
        self.explorer_tree.heading('status', text='Статус')
        
        self.explorer_tree.column('#0', width=300)
        self.explorer_tree.column('type', width=150)
        self.explorer_tree.column('size', width=100)
        self.explorer_tree.column('status', width=100)
        
        # Словарь для хранения путей элементов дерева
        self.explorer_item_paths = {}  # {item_id: path}
        
        # Привязка событий
        self.explorer_tree.bind('<<TreeviewOpen>>', self.on_explorer_expand)
        self.explorer_tree.bind('<Double-1>', self.on_explorer_double_click)
        
        # Информационная панель
        info_frame = ttk.LabelFrame(frame, text="Информация")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.explorer_info = tk.Text(info_frame, height=3, wrap=tk.WORD)
        self.explorer_info.pack(fill=tk.X, padx=5, pady=5)
        
        # Заполняем дерево при создании
        self.refresh_explorer()
    
    def create_component_creator_tab(self):
        """Создание вкладки для создания компонентов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Создать компонент")
        
        # Верхняя панель: выбор существующего компонента или создание нового
        select_frame = ttk.LabelFrame(frame, text="Работа с компонентом")
        select_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Выбор существующего компонента
        select_comp_frame = ttk.Frame(select_frame)
        select_comp_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(select_comp_frame, text="Выбрать существующий компонент:").pack(side=tk.LEFT, padx=5)
        self.existing_component_id = tk.StringVar()
        self.existing_component_combo = ttk.Combobox(select_comp_frame, textvariable=self.existing_component_id,
                                                     state='readonly', width=40)
        self.existing_component_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.existing_component_combo.bind('<<ComboboxSelected>>', self.on_existing_component_selected)
        ttk.Button(select_comp_frame, text="Загрузить", 
                  command=self.load_existing_component).pack(side=tk.LEFT, padx=5)
        ttk.Button(select_comp_frame, text="Обновить список", 
                  command=self.update_existing_components_list).pack(side=tk.LEFT, padx=5)
        
        # Обновим список компонентов после создания всех виджетов
        # Используем after_idle для гарантии, что COMPONENTS_CONFIG загружен
        if hasattr(self, 'root'):
            self.root.after_idle(self.update_existing_components_list)
        
        # Верхняя панель: основная информация
        info_frame = ttk.LabelFrame(frame, text="Основная информация")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # ID компонента
        id_frame = ttk.Frame(info_frame)
        id_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(id_frame, text="ID компонента:").pack(side=tk.LEFT, padx=5)
        self.new_component_id = tk.StringVar()
        ttk.Entry(id_frame, textvariable=self.new_component_id, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Название
        name_frame = ttk.Frame(info_frame)
        name_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(name_frame, text="Название:").pack(side=tk.LEFT, padx=5)
        self.new_component_name = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.new_component_name, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Категория с русскими комментариями
        category_frame = ttk.Frame(info_frame)
        category_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(category_frame, text="Категория:").pack(side=tk.LEFT, padx=5)
        self.new_component_category = tk.StringVar(value='application')
        
        # Словарь соответствия категорий и их русских названий с комментариями
        self.category_display_map = {
            'system': 'Система - системные компоненты',
            'application': 'Приложение - пользовательские приложения',
            'wine_packages': 'Wine пакеты - пакеты для Wine',
            'wine_environment': 'Wine окружение - настройки Wine',
            'wine_application': 'Wine приложение - приложения через Wine',
            'apt_packages': 'APT пакеты - пакеты Debian/Ubuntu',
            'winetricks': 'Winetricks - утилиты Winetricks',
            'desktop_shortcut': 'Ярлык рабочего стола - ярлыки приложений',
            'system_config': 'Системная конфигурация - настройки системы',
            'package': 'Пакет - группа компонентов',
            'library': 'Библиотека - библиотеки и зависимости',
            'tool': 'Инструмент - утилиты и инструменты',
            'config': 'Конфигурация - файлы конфигурации',
            'plugin': 'Плагин - плагины и расширения',
            'cache': 'Кэш - кэшированные данные'
        }
        
        # Создаем список значений для отображения
        category_display_values = list(self.category_display_map.values())
        category_combo = ttk.Combobox(category_frame, textvariable=self.new_component_category, 
                                      values=category_display_values,
                                      state='readonly', width=50)
        category_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Словарь для обратного перевода (из русского в английский)
        self.category_reverse_map = {v: k for k, v in self.category_display_map.items()}
        
        # Привязываем обработчик изменения для синхронизации значения
        def on_category_change(event=None):
            display_value = self.new_component_category.get()
            if display_value in self.category_reverse_map:
                # Сохраняем английское значение в скрытой переменной
                if not hasattr(self, '_component_category_value'):
                    self._component_category_value = tk.StringVar()
                self._component_category_value.set(self.category_reverse_map[display_value])
        
        category_combo.bind('<<ComboboxSelected>>', on_category_change)
        
        # Описание
        desc_frame = ttk.Frame(info_frame)
        desc_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(desc_frame, text="Описание:").pack(side=tk.LEFT, padx=5)
        self.new_component_description = tk.StringVar()
        ttk.Entry(desc_frame, textvariable=self.new_component_description, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Средняя панель: файлы компонента
        files_frame = ttk.LabelFrame(frame, text="Файлы компонента")
        files_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки управления файлами
        files_buttons = ttk.Frame(files_frame)
        files_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(files_buttons, text="Добавить файл", 
                  command=self.add_component_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(files_buttons, text="Добавить папку", 
                  command=self.add_component_dir).pack(side=tk.LEFT, padx=2)
        ttk.Button(files_buttons, text="Удалить", 
                  command=self.remove_component_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(files_buttons, text="Очистить", 
                  command=self.clear_component_files).pack(side=tk.LEFT, padx=2)
        
        # Список файлов
        files_list_frame = ttk.Frame(files_frame)
        files_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar_files = ttk.Scrollbar(files_list_frame)
        scrollbar_files.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.component_files_listbox = tk.Listbox(files_list_frame, yscrollcommand=scrollbar_files.set,
                                                 selectmode=tk.SINGLE)
        self.component_files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_files.config(command=self.component_files_listbox.yview)
        
        # Список файлов для компонента
        self.component_files = []  # Список путей к файлам/папкам
        
        # Панель: путь сохранения архива
        archive_path_frame = ttk.LabelFrame(frame, text="Путь сохранения архива")
        archive_path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        path_entry_frame = ttk.Frame(archive_path_frame)
        path_entry_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(path_entry_frame, text="Путь:").pack(side=tk.LEFT, padx=5)
        self.archive_output_path = tk.StringVar()
        self.archive_output_path.set(os.path.join(self.astrapack_dir, 'Astra'))
        ttk.Entry(path_entry_frame, textvariable=self.archive_output_path, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(path_entry_frame, text="Обзор...", 
                  command=self.select_archive_output_path).pack(side=tk.LEFT, padx=5)
        
        # Нижняя панель: кнопки действий
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(action_frame, text="Создать компонент", 
                  command=self.create_new_component_from_ui).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Создать архив компонента", 
                  command=self.create_component_archive).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Очистить форму", 
                  command=self.clear_component_form).pack(side=tk.LEFT, padx=5)
        
        # Обновляем список компонентов после создания всех виджетов вкладки
        self.root.after_idle(self.update_existing_components_list)
    
    def get_dir_size(self, path):
        """Получить размер директории"""
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self.get_dir_size(entry.path)
        except (OSError, PermissionError):
            # Игнорируем ошибки доступа к файлам/папкам
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
                    # Проверяем, является ли файл архивом
                    if entry.name.endswith('.tar.gz') or entry.name.endswith('.tar'):
                        # Это архив - добавляем как папку с возможностью разворачивания
                        item = self.structure_tree.insert(parent, 'end', text=entry.name,
                                                         values=(self.format_size(size), 'Архив'))
                        # Добавляем пустой дочерний элемент для разворачивания
                        self.structure_tree.insert(item, 'end', text='[Загрузка...]', 
                                                  values=('', ''))
                        # Привязываем обработчик разворачивания
                        self.structure_tree.item(item, open=False)
                    else:
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
    
    def expand_archive(self, item_id, archive_path):
        """Развернуть структуру архива"""
        try:
            # Удаляем элемент "[Загрузка...]"
            children = self.structure_tree.get_children(item_id)
            for child in children:
                self.structure_tree.delete(child)
            
            # Читаем структуру архива
            with tarfile.open(archive_path, 'r:gz' if archive_path.endswith('.gz') else 'r') as tar:
                # Создаем словарь для хранения структуры папок
                # Ключ - путь в архиве, значение - item_id в дереве
                dirs = {}
                
                # Сортируем элементы по пути для правильного построения дерева
                members = sorted(tar.getmembers(), key=lambda m: m.name)
                
                for member in members:
                    if member.name.startswith('.'):
                        continue
                    
                    # Определяем путь в архиве
                    path_parts = [p for p in member.name.split('/') if p]
                    if not path_parts:
                        continue
                    
                    # Строим путь по частям
                    for i in range(len(path_parts)):
                        path_key = '/'.join(path_parts[:i+1])
                        
                        if path_key not in dirs:
                            # Определяем родительский элемент
                            if i == 0:
                                # Корневой элемент архива
                                parent_item = item_id
                            else:
                                # Вложенная папка
                                parent_path = '/'.join(path_parts[:i])
                                parent_item = dirs.get(parent_path, item_id)
                            
                            part_name = path_parts[i]
                            
                            # Проверяем, является ли это последним элементом пути
                            is_last = (i == len(path_parts) - 1)
                            
                            if is_last and not member.isdir():
                                # Это файл
                                size = member.size if hasattr(member, 'size') else 0
                                file_item = self.structure_tree.insert(parent_item, 'end',
                                                                      text=part_name,
                                                                      values=(self.format_size(size), 'Файл'))
                                dirs[path_key] = file_item
                            else:
                                # Это папка (или промежуточная папка)
                                dir_item = self.structure_tree.insert(parent_item, 'end', 
                                                                     text=part_name,
                                                                     values=('', 'Папка'))
                                dirs[path_key] = dir_item
        except Exception as e:
            # В случае ошибки показываем сообщение
            self.structure_tree.insert(item_id, 'end', text=f'[Ошибка: {e}]', 
                                      values=('', ''))
    
    def on_tree_open(self, event):
        """Обработчик разворачивания элемента дерева"""
        # Получаем ID элемента, который разворачивается
        # В tkinter Treeview событие <<TreeviewOpen>> не передает item напрямую
        # Используем focus() для получения текущего элемента
        item_id = self.structure_tree.focus()
        if not item_id:
            return
        
        # Получаем значения элемента
        item_values = self.structure_tree.item(item_id, 'values')
        
        # Проверяем, является ли это архивом
        if len(item_values) > 1 and item_values[1] == 'Архив':
            # Получаем полный путь к архиву
            archive_path = self._get_item_path(item_id)
            if archive_path and os.path.exists(archive_path):
                # Разворачиваем архив
                self.expand_archive(item_id, archive_path)
    
    def _get_item_path(self, item_id):
        """Получить полный путь к элементу дерева"""
        path_parts = []
        current = item_id
        
        while current:
            text = self.structure_tree.item(current, 'text')
            if text == 'AstraPack':
                # Дошли до корня - формируем путь
                if path_parts:
                    return os.path.join(self.astrapack_dir, *path_parts)
                return None
            # Пропускаем служебные элементы
            if not text.startswith('[') and text != '[Загрузка...]':
                path_parts.insert(0, text)
            current = self.structure_tree.parent(current)
            if not current:
                break
        
        if path_parts:
            return os.path.join(self.astrapack_dir, *path_parts)
        return None
    
    def update_structure_info(self):
        """Обновить информацию о структуре"""
        info = []
        
        if os.path.exists(self.astrapack_dir):
            total_size = self.get_dir_size(self.astrapack_dir)
            info.append(f"Общий размер: {self.format_size(total_size)}")
            
            # Подсчитываем группы
            groups_found = []
            for group_id, group_info in self.package_groups.items():
                folder_name = self.get_group_folder_name(group_id)
                group_path = os.path.join(self.astrapack_dir, folder_name)
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
                folder_name = self.get_group_folder_name(group_id)
                group_path = os.path.join(self.astrapack_dir, folder_name)
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
    
    def select_explorer_root_folder(self):
        """Выбрать корневую папку для обзора"""
        folder = filedialog.askdirectory(
            title="Выберите корневую папку",
            initialdir=self.explorer_root_path.get()
        )
        if folder:
            self.explorer_root_path.set(folder)
            self.refresh_explorer()
    
    def refresh_explorer(self):
        """Обновить дерево обзора"""
        # Очищаем дерево
        for item in self.explorer_tree.get_children():
            self.explorer_tree.delete(item)
        
        # Очищаем словарь путей
        self.explorer_item_paths.clear()
        
        # Получаем корневую папку
        root_path = self.explorer_root_path.get().strip()
        if not root_path or not os.path.exists(root_path):
            self.explorer_info.delete(1.0, tk.END)
            self.explorer_info.insert(1.0, "Папка не существует или не указана")
            return
        
        # Строим дерево файловой системы
        file_tree = build_file_tree(root_path)
        if file_tree:
            self.populate_explorer_tree('', file_tree)
        
        # Обновляем информацию
        self.update_explorer_info(root_path)
    
    def populate_explorer_tree(self, parent_item, tree_node):
        """Заполнить дерево обзора из структуры дерева"""
        if not tree_node:
            return
        
        # Определяем тип и иконку
        node_type = tree_node.get('type', 'unknown')
        name = tree_node.get('name', '')
        path = tree_node.get('path', '')
        
        if node_type == 'directory':
            # Определяем специальные типы директорий
            if 'Components' in name:
                display_type = '📦 Компоненты'
            elif 'Bundles' in name:
                display_type = '📚 Сборки'
            elif os.path.exists(os.path.join(path, '.component.json')):
                display_type = '🔧 Компонент'
            elif os.path.exists(os.path.join(path, '.bundle.json')):
                display_type = '📦 Сборка'
            else:
                display_type = '📁 Папка'
            
            size = ''
            status = ''
        else:
            # Это файл
            size = tree_node.get('size', 0)
            if name.endswith('.tar.gz'):
                if 'component_' in name:
                    display_type = '📦 Архив компонента'
                elif 'bundle_' in name:
                    display_type = '📚 Архив сборки'
                else:
                    display_type = '📦 Архив'
            elif name in ['.component.json', '.bundle.json']:
                display_type = '⚙️ Конфигурация'
            else:
                display_type = '📄 Файл'
            
            status = '✓' if os.path.exists(path) else '✗'
            size = self.format_size(size) if size else ''
        
        # Добавляем элемент в дерево
        item_id = self.explorer_tree.insert(
            parent_item, 'end',
            text=name,
            values=(display_type, size, status),
            tags=(node_type,)
        )
        
        # Сохраняем путь в словаре
        self.explorer_item_paths[item_id] = path
        
        # Добавляем дочерние элементы
        children = tree_node.get('children', [])
        if children:
            for child in children:
                self.populate_explorer_tree(item_id, child)
        
        # Настраиваем цвета тегов
        self.explorer_tree.tag_configure('directory', foreground='blue')
        self.explorer_tree.tag_configure('file', foreground='black')
    
    def on_explorer_expand(self, event):
        """Обработчик разворачивания элемента в обзоре"""
        item_id = self.explorer_tree.focus()
        if not item_id:
            return
        
        # Если элемент уже развернут, ничего не делаем
        if self.explorer_tree.get_children(item_id):
            return
    
    def on_explorer_double_click(self, event):
        """Обработчик двойного клика в обзоре"""
        item_id = self.explorer_tree.focus()
        if not item_id:
            return
        
        path = self.explorer_item_paths.get(item_id)
        if not path:
            return
        
        # Если это конфигурационный файл, открываем его
        if path.endswith('.component.json') or path.endswith('.bundle.json'):
            self.open_config_file(path)
        # Если это папка, открываем в Finder
        elif os.path.isdir(path):
            if sys.platform == "darwin":  # macOS
                os.system(f'open "{path}"')
            elif sys.platform == "win32":  # Windows
                os.system(f'explorer "{path}"')
            else:  # Linux
                os.system(f'xdg-open "{path}"')
    
    def open_config_file(self, config_path):
        """Открыть конфигурационный файл для просмотра/редактирования"""
        if not os.path.exists(config_path):
            messagebox.showerror("Ошибка", "Файл не найден")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Создаем окно для просмотра/редактирования
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Конфигурация: {os.path.basename(config_path)}")
            dialog.geometry("800x600")
            
            # Текстовая область
            text_frame = ttk.Frame(dialog)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.insert(1.0, content)
            
            # Кнопки
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill=tk.X, padx=5, pady=5)
            
            def save_config():
                try:
                    new_content = text_widget.get(1.0, tk.END)
                    # Валидируем JSON
                    json.loads(new_content)
                    # Сохраняем
                    with open(config_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    messagebox.showinfo("Успех", "Конфигурация сохранена")
                    dialog.destroy()
                    # Обновляем обзор
                    self.refresh_explorer()
                except json.JSONDecodeError as e:
                    messagebox.showerror("Ошибка", f"Неверный JSON: {e}")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Ошибка сохранения: {e}")
            
            ttk.Button(button_frame, text="Сохранить", command=save_config).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
    
    def update_explorer_info(self, root_path):
        """Обновить информацию в панели обзора"""
        info = []
        
        if os.path.exists(root_path):
            # Подсчитываем компоненты и сборки
            components_dir = os.path.join(root_path, 'Components')
            bundles_dir = os.path.join(root_path, 'Bundles')
            
            components_count = 0
            bundles_count = 0
            
            if os.path.exists(components_dir):
                for item in os.listdir(components_dir):
                    item_path = os.path.join(components_dir, item)
                    if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, '.component.json')):
                        components_count += 1
            
            if os.path.exists(bundles_dir):
                for item in os.listdir(bundles_dir):
                    item_path = os.path.join(bundles_dir, item)
                    if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, '.bundle.json')):
                        bundles_count += 1
            
            info.append(f"Путь: {root_path}")
            info.append(f"Компонентов: {components_count}")
            info.append(f"Сборок: {bundles_count}")
            
            # Размер директории
            try:
                total_size = self.get_dir_size(root_path)
                info.append(f"Общий размер: {self.format_size(total_size)}")
            except:
                pass
        
        self.explorer_info.delete(1.0, tk.END)
        self.explorer_info.insert(1.0, ' | '.join(info))
    
    def add_component_file(self):
        """Добавить файл в компонент"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл для компонента",
            initialdir=self.astrapack_dir
        )
        if file_path:
            self.component_files.append(('file', file_path))
            self.update_component_files_listbox()
    
    def add_component_dir(self):
        """Добавить папку в компонент"""
        dir_path = filedialog.askdirectory(
            title="Выберите папку для компонента",
            initialdir=self.astrapack_dir
        )
        if dir_path:
            self.component_files.append(('dir', dir_path))
            self.update_component_files_listbox()
    
    def remove_component_file(self):
        """Удалить выбранный файл из списка"""
        selection = self.component_files_listbox.curselection()
        if selection:
            index = selection[0]
            del self.component_files[index]
            self.update_component_files_listbox()
    
    def clear_component_files(self):
        """Очистить список файлов компонента"""
        if self.component_files:
            if messagebox.askyesno("Подтверждение", "Очистить список файлов?"):
                self.component_files = []
                self.update_component_files_listbox()
    
    def update_existing_components_list(self):
        """Обновить список существующих компонентов (асинхронно)"""
        try:
            # Проверяем, что виджет создан
            if not hasattr(self, 'existing_component_combo') or self.existing_component_combo is None:
                print("⚠️ Виджет existing_component_combo еще не создан")
                return
            
            if not COMPONENTS_CONFIG:
                print("⚠️ COMPONENTS_CONFIG пуст при обновлении списка")
                # Устанавливаем пустой список
                self.existing_component_combo['values'] = []
                return
            
            # Выполняем обработку в фоновом потоке для больших списков
            def process_components():
                components_list = []
                for comp_id, comp_config in COMPONENTS_CONFIG.items():
                    comp_name = comp_config.get('name', comp_id)
                    sort_order = comp_config.get('sort_order', 999)
                    components_list.append((sort_order, f"{comp_id} - {comp_name}"))
                
                # Сортируем по sort_order, затем по имени
                sorted_list = sorted(components_list, key=lambda x: (x[0], x[1]))
                # Извлекаем только строки для отображения
                display_list = [item[1] for item in sorted_list]
                
                # Обновляем UI в главном потоке
                self.root.after_idle(lambda: self._set_component_list(display_list))
            
            # Запускаем обработку в отдельном потоке для больших списков
            if len(COMPONENTS_CONFIG) > 50:
                import threading
                thread = threading.Thread(target=process_components, daemon=True)
                thread.start()
            else:
                # Для небольших списков обрабатываем сразу
                process_components()
                
        except Exception as e:
            print(f"❌ Ошибка при обновлении списка компонентов: {e}")
            import traceback
            traceback.print_exc()
    
    def _set_component_list(self, display_list):
        """Установить список компонентов в виджет (вызывается из главного потока)"""
        try:
            self.existing_component_combo['values'] = display_list
            print(f"✓ Обновлен список компонентов: {len(display_list)} элементов (отсортировано по sort_order)")
        except Exception as e:
            print(f"❌ Ошибка при установке списка компонентов: {e}")
    
    def on_existing_component_selected(self, event=None):
        """Обработчик выбора существующего компонента"""
        selection = self.existing_component_id.get()
        if selection:
            component_id = selection.split(' - ')[0]
            self.new_component_id.set(component_id)
            
            # Автоматически загружаем данные компонента, включая категорию
            if component_id in COMPONENTS_CONFIG:
                config = COMPONENTS_CONFIG[component_id]
                
                # Устанавливаем название
                self.new_component_name.set(config.get('name', ''))
                
                # Устанавливаем категорию с русским названием
                category = config.get('category', 'application')
                if hasattr(self, 'category_display_map') and category in self.category_display_map:
                    display_category = self.category_display_map[category]
                    self.new_component_category.set(display_category)
                else:
                    # Fallback на английское значение
                    self.new_component_category.set(category)
                
                # Устанавливаем описание
                self.new_component_description.set(config.get('description', ''))
    
    def load_existing_component(self):
        """Загрузить данные существующего компонента в форму"""
        selection = self.existing_component_id.get()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите компонент из списка")
            return
        
        component_id = selection.split(' - ')[0]
        if component_id not in COMPONENTS_CONFIG:
            messagebox.showerror("Ошибка", f"Компонент '{component_id}' не найден")
            return
        
        config = COMPONENTS_CONFIG[component_id]
        
        # Заполняем форму
        self.new_component_id.set(component_id)
        self.new_component_name.set(config.get('name', ''))
        
        # Устанавливаем категорию с русским названием
        category = config.get('category', 'application')
        if hasattr(self, 'category_display_map') and category in self.category_display_map:
            display_category = self.category_display_map[category]
            self.new_component_category.set(display_category)
        else:
            # Fallback на английское значение
            self.new_component_category.set(category)
        
        self.new_component_description.set(config.get('description', ''))
        
        messagebox.showinfo("Загружено", f"Данные компонента '{component_id}' загружены в форму")
    
    def select_archive_output_path(self):
        """Выбрать путь для сохранения архива"""
        path = filedialog.askdirectory(
            title="Выберите папку для сохранения архива",
            initialdir=self.archive_output_path.get() if self.archive_output_path.get() else self.astrapack_dir
        )
        if path:
            self.archive_output_path.set(path)
    
    def update_component_files_listbox(self):
        """Обновить список файлов компонента с статистикой"""
        self.component_files_listbox.delete(0, tk.END)
        
        # Подсчитываем статистику
        files_count = 0
        dirs_count = 0
        
        for item_type, item_path in self.component_files:
            if item_type == 'dir':
                dirs_count += 1
                # Подсчитываем файлы и подпапки в директории
                if os.path.exists(item_path) and os.path.isdir(item_path):
                    try:
                        for root, dirs_list, files_list in os.walk(item_path):
                            files_count += len(files_list)
                            dirs_count += len(dirs_list)
                    except Exception:
                        pass
            else:
                files_count += 1
        
        # Добавляем элементы в список
        for item_type, item_path in self.component_files:
            display_name = os.path.basename(item_path)
            if item_type == 'dir':
                display_name = f"[Папка] {display_name}"
            else:
                display_name = f"[Файл] {display_name}"
            self.component_files_listbox.insert(tk.END, display_name)
        
        # Добавляем статистику в конец списка
        if files_count > 0 or dirs_count > 0:
            stats_text = f"--- Статистика: файлов: {files_count}, папок: {dirs_count} ---"
            self.component_files_listbox.insert(tk.END, stats_text)
    
    def clear_component_form(self):
        """Очистить форму создания компонента"""
        self.new_component_id.set('')
        self.new_component_name.set('')
        # Устанавливаем категорию по умолчанию (русское значение)
        if hasattr(self, 'category_display_map') and 'application' in self.category_display_map:
            self.new_component_category.set(self.category_display_map['application'])
        else:
            self.new_component_category.set('application')
        self.new_component_description.set('')
        self.component_files = []
        self.update_component_files_listbox()
    
    def create_new_component_from_ui(self):
        """Создать новый компонент из формы"""
        component_id = self.new_component_id.get().strip()
        component_name = self.new_component_name.get().strip()
        # Получаем категорию (переводим из русского отображения в английское значение)
        category_display = self.new_component_category.get()
        if hasattr(self, 'category_reverse_map') and category_display in self.category_reverse_map:
            category = self.category_reverse_map[category_display]
        else:
            # Если не найдено в словаре, используем как есть (fallback для старых значений)
            category = category_display
        description = self.new_component_description.get().strip()
        
        if not component_id:
            messagebox.showerror("Ошибка", "ID компонента не может быть пустым")
            return
        
        if not component_name:
            component_name = component_id
        
        # Определяем корневую папку для компонентов
        root_path = self.explorer_root_path.get().strip() if hasattr(self, 'explorer_root_path') else self.astrapack_dir
        components_dir = os.path.join(root_path, 'Components')
        os.makedirs(components_dir, exist_ok=True)
        
        # Создаем папку компонента
        component_path = os.path.join(components_dir, component_id)
        if os.path.exists(component_path):
            if not messagebox.askyesno("Подтверждение", 
                                      f"Компонент '{component_id}' уже существует. Заменить?"):
                return
        else:
            os.makedirs(component_path, exist_ok=True)
        
        # Создаем базовую конфигурацию компонента
        component_config = {
            'name': component_name,
            'category': category,
            'description': description or f'Компонент {component_name}',
            'dependencies': [],
            'gui_selectable': True,
            'sort_order': 999
        }
        
        # Создаем структуру .component.json
        component_data = {
            'version': '1.0',
            'component_id': component_id,
            'component': component_config,
            'archive': {
                'archive_name': f'component_{component_id}.tar.gz',
                'created': None
            },
            'metadata': {
                'created': datetime.now().isoformat(),
                'author': 'FSA',
                'version': '1.0.0'
            }
        }
        
        # Сохраняем конфигурацию
        config_path = os.path.join(component_path, '.component.json')
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(component_data, f, indent=2, ensure_ascii=False)
            
            # Добавляем в глобальные структуры
            COMPONENTS_CONFIG[component_id] = component_config
            COMPONENTS_DATA[component_id] = {
                'config': component_config,
                'metadata': component_data['metadata'],
                'path': component_path,
                'archive_path': None,
                'source': 'filesystem'
            }
            
            messagebox.showinfo("Успех", f"Компонент '{component_id}' создан в:\n{component_path}")
            
            # Обновляем обзор
            if hasattr(self, 'refresh_explorer'):
                self.refresh_explorer()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать компонент:\n{e}")
    
    def create_component_archive(self):
        """Создать архив компонента"""
        component_id = self.new_component_id.get().strip()
        
        if not component_id:
            messagebox.showerror("Ошибка", "Укажите ID компонента")
            return
        
        # Проверяем, существует ли компонент в конфигурации
        if component_id not in COMPONENTS_CONFIG:
            messagebox.showerror("Ошибка", f"Компонент '{component_id}' не найден в конфигурации.")
            return
        
        # Проверяем наличие файлов
        if not self.component_files:
            if not messagebox.askyesno("Подтверждение", 
                                      "Нет файлов для архивации. Создать архив без файлов?"):
                return
        
        # Определяем путь сохранения архива
        output_path = self.archive_output_path.get().strip()
        if not output_path:
            output_path = self.astrapack_dir
        
        if not os.path.exists(output_path):
            try:
                os.makedirs(output_path, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать папку для архива:\n{e}")
                return
        
        # Определяем имя архива
        component_config = COMPONENTS_CONFIG[component_id]
        version = component_config.get('version', '1.0.0')
        archive_name = f'component_{component_id}_v{version}.tar.gz'
        archive_path = os.path.join(output_path, archive_name)
        
        # Проверяем, существует ли архив
        if os.path.exists(archive_path):
            if not messagebox.askyesno("Подтверждение", 
                                      f"Архив уже существует:\n{archive_path}\n\nЗаменить?"):
                return
        
        # Показываем окно подтверждения с возможностью редактирования имени
        new_archive_name = self._confirm_archive_creation(archive_name, archive_path, len(self.component_files))
        if not new_archive_name:
            return
        
        # Обновляем имя архива и путь если изменилось
        if new_archive_name != archive_name:
            archive_name = new_archive_name
            archive_path = os.path.join(output_path, archive_name)
        
        # Создаем временную директорию для сборки архива
        temp_dir = tempfile.mkdtemp()
        try:
            # Копируем файлы во временную директорию
            items_to_archive = []
            for item_type, item_path in self.component_files:
                if os.path.exists(item_path):
                    item_name = os.path.basename(item_path)
                    items_to_archive.append((item_path, item_name))
            
            # Создаем конфигурацию для архива
            component_config = COMPONENTS_CONFIG[component_id]
            
            # Получаем версию из конфигурации или используем по умолчанию
            version = component_config.get('version', '1.0.0')
            
            # Получаем метаданные, если компонент есть в COMPONENTS_DATA
            metadata_version = version
            if component_id in COMPONENTS_DATA:
                metadata_version = COMPONENTS_DATA[component_id].get('metadata', {}).get('version', version)
            
            config_data = {
                'version': '1.0',
                'component_id': component_id,
                'component': component_config,
                'metadata': {
                    'created': datetime.now().isoformat(),
                    'version': metadata_version
                }
            }
            
            config_path = os.path.join(temp_dir, '.component_config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # Копируем файлы
            for item_path, item_name in items_to_archive:
                target_path = os.path.join(temp_dir, item_name)
                if os.path.isdir(item_path):
                    shutil.copytree(item_path, target_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(item_path, target_path)
            
            # Создаем окно прогресса
            progress_window = self._create_progress_window(archive_name, archive_path, len(items_to_archive))
            progress_window.cancelled = False
            
            try:
                # Создаем архив с прогрессом
                total_files = sum(len(files) for _, _, files in os.walk(temp_dir))
                processed_files = 0
                
                with tarfile.open(archive_path, 'w:gz') as tar:
                    for root, dirs, files in os.walk(temp_dir):
                        if progress_window.cancelled:
                            break
                        for file in files:
                            if progress_window.cancelled:
                                break
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            tar.add(file_path, arcname=arcname, recursive=False)
                            processed_files += 1
                            
                            # Обновляем прогресс
                            progress = (processed_files / total_files) * 100 if total_files > 0 else 0
                            self.root.after_idle(lambda p=progress, t=total_files, f=file_path: 
                                         self._update_progress_window(progress_window, p, t, 0, f))
                            # Обрабатываем события для обновления UI и возможности нажать кнопку отмены
                            progress_window.update_idletasks()
                            progress_window.update()
                
                if progress_window.cancelled:
                    # Удаляем частично созданный архив
                    if os.path.exists(archive_path):
                        os.remove(archive_path)
                    progress_window.destroy()
                    messagebox.showinfo("Отмена", "Создание архива отменено")
                    return
                
                # Завершаем прогресс
                self.root.after_idle(lambda: self._finalize_progress_window(progress_window, True, None))
                progress_window.update()
                time.sleep(0.5)
                progress_window.destroy()
            except Exception as e:
                self.root.after_idle(lambda: self._finalize_progress_window(progress_window, False, str(e)))
                progress_window.update()
                time.sleep(1)
                progress_window.destroy()
                raise
            
            # Обновляем информацию об архиве в .component.json (если компонент в файловой структуре)
            if component_id in COMPONENTS_DATA:
                component_data = COMPONENTS_DATA[component_id]
                component_path = component_data.get('path')
                
                if component_path and os.path.exists(component_path):
                    component_data_file = os.path.join(component_path, '.component.json')
                    if os.path.exists(component_data_file):
                        with open(component_data_file, 'r', encoding='utf-8') as f:
                            component_data_full = json.load(f)
                        
                        component_data_full['archive']['archive_name'] = archive_name
                        component_data_full['archive']['created'] = datetime.now().isoformat()
                        component_data_full['archive']['archive_size'] = os.path.getsize(archive_path)
                        
                        with open(component_data_file, 'w', encoding='utf-8') as f:
                            json.dump(component_data_full, f, indent=2, ensure_ascii=False)
                    
                    # Обновляем COMPONENTS_DATA
                    COMPONENTS_DATA[component_id]['archive_path'] = archive_path
                else:
                    # Компонент из astra_automation.py - добавляем информацию об архиве
                    if 'archive_path' not in COMPONENTS_DATA[component_id]:
                        COMPONENTS_DATA[component_id]['archive_path'] = archive_path
            
            archive_size = os.path.getsize(archive_path)
            messagebox.showinfo("Успех", 
                              f"Архив компонента создан:\n{archive_path}\n"
                              f"Размер: {self.format_size(archive_size)}")
            
            # Обновляем обзор
            if hasattr(self, 'refresh_explorer'):
                self.refresh_explorer()
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать архив:\n{e}")
            import traceback
            traceback.print_exc()
        finally:
            # Удаляем временную директорию
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def update_available_components_list(self):
        """Обновить список доступных компонентов"""
        self.available_components_listbox.delete(0, tk.END)
        
        for component_id in sorted(COMPONENTS_CONFIG.keys()):
            config = COMPONENTS_CONFIG[component_id]
            name = config.get('name', component_id)
            category = config.get('category', 'unknown')
            display_text = f"{name} ({component_id}) [{category}]"
            self.available_components_listbox.insert(tk.END, display_text)
    
    def filter_bundle_components(self, event=None):
        """Фильтровать список доступных компонентов"""
        search_text = self.bundle_component_search.get().lower()
        self.available_components_listbox.delete(0, tk.END)
        
        for component_id in sorted(COMPONENTS_CONFIG.keys()):
            config = COMPONENTS_CONFIG[component_id]
            name = config.get('name', component_id)
            category = config.get('category', 'unknown')
            
            if (search_text in component_id.lower() or 
                search_text in name.lower() or 
                search_text in category.lower()):
                display_text = f"{name} ({component_id}) [{category}]"
                self.available_components_listbox.insert(tk.END, display_text)
    
    def add_component_to_bundle(self):
        """Добавить компонент в сборку"""
        selection = self.available_components_listbox.curselection()
        if not selection:
            messagebox.showinfo("Информация", "Выберите компоненты для добавления")
            return
        
        for index in selection:
            item = self.available_components_listbox.get(index)
            # Извлекаем component_id из строки вида "Name (component_id) [category]"
            if '(' in item and ')' in item:
                component_id = item.split('(')[1].split(')')[0]
                if component_id not in self.bundle_components:
                    self.bundle_components.append(component_id)
        
        self.update_bundle_components_tree()
    
    def remove_component_from_bundle(self):
        """Удалить компонент из сборки"""
        selection = self.bundle_components_tree.selection()
        if not selection:
            messagebox.showinfo("Информация", "Выберите компонент для удаления")
            return
        
        for item_id in selection:
            component_id = self.bundle_tree_component_ids.get(item_id)
            if component_id and component_id in self.bundle_components:
                self.bundle_components.remove(component_id)
        
        self.update_bundle_components_tree()
    
    def resolve_bundle_dependencies(self):
        """Разрешить зависимости для сборки"""
        if not self.bundle_components:
            messagebox.showinfo("Информация", "Добавьте компоненты в сборку")
            return
        
        # Разрешаем зависимости
        resolved = self.resolve_dependencies_for_bundle(self.bundle_components)
        
        # Обновляем список
        self.bundle_components = resolved
        self.update_bundle_components_tree()
        
        added_count = len(resolved) - len(self.bundle_components)
        if added_count > 0:
            messagebox.showinfo("Зависимости разрешены", 
                              f"Добавлено {added_count} зависимых компонентов")
    
    def resolve_dependencies_for_bundle(self, component_ids):
        """Разрешить зависимости для списка компонентов"""
        resolved = set()
        to_process = list(component_ids)
        
        while to_process:
            component_id = to_process.pop(0)
            if component_id in resolved:
                continue
            
            resolved.add(component_id)
            
            # Получаем зависимости
            if component_id in COMPONENTS_CONFIG:
                config = COMPONENTS_CONFIG[component_id]
                deps = config.get('dependencies', [])
                for dep_id in deps:
                    if dep_id not in resolved:
                        to_process.append(dep_id)
        
        return list(resolved)
    
    def update_bundle_components_tree(self):
        """Обновить дерево компонентов сборки"""
        # Очищаем дерево
        for item in self.bundle_components_tree.get_children():
            self.bundle_components_tree.delete(item)
        
        # Очищаем словарь component_id
        self.bundle_tree_component_ids.clear()
        
        # Строим порядок установки
        install_order = self.build_install_order(self.bundle_components)
        
        for component_id in install_order:
            if component_id not in COMPONENTS_CONFIG:
                continue
            
            config = COMPONENTS_CONFIG[component_id]
            name = config.get('name', component_id)
            
            # Получаем информацию об архиве
            archive_name = None
            if component_id in COMPONENTS_DATA:
                archive_path = COMPONENTS_DATA[component_id].get('archive_path')
                if archive_path:
                    archive_name = os.path.basename(archive_path)
            
            # Получаем зависимости
            deps = config.get('dependencies', [])
            deps_display = ', '.join(deps[:3])
            if len(deps) > 3:
                deps_display += f" +{len(deps)-3}"
            
            item_id = self.bundle_components_tree.insert(
                '', 'end',
                text=name,
                values=(archive_name or '[Нет архива]', deps_display or 'Нет')
            )
            # Сохраняем component_id в словаре
            self.bundle_tree_component_ids[item_id] = component_id
    
    def build_install_order(self, component_ids):
        """Построить порядок установки компонентов с учетом зависимостей"""
        # Разрешаем все зависимости
        all_components = self.resolve_dependencies_for_bundle(component_ids)
        
        # Строим граф зависимостей
        dependency_graph = {}
        for comp_id in all_components:
            if comp_id in COMPONENTS_CONFIG:
                config = COMPONENTS_CONFIG[comp_id]
                deps = config.get('dependencies', [])
                dependency_graph[comp_id] = deps
        
        # Топологическая сортировка
        install_order = []
        visited = set()
        temp_visited = set()
        
        def visit(node):
            if node in temp_visited:
                return  # Циклическая зависимость
            if node in visited:
                return
            
            temp_visited.add(node)
            for dep in dependency_graph.get(node, []):
                if dep in all_components:
                    visit(dep)
            temp_visited.remove(node)
            visited.add(node)
            install_order.append(node)
        
        for comp_id in all_components:
            if comp_id not in visited:
                visit(comp_id)
        
        return install_order
    
    def clear_bundle_form(self):
        """Очистить форму создания сборки"""
        self.new_bundle_id.set('')
        self.new_bundle_name.set('')
        self.new_bundle_version.set('1.0.0')
        self.new_bundle_description.set('')
        self.bundle_components = []
        self.update_bundle_components_tree()
    
    def create_new_bundle_from_ui(self):
        """Создать новую сборку из формы"""
        bundle_id = self.new_bundle_id.get().strip()
        bundle_name = self.new_bundle_name.get().strip()
        bundle_version = self.new_bundle_version.get().strip()
        description = self.new_bundle_description.get().strip()
        
        if not bundle_id:
            messagebox.showerror("Ошибка", "ID сборки не может быть пустым")
            return
        
        if not bundle_name:
            bundle_name = bundle_id
        
        if not bundle_version:
            bundle_version = '1.0.0'
        
        if not self.bundle_components:
            messagebox.showerror("Ошибка", "Добавьте хотя бы один компонент в сборку")
            return
        
        # Определяем корневую папку для сборок
        root_path = self.explorer_root_path.get().strip() if hasattr(self, 'explorer_root_path') else self.astrapack_dir
        bundles_dir = os.path.join(root_path, 'Bundles')
        os.makedirs(bundles_dir, exist_ok=True)
        
        # Создаем папку сборки
        bundle_path = os.path.join(bundles_dir, bundle_id)
        if os.path.exists(bundle_path):
            if not messagebox.askyesno("Подтверждение", 
                                      f"Сборка '{bundle_id}' уже существует. Заменить?"):
                return
        else:
            os.makedirs(bundle_path, exist_ok=True)
        
        # Разрешаем зависимости
        all_components = self.resolve_dependencies_for_bundle(self.bundle_components)
        install_order = self.build_install_order(all_components)
        
        # Строим граф зависимостей
        dependencies = {}
        for comp_id in all_components:
            if comp_id in COMPONENTS_CONFIG:
                config = COMPONENTS_CONFIG[comp_id]
                deps = config.get('dependencies', [])
                if deps:
                    dependencies[comp_id] = deps
        
        # Формируем список компонентов с информацией
        components_list = []
        for comp_id in install_order:
            component_info = {
                'component_id': comp_id,
                'required': comp_id in self.bundle_components
            }
            
            # Получаем информацию об архиве
            if comp_id in COMPONENTS_DATA:
                archive_path = COMPONENTS_DATA[comp_id].get('archive_path')
                if archive_path:
                    component_info['archive_name'] = os.path.basename(archive_path)
                    component_info['component_path'] = COMPONENTS_DATA[comp_id].get('path', '')
                else:
                    component_info['archive_name'] = None
            else:
                component_info['archive_name'] = None
            
            components_list.append(component_info)
        
        # Создаем структуру .bundle.json
        bundle_data = {
            'version': '1.0',
            'bundle_id': bundle_id,
            'bundle': {
                'name': bundle_name,
                'version': bundle_version,
                'description': description or f'Сборка {bundle_name}',
                'author': 'FSA',
                'platform': 'linux-x64'
            },
            'components': components_list,
            'dependencies': dependencies,
            'install_order': install_order,
            'archive': {
                'archive_name': f'bundle_{bundle_id}_v{bundle_version}.tar.gz',
                'created': None
            },
            'metadata': {
                'created': datetime.now().isoformat(),
                'components_count': len(all_components),
                'tags': []
            }
        }
        
        # Сохраняем конфигурацию
        config_path = os.path.join(bundle_path, '.bundle.json')
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(bundle_data, f, indent=2, ensure_ascii=False)
            
            # Добавляем в глобальные структуры
            BUNDLES_DATA[bundle_id] = {
                'config': bundle_data['bundle'],
                'components': components_list,
                'dependencies': dependencies,
                'install_order': install_order,
                'metadata': bundle_data['metadata'],
                'path': bundle_path,
                'archive_path': None,
                'source': 'filesystem'
            }
            
            messagebox.showinfo("Успех", 
                              f"Сборка '{bundle_id}' создана в:\n{bundle_path}\n"
                              f"Компонентов: {len(all_components)}")
            
            # Обновляем обзор
            if hasattr(self, 'refresh_explorer'):
                self.refresh_explorer()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать сборку:\n{e}")
            import traceback
            traceback.print_exc()
    
    def create_bundle_archive(self):
        """Создать архив сборки"""
        bundle_id = self.new_bundle_id.get().strip()
        
        if not bundle_id:
            messagebox.showerror("Ошибка", "Укажите ID сборки")
            return
        
        # Проверяем, существует ли сборка
        if bundle_id not in BUNDLES_DATA:
            messagebox.showerror("Ошибка", f"Сборка '{bundle_id}' не найдена. Сначала создайте сборку.")
            return
        
        bundle_data = BUNDLES_DATA[bundle_id]
        bundle_path = bundle_data['path']
        
        if not os.path.exists(bundle_path):
            messagebox.showerror("Ошибка", f"Папка сборки не найдена: {bundle_path}")
            return
        
        # Получаем версию
        bundle_version = bundle_data['config'].get('version', '1.0.0')
        archive_name = f'bundle_{bundle_id}_v{bundle_version}.tar.gz'
        archive_path = os.path.join(bundle_path, archive_name)
        
        # Подсчитываем количество элементов для архивации
        components_list = bundle_data['components']
        items_count = len(components_list) + 1  # +1 для конфигурации
        
        # Показываем окно подтверждения с возможностью редактирования имени
        new_archive_name = self._confirm_archive_creation(archive_name, archive_path, items_count)
        if not new_archive_name:
            return
        
        # Обновляем имя архива и путь если изменилось
        if new_archive_name != archive_name:
            archive_name = new_archive_name
            archive_path = os.path.join(bundle_path, archive_name)
        
        # Создаем временную директорию для сборки
        temp_dir = tempfile.mkdtemp()
        try:
            components_dir = os.path.join(temp_dir, 'components')
            os.makedirs(components_dir, exist_ok=True)
            
            # Копируем архивы компонентов
            components_list = bundle_data['components']
            copied_count = 0
            
            for component_info in components_list:
                component_id = component_info['component_id']
                
                # Получаем путь к архиву компонента
                archive_name_comp = component_info.get('archive_name')
                if not archive_name_comp:
                    continue
                
                # Ищем архив компонента
                if component_id in COMPONENTS_DATA:
                    archive_path_comp = COMPONENTS_DATA[component_id].get('archive_path')
                    if archive_path_comp and os.path.exists(archive_path_comp):
                        dest_path = os.path.join(components_dir, archive_name_comp)
                        shutil.copy2(archive_path_comp, dest_path)
                        copied_count += 1
                    else:
                        # Пробуем найти в папке компонента
                        comp_path = COMPONENTS_DATA[component_id].get('path')
                        if comp_path:
                            possible_archive = os.path.join(comp_path, archive_name_comp)
                            if os.path.exists(possible_archive):
                                dest_path = os.path.join(components_dir, archive_name_comp)
                                shutil.copy2(possible_archive, dest_path)
                                copied_count += 1
            
            # Создаем конфигурацию сборки для архива
            bundle_config = {
                'version': '1.0',
                'bundle_id': bundle_id,
                'bundle': bundle_data['config'],
                'components': components_list,
                'dependencies': bundle_data['dependencies'],
                'install_order': bundle_data['install_order'],
                'metadata': bundle_data['metadata']
            }
            
            config_path = os.path.join(temp_dir, '.bundle_config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(bundle_config, f, indent=2, ensure_ascii=False)
            
            # Создаем окно прогресса
            progress_window = self._create_progress_window(archive_name, archive_path, items_count)
            progress_window.cancelled = False
            
            try:
                # Создаем архив сборки с прогрессом
                total_files = sum(len(files) for _, _, files in os.walk(temp_dir))
                processed_files = 0
                
                with tarfile.open(archive_path, 'w:gz') as tar:
                    for root, dirs, files in os.walk(temp_dir):
                        if progress_window.cancelled:
                            break
                        for file in files:
                            if progress_window.cancelled:
                                break
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            tar.add(file_path, arcname=arcname, recursive=False)
                            processed_files += 1
                            
                            # Обновляем прогресс
                            progress = (processed_files / total_files) * 100 if total_files > 0 else 0
                            self.root.after_idle(lambda p=progress, t=total_files, f=file_path: 
                                         self._update_progress_window(progress_window, p, t, 0, f))
                            # Обрабатываем события для обновления UI и возможности нажать кнопку отмены
                            progress_window.update_idletasks()
                            progress_window.update()
                
                if progress_window.cancelled:
                    # Удаляем частично созданный архив
                    if os.path.exists(archive_path):
                        os.remove(archive_path)
                    progress_window.destroy()
                    messagebox.showinfo("Отмена", "Создание архива отменено")
                    return
                
                # Завершаем прогресс
                self.root.after_idle(lambda: self._finalize_progress_window(progress_window, True, None))
                progress_window.update()
                time.sleep(0.5)
                progress_window.destroy()
            except Exception as e:
                self.root.after_idle(lambda: self._finalize_progress_window(progress_window, False, str(e)))
                progress_window.update()
                time.sleep(1)
                progress_window.destroy()
                raise
            
            # Обновляем информацию об архиве в .bundle.json
            bundle_data_file = os.path.join(bundle_path, '.bundle.json')
            if os.path.exists(bundle_data_file):
                with open(bundle_data_file, 'r', encoding='utf-8') as f:
                    bundle_data_full = json.load(f)
                
                bundle_data_full['archive']['archive_name'] = archive_name
                bundle_data_full['archive']['created'] = datetime.now().isoformat()
                bundle_data_full['archive']['archive_size'] = os.path.getsize(archive_path)
                
                with open(bundle_data_file, 'w', encoding='utf-8') as f:
                    json.dump(bundle_data_full, f, indent=2, ensure_ascii=False)
            
            # Обновляем BUNDLES_DATA
            BUNDLES_DATA[bundle_id]['archive_path'] = archive_path
            
            archive_size = os.path.getsize(archive_path)
            messagebox.showinfo("Успех", 
                              f"Архив сборки создан:\n{archive_path}\n"
                              f"Размер: {self.format_size(archive_size)}\n"
                              f"Компонентов: {copied_count}")
            
            # Обновляем обзор
            if hasattr(self, 'refresh_explorer'):
                self.refresh_explorer()
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать архив:\n{e}")
            import traceback
            traceback.print_exc()
        finally:
            # Удаляем временную директорию
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
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
        self.current_group_id = group_id
        group_info = self.package_groups.get(group_id, {})
        
        # Обновляем дерево структуры архива
        self.update_archive_structure_tree(group_id, group_info)
    
    def update_archive_structure_tree(self, group_id, group_info):
        """Обновить дерево структуры архива с предпросмотром содержимого"""
        # Очищаем дерево
        for item in self.archive_structure_tree.get_children():
            self.archive_structure_tree.delete(item)
        
        # Получаем пользовательские источники и исключенные элементы для этой группы
        custom_sources = self.custom_sources.get(group_id, {})
        excluded = self.excluded_items.get(group_id, set())
        additional = self.additional_items.get(group_id, [])
        
        total_size = 0
        total_items = 0
        excluded_size = 0
        excluded_count = 0
        
        # Если есть source_dir - показываем содержимое папки (без головной папки)
        if 'source_dir' in group_info:
            source_dir_name = group_info['source_dir']
            source_path = os.path.join(self.script_dir, source_dir_name)
            
            # Проверяем пользовательский источник
            custom_source = custom_sources.get(source_dir_name)
            if custom_source:
                source_path = custom_source
            
            if os.path.exists(source_path) and os.path.isdir(source_path):
                # Показываем содержимое папки (как оно будет в архиве - без папки CountPack)
                for item in sorted(os.listdir(source_path)):
                    item_path = os.path.join(source_path, item)
                    
                    # Определяем тип и размер
                    if os.path.isdir(item_path):
                        item_type = "Папка"
                        item_size = self.get_dir_size(item_path)
                    else:
                        item_type = "Файл"
                        item_size = os.path.getsize(item_path)
                    
                    # Имя в архиве - просто item (без папки CountPack)
                    name_in_archive = item
                    
                    # Проверяем, исключен ли элемент
                    is_excluded = name_in_archive in excluded
                    
                    if is_excluded:
                        excluded_size += item_size
                        excluded_count += 1
                        status = f"✗ Исключено ({self.format_size(item_size)})"
                        tags = (item_type.lower(), 'excluded')
                    else:
                        total_size += item_size
                        total_items += 1
                        status = f"✓ Найден ({self.format_size(item_size)})"
                        tags = (item_type.lower(),)
                    
                    source_display = item_path
                    
                    item_id = self.archive_structure_tree.insert('', 'end',
                                                                 text=f"[{item_type}] {name_in_archive}",
                                                                 values=(source_display, status),
                                                                 tags=tags)
                    
                    # Сохраняем имя элемента в данных элемента для последующего использования
                    self.archive_structure_tree.set(item_id, 'item_name', name_in_archive)
            else:
                # Папка не найдена
                status = "⚠ Не найден"
                source_display = source_path if source_path else "[Не указан]"
                self.archive_structure_tree.insert('', 'end',
                                                     text=f"[Папка] {source_dir_name}",
                                                     values=(source_display, status),
                                                     tags=('source_dir',))
        else:
            # Добавляем файлы
            if 'files' in group_info:
                for file_name in group_info['files']:
                    # Проверяем пользовательский источник
                    custom_source = custom_sources.get(file_name)
                    
                    if custom_source:
                        source_path = custom_source
                    else:
                        source_path = os.path.join(self.astrapack_dir, file_name)
                    
                    # Проверяем существование и тип (должен быть файл, а не папка)
                    if os.path.exists(source_path) and os.path.isfile(source_path):
                        status = "✓ Найден"
                        source_display = source_path
                    elif os.path.exists(source_path) and os.path.isdir(source_path):
                        status = "⚠ Это папка"
                        source_display = source_path
                    else:
                        status = "⚠ Не указан"
                        source_display = "[Не указан]"
                    
                    item_id = self.archive_structure_tree.insert('', 'end',
                                                                 text=f"[Файл] {file_name}",
                                                                 values=(source_display, status),
                                                                 tags=('file',))
            
            # Добавляем папки
            if 'dirs' in group_info:
                for dir_name in group_info['dirs']:
                    # Проверяем пользовательский источник
                    custom_source = custom_sources.get(dir_name)
                    
                    if custom_source:
                        source_path = custom_source
                    else:
                        source_path = os.path.join(self.astrapack_dir, dir_name)
                    
                    # Проверяем существование и тип (должна быть папка, а не файл)
                    if os.path.exists(source_path) and os.path.isdir(source_path):
                        status = "✓ Найден"
                        source_display = source_path
                    elif os.path.exists(source_path) and os.path.isfile(source_path):
                        status = "⚠ Это файл"
                        source_display = source_path
                    else:
                        status = "⚠ Не указан"
                        source_display = "[Не указан]"
                    
                    item_id = self.archive_structure_tree.insert('', 'end',
                                                                 text=f"[Папка] {dir_name}",
                                                                 values=(source_display, status),
                                                                 tags=('dir',))
                    
                    if os.path.exists(source_path) and os.path.isdir(source_path):
                        dir_size = self.get_dir_size(source_path)
                        total_size += dir_size
                        total_items += 1
                    elif os.path.exists(source_path) and os.path.isfile(source_path):
                        file_size = os.path.getsize(source_path)
                        total_size += file_size
                        total_items += 1
        
        # Добавляем дополнительные элементы
        for item_path, arcname in additional:
            if os.path.exists(item_path):
                if os.path.isdir(item_path):
                    item_type = "Папка"
                    item_size = self.get_dir_size(item_path)
                else:
                    item_type = "Файл"
                    item_size = os.path.getsize(item_path)
                
                total_size += item_size
                total_items += 1
                
                status = f"✓ Дополнительный ({self.format_size(item_size)})"
                source_display = item_path
                
                item_id = self.archive_structure_tree.insert('', 'end',
                                                             text=f"[{item_type}] {arcname}",
                                                             values=(source_display, status),
                                                             tags=(item_type.lower(), 'additional'))
                self.archive_structure_tree.set(item_id, 'item_name', arcname)
        
        # Добавляем итоговую строку с общей информацией
        total_display = f"Всего элементов: {total_items}"
        if excluded_count > 0:
            total_display += f" (исключено: {excluded_count})"
        
        size_display = f"Общий размер: {self.format_size(total_size)}"
        if excluded_size > 0:
            size_display += f" (исключено: {self.format_size(excluded_size)})"
        
        if total_items > 0 or excluded_count > 0:
            self.archive_structure_tree.insert('', 'end',
                                                 text="[ИТОГО]",
                                                 values=(total_display, size_display),
                                                 tags=('total',))
        
        # Настраиваем цвета для статусов
        self.archive_structure_tree.tag_configure('source_dir', foreground='blue')
        self.archive_structure_tree.tag_configure('total', foreground='green', font=('TkDefaultFont', 9, 'bold'))
        self.archive_structure_tree.tag_configure('папка', foreground='blue')
        self.archive_structure_tree.tag_configure('файл', foreground='black')
        self.archive_structure_tree.tag_configure('excluded', foreground='gray', 
                                                  font=('TkDefaultFont', 9, 'strikethrough'))
        self.archive_structure_tree.tag_configure('additional', foreground='green')
    
    def exclude_selected_items(self):
        """Исключить выбранные элементы из архивации"""
        if not self.current_group_id:
            messagebox.showwarning("Предупреждение", "Выберите компонент для управления элементами")
            return
        
        selection = self.archive_structure_tree.selection()
        if not selection:
            messagebox.showinfo("Информация", "Выберите элементы для исключения")
            return
        
        # Инициализируем множество исключенных элементов для этой группы
        if self.current_group_id not in self.excluded_items:
            self.excluded_items[self.current_group_id] = set()
        
        excluded_count = 0
        for item_id in selection:
            item_tags = self.archive_structure_tree.item(item_id, 'tags')
            # Пропускаем итоговую строку
            if 'total' in item_tags:
                continue
            
            # Получаем имя элемента
            item_name = self.archive_structure_tree.set(item_id, 'item_name')
            if not item_name:
                # Пытаемся извлечь из текста
                item_text = self.archive_structure_tree.item(item_id, 'text')
                if ']' in item_text:
                    item_name = item_text.split(']')[1].strip()
                else:
                    continue
            
            # Добавляем в исключенные
            self.excluded_items[self.current_group_id].add(item_name)
            excluded_count += 1
        
        if excluded_count > 0:
            # Обновляем дерево
            group_info = self.package_groups.get(self.current_group_id, {})
            self.update_archive_structure_tree(self.current_group_id, group_info)
            messagebox.showinfo("Успех", f"Исключено элементов: {excluded_count}")
    
    def include_selected_items(self):
        """Включить выбранные элементы в архивацию"""
        if not self.current_group_id:
            messagebox.showwarning("Предупреждение", "Выберите компонент для управления элементами")
            return
        
        selection = self.archive_structure_tree.selection()
        if not selection:
            messagebox.showinfo("Информация", "Выберите элементы для включения")
            return
        
        if self.current_group_id not in self.excluded_items:
            return
        
        included_count = 0
        for item_id in selection:
            item_tags = self.archive_structure_tree.item(item_id, 'tags')
            # Пропускаем итоговую строку
            if 'total' in item_tags:
                continue
            
            # Получаем имя элемента
            item_name = self.archive_structure_tree.set(item_id, 'item_name')
            if not item_name:
                # Пытаемся извлечь из текста
                item_text = self.archive_structure_tree.item(item_id, 'text')
                if ']' in item_text:
                    item_name = item_text.split(']')[1].strip()
                else:
                    continue
            
            # Удаляем из исключенных
            if item_name in self.excluded_items[self.current_group_id]:
                self.excluded_items[self.current_group_id].remove(item_name)
                included_count += 1
        
        if included_count > 0:
            # Обновляем дерево
            group_info = self.package_groups.get(self.current_group_id, {})
            self.update_archive_structure_tree(self.current_group_id, group_info)
            messagebox.showinfo("Успех", f"Включено элементов: {included_count}")
    
    def include_all_items(self):
        """Включить все элементы в архивацию"""
        if not self.current_group_id:
            messagebox.showwarning("Предупреждение", "Выберите компонент для управления элементами")
            return
        
        if self.current_group_id in self.excluded_items:
            excluded_count = len(self.excluded_items[self.current_group_id])
            self.excluded_items[self.current_group_id].clear()
            
            # Обновляем дерево
            group_info = self.package_groups.get(self.current_group_id, {})
            self.update_archive_structure_tree(self.current_group_id, group_info)
            messagebox.showinfo("Успех", f"Включено всех элементов: {excluded_count}")
        else:
            messagebox.showinfo("Информация", "Нет исключенных элементов")
    
    def add_structure_item(self):
        """Добавить элемент из другого места"""
        if not self.current_group_id:
            messagebox.showwarning("Предупреждение", "Выберите компонент для добавления элементов")
            return
        
        # Спрашиваем, что добавляем - файл или папку
        choice = messagebox.askyesnocancel("Выбор типа", 
                                          "Добавить файл?\n\nДа - файл\nНет - папка\nОтмена - отменить")
        if choice is None:
            return
        
        if choice:
            # Выбираем файл
            file_path = filedialog.askopenfilename(
                title="Выберите файл для добавления в архив"
            )
            if not file_path:
                return
            
            item_path = file_path
            item_name = os.path.basename(file_path)
        else:
            # Выбираем папку
            dir_path = filedialog.askdirectory(
                title="Выберите папку для добавления в архив"
            )
            if not dir_path:
                return
            
            item_path = dir_path
            item_name = os.path.basename(dir_path)
        
        # Спрашиваем имя в архиве
        arcname = simpledialog.askstring(
            "Имя в архиве",
            f"Введите имя элемента в архиве (по умолчанию: {item_name}):",
            initialvalue=item_name
        )
        
        if not arcname:
            arcname = item_name
        
        # Инициализируем список дополнительных элементов для этой группы
        if self.current_group_id not in self.additional_items:
            self.additional_items[self.current_group_id] = []
        
        # Добавляем элемент
        self.additional_items[self.current_group_id].append((item_path, arcname))
        
        # Обновляем дерево
        group_info = self.package_groups.get(self.current_group_id, {})
        self.update_archive_structure_tree(self.current_group_id, group_info)
        messagebox.showinfo("Успех", f"Добавлен элемент: {arcname}")
    
    def on_structure_item_right_click(self, event):
        """Обработчик правого клика для контекстного меню"""
        if not self.current_group_id:
            return
        
        item_id = self.archive_structure_tree.identify_row(event.y)
        if not item_id:
            return
        
        # Выделяем элемент
        self.archive_structure_tree.selection_set(item_id)
        
        # Создаем контекстное меню
        menu = tk.Menu(self.root, tearoff=0)
        
        item_tags = self.archive_structure_tree.item(item_id, 'tags')
        if 'excluded' in item_tags:
            menu.add_command(label="Включить в архив", command=self.include_selected_items)
        elif 'total' not in item_tags:
            menu.add_command(label="Исключить из архива", command=self.exclude_selected_items)
        
        if 'additional' in item_tags:
            menu.add_command(label="Удалить дополнительный элемент", 
                           command=lambda: self.remove_additional_item(item_id))
        
        menu.add_separator()
        menu.add_command(label="Изменить источник", command=self.on_structure_item_double_click)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def remove_additional_item(self, item_id):
        """Удалить дополнительный элемент"""
        if not self.current_group_id:
            return
        
        item_name = self.archive_structure_tree.set(item_id, 'item_name')
        if not item_name:
            return
        
        if self.current_group_id in self.additional_items:
            # Удаляем элемент из списка
            self.additional_items[self.current_group_id] = [
                (path, name) for path, name in self.additional_items[self.current_group_id]
                if name != item_name
            ]
            
            # Обновляем дерево
            group_info = self.package_groups.get(self.current_group_id, {})
            self.update_archive_structure_tree(self.current_group_id, group_info)
    
    def on_structure_item_double_click(self, event=None):
        """Обработчик двойного клика по элементу структуры для указания источника"""
        if not self.current_group_id:
            return
        
        selection = self.archive_structure_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        item_text = self.archive_structure_tree.item(item_id, 'text')
        item_tags = self.archive_structure_tree.item(item_id, 'tags')
        
        # Извлекаем имя элемента (убираем префикс [Файл] или [Папка])
        if '[Файл]' in item_text:
            item_name = item_text.replace('[Файл]', '').strip()
        elif '[Папка]' in item_text:
            item_name = item_text.replace('[Папка]', '').strip()
        else:
            item_name = item_text.strip()
        
        # Определяем тип элемента
        if 'dir' in item_tags or 'source_dir' in item_tags:
            # Выбираем папку
            source_path = filedialog.askdirectory(
                title=f"Выберите папку для: {item_name}",
                initialdir=self.astrapack_dir
            )
        else:
            # Выбираем файл
            source_path = filedialog.askopenfilename(
                title=f"Выберите файл для: {item_name}",
                initialdir=self.astrapack_dir
            )
        
        if source_path:
            # Сохраняем пользовательский источник
            if self.current_group_id not in self.custom_sources:
                self.custom_sources[self.current_group_id] = {}
            
            self.custom_sources[self.current_group_id][item_name] = source_path
            
            # Обновляем дерево
            group_info = self.package_groups.get(self.current_group_id, {})
            self.update_archive_structure_tree(self.current_group_id, group_info)
    
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
        self.archive_groups(groups_to_archive, custom_files=self.custom_files)
    
    def archive_all(self):
        """Архивировать все компоненты"""
        groups_to_archive = list(self.package_groups.keys())
        self.archive_groups(groups_to_archive, custom_files=self.custom_files)
    
    def add_custom_file(self):
        """Добавить файл для архивации"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл для архивации",
            initialdir=self.astrapack_dir
        )
        if file_path:
            self.custom_files.append(('file', file_path))
            self.update_custom_listbox()
    
    def add_custom_dir(self):
        """Добавить папку для архивации"""
        dir_path = filedialog.askdirectory(
            title="Выберите папку для архивации",
            initialdir=self.astrapack_dir
        )
        if dir_path:
            self.custom_files.append(('dir', dir_path))
            self.update_custom_listbox()
    
    def remove_custom_item(self):
        """Удалить выбранный элемент из списка"""
        selection = self.custom_listbox.curselection()
        if selection:
            index = selection[0]
            del self.custom_files[index]
            self.update_custom_listbox()
    
    def clear_custom_items(self):
        """Очистить список пользовательских файлов"""
        if self.custom_files:
            if messagebox.askyesno("Подтверждение", "Очистить список дополнительных файлов?"):
                self.custom_files = []
                self.update_custom_listbox()
    
    def update_custom_listbox(self):
        """Обновить список пользовательских файлов с статистикой"""
        self.custom_listbox.delete(0, tk.END)
        
        # Подсчитываем статистику
        files_count = 0
        dirs_count = 0
        
        for item_type, item_path in self.custom_files:
            if item_type == 'dir':
                dirs_count += 1
                # Подсчитываем файлы и подпапки в директории
                if os.path.exists(item_path) and os.path.isdir(item_path):
                    try:
                        for root, dirs_list, files_list in os.walk(item_path):
                            files_count += len(files_list)
                            dirs_count += len(dirs_list)
                    except Exception:
                        pass
            else:
                files_count += 1
        
        # Добавляем элементы в список
        for item_type, item_path in self.custom_files:
            display_name = os.path.basename(item_path)
            if item_type == 'dir':
                display_name = f"[Папка] {display_name}"
            else:
                display_name = f"[Файл] {display_name}"
            self.custom_listbox.insert(tk.END, display_name)
        
        # Добавляем статистику в конец списка
        if files_count > 0 or dirs_count > 0:
            stats_text = f"--- Статистика: файлов: {files_count}, папок: {dirs_count} ---"
            self.custom_listbox.insert(tk.END, stats_text)
    
    def _confirm_archive_creation(self, archive_name, archive_path, items_count):
        """Показать окно подтверждения создания архива с возможностью редактирования имени"""
        confirm_dialog = tk.Toplevel(self.root)
        confirm_dialog.title("Подтверждение создания архива")
        confirm_dialog.geometry("600x320")
        confirm_dialog.resizable(False, False)
        confirm_dialog.transient(self.root)
        confirm_dialog.grab_set()
        
        # Центрируем окно
        confirm_dialog.update_idletasks()
        x = (confirm_dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (confirm_dialog.winfo_screenheight() // 2) - (320 // 2)
        confirm_dialog.geometry(f"600x320+{x}+{y}")
        
        # Заголовок
        title_label = tk.Label(confirm_dialog, text="Создание архива", 
                              font=('TkDefaultFont', 14, 'bold'))
        title_label.pack(pady=15)
        
        # Информация об архиве
        info_frame = tk.Frame(confirm_dialog)
        info_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Имя архива с возможностью редактирования
        tk.Label(info_frame, text=f"Имя архива:", font=('TkDefaultFont', 10, 'bold'), anchor='w').pack(fill=tk.X, pady=2)
        archive_name_var = tk.StringVar(value=archive_name)
        archive_name_entry = tk.Entry(info_frame, textvariable=archive_name_var, font=('TkDefaultFont', 10))
        archive_name_entry.pack(fill=tk.X, pady=2, padx=(10, 0))
        
        tk.Label(info_frame, text=f"Путь сохранения:", font=('TkDefaultFont', 10, 'bold'), anchor='w').pack(fill=tk.X, pady=2)
        path_label = tk.Label(info_frame, text=f"  {os.path.dirname(archive_path)}", font=('TkDefaultFont', 9), 
                             anchor='w', fg='gray', wraplength=550, justify='left')
        path_label.pack(fill=tk.X, pady=2)
        
        tk.Label(info_frame, text=f"Элементов для архивации: {items_count}", 
                font=('TkDefaultFont', 10), anchor='w').pack(fill=tk.X, pady=2)
        
        # Кнопки
        buttons_frame = tk.Frame(confirm_dialog)
        buttons_frame.pack(pady=15)
        
        confirmed = [False]
        final_archive_name = [archive_name]
        
        def on_confirm():
            new_name = archive_name_var.get().strip()
            if not new_name:
                messagebox.showerror("Ошибка", "Имя архива не может быть пустым")
                return
            # Проверяем расширение
            if not new_name.endswith('.tar.gz'):
                new_name += '.tar.gz'
            final_archive_name[0] = new_name
            confirmed[0] = True
            confirm_dialog.destroy()
        
        def on_cancel():
            confirmed[0] = False
            confirm_dialog.destroy()
        
        tk.Button(buttons_frame, text="Создать архив", command=on_confirm, 
                 font=('TkDefaultFont', 10), width=15, bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Отмена", command=on_cancel, 
                 font=('TkDefaultFont', 10), width=15).pack(side=tk.LEFT, padx=5)
        
        # Обработка Enter и Escape
        confirm_dialog.bind('<Return>', lambda e: on_confirm())
        confirm_dialog.bind('<Escape>', lambda e: on_cancel())
        archive_name_entry.focus_set()
        archive_name_entry.select_range(0, tk.END)
        
        # Ждем закрытия окна
        confirm_dialog.wait_window()
        
        if confirmed[0]:
            return final_archive_name[0]
        return None
    
    def archive_groups(self, group_ids, custom_files=None):
        """Архивировать указанные группы (быстро через системный tar с прогрессом)"""
        if custom_files is None:
            custom_files = []
        
        results = []
        
        for group_id in group_ids:
            group_info = self.package_groups.get(group_id)
            if not group_info:
                continue
            
            try:
                # Определяем имя архива
                if 'archive_name' in group_info:
                    archive_name = group_info['archive_name']
                else:
                    archive_name = f"{group_id}_packages.tar.gz"
                
                # Определяем расположение архива (с учетом пользовательских настроек)
                folder_name = self.get_group_folder_name(group_id)
                group_path = os.path.join(self.astrapack_dir, folder_name)
                
                # Проверяем пользовательское расположение
                if hasattr(self, 'custom_archive_locations') and group_id in self.custom_archive_locations:
                    custom_location = self.custom_archive_locations[group_id]
                    if custom_location:
                        if os.path.isdir(custom_location):
                            archive_path = os.path.join(custom_location, archive_name)
                        else:
                            archive_path = custom_location
                    else:
                        archive_location = group_info.get('archive_location', 'group')
                        if archive_location == 'root':
                            archive_path = os.path.join(self.script_dir, archive_name)
                        else:
                            os.makedirs(group_path, exist_ok=True)
                            archive_path = os.path.join(group_path, archive_name)
                else:
                    archive_location = group_info.get('archive_location', 'group')
                    if archive_location == 'root':
                        archive_path = os.path.join(self.script_dir, archive_name)
                    else:
                        os.makedirs(group_path, exist_ok=True)
                        archive_path = os.path.join(group_path, archive_name)
                
                # Создаем директорию для архива если её нет
                archive_dir = os.path.dirname(archive_path)
                if archive_dir:
                    os.makedirs(archive_dir, exist_ok=True)
                
                # Собираем список элементов для архивации
                items_to_archive = []
                custom_sources = self.custom_sources.get(group_id, {})
                excluded = self.excluded_items.get(group_id, set())
                additional = self.additional_items.get(group_id, [])
                
                # Если есть source_dir - добавляем содержимое папки
                if 'source_dir' in group_info:
                    source_dir_name = group_info['source_dir']
                    if source_dir_name in custom_sources:
                        source_path = custom_sources[source_dir_name]
                    else:
                        source_path = os.path.join(self.script_dir, source_dir_name)
                    
                    if os.path.exists(source_path) and os.path.isdir(source_path):
                        # Добавляем содержимое папки (не саму папку)
                        for item in os.listdir(source_path):
                            # Пропускаем исключенные элементы
                            if item in excluded:
                                continue
                            
                            item_path = os.path.join(source_path, item)
                            items_to_archive.append((item_path, item))  # (путь, имя_в_архиве)
                
                # Добавляем файлы и папки из списка
                if 'files' in group_info:
                    for file_name in group_info['files']:
                        if file_name in custom_sources:
                            file_path = custom_sources[file_name]
                        else:
                            file_path = os.path.join(self.astrapack_dir, file_name)
                        
                        if os.path.exists(file_path):
                            items_to_archive.append((file_path, file_name))
                
                if 'dirs' in group_info:
                    for dir_name in group_info['dirs']:
                        if dir_name in custom_sources:
                            dir_path = custom_sources[dir_name]
                        else:
                            dir_path = os.path.join(self.astrapack_dir, dir_name)
                        
                        if os.path.exists(dir_path):
                            items_to_archive.append((dir_path, dir_name))
                
                # Добавляем пользовательские файлы/папки
                existing_names = set()
                for item_type, item_path in custom_files:
                    if os.path.exists(item_path):
                        item_name = os.path.basename(item_path)
                        if item_name not in existing_names:
                            items_to_archive.append((item_path, item_name))
                            existing_names.add(item_name)
                
                # Используем быструю архивацию через системный tar
                if items_to_archive:
                    # Показываем окно подтверждения
                    if not self._confirm_archive_creation(archive_name, archive_path, len(items_to_archive)):
                        results.append(f"⊘ {group_info['name']}: архивация отменена")
                        continue
                    
                    success = self._archive_with_tar_fast(archive_path, items_to_archive, group_info['name'], group_id, archive_name)
                    if success:
                        archive_size = os.path.getsize(archive_path)
                        results.append(f"✓ {group_info['name']}: {archive_name} создан "
                                     f"({self.format_size(archive_size)}, элементов: {len(items_to_archive)})")
                    else:
                        results.append(f"✗ {group_info['name']}: ошибка архивации")
                else:
                    results.append(f"✗ {group_info['name']}: нет элементов для архивации")
                
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
    
    def _get_archive_worker_path(self):
        """Получить путь к скрипту (используем сам файл с флагом --archive-worker)"""
        # Используем сам файл package_manager_gui.py с флагом --archive-worker
        script_path = os.path.abspath(__file__)
        return script_path
    
    def _archive_with_tar_fast(self, archive_path, items_to_archive, group_name, group_id=None, archive_name=None):
        """Быстрая архивация через системный tar с прогрессом (через subprocess для параллельности)"""
        try:
            # Проверяем наличие tar
            if not shutil.which('tar'):
                # Fallback на Python tarfile
                return self._archive_with_tarfile(archive_path, items_to_archive, group_id, archive_name)
            
            # Проверяем, не запущен ли уже процесс для этого архива
            if archive_path in self.active_archive_processes:
                # Если процесс уже запущен, просто возвращаем его статус
                process_info = self.active_archive_processes[archive_path]
                if process_info['process'].poll() is None:
                    # Процесс еще выполняется
                    return True  # Считаем что успешно, так как процесс уже запущен
            
            # Создаем окно прогресса
            archive_name_display = archive_name or os.path.basename(archive_path)
            progress_window = self._create_progress_window(archive_name_display, archive_path, len(items_to_archive))
            
            # Создаем временные файлы для конфигурации и прогресса
            temp_dir = tempfile.mkdtemp(prefix='archive_worker_')
            config_file = os.path.join(temp_dir, 'config.json')
            progress_file = os.path.join(temp_dir, 'progress.json')
            
            # Подготавливаем конфигурацию для воркера
            components_config = None
            if group_id:
                components_config = self._extract_components_for_group(group_id, items_to_archive)
            
            config_data = {
                'archive_path': archive_path,
                'items_to_archive': items_to_archive,
                'temp_dir': os.path.join(os.path.dirname(archive_path), '.temp_archive'),
                'group_id': group_id,
                'group_name': group_name,
                'archive_name': archive_name,
                'components_config': components_config
            }
            
            # Сохраняем конфигурацию
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False)
            
            # Получаем путь к воркеру (используем сам файл с флагом --archive-worker)
            worker_path = self._get_archive_worker_path()
            
            # Запускаем воркер как subprocess (используем сам файл с флагом --archive-worker)
            process = subprocess.Popen(
                [sys.executable, worker_path, '--archive-worker', config_file, progress_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Сохраняем информацию о процессе
            self.active_archive_processes[archive_path] = {
                'process': process,
                'progress_file': progress_file,
                'config_file': config_file,
                'progress_window': progress_window,
                'temp_dir': temp_dir
            }
            
            # Функция отмены
            def cancel_archive():
                if process.poll() is None:
                    process.terminate()
                    process.wait()
                # Удаляем из активных процессов
                if archive_path in self.active_archive_processes:
                    del self.active_archive_processes[archive_path]
            
            progress_window.cancel_callback = cancel_archive
            
            # Мониторим прогресс через чтение файла прогресса
            start_time = time.time()
            archive_success = False
            archive_error = None
            
            while process.poll() is None:
                # Проверяем отмену
                if progress_window.cancelled:
                    process.terminate()
                    process.wait()
                    archive_success = False
                    archive_error = "Отменено пользователем"
                    break
                
                # Читаем прогресс из файла
                if os.path.exists(progress_file):
                    try:
                        with open(progress_file, 'r', encoding='utf-8') as f:
                            progress_data = json.load(f)
                        
                        progress = progress_data.get('progress', 0)
                        status = progress_data.get('status', 'Обработка...')
                        current_file = progress_data.get('current_file')
                        elapsed = progress_data.get('elapsed', int(time.time() - start_time))
                        
                        # Обновляем UI
                        self.root.after_idle(lambda p=progress, s=status, f=current_file, e=elapsed: 
                                           self._update_progress_window_from_data(progress_window, p, s, f, e))
                    except Exception:
                        pass
                
                # Обрабатываем события главного окна и окна прогресса
                self.root.update_idletasks()
                if progress_window and progress_window.winfo_exists():
                    progress_window.update_idletasks()
                    progress_window.update()
                
                time.sleep(0.1)  # Проверяем прогресс каждые 0.1 секунды
            
            # Получаем результат
            return_code = process.wait()
            archive_success = (return_code == 0)
            
            if return_code != 0:
                stderr = process.stderr.read().decode('utf-8', errors='ignore')
                archive_error = stderr[:100] if stderr else "Неизвестная ошибка"
            
            # Удаляем из активных процессов
            if archive_path in self.active_archive_processes:
                process_info = self.active_archive_processes[archive_path]
                # Удаляем временные файлы
                try:
                    if os.path.exists(process_info['config_file']):
                        os.remove(process_info['config_file'])
                    if os.path.exists(process_info['progress_file']):
                        os.remove(process_info['progress_file'])
                    if os.path.exists(process_info['temp_dir']):
                        shutil.rmtree(process_info['temp_dir'], ignore_errors=True)
                except Exception:
                    pass
                del self.active_archive_processes[archive_path]
            
            # Финальное обновление UI
            if progress_window and progress_window.winfo_exists():
                self.root.after_idle(lambda: self._finalize_progress_window(
                    progress_window, archive_success, archive_error))
                time.sleep(0.5)  # Показываем финальное состояние
                progress_window.destroy()
            
            return archive_success and os.path.exists(archive_path) and os.path.getsize(archive_path) > 0
                    
        except Exception as e:
            print(f"Ошибка быстрой архивации: {e}")
            # Fallback на Python tarfile
            return self._archive_with_tarfile(archive_path, items_to_archive, group_id, archive_name)
    
    def _create_progress_window(self, archive_name, archive_path, total_items, cancel_callback=None):
        """Создать окно прогресса архивации с кнопкой отмены"""
        progress_window = tk.Toplevel(self.root)
        progress_window.title(f"Архивация: {archive_name}")
        progress_window.geometry("600x280")
        progress_window.resizable(False, False)
        
        # Центрируем окно
        progress_window.transient(self.root)
        # Используем grab_set только для модальности, но не блокируем полностью события
        progress_window.grab_set()
        # Делаем окно фокусируемым
        progress_window.focus_set()
        
        # Флаг отмены
        progress_window.cancelled = False
        
        # Заголовок
        title_label = tk.Label(progress_window, text=f"Создание архива: {archive_name}", 
                              font=('TkDefaultFont', 12, 'bold'))
        title_label.pack(pady=10)
        
        # Информация об архиве
        archive_info_frame = tk.Frame(progress_window)
        archive_info_frame.pack(pady=5, padx=20, fill=tk.X)
        
        archive_path_label = tk.Label(archive_info_frame, text=f"Путь: {archive_path}", 
                                      font=('TkDefaultFont', 9), fg='gray', anchor='w', justify='left')
        archive_path_label.pack(fill=tk.X)
        
        items_count_label = tk.Label(archive_info_frame, text=f"Элементов для архивации: {total_items}", 
                                     font=('TkDefaultFont', 9), fg='gray', anchor='w')
        items_count_label.pack(fill=tk.X)
        
        # Прогресс-бар
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, 
                                       maximum=100, length=550, mode='determinate')
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        
        # Статус
        status_label = tk.Label(progress_window, text="Подготовка...", 
                               font=('TkDefaultFont', 10))
        status_label.pack(pady=5)
        
        # Детали
        details_label = tk.Label(progress_window, text="", 
                                font=('TkDefaultFont', 9), fg='gray')
        details_label.pack(pady=5)
        
        # Кнопка отмены
        cancel_button = tk.Button(progress_window, text="Отменить", 
                                 command=lambda: self._cancel_archive(progress_window, cancel_callback),
                                 font=('TkDefaultFont', 10))
        cancel_button.pack(pady=10)
        
        # Сохраняем ссылки на элементы в окне
        progress_window.progress_var = progress_var
        progress_window.status_label = status_label
        progress_window.details_label = details_label
        progress_window.cancel_button = cancel_button
        progress_window.current_item = 0
        progress_window.total_items = total_items
        progress_window.cancel_callback = cancel_callback
        
        # Обновляем окно
        progress_window.update()
        
        return progress_window
    
    def _cancel_archive(self, progress_window, cancel_callback=None):
        """Отменить архивацию"""
        if messagebox.askyesno("Отмена архивации", "Вы уверены, что хотите отменить создание архива?"):
            progress_window.cancelled = True
            if cancel_callback:
                cancel_callback()
            progress_window.status_label.config(text="Отмена...", fg='orange')
            progress_window.cancel_button.config(state=tk.DISABLED)
    
    def _update_progress_window(self, progress_window, progress, total_items, elapsed, current_file=None):
        """Обновить окно прогресса (вызывается из главного потока)"""
        if progress_window and progress_window.winfo_exists():
            if progress_window.cancelled:
                return
            try:
                progress_window.progress_var.set(progress)
                # Вычисляем приблизительное количество обработанных элементов
                processed = int((progress / 100) * total_items) if total_items > 0 else 0
                status_text = f"Обработано: {processed} из {total_items} элементов"
                if current_file:
                    # Обрезаем длинные имена файлов
                    file_name = os.path.basename(current_file)
                    if len(file_name) > 50:
                        file_name = file_name[:47] + "..."
                    status_text += f"\nТекущий файл: {file_name}"
                progress_window.status_label.config(text=status_text)
                progress_window.details_label.config(
                    text=f"Время: {elapsed}с"
                )
                # Принудительно обновляем окно
                progress_window.update_idletasks()
            except Exception as e:
                # Игнорируем ошибки при обновлении (окно может быть закрыто)
                pass
    
    def _update_progress_window_from_data(self, progress_window, progress, status, current_file=None, elapsed=0):
        """Обновить окно прогресса из данных воркера"""
        if progress_window and progress_window.winfo_exists():
            if progress_window.cancelled:
                return
            try:
                progress_window.progress_var.set(progress)
                status_text = status
                if current_file:
                    # Обрезаем длинные имена файлов
                    file_name = os.path.basename(current_file)
                    if len(file_name) > 50:
                        file_name = file_name[:47] + "..."
                    status_text += f"\nТекущий файл: {file_name}"
                progress_window.status_label.config(text=status_text)
                progress_window.details_label.config(
                    text=f"Время: {elapsed}с"
                )
                # Принудительно обновляем окно
                progress_window.update_idletasks()
            except Exception:
                # Игнорируем ошибки при обновлении (окно может быть закрыто)
                pass
    
    def _finalize_progress_window(self, progress_window, success, error):
        """Завершить окно прогресса (вызывается из главного потока)"""
        if progress_window and progress_window.winfo_exists():
            if progress_window.cancelled:
                progress_window.progress_var.set(0)
                progress_window.status_label.config(text="Архивация отменена", fg='orange')
                progress_window.details_label.config(text="")
                progress_window.cancel_button.config(state=tk.DISABLED)
            elif success:
                progress_window.progress_var.set(100)
                progress_window.status_label.config(text="Архивация завершена!", fg='green')
                progress_window.details_label.config(text="")
                progress_window.cancel_button.config(text="Закрыть", command=progress_window.destroy)
            else:
                progress_window.status_label.config(text=f"Ошибка: {error[:50] if error else 'Неизвестная ошибка'}", fg='red')
                progress_window.details_label.config(text="")
                progress_window.cancel_button.config(text="Закрыть", command=progress_window.destroy)
    
    def _archive_with_tarfile(self, archive_path, items_to_archive, group_id=None, archive_name=None):
        """Архивация через Python tarfile (fallback)"""
        try:
            # Создаем временную директорию для сборки
            temp_dir = os.path.join(os.path.dirname(archive_path), '.temp_archive')
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Копируем элементы во временную директорию
                for item_path, arcname in items_to_archive:
                    if os.path.exists(item_path):
                        target_path = os.path.join(temp_dir, arcname)
                        if os.path.isdir(item_path):
                            shutil.copytree(item_path, target_path, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item_path, target_path)
                
                # НОВОЕ: Создаем файл конфигурации компонентов
                components_config = self._extract_components_for_group(group_id, items_to_archive)
                if components_config:
                    config_path = os.path.join(temp_dir, '.components_config.json')
                    config_data = {
                        'version': '1.0',
                        'components': components_config,
                        'metadata': {
                            'created': datetime.now().isoformat(),
                            'group_id': group_id or 'unknown',
                            'group_name': self.package_groups.get(group_id, {}).get('name', 'Unknown') if group_id else 'Unknown',
                            'archive_name': archive_name or os.path.basename(archive_path),
                            'items_count': len(items_to_archive)
                        }
                    }
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, indent=2, ensure_ascii=False)
                
                # Создаем архив из временной директории
                with tarfile.open(archive_path, 'w:gz') as tar:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            tar.add(file_path, arcname=arcname, recursive=False)
            finally:
                # Удаляем временную директорию
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            
            return True
        except Exception as e:
            print(f"Ошибка архивации через tarfile: {e}")
            return False
    
    def _extract_components_for_group(self, group_id, items_to_archive):
        """
        Извлечь конфигурации компонентов, связанных с группой
        
        Args:
            group_id: ID группы
            items_to_archive: Список элементов для архивации
        
        Returns:
            dict: Словарь {component_id: config} компонентов для этой группы
        """
        components_config = {}
        
        if not group_id or not COMPONENTS_CONFIG:
            return components_config
        
        # Получаем имя группы для поиска связанных компонентов
        group_info = self.package_groups.get(group_id, {})
        group_name = group_info.get('name', '')
        archive_name = group_info.get('archive_name', '')
        
        # Ищем компоненты, которые могут быть связаны с этой группой
        # По имени архива, имени группы, или по содержимому архива
        for component_id, config in COMPONENTS_CONFIG.items():
            # Проверяем различные признаки связи
            component_name = config.get('name', '')
            component_path = config.get('path', '')
            
            # Простая эвристика: если имя компонента содержит имя группы или наоборот
            if (group_name and group_name.lower() in component_name.lower()) or \
               (component_name and component_name.lower() in group_name.lower()):
                components_config[component_id] = config
                continue
            
            # Проверяем по имени архива
            if archive_name:
                archive_base = os.path.splitext(os.path.splitext(archive_name)[0])[0]  # Убираем .tar.gz
                if archive_base.lower() in component_id.lower() or \
                   archive_base.lower() in component_name.lower():
                    components_config[component_id] = config
                    continue
            
            # Проверяем по содержимому архива (имена файлов)
            archive_items = [item[1] for item in items_to_archive]  # Имена в архиве
            for item_name in archive_items:
                if item_name.lower() in component_id.lower() or \
                   item_name.lower() in component_name.lower():
                    components_config[component_id] = config
                    break
        
        # НОВОЕ: Включаем пакеты шаблонов Wine и их шаблоны
        # Если в архиве есть компоненты, связанные с Wine, включаем пакеты шаблонов
        wine_related = any('wine' in comp_id.lower() or 'wine' in config.get('name', '').lower() 
                          for comp_id, config in components_config.items())
        
        if wine_related:
            # Добавляем все пакеты шаблонов Wine
            for component_id, config in COMPONENTS_CONFIG.items():
                if config.get('category') == 'package' and config.get('package_type') == 'wine_templates':
                    components_config[component_id] = config
                    # Добавляем все шаблоны из пакета
                    package_templates = config.get('package_templates', [])
                    for template_id in package_templates:
                        if template_id in COMPONENTS_CONFIG:
                            components_config[template_id] = COMPONENTS_CONFIG[template_id]
        
        return components_config
    
    def save_config_to_archive(self, component_id, archive_path):
        """
        Сохранить конфигурацию компонента обратно в архив
        
        Args:
            component_id: ID компонента
            archive_path: Путь к архиву
        
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        if component_id not in COMPONENTS_CONFIG:
            return False
        
        try:
            # Создаем временную директорию для распаковки
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Распаковываем архив
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(temp_dir)
                
                # Обновляем конфигурацию в архиве
                config_path = os.path.join(temp_dir, '.components_config.json')
                
                if os.path.exists(config_path):
                    # Читаем существующую конфигурацию
                    with open(config_path, 'r', encoding='utf-8') as f:
                        archive_config = json.load(f)
                else:
                    # Создаем новую конфигурацию
                    archive_config = {
                        'version': '1.0',
                        'components': {},
                        'metadata': {
                            'created': datetime.now().isoformat(),
                            'archive_name': os.path.basename(archive_path)
                        }
                    }
                
                # Обновляем конфигурацию компонента
                archive_config['components'][component_id] = get_component_data(component_id)
                archive_config['metadata']['updated'] = datetime.now().isoformat()
                
                # Сохраняем обратно
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(archive_config, f, indent=2, ensure_ascii=False)
                
                # Пересоздаем архив
                with tarfile.open(archive_path, 'w:gz') as tar:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            tar.add(file_path, arcname=arcname, recursive=False)
                
                return True
            except Exception as inner_e:
                print(f"Ошибка при обработке архива: {inner_e}")
                return False
            finally:
                # Удаляем временную директорию
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации в архив: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def build_dependency_tree(self):
        """Строит дерево зависимостей компонентов
        
        ВАЖНО: dependencies - это компоненты, от которых зависит текущий компонент.
        Если компонент A имеет dependencies: [B, C], то B и C - родители A.
        Но для дерева отображения выбираем главного родителя (первая зависимость по приоритету).
        
        НОВОЕ: Пакеты шаблонов Wine отображаются как корневые узлы, шаблоны - как их дочерние элементы.
        """
        tree = {}
        # Первый проход: создаем узлы
        for component_id, config in COMPONENTS_CONFIG.items():
            tree[component_id] = {
                'config': config,
                'children': [],
                'main_parent': None  # Главный родитель для отображения в дереве
            }
        
        # Специальная обработка для пакетов шаблонов Wine
        # Связываем шаблоны с их пакетами
        for component_id, config in COMPONENTS_CONFIG.items():
            # Если это пакет шаблонов
            if config.get('category') == 'package' and config.get('package_type') == 'wine_templates':
                package_templates = config.get('package_templates', [])
                # Связываем шаблоны с пакетом
                for template_id in package_templates:
                    if template_id in tree:
                        # Шаблон становится дочерним элементом пакета
                        tree[template_id]['main_parent'] = component_id
                        tree[component_id]['children'].append(template_id)
        
        # Второй проход: связываем зависимости (для обычных компонентов)
        # Для каждого компонента ищем его главного родителя (первая зависимость по приоритету)
        for component_id, node in tree.items():
            config = node['config']
            
            # Пропускаем пакеты и шаблоны (они уже обработаны выше)
            if config.get('category') == 'package' and config.get('package_type') == 'wine_templates':
                continue
            if config.get('template') == True:
                continue
            
            dependencies = get_component_field(component_id, 'dependencies', [])
            if dependencies:
                # Сортируем зависимости по приоритету (выше приоритет = раньше в списке)
                sorted_deps = sorted(dependencies, 
                                   key=lambda x: get_component_field(x, 'sort_order', 999))
                # Главный родитель - первая зависимость (с наименьшим приоритетом)
                main_parent = sorted_deps[0]
                if main_parent in tree:
                    # Проверяем, что родитель не является шаблоном (шаблоны уже привязаны к пакетам)
                    parent_config = tree[main_parent]['config']
                    if not (parent_config.get('template') == True):
                        tree[component_id]['main_parent'] = main_parent
                        tree[main_parent]['children'].append(component_id)
        
        return tree
    
    def render_component(self, parent_item, component_id, dependency_tree, 
                        indent=0, is_last=False, prefix=""):
        """Рекурсивно отображает компонент в дереве с поддержкой сворачивания"""
        if component_id not in COMPONENTS_CONFIG:
            return
        
        config = get_component_data(component_id)
        if not config:
            return
        
        # Шаблоны отображаются только внутри пакетов
        # Если шаблон не имеет родителя-пакета, пропускаем его
        if config.get('template') == True:
            # Проверяем, есть ли у шаблона родитель-пакет
            main_parent = dependency_tree[component_id].get('main_parent')
            if main_parent:
                parent_config = get_component_data(main_parent)
                if parent_config and parent_config.get('category') == 'package' and \
                   parent_config.get('package_type') == 'wine_templates':
                    # Шаблон будет отображен как дочерний элемент пакета
                    pass  # Продолжаем обработку
                else:
                    return  # Пропускаем шаблон без пакета
            else:
                return  # Пропускаем шаблон без родителя
        
        # Получаем данные компонента
        component_name = get_component_field(component_id, 'name', component_id)
        category = get_component_field(component_id, 'category', 'unknown')
        sort_order = get_component_field(component_id, 'sort_order', 999)
        
        # Формируем имя для отображения (только название, без ID)
        display_name = component_name
        
        # Переводим категорию на русский
        category_translated = self.translate_value('category', category)
        
        # Добавляем элемент в дерево КАК ДОЧЕРНИЙ (это важно для сворачивания!)
        item_id = self.component_tree.insert(
            parent_item,  # Родительский элемент - это ключ для иерархии!
            'end', 
            text=display_name,
            values=(category_translated, '[---]'),
            tags=(category,),
            open=True  # По умолчанию развернуто для корневых элементов
        )
        
        # Сохраняем соответствие
        self.component_tree_item_to_id[item_id] = component_id
        
        # Рекурсивно отображаем дочерние компоненты
        children = dependency_tree[component_id]['children']
        # Сортируем дочерние компоненты по приоритету
        children.sort(key=lambda x: get_component_field(x, 'sort_order', 999))
        
        for i, child_id in enumerate(children):
            is_last_child = (i == len(children) - 1)
            # Передаем item_id как parent_item для создания иерархии
            self.render_component(item_id, child_id, dependency_tree, 
                                 indent + 1, is_last_child, prefix="")
    
    def update_component_tree(self, batch_size=10, start_index=0):
        """Обновить дерево компонентов (с постепенной загрузкой)"""
        # Очищаем дерево только при первой загрузке
        if start_index == 0:
            for item in self.component_tree.get_children():
                self.component_tree.delete(item)
            self.component_tree_item_to_id.clear()
            
            if not COMPONENTS_CONFIG:
                self.component_tree.insert('', 'end', text="COMPONENTS_CONFIG не загружен")
                return
            
            # Показываем индикатор загрузки
            self._loading_item_id = self.component_tree.insert('', 'end', text="Загрузка компонентов...", 
                                                     values=('', 'Загрузка'))
            self.root.update_idletasks()
        
        # Строим дерево зависимостей (только один раз)
        if start_index == 0:
            self._dependency_tree_cache = self.build_dependency_tree()
            dependency_tree = self._dependency_tree_cache
            
            # Находим корневые компоненты (без родителя)
            # Пакеты шаблонов имеют приоритет и отображаются первыми
            root_components = []
            package_components = []
            for component_id, node in dependency_tree.items():
                if node['main_parent'] is None:
                    config = get_component_data(component_id)
                    sort_order = get_component_field(component_id, 'sort_order', 999)
                    # Отделяем пакеты от обычных компонентов
                    if config and config.get('category') == 'package' and config.get('package_type') == 'wine_templates':
                        package_components.append((component_id, sort_order))
                    else:
                        root_components.append((component_id, sort_order))
            
            # Сортируем по приоритету
            package_components.sort(key=lambda x: x[1])
            root_components.sort(key=lambda x: x[1])
            
            # Объединяем: сначала пакеты, потом остальные компоненты
            self._all_root_components = package_components + root_components
            
            # Удаляем индикатор загрузки
            if hasattr(self, '_loading_item_id'):
                try:
                    self.component_tree.delete(self._loading_item_id)
                    delattr(self, '_loading_item_id')
                except:
                    pass
        
        dependency_tree = self._dependency_tree_cache
        all_root_components = self._all_root_components
        
        # Отображаем компоненты порциями
        end_index = min(start_index + batch_size, len(all_root_components))
        
        for i in range(start_index, end_index):
            component_id, _ = all_root_components[i]
            is_last = (i == len(all_root_components) - 1)
            self.render_component('', component_id, dependency_tree, 
                                 indent=0, is_last=is_last, prefix="")
        
        # Если есть еще компоненты, загружаем следующую порцию
        if end_index < len(all_root_components):
            self.root.after(50, lambda: self.update_component_tree(batch_size, end_index))
        else:
            # Все компоненты загружены
            pass
        
        # Настраиваем цвета тегов с единым размером шрифта 10 для всех элементов
        self.component_tree.tag_configure('system', foreground='blue', font=('TkDefaultFont', 10))
        self.component_tree.tag_configure('application', foreground='green', font=('TkDefaultFont', 10))
        self.component_tree.tag_configure('library', foreground='purple', font=('TkDefaultFont', 10))
        self.component_tree.tag_configure('tool', foreground='orange', font=('TkDefaultFont', 10))
        self.component_tree.tag_configure('config', foreground='gray', font=('TkDefaultFont', 10))
        self.component_tree.tag_configure('plugin', foreground='brown', font=('TkDefaultFont', 10))
        self.component_tree.tag_configure('cache', foreground='darkgray', font=('TkDefaultFont', 10))
        self.component_tree.tag_configure('package', foreground='darkblue', font=('TkDefaultFont', 10, 'bold'))
        self.component_tree.tag_configure('wine_application_template', foreground='darkgreen', font=('TkDefaultFont', 10, 'italic'))
        self.component_tree.tag_configure('unknown', foreground='black', font=('TkDefaultFont', 10))
        
        # Теги для визуализации перетаскивания
        self.component_tree.tag_configure('drag_target', background='lightblue', foreground='darkblue')
        self.component_tree.tag_configure('drag_invalid', background='lightcoral', foreground='darkred')
        
        # Обновляем состояние кнопок перемещения после обновления дерева
        self._update_move_buttons_state()
        
        # Восстанавливаем выбор компонента и обновляем поля формы, если компонент был выбран
        if hasattr(self, 'current_component_id') and self.current_component_id:
            # Небольшая задержка для завершения обновления дерева
            self.root.after_idle(lambda: self.select_component_in_tree(self.current_component_id))
    
    def expand_all_components(self):
        """Развернуть все узлы дерева"""
        def expand_item(item_id):
            """Рекурсивно разворачивает узел и все его дочерние узлы"""
            try:
                self.component_tree.item(item_id, open=True)
                for child_id in self.component_tree.get_children(item_id):
                    expand_item(child_id)
            except:
                pass
        
        # Разворачиваем все корневые элементы
        for item_id in self.component_tree.get_children():
            expand_item(item_id)
    
    def collapse_all_components(self):
        """Свернуть все узлы дерева"""
        def collapse_item(item_id):
            """Рекурсивно сворачивает узел и все его дочерние узлы"""
            try:
                self.component_tree.item(item_id, open=False)
                for child_id in self.component_tree.get_children(item_id):
                    collapse_item(child_id)
            except:
                pass
        
        # Сворачиваем все корневые элементы
        for item_id in self.component_tree.get_children():
            collapse_item(item_id)
    
    def move_component_up(self):
        """Переместить выбранный компонент вверх с изменением sort_order"""
        selected_items = self.component_tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        component_id = self.component_tree_item_to_id.get(item_id)
        if not component_id or component_id not in COMPONENTS_CONFIG:
            return
        
        # Строим дерево зависимостей для проверки уровня элемента
        dependency_tree = self.build_dependency_tree()
        
        # Проверяем, является ли элемент корневым (без родителя)
        if dependency_tree[component_id]['main_parent'] is not None:
            # Это дочерний элемент - перемещение запрещено
            import tkinter.messagebox as messagebox
            messagebox.showinfo("Информация", 
                              "Дочерние элементы можно перемещать только через перетаскивание (Drag and Drop)")
            return
        
        # Получаем текущий sort_order
        current_sort = get_component_field(component_id, 'sort_order', 999)
        
        # Определяем тип компонента (пакет или обычный)
        config = get_component_data(component_id)
        is_package = config and config.get('category') == 'package' and config.get('package_type') == 'wine_templates'
        
        # Находим корневые компоненты того же типа
        root_components = []
        for comp_id, node in dependency_tree.items():
            if node['main_parent'] is None:
                comp_config = get_component_data(comp_id)
                comp_is_package = comp_config and comp_config.get('category') == 'package' and comp_config.get('package_type') == 'wine_templates'
                if comp_is_package == is_package:
                    sort_order = get_component_field(comp_id, 'sort_order', 999)
                    root_components.append((comp_id, sort_order))
        
        # Сортируем по sort_order
        root_components.sort(key=lambda x: x[1])
        
        # Находим позицию текущего компонента
        current_index = None
        for i, (comp_id, _) in enumerate(root_components):
            if comp_id == component_id:
                current_index = i
                break
        
        if current_index is None or current_index == 0:
            return  # Уже вверху или не найден
        
        # Меняем местами sort_order с предыдущим компонентом
        prev_component_id, prev_sort = root_components[current_index - 1]
        
        # Сохраняем состояние для отмены (включая информацию о пакете и его шаблонах)
        undo_data = {
            'action': 'move_component',
            'component_id': component_id,
            'neighbor_id': prev_component_id,
            'old_sort_order': current_sort,
            'old_neighbor_sort_order': prev_sort,
            'direction': 'up',
            'description': f"Перемещение компонента '{get_component_field(component_id, 'name', component_id)}' вверх"
        }
        
        # Если это пакет, сохраняем информацию о его шаблонах для отмены
        if is_package:
            undo_data['is_package'] = True
            undo_data['package_templates'] = config.get('package_templates', []).copy()
        
        self.add_to_undo_history(undo_data)
        
        # Обновляем sort_order
        if component_id in COMPONENTS_CONFIG:
            COMPONENTS_CONFIG[component_id]['sort_order'] = prev_sort
        if prev_component_id in COMPONENTS_CONFIG:
            COMPONENTS_CONFIG[prev_component_id]['sort_order'] = current_sort
        
        # Обновляем дерево
        self.update_component_tree()
        
        # Восстанавливаем выделение
        for item_id, comp_id in self.component_tree_item_to_id.items():
            if comp_id == component_id:
                self.component_tree.selection_set(item_id)
                self.component_tree.see(item_id)
                break
    
    def move_component_down(self):
        """Переместить выбранный компонент вниз с изменением sort_order"""
        selected_items = self.component_tree.selection()
        if not selected_items:
            return
        
        item_id = selected_items[0]
        component_id = self.component_tree_item_to_id.get(item_id)
        if not component_id or component_id not in COMPONENTS_CONFIG:
            return
        
        # Строим дерево зависимостей для проверки уровня элемента
        dependency_tree = self.build_dependency_tree()
        
        # Проверяем, является ли элемент корневым (без родителя)
        if dependency_tree[component_id]['main_parent'] is not None:
            # Это дочерний элемент - перемещение запрещено
            import tkinter.messagebox as messagebox
            messagebox.showinfo("Информация", 
                              "Дочерние элементы можно перемещать только через перетаскивание (Drag and Drop)")
            return
        
        # Получаем текущий sort_order
        current_sort = get_component_field(component_id, 'sort_order', 999)
        
        # Определяем тип компонента (пакет или обычный)
        config = get_component_data(component_id)
        is_package = config and config.get('category') == 'package' and config.get('package_type') == 'wine_templates'
        
        # Находим корневые компоненты того же типа
        root_components = []
        for comp_id, node in dependency_tree.items():
            if node['main_parent'] is None:
                comp_config = get_component_data(comp_id)
                comp_is_package = comp_config and comp_config.get('category') == 'package' and comp_config.get('package_type') == 'wine_templates'
                if comp_is_package == is_package:
                    sort_order = get_component_field(comp_id, 'sort_order', 999)
                    root_components.append((comp_id, sort_order))
        
        # Сортируем по sort_order
        root_components.sort(key=lambda x: x[1])
        
        # Находим позицию текущего компонента
        current_index = None
        for i, (comp_id, _) in enumerate(root_components):
            if comp_id == component_id:
                current_index = i
                break
        
        if current_index is None or current_index == len(root_components) - 1:
            return  # Уже внизу или не найден
        
        # Меняем местами sort_order со следующим компонентом
        next_component_id, next_sort = root_components[current_index + 1]
        
        # Сохраняем состояние для отмены (включая информацию о пакете и его шаблонах)
        undo_data = {
            'action': 'move_component',
            'component_id': component_id,
            'neighbor_id': next_component_id,
            'old_sort_order': current_sort,
            'old_neighbor_sort_order': next_sort,
            'direction': 'down',
            'description': f"Перемещение компонента '{get_component_field(component_id, 'name', component_id)}' вниз"
        }
        
        # Если это пакет, сохраняем информацию о его шаблонах для отмены
        if is_package:
            undo_data['is_package'] = True
            undo_data['package_templates'] = config.get('package_templates', []).copy()
        
        self.add_to_undo_history(undo_data)
        
        # Обновляем sort_order
        if component_id in COMPONENTS_CONFIG:
            COMPONENTS_CONFIG[component_id]['sort_order'] = next_sort
        if next_component_id in COMPONENTS_CONFIG:
            COMPONENTS_CONFIG[next_component_id]['sort_order'] = current_sort
        
        # Обновляем дерево
        self.update_component_tree()
        
        # Восстанавливаем выделение
        for item_id, comp_id in self.component_tree_item_to_id.items():
            if comp_id == component_id:
                self.component_tree.selection_set(item_id)
                self.component_tree.see(item_id)
                break
    
    def on_drag_start(self, event):
        """Начало перетаскивания компонента"""
        item = self.component_tree.identify_row(event.y)
        if item:
            # Очищаем все предыдущие подсветки
            self.clear_all_drag_highlights()
            
            self.drag_start_item = item
            import time
            self.drag_start_time = time.time()
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.drag_highlight_item = None
            self.drag_original_tags = {}  # Очищаем словарь оригинальных тегов
    
    def clear_all_drag_highlights(self):
        """Очистить все подсветки перетаскивания со всех элементов дерева"""
        # Сначала восстанавливаем элементы с сохраненными оригинальными тегами
        for item_id, original_tags in self.drag_original_tags.items():
            try:
                # Восстанавливаем оригинальные теги
                if original_tags:
                    self.component_tree.item(item_id, tags=original_tags)
                else:
                    # Если тегов не было, убираем теги подсветки
                    item_config = self.component_tree.item(item_id)
                    current_tags = item_config.get('tags', ())
                    clean_tags = [tag for tag in current_tags if tag not in ('drag_target', 'drag_invalid')]
                    self.component_tree.item(item_id, tags=clean_tags if clean_tags else ())
                # Восстанавливаем статус
                self.component_tree.set(item_id, 'status', '[---]')
            except:
                pass
        
        # Дополнительно: проходим по всем элементам дерева и убираем теги подсветки
        # (на случай, если какие-то элементы не были в словаре)
        def clear_item_tags(item_id):
            try:
                item_config = self.component_tree.item(item_id)
                current_tags = item_config.get('tags', ())
                if current_tags:
                    # Убираем теги подсветки
                    clean_tags = [tag for tag in current_tags if tag not in ('drag_target', 'drag_invalid')]
                    if len(clean_tags) != len(current_tags):
                        # Если были теги подсветки, обновляем
                        self.component_tree.item(item_id, tags=clean_tags if clean_tags else ())
                        self.component_tree.set(item_id, 'status', '[---]')
                # Рекурсивно обрабатываем дочерние элементы
                for child_id in self.component_tree.get_children(item_id):
                    clear_item_tags(child_id)
            except:
                pass
        
        # Обрабатываем все корневые элементы
        for root_item in self.component_tree.get_children():
            clear_item_tags(root_item)
        
        self.drag_original_tags.clear()
        self.drag_highlight_item = None
    
    def _update_move_buttons_state(self):
        """Обновить состояние кнопок перемещения в зависимости от выбранного элемента"""
        if not hasattr(self, 'move_up_button') or not hasattr(self, 'move_down_button'):
            return
        
        selected_items = self.component_tree.selection()
        if not selected_items:
            # Нет выбора - отключаем кнопки
            self.move_up_button.config(state=tk.DISABLED)
            self.move_down_button.config(state=tk.DISABLED)
            return
        
        item_id = selected_items[0]
        component_id = self.component_tree_item_to_id.get(item_id)
        
        if not component_id or component_id not in COMPONENTS_CONFIG:
            # Невалидный выбор - отключаем кнопки
            self.move_up_button.config(state=tk.DISABLED)
            self.move_down_button.config(state=tk.DISABLED)
            return
        
        # Проверяем, является ли элемент корневым (без родителя)
        dependency_tree = self.build_dependency_tree()
        is_root = dependency_tree.get(component_id, {}).get('main_parent') is None
        
        # Включаем/отключаем кнопки в зависимости от уровня элемента
        self.move_up_button.config(state=tk.NORMAL if is_root else tk.DISABLED)
        self.move_down_button.config(state=tk.NORMAL if is_root else tk.DISABLED)
    
    def on_drag_motion(self, event):
        """Перетаскивание компонента с визуальной обратной связью"""
        if not self.drag_start_item:
            return
        
        # Проверяем, что мышь переместилась достаточно далеко (минимум 5 пикселей)
        import math
        distance = math.sqrt((event.x - self.drag_start_x)**2 + (event.y - self.drag_start_y)**2)
        if distance < 5:
            return  # Слишком маленькое перемещение, это еще не перетаскивание
        
        # Изменяем курсор для визуальной обратной связи
        self.component_tree.config(cursor='hand2')
        
        # Убираем предыдущую подсветку
        if self.drag_highlight_item:
            try:
                # Восстанавливаем оригинальные теги предыдущего элемента
                if self.drag_highlight_item in self.drag_original_tags:
                    original_tags = self.drag_original_tags[self.drag_highlight_item]
                    self.component_tree.item(self.drag_highlight_item, tags=original_tags)
                    del self.drag_original_tags[self.drag_highlight_item]
                self.component_tree.set(self.drag_highlight_item, 'status', '[---]')
            except:
                pass
            self.drag_highlight_item = None
        
        # Определяем элемент под курсором
        item = self.component_tree.identify_row(event.y)
        
        if item and item != self.drag_start_item:
            # Сохраняем оригинальные теги элемента перед подсветкой
            if item not in self.drag_original_tags:
                try:
                    item_config = self.component_tree.item(item)
                    original_tags = item_config.get('tags', ())
                    # Убираем теги подсветки из оригинальных, если они есть
                    clean_original = tuple(tag for tag in original_tags if tag not in ('drag_target', 'drag_invalid'))
                    self.drag_original_tags[item] = clean_original
                except:
                    self.drag_original_tags[item] = ()
            
            # Проверяем, что это валидная цель для перетаскивания
            source_component_id = self.component_tree_item_to_id.get(self.drag_start_item)
            target_component_id = self.component_tree_item_to_id.get(item)
            
            if source_component_id and target_component_id and source_component_id != target_component_id:
                # Подсвечиваем целевую строку
                try:
                    self.component_tree.set(item, 'status', '[→]')
                    self.drag_highlight_item = item
                    # Добавляем тег подсветки к существующим тегам
                    original_tags = self.drag_original_tags.get(item, ())
                    new_tags = list(original_tags) + ['drag_target']
                    self.component_tree.item(item, tags=tuple(new_tags))
                except:
                    pass
            else:
                # Недопустимая цель - показываем запрет
                try:
                    self.component_tree.set(item, 'status', '[✗]')
                    self.drag_highlight_item = item
                    # Добавляем тег запрета к существующим тегам
                    original_tags = self.drag_original_tags.get(item, ())
                    new_tags = list(original_tags) + ['drag_invalid']
                    self.component_tree.item(item, tags=tuple(new_tags))
                except:
                    pass
        else:
            # Курсор не над элементом или над исходным элементом
            self.drag_highlight_item = None
    
    def on_drag_release(self, event):
        """Завершение перетаскивания - связывание компонентов"""
        # Восстанавливаем курсор
        self.component_tree.config(cursor='')
        
        # Очищаем все подсветки
        self.clear_all_drag_highlights()
        
        if not self.drag_start_item:
            return
        
        # Проверяем, что мышь переместилась достаточно далеко (минимум 5 пикселей)
        import math
        distance = math.sqrt((event.x - self.drag_start_x)**2 + (event.y - self.drag_start_y)**2)
        if distance < 5:
            # Это был просто клик, не перетаскивание
            self.drag_start_item = None
            return
        
        target_item = self.component_tree.identify_row(event.y)
        
        if not target_item or target_item == self.drag_start_item:
            self.drag_start_item = None
            return
        
        # Получаем ID компонентов
        source_component_id = self.component_tree_item_to_id.get(self.drag_start_item)
        target_component_id = self.component_tree_item_to_id.get(target_item)
        
        if not source_component_id or not target_component_id:
            self.drag_start_item = None
            return
        
        if source_component_id == target_component_id:
            self.drag_start_item = None
            return
        
        # Проверяем, что компоненты существуют
        if source_component_id not in COMPONENTS_CONFIG or target_component_id not in COMPONENTS_CONFIG:
            self.drag_start_item = None
            return
        
        # Сохраняем состояние для отмены (до изменения)
        old_dependencies = COMPONENTS_CONFIG[source_component_id].get('dependencies', []).copy()
        
        # Добавляем зависимость: source зависит от target
        if 'dependencies' not in COMPONENTS_CONFIG[source_component_id]:
            COMPONENTS_CONFIG[source_component_id]['dependencies'] = []
        
        dependencies = COMPONENTS_CONFIG[source_component_id]['dependencies']
        if target_component_id not in dependencies:
            dependencies.append(target_component_id)
            COMPONENTS_CONFIG[source_component_id]['dependencies'] = dependencies
            
            # Сохраняем действие в историю отмены
            self.add_to_undo_history({
                'action': 'add_dependency',
                'component_id': source_component_id,
                'old_value': old_dependencies,
                'new_value': dependencies.copy(),
                'description': f"Добавлена зависимость '{get_component_field(target_component_id, 'name', target_component_id)}'"
            })
            
            # Обновляем дерево
            self.update_component_tree()
            
            # Восстанавливаем выделение
            for item_id, comp_id in self.component_tree_item_to_id.items():
                if comp_id == source_component_id:
                    self.component_tree.selection_set(item_id)
                    self.component_tree.see(item_id)
                    break
            
            # Показываем сообщение
            import tkinter.messagebox as messagebox
            source_name = get_component_field(source_component_id, 'name', source_component_id)
            target_name = get_component_field(target_component_id, 'name', target_component_id)
            messagebox.showinfo("Зависимость добавлена", 
                              f"Компонент '{source_name}' теперь зависит от '{target_name}'")
        
        self.drag_start_item = None
    
    def add_to_undo_history(self, action_data):
        """Добавить действие в историю отмены"""
        self.undo_history.append(action_data)
        
        # Ограничиваем размер истории
        if len(self.undo_history) > self.max_undo_history:
            self.undo_history.pop(0)
        
        # Активируем кнопку отмены
        self.undo_button.config(state=tk.NORMAL)
    
    def undo_last_action(self):
        """Отменить последнее действие"""
        if not self.undo_history:
            return
        
        # Получаем последнее действие
        last_action = self.undo_history.pop()
        
        try:
            if last_action['action'] == 'add_dependency':
                # Отменяем добавление зависимости
                component_id = last_action['component_id']
                if component_id in COMPONENTS_CONFIG:
                    COMPONENTS_CONFIG[component_id]['dependencies'] = last_action['old_value'].copy()
                    # Обновляем дерево
                    self.update_component_tree()
                    # Восстанавливаем выделение
                    for item_id, comp_id in self.component_tree_item_to_id.items():
                        if comp_id == component_id:
                            self.component_tree.selection_set(item_id)
                            self.component_tree.see(item_id)
                            break
            
            elif last_action['action'] == 'save_config':
                # Отменяем сохранение конфигурации
                component_id = last_action['component_id']
                if component_id in COMPONENTS_CONFIG:
                    # Восстанавливаем старое значение
                    field_name = last_action['field_name']
                    COMPONENTS_CONFIG[component_id][field_name] = last_action['old_value']
                    # Обновляем дерево и панель конфигурации
                    self.update_component_tree()
                    if self.current_component_id == component_id:
                        self.on_component_select(None)
            
            elif last_action['action'] == 'move_component':
                # Отменяем перемещение компонента
                component_id = last_action['component_id']
                if component_id in COMPONENTS_CONFIG:
                    COMPONENTS_CONFIG[component_id]['sort_order'] = last_action['old_sort_order']
                    # Восстанавливаем sort_order соседнего компонента
                    neighbor_id = last_action.get('neighbor_id')
                    if neighbor_id and neighbor_id in COMPONENTS_CONFIG:
                        COMPONENTS_CONFIG[neighbor_id]['sort_order'] = last_action['old_neighbor_sort_order']
                    # Обновляем дерево
                    self.update_component_tree()
                    # Восстанавливаем выделение
                    for item_id, comp_id in self.component_tree_item_to_id.items():
                        if comp_id == component_id:
                            self.component_tree.selection_set(item_id)
                            self.component_tree.see(item_id)
                            break
            
            # Показываем сообщение об отмене
            import tkinter.messagebox as messagebox
            messagebox.showinfo("Действие отменено", 
                              f"Отменено: {last_action.get('description', 'Последнее действие')}")
        
        except Exception as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Ошибка отмены", f"Не удалось отменить действие: {e}")
            import traceback
            traceback.print_exc()
        
        # Обновляем состояние кнопки отмены
        if not self.undo_history:
            self.undo_button.config(state=tk.DISABLED)
    
    def filter_components(self, event=None):
        """Фильтровать компоненты по поисковому запросу"""
        search_text = self.component_search.get().lower()
        
        if not search_text:
            # Если поиск пустой, показываем все компоненты
            self.update_component_tree()
            return
        
        # Очищаем дерево
        for item in self.component_tree.get_children():
            self.component_tree.delete(item)
        self.component_tree_item_to_id.clear()
        
        if not COMPONENTS_CONFIG:
            self.component_tree.insert('', 'end', text="COMPONENTS_CONFIG не загружен")
            return
        
        # Строим дерево зависимостей
        dependency_tree = self.build_dependency_tree()
        
        # Находим корневые компоненты
        root_components = []
        for component_id, node in dependency_tree.items():
            if node['main_parent'] is None:
                sort_order = get_component_field(component_id, 'sort_order', 999)
                root_components.append((component_id, sort_order))
        
        root_components.sort(key=lambda x: x[1])
        
        # Функция для проверки совпадения компонента или его детей
        def matches_search(component_id):
            """Проверяет, совпадает ли компонент или его дети с поисковым запросом"""
            config = get_component_data(component_id)
            if not config:
                return False
            
            component_name = get_component_field(component_id, 'name', component_id)
            if search_text in component_id.lower() or search_text in component_name.lower():
                return True
            
            # Проверяем дочерние компоненты
            for child_id in dependency_tree[component_id]['children']:
                if matches_search(child_id):
                    return True
            
            return False
        
        # Отображаем только совпадающие компоненты
        for i, (component_id, _) in enumerate(root_components):
            if matches_search(component_id):
                is_last = (i == len(root_components) - 1)
                self.render_component('', component_id, dependency_tree, 
                                     indent=0, is_last=is_last, prefix="")
        
        # Обновляем состояние кнопок перемещения после фильтрации
        self._update_move_buttons_state()
    
    def get_field_label(self, field_name):
        """Получить русское название поля"""
        labels = {
            'name': 'Название',
            'command_name': 'Имя команды',
            'path': 'Путь',
            'category': 'Категория',
            'dependencies': 'Зависимости',
            'check_paths': 'Пути проверки',
            'install_method': 'Метод установки',
            'uninstall_method': 'Метод удаления',
            'gui_selectable': 'Выбираемый в GUI',
            'description': 'Описание',
            'sort_order': 'Порядок сортировки',
            'download_url': 'URL загрузки',
            'download_url_x86': 'URL загрузки (x86)',
            'download_url_x64': 'URL загрузки (x64)',
            'download_url_32': 'URL загрузки (32-bit)',
            'download_url_64': 'URL загрузки (64-bit)',
            'download_sha256': 'SHA256 хеш',
            'download_filename': 'Имя файла загрузки',
            'source_priority': 'Приоритет источника',
            'source_fallback': 'Резервный источник',
            'template': 'Шаблон',
            'wineprefix_path': 'Путь к WINEPREFIX',
            'package_file': 'Файл пакета',
            'apt_packages': 'APT пакеты',
            'wine_packages': 'Wine пакеты',
            'winetricks_packages': 'Winetricks пакеты',
            'environment_variables': 'Переменные окружения',
            'registry_keys': 'Ключи реестра',
            'files_to_copy': 'Файлы для копирования',
            'directories_to_create': 'Директории для создания',
            'post_install_commands': 'Команды после установки',
            'pre_uninstall_commands': 'Команды перед удалением',
            'post_uninstall_commands': 'Команды после удаления',
            'package_type': 'Тип пакета',
            'package_templates': 'Шаблоны в пакете',
            'target_wineprefixes': 'Целевые WINEPREFIX',
            'package_category': 'Категория пакета',
            'auto_generated': 'Автоматически создан',
            'version': 'Версия',
            'template_groups': 'Группы шаблона',
        }
        return labels.get(field_name, field_name)
    
    def translate_value(self, field_name, value):
        """Перевести значение поля на русский язык"""
        if value is None:
            return ''
        
        # Перевод категорий
        if field_name == 'category':
            category_translations = {
                'system': 'Система',
                'application': 'Приложение',
                'library': 'Библиотека',
                'tool': 'Инструмент',
                'config': 'Конфигурация',
                'plugin': 'Плагин',
                'cache': 'Кэш',
                'desktop_shortcut': 'Ярлык рабочего стола',
                'system_config': 'Системная конфигурация',
                'apt_packages': 'APT пакеты',
                'wine_packages': 'Wine пакеты',
                'wine_environment': 'Окружение Wine',
                'winetricks': 'Winetricks',
                'package': 'Пакет',
                'wine_application_template': 'Шаблон Wine приложения',
                'unknown': 'Неизвестно',
            }
            return category_translations.get(str(value), str(value))
        
        # Перевод методов установки/удаления
        if field_name in ['install_method', 'uninstall_method']:
            method_translations = {
                'apt': 'APT',
                'wine': 'Wine',
                'winetricks': 'Winetricks',
                'copy': 'Копирование',
                'symlink': 'Символическая ссылка',
                'script': 'Скрипт',
                'manual': 'Вручную',
                'none': 'Нет',
            }
            return method_translations.get(str(value), str(value))
        
        # Перевод приоритета источника
        if field_name == 'source_priority':
            priority_translations = {
                'archive': 'Архив',
                'download': 'Загрузка',
                'local': 'Локальный',
                'network': 'Сеть',
            }
            return priority_translations.get(str(value), str(value))
        
        # Для булевых значений
        if isinstance(value, bool):
            return 'Да' if value else 'Нет'
        
        return value
    
    def add_copy_paste_menu(self, widget):
        """Добавить контекстное меню с копированием/вставкой к виджету"""
        def show_context_menu(event):
            menu = tk.Menu(self.root, tearoff=0)
            
            # Копирование
            def copy_text():
                try:
                    if isinstance(widget, tk.Text):
                        text = widget.get('1.0', tk.END).rstrip('\n')
                    elif isinstance(widget, ttk.Entry):
                        text = widget.get()
                    elif isinstance(widget, ttk.Combobox):
                        text = widget.get()
                    else:
                        return
                    
                    if text:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(text)
                except Exception as e:
                    print(f"Ошибка копирования: {e}")
            
            # Вставка
            def paste_text():
                try:
                    text = self.root.clipboard_get()
                    if not text:
                        return
                    
                    if isinstance(widget, tk.Text):
                        # Удаляем выделенный текст или вставляем в позицию курсора
                        try:
                            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                        except:
                            pass
                        widget.insert(tk.INSERT, text)
                    elif isinstance(widget, ttk.Entry):
                        # Удаляем выделенный текст или вставляем в позицию курсора
                        try:
                            start = widget.index(tk.SEL_FIRST)
                            end = widget.index(tk.SEL_LAST)
                            widget.delete(start, end)
                            widget.insert(start, text)
                        except:
                            widget.insert(tk.INSERT, text)
                    elif isinstance(widget, ttk.Combobox):
                        widget.set(text)
                except Exception as e:
                    print(f"Ошибка вставки: {e}")
            
            menu.add_command(label="Копировать (Ctrl+C)", command=copy_text)
            menu.add_command(label="Вставить (Ctrl+V)", command=paste_text)
            menu.add_separator()
            menu.add_command(label="Выделить всё (Ctrl+A)", 
                           command=lambda: widget.event_generate("<<SelectAll>>"))
            
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
        
        # Привязываем контекстное меню
        if sys.platform == "darwin":  # macOS
            widget.bind('<Button-2>', show_context_menu)
            widget.bind('<Control-Button-1>', show_context_menu)
        else:
            widget.bind('<Button-3>', show_context_menu)
        
        # Привязываем горячие клавиши
        def on_copy(event):
            try:
                if isinstance(widget, tk.Text):
                    text = widget.get('1.0', tk.END).rstrip('\n')
                elif isinstance(widget, ttk.Entry):
                    text = widget.get()
                elif isinstance(widget, ttk.Combobox):
                    text = widget.get()
                else:
                    return
                
                if text:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
                return "break"
            except:
                return "break"
        
        def on_paste(event):
            try:
                text = self.root.clipboard_get()
                if not text:
                    return "break"
                
                if isinstance(widget, tk.Text):
                    try:
                        widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    except:
                        pass
                    widget.insert(tk.INSERT, text)
                elif isinstance(widget, ttk.Entry):
                    try:
                        start = widget.index(tk.SEL_FIRST)
                        end = widget.index(tk.SEL_LAST)
                        widget.delete(start, end)
                        widget.insert(start, text)
                    except:
                        widget.insert(tk.INSERT, text)
                elif isinstance(widget, ttk.Combobox):
                    widget.set(text)
                return "break"
            except:
                return "break"
        
        widget.bind('<Control-c>', on_copy)
        widget.bind('<Command-c>', on_copy)  # macOS
        widget.bind('<Control-v>', on_paste)
        widget.bind('<Command-v>', on_paste)  # macOS
    
    def create_config_field(self, parent, field_name, value, row, max_label_width=None):
        """Создать поле для редактирования значения конфигурации"""
        label_text = self.get_field_label(field_name)
        label = ttk.Label(parent, text=f"{label_text}:", anchor='w')
        # Используем динамическую ширину если указана, иначе фиксированную для совместимости
        if max_label_width:
            # Вычисляем ширину в символах (примерно)
            label.config(width=max_label_width)
        label.grid(row=row, column=0, sticky='w', padx=5, pady=2)
        
        # Определяем тип значения и создаем соответствующий виджет
        if isinstance(value, bool):
            var = tk.BooleanVar(value=value)
            # Для булевых значений показываем чекбокс с текстом
            widget = ttk.Checkbutton(parent, variable=var, text='')
            widget.grid(row=row, column=1, sticky='w', padx=5, pady=2)
            self.component_config_fields[field_name] = ('bool', var)
        
        elif isinstance(value, int):
            entry = ttk.Entry(parent)
            entry.insert(0, str(value))
            entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
            self.add_copy_paste_menu(entry)
            self.component_config_fields[field_name] = ('int', entry)
        
        elif isinstance(value, float):
            entry = ttk.Entry(parent)
            entry.insert(0, str(value))
            entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
            self.add_copy_paste_menu(entry)
            self.component_config_fields[field_name] = ('float', entry)
        
        elif isinstance(value, list):
            # Специальная обработка для полей пакетов
            if field_name == 'package_templates':
                # Для списка шаблонов в пакете - используем многострочное поле с ID шаблонов
                frame = ttk.Frame(parent)
                frame.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
                
                # Получаем список всех доступных шаблонов для подсказки
                available_templates = [comp_id for comp_id, comp_config in COMPONENTS_CONFIG.items() 
                                       if comp_config.get('template') == True and 
                                       comp_config.get('category') == 'wine_application_template']
                
                text_widget = tk.Text(frame, height=min(len(value) + 1, 5), wrap=tk.WORD)
                text_widget.insert(1.0, '\n'.join(value))
                text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                text_widget.configure(yscrollcommand=scrollbar.set)
                
                self.add_copy_paste_menu(text_widget)
                
                # Добавляем подсказку
                hint_label = ttk.Label(parent, text=f"Доступные шаблоны: {', '.join(available_templates[:5])}{'...' if len(available_templates) > 5 else ''}", 
                                       font=('TkDefaultFont', 8), foreground='gray')
                hint_label.grid(row=row+1, column=1, sticky='w', padx=5, pady=0)
                
                self.component_config_fields[field_name] = ('list', text_widget)
                # Сохраняем информацию о дополнительной строке для вызывающего кода
                self._last_field_extra_row = True
                return
                
            elif field_name == 'target_wineprefixes':
                # Для списка целевых wineprefix - используем многострочное поле
                frame = ttk.Frame(parent)
                frame.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
                
                # Получаем список всех доступных wineprefix для подсказки
                available_wineprefixes = get_all_wineprefixes(COMPONENTS_CONFIG)
                
                text_widget = tk.Text(frame, height=min(len(value) + 1, 5), wrap=tk.WORD)
                text_widget.insert(1.0, '\n'.join(value))
                text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                text_widget.configure(yscrollcommand=scrollbar.set)
                
                self.add_copy_paste_menu(text_widget)
                
                # Добавляем подсказку
                hint_label = ttk.Label(parent, text=f"Доступные wineprefix: {', '.join(available_wineprefixes)}", 
                                       font=('TkDefaultFont', 8), foreground='gray')
                hint_label.grid(row=row+1, column=1, sticky='w', padx=5, pady=0)
                
                self.component_config_fields[field_name] = ('list', text_widget)
                # Сохраняем информацию о дополнительной строке для вызывающего кода
                self._last_field_extra_row = True
                return
            
            # Для обычных списков используем многострочное текстовое поле
            frame = ttk.Frame(parent)
            frame.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
            
            # Переводим элементы списка если это зависимости (компоненты)
            if field_name == 'dependencies':
                # Для зависимостей оставляем как есть (это ID компонентов)
                display_items = [str(item) for item in value]
            else:
                # Для других списков переводим значения
                display_items = [str(self.translate_value(field_name, item)) for item in value]
            
            text_widget = tk.Text(frame, height=min(len(value) + 1, 5), wrap=tk.WORD)
            text_widget.insert(1.0, '\n'.join(display_items))
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            self.add_copy_paste_menu(text_widget)
            
            self.component_config_fields[field_name] = ('list', text_widget)
        
        elif isinstance(value, dict):
            # Для словарей используем многострочное текстовое поле с JSON
            frame = ttk.Frame(parent)
            frame.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
            
            text_widget = tk.Text(frame, height=min(len(str(value).split('\n')) + 1, 5), wrap=tk.WORD)
            text_widget.insert(1.0, json.dumps(value, indent=2, ensure_ascii=False))
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            self.add_copy_paste_menu(text_widget)
            
            self.component_config_fields[field_name] = ('dict', text_widget)
        
        else:
            # Для строк используем обычное текстовое поле
            # Переводим значение если нужно
            display_value = self.translate_value(field_name, value)
            
            # Специальная обработка для категории - используем выпадающий список
            if field_name == 'category':
                category_combo = ttk.Combobox(parent, width=40, state='readonly')
                category_display_values = ('Система', 'Приложение', 'Библиотека', 'Инструмент', 'Конфигурация', 
                                          'Плагин', 'Кэш', 'Ярлык рабочего стола', 'Пакет', 'Winetricks')
                category_combo['values'] = category_display_values
                
                # Устанавливаем текущее значение (переводим английское в русское)
                current_display = self.translate_value('category', value)
                if current_display in category_display_values:
                    category_combo.current(category_display_values.index(current_display))
                else:
                    category_combo.current(0)
                
                category_combo.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
                self.add_copy_paste_menu(category_combo)
                self.component_config_fields[field_name] = ('category', category_combo)
                return
            
            # Специальная обработка для package_type
            if field_name == 'package_type':
                package_type_combo = ttk.Combobox(parent, width=40, state='readonly')
                package_type_values = ('wine_templates', 'standard')
                package_type_combo['values'] = package_type_values
                
                if value in package_type_values:
                    package_type_combo.current(package_type_values.index(value))
                else:
                    package_type_combo.current(0)
                
                package_type_combo.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
                self.add_copy_paste_menu(package_type_combo)
                self.component_config_fields[field_name] = ('package_type', package_type_combo)
                return
            
            # Специальная обработка для auto_generated - только для чтения
            if field_name == 'auto_generated' and value == True:
                label_readonly = ttk.Label(parent, text='Да (автоматически создан)', foreground='gray')
                label_readonly.grid(row=row, column=1, sticky='w', padx=5, pady=2)
                # Не добавляем в component_config_fields, так как это поле только для чтения
                return
            
            # Если строка длинная, используем многострочное поле
            if isinstance(value, str) and len(value) > 80:
                frame = ttk.Frame(parent)
                frame.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
                
                text_widget = tk.Text(frame, height=3, wrap=tk.WORD)
                text_widget.insert(1.0, str(display_value))
                text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                text_widget.configure(yscrollcommand=scrollbar.set)
                
                self.add_copy_paste_menu(text_widget)
                
                self.component_config_fields[field_name] = ('str', text_widget)
            else:
                entry = ttk.Entry(parent)
                entry.insert(0, str(display_value) if display_value is not None else '')
                entry.grid(row=row, column=1, sticky='ew', padx=5, pady=2)
                self.add_copy_paste_menu(entry)
                self.component_config_fields[field_name] = ('str', entry)
        
        # Настраиваем растягивание колонки
        parent.columnconfigure(1, weight=1)
    
    def on_component_select(self, event):
        """Обработчик выбора компонента"""
        selection = self.component_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        component_id = self.component_tree_item_to_id.get(item_id)
        
        if not component_id:
            return
        
        config = get_component_data(component_id)
        if not config:
            return
        
        self.current_component_id = component_id
        
        # Обновляем ID компонента
        self.component_id_label.config(text=component_id)
        
        # Обновляем состояние кнопок перемещения
        self._update_move_buttons_state()
        
        # Очищаем предыдущие поля
        for widget in self.component_config_frame.winfo_children():
            widget.destroy()
        self.component_config_fields.clear()
        
        # Сортируем поля для удобства отображения
        priority_fields = ['name', 'command_name', 'description', 'category', 'sort_order', 
                          'dependencies', 'path', 'check_paths', 'install_method', 
                          'uninstall_method', 'gui_selectable']
        
        # Разделяем поля на приоритетные и остальные
        priority_items = []
        other_items = []
        
        for key, value in config.items():
            if key in priority_fields:
                priority_items.append((key, value))
            else:
                other_items.append((key, value))
        
        # Сортируем приоритетные поля по порядку
        priority_items.sort(key=lambda x: priority_fields.index(x[0]) if x[0] in priority_fields else 999)
        other_items.sort(key=lambda x: x[0])
        
        # Вычисляем максимальную ширину label для динамического размера
        all_labels = [self.get_field_label(key) for key, _ in priority_items + other_items]
        max_label_width = max(len(label) for label in all_labels) if all_labels else 25
        # Добавляем небольшой отступ
        max_label_width = min(max_label_width + 2, 40)
        
        # Создаем поля
        row = 0
        for key, value in priority_items + other_items:
            self._last_field_extra_row = False  # Сбрасываем флаг перед созданием поля
            self.create_config_field(self.component_config_frame, key, value, row, max_label_width)
            row += 1
            # Если поле добавило дополнительную строку (подсказку), увеличиваем row еще раз
            if hasattr(self, '_last_field_extra_row') and self._last_field_extra_row:
                row += 1
        
        # Активируем кнопки управления
        self.save_config_button.config(state=tk.NORMAL)
        self.delete_component_button.config(state=tk.NORMAL)
        
        # Обновляем прокрутку и ширину окна в canvas
        self.component_config_canvas.update_idletasks()
        self.component_config_canvas.configure(scrollregion=self.component_config_canvas.bbox("all"))
        
        # Обновляем ширину окна в canvas для правильного растягивания
        canvas_width = self.component_config_canvas.winfo_width()
        if canvas_width > 1 and hasattr(self, 'component_config_canvas_window'):
            self.component_config_canvas.itemconfig(self.component_config_canvas_window, width=canvas_width)
    
    def save_component_config(self):
        """Сохранить изменения конфигурации компонента"""
        if not self.current_component_id:
            return
        
        if self.current_component_id not in COMPONENTS_CONFIG:
            messagebox.showerror("Ошибка", "Компонент не найден в конфигурации")
            return
        
        # Сохраняем старые значения для отмены
        old_config = {}
        for field_name in self.component_config_fields.keys():
            if field_name in COMPONENTS_CONFIG[self.current_component_id]:
                old_value = COMPONENTS_CONFIG[self.current_component_id][field_name]
                # Создаем копию для безопасного хранения
                if isinstance(old_value, list):
                    old_config[field_name] = old_value.copy()
                elif isinstance(old_value, dict):
                    old_config[field_name] = old_value.copy()
                else:
                    old_config[field_name] = old_value
        
        # Собираем значения из полей
        updated_config = {}
        
        for field_name, (field_type, widget) in self.component_config_fields.items():
            try:
                if field_type == 'bool':
                    value = widget.get()
                elif field_type == 'int':
                    value = int(widget.get())
                elif field_type == 'float':
                    value = float(widget.get())
                elif field_type == 'list':
                    text = widget.get(1.0, tk.END).strip()
                    if text:
                        # Парсим список из текста (каждая строка - элемент)
                        value = [line.strip() for line in text.split('\n') if line.strip()]
                    else:
                        value = []
                elif field_type == 'dict':
                    text = widget.get(1.0, tk.END).strip()
                    if text:
                        value = json.loads(text)
                    else:
                        value = {}
                elif field_type == 'category':
                    # Для категории получаем значение из Combobox и переводим обратно
                    selected_display = widget.get()
                    reverse_category = {
                        'Система': 'system',
                        'Приложение': 'application',
                        'Библиотека': 'library',
                        'Инструмент': 'tool',
                        'Конфигурация': 'config',
                        'Плагин': 'plugin',
                        'Кэш': 'cache',
                        'Ярлык рабочего стола': 'desktop_shortcut',
                        'Пакет': 'package',
                        'Winetricks': 'winetricks',
                    }
                    value = reverse_category.get(selected_display, selected_display)
                elif field_type == 'package_type':
                    # Для типа пакета получаем значение из Combobox
                    value = widget.get()
                else:  # str
                    if isinstance(widget, tk.Text):
                        value = widget.get(1.0, tk.END).strip()
                    else:
                        value = widget.get().strip()
                    
                    # Обратный перевод для некоторых полей (из русского обратно в английский)
                    if field_name in ['install_method', 'uninstall_method']:
                        reverse_method = {
                            'APT': 'apt',
                            'Wine': 'wine',
                            'Winetricks': 'winetricks',
                            'Копирование': 'copy',
                            'Символическая ссылка': 'symlink',
                            'Скрипт': 'script',
                            'Вручную': 'manual',
                            'Нет': 'none',
                        }
                        value = reverse_method.get(value, value)
                    elif field_name == 'source_priority':
                        reverse_priority = {
                            'Архив': 'archive',
                            'Загрузка': 'download',
                            'Локальный': 'local',
                            'Сеть': 'network',
                        }
                        value = reverse_priority.get(value, value)
                
                updated_config[field_name] = value
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Неверное значение поля '{self.get_field_label(field_name)}': {e}")
                return
            except json.JSONDecodeError as e:
                messagebox.showerror("Ошибка", f"Неверный JSON в поле '{self.get_field_label(field_name)}': {e}")
                return
        
        # Сохраняем изменения в историю отмены (только для измененных полей)
        changed_fields = []
        for field_name, new_value in updated_config.items():
            old_value = old_config.get(field_name)
            if old_value != new_value:
                changed_fields.append(field_name)
                # Сохраняем каждое изменение отдельно для более точной отмены
                self.add_to_undo_history({
                    'action': 'save_config',
                    'component_id': self.current_component_id,
                    'field_name': field_name,
                    'old_value': old_value,
                    'new_value': new_value,
                    'description': f"Изменение поля '{self.get_field_label(field_name)}' компонента '{get_component_field(self.current_component_id, 'name', self.current_component_id)}'"
                })
        
        # Обновляем конфигурацию
        COMPONENTS_CONFIG[self.current_component_id].update(updated_config)
        
        # НОВОЕ: Сохраняем конфигурацию обратно в архив (если компонент из архива)
        archive_path = find_archive_for_component(self.current_component_id, self.astrapack_dir)
        if archive_path:
            if self.save_config_to_archive(self.current_component_id, archive_path):
                messagebox.showinfo("Успех", 
                                  f"Конфигурация компонента '{self.current_component_id}' сохранена в архив")
            else:
                messagebox.showwarning("Предупреждение", 
                                     f"Конфигурация сохранена в памяти, но не удалось обновить архив")
        else:
            messagebox.showinfo("Успех", 
                              f"Конфигурация компонента '{self.current_component_id}' сохранена (только в памяти)")
        
        # Обновляем дерево компонентов (на случай изменения имени или категории)
        self.update_component_tree()
        
        # Выбираем компонент снова после обновления
        if self.current_component_id:
            self.select_component_in_tree(self.current_component_id)
    
    def create_new_component(self):
        """Создать новый компонент"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Создать новый компонент")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Поля для ввода
        fields_frame = ttk.Frame(dialog)
        fields_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ID компонента
        ttk.Label(fields_frame, text="ID компонента:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        id_entry = ttk.Entry(fields_frame, width=40)
        id_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        id_entry.focus()
        
        # Название
        ttk.Label(fields_frame, text="Название:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        name_entry = ttk.Entry(fields_frame, width=40)
        name_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        
        # Категория (с русскими названиями для отображения)
        ttk.Label(fields_frame, text="Категория:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        category_combo = ttk.Combobox(fields_frame, width=37, state='readonly')
        # Значения для отображения (русские) и их соответствие английским
        category_display_values = ('Система', 'Приложение', 'Библиотека', 'Инструмент', 'Конфигурация', 
                                  'Плагин', 'Кэш', 'Ярлык рабочего стола', 'Пакет', 'Winetricks')
        category_combo['values'] = category_display_values
        category_combo.current(1)  # По умолчанию 'Приложение' (application)
        category_combo.grid(row=2, column=1, sticky='ew', padx=5, pady=5)
        
        # Словарь для обратного перевода
        category_reverse_map = {
            'Система': 'system',
            'Приложение': 'application',
            'Библиотека': 'library',
            'Инструмент': 'tool',
            'Конфигурация': 'config',
            'Плагин': 'plugin',
            'Кэш': 'cache',
            'Ярлык рабочего стола': 'desktop_shortcut',
            'Пакет': 'package',
            'Winetricks': 'winetricks'
        }
        
        # Порядок сортировки
        ttk.Label(fields_frame, text="Порядок сортировки:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        sort_entry = ttk.Entry(fields_frame, width=40)
        sort_entry.insert(0, "999")
        sort_entry.grid(row=3, column=1, sticky='ew', padx=5, pady=5)
        
        fields_frame.columnconfigure(1, weight=1)
        
        # Кнопки
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def create_component():
            component_id = id_entry.get().strip()
            component_name = name_entry.get().strip()
            category_display = category_combo.get()
            # Переводим русское название обратно в английское
            category = category_reverse_map.get(category_display, 'application')
            
            if not component_id:
                messagebox.showerror("Ошибка", "ID компонента не может быть пустым")
                return
            
            if component_id in COMPONENTS_CONFIG:
                if not messagebox.askyesno("Подтверждение", 
                                          f"Компонент '{component_id}' уже существует. Заменить?"):
                    return
            
            try:
                sort_order = int(sort_entry.get().strip() or "999")
            except ValueError:
                messagebox.showerror("Ошибка", "Порядок сортировки должен быть числом")
                return
            
            # Создаем базовую конфигурацию
            new_config = {
                'name': component_name or component_id,
                'category': category,
                'sort_order': sort_order,
                'dependencies': [],
                'gui_selectable': True
            }
            
            # Добавляем в конфигурацию
            COMPONENTS_CONFIG[component_id] = new_config
            
            # Обновляем дерево
            self.update_component_tree()
            
            # Выбираем новый компонент в дереве
            self.select_component_in_tree(component_id)
            
            messagebox.showinfo("Успех", f"Компонент '{component_id}' создан")
            dialog.destroy()
        
        ttk.Button(buttons_frame, text="Создать", command=create_component).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Отмена", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Обработка Enter
        def on_enter(event):
            create_component()
        
        id_entry.bind('<Return>', on_enter)
        name_entry.bind('<Return>', on_enter)
    
    def select_component_in_tree(self, component_id):
        """Выбрать компонент в дереве по ID"""
        # Ищем item_id по component_id
        for item_id, comp_id in self.component_tree_item_to_id.items():
            if comp_id == component_id:
                self.component_tree.selection_set(item_id)
                self.component_tree.see(item_id)
                # Вызываем обработчик выбора
                self.on_component_select(None)
                break
    
    def delete_component(self):
        """Удалить выбранный компонент"""
        if not self.current_component_id:
            return
        
        component_id = self.current_component_id
        component_name = get_component_field(component_id, 'name', component_id)
        
        # Проверяем, используется ли компонент как зависимость
        used_as_dependency = []
        for comp_id, config in COMPONENTS_CONFIG.items():
            if comp_id != component_id:
                deps = config.get('dependencies', [])
                if component_id in deps:
                    used_as_dependency.append(comp_id)
        
        if used_as_dependency:
            deps_list = ', '.join(used_as_dependency[:5])
            if len(used_as_dependency) > 5:
                deps_list += f" и еще {len(used_as_dependency) - 5}"
            messagebox.showerror("Ошибка", 
                               f"Компонент '{component_id}' используется как зависимость в:\n{deps_list}\n\n"
                               f"Сначала удалите зависимости.")
            return
        
        if not messagebox.askyesno("Подтверждение", 
                                 f"Удалить компонент '{component_name}' ({component_id})?\n\n"
                                 f"Это действие нельзя отменить."):
            return
        
        # Удаляем из конфигурации
        del COMPONENTS_CONFIG[component_id]
        
        # Обновляем дерево
        self.update_component_tree()
        
        # Очищаем правую панель
        self.current_component_id = None
        self.component_id_label.config(text="")
        for widget in self.config_scrollable_frame.winfo_children():
            widget.destroy()
        self.component_config_fields.clear()
        self.save_config_button.config(state=tk.DISABLED)
        self.delete_component_button.config(state=tk.DISABLED)
        
        messagebox.showinfo("Успех", f"Компонент '{component_id}' удален")
    
    def on_component_right_click(self, event):
        """Обработчик правого клика по компоненту"""
        item_id = self.component_tree.identify_row(event.y)
        if not item_id:
            return
        
        component_id = self.component_tree_item_to_id.get(item_id)
        if not component_id:
            return
        
        # Выделяем элемент
        self.component_tree.selection_set(item_id)
        self.on_component_select(None)
        
        # Создаем контекстное меню
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Копировать компонент", 
                        command=lambda: self.copy_component_dialog(component_id))
        menu.add_separator()
        menu.add_command(label="Удалить компонент", 
                        command=self.delete_component)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def copy_component_dialog(self, component_id):
        """Показать диалог копирования компонента"""
        if component_id not in COMPONENTS_CONFIG:
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Копировать компонент")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        original_name = get_component_field(component_id, 'name', component_id)
        
        ttk.Label(dialog, text=f"Копировать компонент: {original_name}").pack(pady=10)
        
        ttk.Label(dialog, text="Новый ID компонента:").pack(pady=5)
        new_id_entry = ttk.Entry(dialog, width=40)
        new_id_entry.insert(0, f"{component_id}_copy")
        new_id_entry.pack(pady=5)
        new_id_entry.focus()
        new_id_entry.select_range(0, tk.END)
        
        copy_dependencies = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, text="Копировать зависимости", 
                       variable=copy_dependencies).pack(pady=5)
        
        def do_copy():
            new_id = new_id_entry.get().strip()
            if not new_id:
                messagebox.showerror("Ошибка", "ID не может быть пустым")
                return
            
            if new_id in COMPONENTS_CONFIG:
                if not messagebox.askyesno("Подтверждение", 
                                          f"Компонент '{new_id}' уже существует. Заменить?"):
                    return
            
            # Копируем компонент
            original_config = get_component_data(component_id)
            new_config = json.loads(json.dumps(original_config))  # Глубокое копирование
            
            # Обновляем зависимости если нужно
            if not copy_dependencies.get():
                new_config['dependencies'] = []
            
            # Добавляем метаданные
            new_config['_copied_from'] = component_id
            new_config['_copy_date'] = datetime.now().isoformat()
            
            # Добавляем в конфигурацию
            COMPONENTS_CONFIG[new_id] = new_config
            
            # Обновляем дерево
            self.update_component_tree()
            
            # Выбираем новый компонент
            self.select_component_in_tree(new_id)
            
            messagebox.showinfo("Успех", f"Компонент скопирован: {new_id}")
            dialog.destroy()
        
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Копировать", command=do_copy).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        new_id_entry.bind('<Return>', lambda e: do_copy())
    
    def check_archives(self):
        """Проверить целостность архивов"""
        self.tools_output.delete(1.0, tk.END)
        self.tools_output.insert(tk.END, "Проверка архивов...\n\n")
        
        results = []
        
        for group_id, group_info in self.package_groups.items():
            folder_name = self.get_group_folder_name(group_id)
            group_path = os.path.join(self.astrapack_dir, folder_name)
            
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
            folder_name = self.get_group_folder_name(group_id)
            group_path = os.path.join(self.astrapack_dir, folder_name)
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
    
    def cleanup_temp_files(self):
        """Очистить временные файлы в фоновом режиме (только свои)"""
        def cleanup_worker():
            """Рабочая функция для фоновой очистки"""
            cleaned_items = []
            
            # Ищем ТОЛЬКО директории .temp_archive внутри AstraPack
            # Это единственный тип временных файлов, который создает программа
            if os.path.exists(self.astrapack_dir):
                for root, dirs, files in os.walk(self.astrapack_dir):
                    # Ищем ТОЛЬКО директории с точным именем .temp_archive
                    if '.temp_archive' in dirs:
                        temp_path = os.path.join(root, '.temp_archive')
                        try:
                            # Дополнительная проверка: убеждаемся, что это директория
                            if os.path.isdir(temp_path):
                                shutil.rmtree(temp_path, ignore_errors=True)
                                cleaned_items.append(temp_path)
                        except Exception as e:
                            # Тихая обработка ошибок - не выводим в консоль
                            pass
            
            # Тихая очистка - не выводим сообщения (фоновый режим)
            if cleaned_items:
                # Можно добавить логирование, но не мешаем пользователю
                pass
        
        # Запускаем в отдельном потоке
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def center_window(self):
        """Центрировать окно на экране"""
        # Обновляем информацию о размерах окна
        self.root.update_idletasks()
        
        # Получаем размеры окна
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Если размеры еще не определены, используем значения по умолчанию
        if window_width <= 1 or window_height <= 1:
            window_width = 1200
            window_height = 700
        
        # Получаем размер экрана
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Вычисляем позицию для центрирования
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        
        # Убеждаемся, что окно не выходит за границы экрана
        center_x = max(0, center_x)
        center_y = max(0, center_y)
        
        # Устанавливаем позицию
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    def show_window_on_top(self):
        """Показать окно поверх других окон на 3 секунды"""
        # Поднимаем окно наверх
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.update()
        
        # Через 3 секунды убираем флаг topmost
        self.root.after(3000, lambda: self.root.attributes('-topmost', False))
    
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
    # Проверяем, запущен ли в режиме воркера
    if len(sys.argv) > 1 and sys.argv[1] == '--archive-worker':
        archive_worker_main()
    else:
        # Обычный запуск GUI
        main()


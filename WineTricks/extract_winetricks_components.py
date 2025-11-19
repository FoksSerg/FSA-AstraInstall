#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для извлечения всех компонентов winetricks с метаданными
"""

import re
import os

def parse_winetricks_components(winetricks_file):
    """Парсит файл winetricks и извлекает все компоненты"""
    
    components = {
        'dlls': [],
        'apps': [],
        'fonts': [],
        'settings': [],
        'benchmarks': []
    }
    
    current_component = None
    current_category = None
    metadata_lines = []
    in_metadata = False
    
    with open(winetricks_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Начало метаданных компонента
            metadata_match = re.match(r'^w_metadata\s+(\w+)\s+(dlls|apps|fonts|settings|benchmarks)', line)
            if metadata_match:
                # Сохраняем предыдущий компонент, если есть
                if current_component and current_category:
                    component_data = parse_metadata_block(metadata_lines, current_component)
                    if component_data:
                        components[current_category].append(component_data)
                
                # Начинаем новый компонент
                current_component = metadata_match.group(1)
                current_category = metadata_match.group(2)
                metadata_lines = [line.rstrip()]
                in_metadata = True
                continue
            
            # Продолжение метаданных (строки с обратным слэшем или без)
            if in_metadata:
                line_stripped = line.rstrip()
                metadata_lines.append(line_stripped)
                
                # Конец блока метаданных: пустая строка или начало функции load_
                if line_stripped == '' or line_stripped.startswith('load_'):
                    in_metadata = False
                    if current_component and current_category:
                        component_data = parse_metadata_block(metadata_lines, current_component)
                        if component_data:
                            components[current_category].append(component_data)
                    current_component = None
                    current_category = None
                    metadata_lines = []
    
    # Обрабатываем последний компонент
    if current_component and current_category:
        component_data = parse_metadata_block(metadata_lines, current_component)
        if component_data:
            components[current_category].append(component_data)
    
    return components

def parse_metadata_block(lines, component_name):
    """Парсит блок метаданных компонента"""
    metadata = {
        'name': component_name,
        'title': '',
        'publisher': '',
        'year': '',
        'date': '',
        'media': '',
        'homepage': '',
        'description': ''
    }
    
    full_text = ' '.join(lines)
    
    # Извлекаем поля
    patterns = {
        'title': r'title="([^"]+)"',
        'title_bg': r'title_bg="([^"]+)"',
        'title_uk': r'title_uk="([^"]+)"',
        'publisher': r'publisher="([^"]+)"',
        'year': r'year="([^"]+)"',
        'date': r'date="([^"]+)"',
        'media': r'media="([^"]+)"',
        'homepage': r'homepage="([^"]+)"',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, full_text)
        if match:
            if key.startswith('title'):
                # Приоритет: title > title_uk > title_bg
                if not metadata['title'] or key == 'title':
                    metadata['title'] = match.group(1)
            else:
                metadata[key] = match.group(1)
    
    # Если title не найден, используем имя компонента
    if not metadata['title']:
        metadata['title'] = component_name
    
    return metadata

def generate_markdown_report(components, output_file):
    """Генерирует Markdown файл со всеми компонентами"""
    
    category_names = {
        'dlls': 'DLLs и библиотеки',
        'apps': 'Приложения',
        'fonts': 'Шрифты',
        'settings': 'Настройки',
        'benchmarks': 'Бенчмарки'
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Winetricks - Полный список компонентов\n\n")
        f.write(f"*Сгенерировано автоматически из winetricks*\n\n")
        f.write("---\n\n")
        
        total = sum(len(comps) for comps in components.values())
        f.write(f"**Всего компонентов: {total}**\n\n")
        
        for category in ['dlls', 'apps', 'fonts', 'settings', 'benchmarks']:
            if not components[category]:
                continue
                
            f.write(f"## {category_names[category]} ({len(components[category])} компонентов)\n\n")
            
            # Сортируем по названию
            sorted_components = sorted(components[category], key=lambda x: x['name'])
            
            for comp in sorted_components:
                f.write(f"### {comp['name']}\n\n")
                f.write(f"- **Название:** {comp['title']}\n")
                
                if comp['publisher']:
                    f.write(f"- **Издатель:** {comp['publisher']}\n")
                
                if comp['year']:
                    f.write(f"- **Год:** {comp['year']}\n")
                elif comp['date']:
                    f.write(f"- **Дата:** {comp['date']}\n")
                
                if comp['media']:
                    media_names = {
                        'download': 'Автоматическая загрузка',
                        'manual_download': 'Ручная загрузка'
                    }
                    media_name = media_names.get(comp['media'], comp['media'])
                    f.write(f"- **Тип загрузки:** {media_name}\n")
                
                if comp['homepage']:
                    f.write(f"- **Сайт:** {comp['homepage']}\n")
                
                f.write("\n")
            
            f.write("---\n\n")

def generate_text_report(components, output_file):
    """Генерирует простой текстовый файл"""
    
    category_names = {
        'dlls': 'DLLs и библиотеки',
        'apps': 'Приложения',
        'fonts': 'Шрифты',
        'settings': 'Настройки',
        'benchmarks': 'Бенчмарки'
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Winetricks - Полный список компонентов\n")
        f.write("=" * 80 + "\n\n")
        
        total = sum(len(comps) for comps in components.values())
        f.write(f"Всего компонентов: {total}\n\n")
        
        for category in ['dlls', 'apps', 'fonts', 'settings', 'benchmarks']:
            if not components[category]:
                continue
                
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"{category_names[category]} ({len(components[category])} компонентов)\n")
            f.write("=" * 80 + "\n\n")
            
            # Сортируем по названию
            sorted_components = sorted(components[category], key=lambda x: x['name'])
            
            for comp in sorted_components:
                f.write(f"Компонент: {comp['name']}\n")
                f.write(f"  Название: {comp['title']}\n")
                
                if comp['publisher']:
                    f.write(f"  Издатель: {comp['publisher']}\n")
                
                if comp['year']:
                    f.write(f"  Год: {comp['year']}\n")
                elif comp['date']:
                    f.write(f"  Дата: {comp['date']}\n")
                
                if comp['media']:
                    media_names = {
                        'download': 'Автоматическая загрузка',
                        'manual_download': 'Ручная загрузка'
                    }
                    media_name = media_names.get(comp['media'], comp['media'])
                    f.write(f"  Тип загрузки: {media_name}\n")
                
                if comp['homepage']:
                    f.write(f"  Сайт: {comp['homepage']}\n")
                
                f.write("\n")

if __name__ == '__main__':
    import sys
    
    # Определяем путь к файлу относительно скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    winetricks_file = os.path.join(script_dir, 'winetricks')
    
    if not os.path.exists(winetricks_file):
        print(f"Ошибка: файл {winetricks_file} не найден", file=sys.stderr)
        sys.exit(1)
    
    print("Парсинг winetricks...", file=sys.stderr)
    sys.stderr.flush()
    
    components = parse_winetricks_components(winetricks_file)
    
    # Статистика
    total = sum(len(comps) for comps in components.values())
    print(f"\nНайдено компонентов: {total}", file=sys.stderr)
    for cat, comps in components.items():
        print(f"  {cat}: {len(comps)}", file=sys.stderr)
    sys.stderr.flush()
    
    if total == 0:
        print("ОШИБКА: Компоненты не найдены! Проверьте логику парсинга.", file=sys.stderr)
        sys.exit(1)
    
    # Генерируем отчеты
    output_dir = script_dir
    
    print("\nГенерация Markdown отчета...", file=sys.stderr)
    sys.stderr.flush()
    md_file = os.path.join(output_dir, 'winetricks_components.md')
    generate_markdown_report(components, md_file)
    print(f"  Сохранено: {md_file}", file=sys.stderr)
    
    print("\nГенерация текстового отчета...", file=sys.stderr)
    sys.stderr.flush()
    txt_file = os.path.join(output_dir, 'winetricks_components.txt')
    generate_text_report(components, txt_file)
    print(f"  Сохранено: {txt_file}", file=sys.stderr)
    
    print("\nГотово!", file=sys.stderr)


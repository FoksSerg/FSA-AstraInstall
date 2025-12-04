#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для загрузки установочных файлов компонентов winetricks без установки
Версия: V3.1.153 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import re
import os
import subprocess
import sys
from pathlib import Path

def extract_download_calls(winetricks_file):
    """Извлекает все вызовы w_download из функций load_*"""
    
    downloads = {}  # {component_name: [list of download info]}
    
    current_component = None
    in_load_function = False
    load_function_lines = []
    
    with open(winetricks_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Находим начало функции load_*
            load_match = re.match(r'^load_(\w+)\(\)', line)
            if load_match:
                # Сохраняем предыдущую функцию, если есть
                if current_component and load_function_lines:
                    downloads[current_component] = parse_download_calls(load_function_lines)
                
                current_component = load_match.group(1)
                load_function_lines = []
                in_load_function = True
                continue
            
            # Конец функции load_* (закрывающая скобка или следующая функция)
            if in_load_function:
                # Добавляем строку в функцию
                load_function_lines.append(line)
                
                # Проверяем конец функции
                if line.strip() == '}':
                    if current_component:
                        downloads[current_component] = parse_download_calls(load_function_lines)
                    in_load_function = False
                    current_component = None
                    load_function_lines = []
                # Если встретили новую функцию load_, это тоже конец предыдущей
                elif re.match(r'^load_\w+\(\)', line):
                    # Удаляем последнюю строку (она относится к новой функции)
                    if load_function_lines:
                        load_function_lines.pop()
                    if current_component and load_function_lines:
                        downloads[current_component] = parse_download_calls(load_function_lines)
                    in_load_function = False
                    current_component = None
                    load_function_lines = []
    
    # Обрабатываем последнюю функцию
    if current_component and load_function_lines:
        downloads[current_component] = parse_download_calls(load_function_lines)
    
    return downloads

def parse_download_calls(lines):
    """Парсит вызовы w_download из строк функции"""
    downloads = []
    
    full_text = '\n'.join(lines)
    
    # Паттерн для w_download: w_download url [sha256 [filename]]
    # Ищем строки, которые начинаются с w_download (не в комментариях)
    # Пример: w_download https://example.com/file.exe abc123... file.exe
    # Или: w_download https://example.com/file.exe abc123...
    pattern = r'^\s*w_download\s+([hH][tT][tT][pP][sS]?://[^\s\)]+)\s+([a-f0-9]{64}|[a-f0-9]{40})?\s*([a-zA-Z0-9_\-\.]+\.(exe|zip|msi|msm|cab|dll|ttf|ttc|tar\.gz|tar\.bz2|7z|rar))?'
    
    for match in re.finditer(pattern, full_text, re.MULTILINE):
        url = match.group(1).strip()
        sha256 = match.group(2) if match.group(2) else None
        filename = match.group(3).strip() if match.group(3) else None
        
        # Если filename не указан, берем из URL
        if not filename or filename == '':
            filename = url.split('/')[-1].split('?')[0]
        
        # Очищаем filename от кавычек и пробелов
        filename = filename.strip('"\'')
        
        # Пропускаем, если filename выглядит как команда или переменная
        if filename.startswith('$') or filename.startswith('w_') or filename.startswith('_W_') or filename in ['if', '#', 'fi', 'then', 'else']:
            continue
        
        downloads.append({
            'url': url,
            'sha256': sha256,
            'filename': filename
        })
    
    # Также ищем w_download_to для более сложных случаев
    pattern_to = r'^\s*w_download_to\s+[^\s]+\s+([hH][tT][tT][pP][sS]?://[^\s\)]+)\s+([a-f0-9]{64}|[a-f0-9]{40})?\s*([^\s\)]+)?'
    for match in re.finditer(pattern_to, full_text, re.MULTILINE):
        url = match.group(1).strip()
        sha256 = match.group(2) if match.group(2) else None
        filename = match.group(3).strip() if match.group(3) else None
        
        if not filename or filename == '':
            filename = url.split('/')[-1].split('?')[0]
        
        filename = filename.strip('"\'')
        
        # Пропускаем, если filename выглядит как команда или переменная
        if filename.startswith('$') or filename.startswith('w_') or filename in ['if', '#', 'fi']:
            continue
        
        downloads.append({
            'url': url,
            'sha256': sha256,
            'filename': filename
        })
    
    return downloads

def download_file(url, output_dir, filename=None, sha256=None):
    """Загружает файл по URL"""
    
    if not filename:
        filename = url.split('/')[-1].split('?')[0]
    
    output_path = os.path.join(output_dir, filename)
    
    # Проверяем, существует ли файл
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        if sha256:
            # Проверяем SHA256
            if verify_sha256(output_path, sha256):
                print(f"  ✓ Файл уже существует и корректен: {filename}")
                return True
            else:
                print(f"  ⚠ Файл существует, но checksum не совпадает, перезагружаем...")
        else:
            print(f"  ✓ Файл уже существует: {filename}")
            return True
    
    print(f"  ↓ Загрузка: {filename}")
    print(f"    URL: {url}")
    
    # Используем curl или wget для загрузки
    downloaders = ['curl', 'wget', 'aria2c']
    downloader = None
    
    for d in downloaders:
        if subprocess.run(['which', d], capture_output=True).returncode == 0:
            downloader = d
            break
    
    if not downloader:
        print(f"  ✗ Ошибка: не найден curl, wget или aria2c")
        return False
    
    try:
        if downloader == 'curl':
            cmd = ['curl', '-L', '--fail', '--retry', '3', '-o', output_path, url]
        elif downloader == 'wget':
            cmd = ['wget', '--tries=3', '-O', output_path, url]
        elif downloader == 'aria2c':
            cmd = ['aria2c', '--max-tries=3', '-d', output_dir, '-o', filename, url]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            if sha256:
                if verify_sha256(output_path, sha256):
                    print(f"  ✓ Загружено и проверено: {filename}")
                    return True
                else:
                    print(f"  ✗ Ошибка: checksum не совпадает для {filename}")
                    return False
            else:
                print(f"  ✓ Загружено: {filename}")
                return True
        else:
            print(f"  ✗ Ошибка загрузки: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ✗ Исключение при загрузке: {e}")
        return False

def verify_sha256(filepath, expected_sha256):
    """Проверяет SHA256 файла"""
    import hashlib
    
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    actual_sha256 = sha256_hash.hexdigest()
    return actual_sha256 == expected_sha256.lower()

def download_component_files(component_name, downloads, base_output_dir):
    """Загружает все файлы для компонента"""
    
    component_dir = os.path.join(base_output_dir, component_name)
    os.makedirs(component_dir, exist_ok=True)
    
    print(f"\nКомпонент: {component_name}")
    print(f"  Папка: {component_dir}")
    
    if not downloads:
        print(f"  ⚠ Нет файлов для загрузки (возможно, использует helper функции)")
        return
    
    success_count = 0
    for i, download in enumerate(downloads, 1):
        print(f"\n  Файл {i}/{len(downloads)}:")
        if download_file(download['url'], component_dir, 
                        download['filename'], download['sha256']):
            success_count += 1
    
    print(f"\n  Итого: {success_count}/{len(downloads)} файлов загружено")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Загрузка установочных файлов компонентов winetricks без установки'
    )
    parser.add_argument('--winetricks', 
                       default='winetricks',
                       help='Путь к файлу winetricks (относительно скрипта)')
    parser.add_argument('--output', '-o',
                       default='downloads',
                       help='Директория для загрузки файлов (относительно скрипта)')
    parser.add_argument('--components', '-c',
                       nargs='+',
                       help='Список компонентов для загрузки (если не указано, загружаются все)')
    parser.add_argument('--list', '-l',
                       action='store_true',
                       help='Показать список всех компонентов с файлами для загрузки')
    
    args = parser.parse_args()
    
    # Определяем путь к winetricks относительно скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    winetricks_file = os.path.join(script_dir, args.winetricks)
    
    if not os.path.exists(winetricks_file):
        print(f"Ошибка: файл {winetricks_file} не найден")
        sys.exit(1)
    
    print("Парсинг winetricks...", file=sys.stderr)
    sys.stderr.flush()
    downloads = extract_download_calls(winetricks_file)
    
    # Фильтруем компоненты без загрузок
    components_with_downloads = {k: v for k, v in downloads.items() if v}
    
    print(f"\nНайдено компонентов с загрузками: {len(components_with_downloads)}", file=sys.stderr)
    print(f"Всего компонентов: {len(downloads)}", file=sys.stderr)
    sys.stderr.flush()
    
    if args.list:
        print("\n" + "="*80)
        print("Список компонентов с файлами для загрузки:")
        print("="*80)
        for component, files in sorted(components_with_downloads.items()):
            print(f"\n{component}:")
            for f in files:
                url_short = f['url'][:60] + '...' if len(f['url']) > 60 else f['url']
                print(f"  - {f['filename']} ({url_short})")
        return
    
    # Определяем компоненты для загрузки
    if args.components:
        components_to_download = {k: v for k, v in components_with_downloads.items() 
                                 if k in args.components}
        if len(components_to_download) < len(args.components):
            missing = set(args.components) - set(components_to_download.keys())
            print(f"⚠ Предупреждение: следующие компоненты не найдены или не имеют загрузок: {missing}")
    else:
        components_to_download = components_with_downloads
    
    if not components_to_download:
        print("Нет компонентов для загрузки")
        return
    
    # Создаем базовую директорию
    base_output_dir = os.path.join(script_dir, args.output)
    os.makedirs(base_output_dir, exist_ok=True)
    
    print(f"\nЗагрузка файлов в: {base_output_dir}")
    print(f"Компонентов для загрузки: {len(components_to_download)}\n")
    
    # Загружаем файлы
    success_count = 0
    for component_name, files in sorted(components_to_download.items()):
        try:
            download_component_files(component_name, files, base_output_dir)
            success_count += 1
        except KeyboardInterrupt:
            print("\n\nПрервано пользователем")
            break
        except Exception as e:
            print(f"\n✗ Ошибка при загрузке {component_name}: {e}")
    
    print("\n" + "="*80)
    print(f"Готово! Загружено компонентов: {success_count}/{len(components_to_download)}")
    print(f"Файлы сохранены в: {base_output_dir}")
    print("="*80)

if __name__ == '__main__':
    main()

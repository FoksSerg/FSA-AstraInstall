#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Версия: V2.7.142 (2025.11.27)
"""
Тестовый скрипт для извлечения исходников компонентов из всех доступных источников
Извлекает файлы из архивов, интернета и прямых путей для проверки работы системы
Исключает: desktop_shortcut, CountPack
"""

import os
import sys
import shutil
from pathlib import Path

# Добавляем путь к astra_automation.py
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

try:
    from astra_automation import (
        COMPONENTS_CONFIG,
        get_component_data,
        ComponentHandler
    )
except ImportError as e:
    print(f"[ERROR] Не удалось импортировать модули: {e}")
    sys.exit(1)

class TestComponentExtractor(ComponentHandler):
    """Класс для извлечения файлов компонентов из всех источников"""
    
    def __init__(self, output_dir):
        """Инициализация экстрактора"""
        super().__init__()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.stats = {
            'total_components': 0,
            'extracted_files': 0,
            'skipped': 0,
            'failed': 0,
            'sources': {'archive': 0, 'url': 0, 'direct': 0}
        }
    
    # Реализация абстрактных методов (минимальная, для тестирования не используется)
    def get_category(self) -> str:
        return 'test'
    
    def install(self, component_id: str, config: dict) -> bool:
        return False
    
    def uninstall(self, component_id: str, config: dict) -> bool:
        return False
    
    def check_status(self, component_id: str, config: dict) -> bool:
        return False
    
    def extract_all_components(self):
        """Извлечение всех компонентов из всех источников"""
        print(f"[INFO] Начинаем извлечение компонентов в: {self.output_dir}")
        print(f"[INFO] Исключаем: desktop_shortcut, CountPack\n")
        
        for component_id, config in COMPONENTS_CONFIG.items():
            # Пропускаем ярлыки
            if config.get('category') == 'desktop_shortcut':
                print(f"[SKIP] {component_id}: desktop_shortcut (ярлык)")
                self.stats['skipped'] += 1
                continue
            
            # Пропускаем CountPack
            if config.get('source_dir') == 'CountPack' or 'cont' in component_id.lower():
                if 'cont_designer' in component_id:
                    print(f"[SKIP] {component_id}: CountPack (обрабатывается отдельно)")
                    self.stats['skipped'] += 1
                    continue
            
            # Проверяем наличие файлов для извлечения
            has_files = (
                config.get('package_file') or
                config.get('download_url') or
                config.get('download_url_x86') or
                config.get('download_url_x64') or
                config.get('download_url_32') or
                config.get('download_url_64')
            )
            
            if not has_files:
                continue
            
            self.stats['total_components'] += 1
            print(f"\n{'='*60}")
            print(f"[INFO] Компонент: {component_id} ({config.get('name', 'Unknown')})")
            print(f"{'='*60}")
            
            # Создаем директорию для компонента
            component_dir = self.output_dir / component_id
            component_dir.mkdir(parents=True, exist_ok=True)
            
            # Пробуем извлечь из всех источников
            sources = ['archive', 'url', 'direct']
            extracted_from = []
            
            for source in sources:
                print(f"\n[SOURCE] Пробуем источник: {source.upper()}")
                try:
                    # Получаем файлы из конкретного источника (fallback=False для строгого режима)
                    files_result = self._resolve_component_files(
                        component_id, 
                        cleanup_temp=False, 
                        source_priority=source,
                        fallback=False  # Строгий режим: только указанный источник
                    )
                    
                    if files_result and files_result.get('files'):
                        source_dir = component_dir / source
                        source_dir.mkdir(parents=True, exist_ok=True)
                        
                        files = files_result.get('files', {})
                        actual_source = files_result.get('source', source)
                        
                        for file_key, file_path in files.items():
                            if not file_path or not os.path.exists(file_path):
                                continue
                            
                            # Определяем имя файла
                            if file_key == 'default':
                                dest_name = os.path.basename(file_path)
                            else:
                                original_name = os.path.basename(file_path)
                                dest_name = f"{file_key}_{original_name}"
                            
                            dest_path = source_dir / dest_name
                            
                            try:
                                shutil.copy2(file_path, dest_path)
                                size = os.path.getsize(file_path)
                                print(f"  ✓ {dest_name} ({self._format_size(size)}) [из {actual_source}]")
                                self.stats['extracted_files'] += 1
                                self.stats['sources'][actual_source] += 1
                            except Exception as e:
                                print(f"  ✗ Ошибка копирования {dest_name}: {e}")
                                self.stats['failed'] += 1
                        
                        # Сохраняем информацию о источнике
                        info_file = source_dir / "source_info.txt"
                        with open(info_file, 'w', encoding='utf-8') as f:
                            f.write(f"Source: {source}\n")
                            f.write(f"Actual source used: {actual_source}\n")
                            f.write(f"Component ID: {component_id}\n")
                            f.write(f"Files extracted:\n")
                            for file_key, file_path in files.items():
                                if file_path:
                                    f.write(f"  {file_key}: {os.path.basename(file_path)}\n")
                            if files_result.get('sources'):
                                f.write(f"\nDetailed sources:\n")
                                for file_key, file_source in files_result.get('sources', {}).items():
                                    f.write(f"  {file_key}: {file_source}\n")
                        
                        extracted_from.append(f"{source} ({actual_source})")
                        print(f"  → Сохранено в: {source_dir}")
                    else:
                        print(f"  ✗ Файлы не найдены из источника {source}")
                        
                except Exception as e:
                    print(f"  ✗ Ошибка извлечения из {source}: {e}")
                    self.stats['failed'] += 1
            
            # Сохраняем общую информацию о компоненте
            info_file = component_dir / "component_info.txt"
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"Component ID: {component_id}\n")
                f.write(f"Name: {config.get('name', 'Unknown')}\n")
                f.write(f"Category: {config.get('category', 'Unknown')}\n")
                f.write(f"Description: {config.get('description', 'N/A')}\n\n")
                f.write(f"Extracted from sources: {', '.join(extracted_from) if extracted_from else 'None'}\n\n")
                f.write("Configuration fields:\n")
                if config.get('package_file'):
                    f.write(f"  package_file: {config.get('package_file')}\n")
                if config.get('download_url'):
                    f.write(f"  download_url: {config.get('download_url')}\n")
                if config.get('download_url_x86'):
                    f.write(f"  download_url_x86: {config.get('download_url_x86')}\n")
                if config.get('download_url_x64'):
                    f.write(f"  download_url_x64: {config.get('download_url_x64')}\n")
                if config.get('download_url_32'):
                    f.write(f"  download_url_32: {config.get('download_url_32')}\n")
                if config.get('download_url_64'):
                    f.write(f"  download_url_64: {config.get('download_url_64')}\n")
        
        # Итоговая статистика
        self._print_statistics()
    
    def _print_statistics(self):
        """Вывод итоговой статистики"""
        print("\n" + "="*60)
        print("ИТОГОВАЯ СТАТИСТИКА:")
        print("="*60)
        print(f"  Всего компонентов обработано: {self.stats['total_components']}")
        print(f"  Извлечено файлов: {self.stats['extracted_files']}")
        print(f"  Пропущено компонентов: {self.stats['skipped']}")
        print(f"  Ошибок: {self.stats['failed']}")
        print(f"\n  По источникам:")
        print(f"    Архивы: {self.stats['sources']['archive']}")
        print(f"    Интернет: {self.stats['sources']['url']}")
        print(f"    Прямые пути: {self.stats['sources']['direct']}")
        print(f"\n  Результат сохранен в: {self.output_dir}")
        print("="*60)
    
    @staticmethod
    def _format_size(size_bytes):
        """Форматирование размера файла"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

def main():
    """Главная функция"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "test_extracted_components")
    
    print("="*60)
    print("ТЕСТОВЫЙ СКРИПТ ИЗВЛЕЧЕНИЯ КОМПОНЕНТОВ")
    print("Из всех доступных источников (архив, интернет, прямой путь)")
    print("="*60)
    print(f"Директория скрипта: {script_dir}")
    print(f"Директория вывода: {output_dir}\n")
    
    extractor = TestComponentExtractor(output_dir)
    extractor.extract_all_components()

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для удаления всех папок __pycache__ в проекте
Версия: V3.3.171 (2025.12.05)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import sys
import os
import shutil
from pathlib import Path

def main():
    """Удаляет все папки __pycache__ в проекте"""
    # Получаем корень проекта (родительская директория RunScript/)
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    
    if not project_root.exists():
        print(f"❌ ОШИБКА: Корень проекта не найден: {project_root}")
        sys.exit(1)
    
    print(f"Поиск папок __pycache__ в: {project_root}")
    print()
    
    # Находим все папки __pycache__
    cache_dirs = []
    for root, dirs, files in os.walk(project_root):
        if '__pycache__' in dirs:
            cache_path = Path(root) / '__pycache__'
            cache_dirs.append(cache_path)
    
    if not cache_dirs:
        print("✓ Папки __pycache__ не найдены.")
        return
    
    print(f"Найдено папок: {len(cache_dirs)}")
    print()
    
    # Удаляем все найденные папки
    removed = 0
    for cache_dir in cache_dirs:
        try:
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                print(f"✓ Удалена: {cache_dir.relative_to(project_root)}")
                removed += 1
        except Exception as e:
            print(f"✗ Ошибка при удалении {cache_dir.relative_to(project_root)}: {e}")
    
    print()
    print(f"Удалено папок: {removed}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        sys.exit(1)


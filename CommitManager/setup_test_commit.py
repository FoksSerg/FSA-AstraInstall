#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для инициализации постоянной тестовой директории CommitTest
Версия: V3.4.185 (2025.12.17)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import sys
from pathlib import Path

# Добавляем путь к корню проекта
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from CommitManager.test_environment import TestEnvironment


def setup_test_commit_dir(reset: bool = False):
    """
    Инициализация тестовой директории CommitTest
    
    Args:
        reset: Если True, очистить существующую директорию перед инициализацией
    """
    project_root = Path(__file__).parent.parent
    test_commit_dir = project_root / "CommitTest"
    
    print("=" * 60)
    print("Инициализация тестовой директории CommitTest")
    print("=" * 60)
    print(f"Путь: {test_commit_dir}")
    print()
    
    if reset and test_commit_dir.exists():
        print("⚠️  Режим сброса: существующая директория будет очищена")
        print()
    
    # Создаем тестовую среду
    test_env = TestEnvironment(
        output_callback=print,
        persistent_dir=str(test_commit_dir)
    )
    
    if test_env.setup(reset=reset):
        print()
        print("=" * 60)
        print("✓ Тестовая директория успешно инициализирована!")
        print("=" * 60)
        print()
        print("Теперь вы можете:")
        print("  1. Копировать файлы проекта в CommitTest/")
        print("  2. Создавать новые файлы и директории")
        print("  3. Использовать полный тестовый режим в GUI")
        print("  4. Тестировать алгоритм создания коммитов")
        print()
        print(f"Директория: {test_commit_dir}")
        print("(Добавлена в .gitignore, не отслеживается Git)")
        return True
    else:
        print()
        print("=" * 60)
        print("❌ Ошибка при инициализации тестовой директории")
        print("=" * 60)
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Инициализация тестовой директории CommitTest")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Очистить существующую директорию перед инициализацией"
    )
    
    args = parser.parse_args()
    
    success = setup_test_commit_dir(reset=args.reset)
    sys.exit(0 if success else 1)

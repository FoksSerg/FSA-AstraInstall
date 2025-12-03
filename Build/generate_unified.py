#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт генерации объединенного файла для сборки
Генерирует FSA-AstraInstall.py из исходников проекта
Версия: V2.7.143 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import sys
import subprocess
from pathlib import Path

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent  # Корень проекта (на уровень выше Build/)

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def print_step(message):
    print(f"\n[#] {message}")

def print_success(message):
    print(f"[OK] {message}")

def print_error(message):
    print(f"[ERROR] {message}")

def print_info(message):
    print(f"[i] {message}")

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    """Главная функция - генерирует объединенный файл"""
    print("=" * 60)
    print("=== Генерация объединенного файла ===")
    print("=" * 60)
    
    # Используем build_unified.py для генерации
    build_unified_script = SCRIPT_DIR / "build_unified.py"
    if not build_unified_script.exists():
        print_error(f"Файл не найден: {build_unified_script}")
        return 1
    
    try:
        result = subprocess.run([
            sys.executable, str(build_unified_script)
        ], capture_output=True, text=True, check=True)
        
        print_success("Объединенный файл создан")
        if result.stdout:
            print(result.stdout)
        
        # Проверяем что файл создан (в корне проекта)
        unified_file = PROJECT_DIR / "FSA-AstraInstall.py"
        if unified_file.exists():
            size = unified_file.stat().st_size / (1024 * 1024)
            print(f"\n[OK] Создан файл: {unified_file.name} ({size:.2f} MB)")
            print(f"[i] Файл готов для сборки через DockerManager")
            return 0
        else:
            print_error("Объединенный файл не создан")
            return 1
            
    except subprocess.CalledProcessError as e:
        print_error(f"Ошибка создания объединенного файла: {e}")
        if e.stderr:
            print(e.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

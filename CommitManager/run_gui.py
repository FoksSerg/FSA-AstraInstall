#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт запуска GUI для CommitManager
Версия: V3.4.184 (2025.12.16)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import sys
import os

# Добавляем путь к корню проекта в sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    try:
        from CommitManager.commit_gui import main
        sys.exit(main() or 0)
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Убедитесь, что вы запускаете скрипт из корня проекта")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

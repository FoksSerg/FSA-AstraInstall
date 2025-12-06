#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запускающий скрипт для GUI DockerManager
Версия: V3.1.162 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import sys
import os
from pathlib import Path

# Получаем директорию скрипта
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent

# Добавляем путь к проекту
sys.path.insert(0, str(PROJECT_DIR))

# Переходим в директорию проекта
os.chdir(PROJECT_DIR)

# Запускаем GUI
if __name__ == "__main__":
    from DockerManager.cli import main
    
    # Устанавливаем флаг GUI
    sys.argv = [sys.argv[0], "--gui"]
    
    sys.exit(main())


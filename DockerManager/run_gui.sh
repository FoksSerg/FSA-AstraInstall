#!/bin/bash
# Запускающий скрипт для GUI DockerManager
# Версия: V2.7.143 (2025.12.03)
# Компания: ООО "НПА Вира-Реалтайм"
# Разработчик: @FoksSegr & AI Assistant (@LLM)

# Получаем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Переходим в директорию проекта
cd "$PROJECT_DIR"

# Запускаем GUI
python3 -m DockerManager.cli --gui


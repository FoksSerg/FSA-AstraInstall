#!/bin/bash
# Скрипт сборки бинарного файла в Docker контейнере
# Версия: V3.1.158 (2025.12.05)
# Компания: ООО "НПА Вира-Реалтайм"
# Разработчик: @FoksSegr & AI Assistant (@LLM)

set -e
export PATH="/usr/local/bin:$PATH"

cd /build
mkdir -p bin build

# Проверяем tkinter
echo "[#] Проверка tkinter..."
python3 -c "import tkinter; print('[OK] tkinter доступен')"

# КРИТИЧНО: Сначала исправляем __future__ импорты в объединенном файле
echo "[#] Исправление __future__ импортов (ПЕРВЫМ ДЕЛОМ)..." >&2
python3 /build/DockerManager/scripts/fix_future_imports.py

# Определяем имя входного и выходного файла из переменной окружения
INPUT_FILE="${INPUT_FILE:-FSA-AstraInstall.py}"
OUTPUT_NAME="${OUTPUT_NAME:-FSA-AstraInstall}"

# Проверяем наличие входного файла
if [ ! -f "${INPUT_FILE}" ]; then
    echo "[ERROR] Входной файл не найден: ${INPUT_FILE}" >&2
    exit 1
fi

# Проверка иконки
ICON_FILE="/build/Icons/fly-astra-update.png"
ICON_PARAM=""
ICON_DATA_PARAM=""

if [ -f "$ICON_FILE" ]; then
    ICON_PARAM="--icon $ICON_FILE"
    # Добавляем иконку как ресурс для доступа из кода
    ICON_DATA_PARAM="--add-data $ICON_FILE:Icons"
    echo "[#] Использование иконки: $ICON_FILE" >&2
    # Проверяем размер файла для информации
    ICON_SIZE=$(stat -f%z "$ICON_FILE" 2>/dev/null || stat -c%s "$ICON_FILE" 2>/dev/null || echo "unknown")
    echo "[#] Размер файла иконки: $ICON_SIZE байт" >&2
else
    echo "[WARNING] Иконка не найдена: $ICON_FILE, сборка без иконки" >&2
fi

# Компилируем объединенный файл
# Включаем все необходимые модули для полной функциональности
echo "[#] Компиляция ${INPUT_FILE} в ${OUTPUT_NAME}..."
pyinstaller --onefile --console \
    $ICON_PARAM \
    $ICON_DATA_PARAM \
    --name "${OUTPUT_NAME}" \
    --distpath . \
    --workpath build \
    --specpath build \
    --clean \
    --hidden-import psutil \
    --hidden-import threading \
    --hidden-import queue \
    --hidden-import subprocess \
    --hidden-import shutil \
    --hidden-import json \
    --hidden-import socket \
    --hidden-import ssl \
    --hidden-import urllib \
    --hidden-import urllib.request \
    --hidden-import urllib.parse \
    --hidden-import http.client \
    --hidden-import multiprocessing \
    --hidden-import concurrent.futures \
    --hidden-import configparser \
    --hidden-import logging \
    --hidden-import hashlib \
    --hidden-import tempfile \
    --hidden-import glob \
    --hidden-import fnmatch \
    --hidden-import signal \
    --hidden-import pty \
    --hidden-import select \
    --collect-all psutil \
    "${INPUT_FILE}"

# Устанавливаем права на выполнение
chmod +x "${OUTPUT_NAME}" 2>/dev/null || true

echo "[OK] Сборка завершена"
echo "[OK] Создан файл: ${OUTPUT_NAME}"


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация DockerManager
Версия: V3.1.153 (2025.12.04)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
from pathlib import Path

# ============================================================================
# КОНФИГУРАЦИЯ СЕРВЕРА
# ============================================================================
REMOTE_SERVER = {
    "host": os.environ.get("FSA_BUILD_SERVER", "10.10.55.77"),  # IP Windows Server (WSL2)
    "user": os.environ.get("FSA_BUILD_USER", "fsa"),            # SSH пользователь
    "base_path": os.environ.get("FSA_BUILD_STORAGE_PATH", "/mnt/v/UbuMount"),
    "docker_data": "docker-data",       # Папка для данных Docker
    "incoming": "incoming",              # Входящие исходники
    "outgoing": "outgoing"              # Исходящие сборки
}

# ============================================================================
# ПЛАТФОРМЫ ДЛЯ СБОРКИ
# ============================================================================
BUILD_PLATFORMS = {
    "astra-1.7": {
        "base_image": "debian:buster",
        "glibc": "2.28",
        "python": "3.7",
        "description": "Astra Linux 1.7.x (GLIBC 2.28)",
        "dockerfile": "Dockerfile.astra-1.7",
        "image_name": "fsa-astrainstall-builder:astra-1.7"
    },
    "astra-1.8": {
        "base_image": "debian:bookworm",
        "glibc": "2.36",
        "python": "3.11",
        "description": "Astra Linux 1.8.x (GLIBC 2.36)",
        "dockerfile": "Dockerfile.astra-1.8",
        "image_name": "fsa-astrainstall-builder:astra-1.8"
    },
    "windows": {
        "base_image": "ubuntu:20.04",
        "glibc": "2.31",
        "python": "3.8",
        "description": "Windows (через Wine)",
        "dockerfile": "Dockerfile.windows",
        "image_name": "fsa-astrainstall-builder:windows"
    }
}

# ============================================================================
# ПРОЕКТЫ (с возможностью расширения)
# ============================================================================
PROJECTS = {
    "FSA-AstraInstall": {
        "name": "FSA-AstraInstall",
        "description": "Автоматизация установки Astra Linux",
        "input_file": "FSA-AstraInstall.py",  # Входной Python файл для сборки
        "output_name": "FSA-AstraInstall"     # Имя выходного бинарника (без расширения)
    }
    # В будущем можно добавить:
    # "ДругойПроект": {
    #     "name": "ДругойПроект",
    #     "description": "Описание",
    #     "input_file": "other_project.py",
    #     "output_name": "OtherProject"
    # }
}

# ============================================================================
# НАСТРОЙКИ DOCKER
# ============================================================================
DOCKER_CONFIG = {
    "image_prefix": "fsa-builder",
    "container_timeout": 3600,          # Таймаут контейнера (сек)
    "build_timeout": 1800,              # Таймаут сборки (сек)
    "platform": "linux/amd64"           # Платформа для сборки
}

# ============================================================================
# НАСТРОЙКИ GUI
# ============================================================================
GUI_CONFIG = {
    "window_title": "Build Manager - Управление сборками",
    "window_size": "1200x700",
    "log_lines": 1000                   # Количество строк в логе
}

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================
def get_project_dir():
    """Возвращает путь к корню проекта"""
    return Path(__file__).parent.parent.absolute()

def get_dockmanager_dir():
    """Возвращает путь к DockerManager"""
    return Path(__file__).parent.absolute()

def get_dockerfiles_dir():
    """Возвращает путь к dockerfiles"""
    return get_dockmanager_dir() / "dockerfiles"

def get_scripts_dir():
    """Возвращает путь к scripts"""
    return get_dockmanager_dir() / "scripts"

def get_server_path(relative_path=""):
    """Возвращает полный путь на сервере"""
    base = REMOTE_SERVER["base_path"]
    if relative_path:
        return f"{base}/{relative_path}"
    return base

def get_incoming_path(project):
    """Возвращает путь к incoming для проекта"""
    return get_server_path(f"{REMOTE_SERVER['incoming']}/{project}")

def get_outgoing_path(project, platform=""):
    """Возвращает путь к outgoing для проекта и платформы"""
    base = get_server_path(f"{REMOTE_SERVER['outgoing']}/{project}")
    if platform:
        return f"{base}/{platform}"
    return base

def get_docker_data_path():
    """Возвращает путь к docker-data на сервере"""
    return get_server_path(REMOTE_SERVER["docker_data"])


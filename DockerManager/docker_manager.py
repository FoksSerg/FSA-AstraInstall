#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с Docker образами
Версия: V3.1.153 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import subprocess
import shutil
import platform
from pathlib import Path
from .config import BUILD_PLATFORMS, DOCKER_CONFIG, get_dockerfiles_dir
from .server_connection import execute_ssh_command, print_step, print_success, print_error, print_info
from .logger import get_logger

# Инициализируем логгер
_logger = get_logger("DockerManager.DockerManager")

# ============================================================================
# ПРОВЕРКА DOCKER
# ============================================================================

def check_docker():
    """Проверяет наличие Docker"""
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def wait_for_docker(max_wait=120):
    """Ожидает запуска Docker daemon"""
    print_info("Ожидание запуска Docker daemon...")
    for i in range(max_wait):
        try:
            result = subprocess.run(["docker", "ps"], 
                                  capture_output=True, text=True, timeout=2)
            error_text = result.stderr + result.stdout
            if result.returncode == 0 and "Cannot connect" not in error_text:
                print_success("Docker daemon запущен")
                return True
        except:
            pass
        if i % 10 == 0 and i > 0:
            print_info(f"Ожидание... ({i}/{max_wait} сек)")
        import time
        time.sleep(1)
    print_error("Docker daemon не запустился за отведенное время")
    return False

# ============================================================================
# РАБОТА С ОБРАЗАМИ (ЛОКАЛЬНО)
# ============================================================================

def check_image_exists(image_name):
    """Проверяет существует ли Docker образ локально"""
    result = subprocess.run(
        ["docker", "images", "-q", image_name],
        capture_output=True, text=True
    )
    return bool(result.stdout.strip())

def build_image(dockerfile_path, image_name, context_path, platform=None):
    """Собирает Docker образ локально"""
    print_step(f"Сборка Docker образа {image_name}...")
    
    cmd = ["docker", "build"]
    if platform:
        cmd.extend(["--platform", platform])
    cmd.extend([
        "-f", str(dockerfile_path),
        "-t", image_name,
        str(context_path)
    ])
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print_success(f"Docker образ {image_name} собран")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Ошибка сборки образа: {e}")
        if e.stderr:
            print_error(e.stderr)
        return False

# ============================================================================
# РАБОТА С ОБРАЗАМИ (УДАЛЕННО)
# ============================================================================

def check_remote_image_exists(image_name):
    """Проверяет существует ли Docker образ на удаленном сервере"""
    try:
        result = execute_ssh_command(
            f"docker images -q {image_name}",
            check=False
        )
        return bool(result.stdout.strip())
    except Exception as e:
        print_error(f"Ошибка проверки образа на сервере: {e}")
        return False

def build_remote_image(dockerfile_path, image_name, context_path, platform=None):
    """Собирает Docker образ на удаленном сервере"""
    print_step(f"Сборка Docker образа {image_name} на сервере...")
    
    # Формируем команду docker build
    cmd = "docker build"
    if platform:
        cmd += f" --platform {platform}"
    cmd += f" -f {dockerfile_path} -t {image_name} {context_path}"
    
    try:
        result = execute_ssh_command(cmd, check=True, capture_output=False)
        print_success(f"Docker образ {image_name} собран на сервере")
        return True
    except Exception as e:
        print_error(f"Ошибка сборки образа на сервере: {e}")
        return False

def get_remote_images():
    """Получает список образов на удаленном сервере"""
    try:
        result = execute_ssh_command("docker images --format '{{.Repository}}:{{.Tag}}'", check=True)
        images = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        return images
    except Exception as e:
        print_error(f"Ошибка получения списка образов: {e}")
        return []

def remove_remote_image(image_name):
    """Удаляет Docker образ на удаленном сервере"""
    print_step(f"Удаление образа {image_name} на сервере...")
    try:
        execute_ssh_command(f"docker rmi -f {image_name}", check=True)
        print_success(f"Образ {image_name} удален")
        return True
    except Exception as e:
        print_error(f"Ошибка удаления образа: {e}")
        return False

# ============================================================================
# ПОЛУЧЕНИЕ DOCKERFILE
# ============================================================================

def get_dockerfile_path(platform):
    """Возвращает путь к Dockerfile для платформы"""
    if platform not in BUILD_PLATFORMS:
        print_error(f"Неизвестная платформа: {platform}")
        return None
    
    dockerfile_name = BUILD_PLATFORMS[platform]["dockerfile"]
    dockerfile_path = get_dockerfiles_dir() / dockerfile_name
    
    if not dockerfile_path.exists():
        print_error(f"Dockerfile не найден: {dockerfile_path}")
        return None
    
    return dockerfile_path


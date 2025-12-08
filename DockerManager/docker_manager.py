#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с Docker образами
Версия: V3.3.166 (2025.12.03)
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
    """Получает список образов на удаленном сервере (только имена)"""
    try:
        result = execute_ssh_command("docker images --format '{{.Repository}}:{{.Tag}}'", check=True)
        images = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        return images
    except Exception as e:
        print_error(f"Ошибка получения списка образов: {e}")
        return []

def get_remote_images_detailed():
    """Получает список образов на удаленном сервере с размером и датой"""
    try:
        # Формат: Repository:Tag\tSize\tCreatedAt
        result = execute_ssh_command(
            "docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}'",
            check=True
        )
        images = []
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                images.append({
                    'name': parts[0],
                    'size': parts[1],
                    'date': parts[2]
                })
            elif len(parts) == 1:
                # Fallback если формат не сработал
                images.append({
                    'name': parts[0],
                    'size': '',
                    'date': ''
                })
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

# ============================================================================
# ГЕНЕРАЦИЯ DOCKERFILE ИЗ КОМПОНЕНТОВ
# ============================================================================

def generate_dockerfile_from_config(config):
    """Генерирует Dockerfile из конфигурации компонентов"""
    dockerfile_lines = []
    
    # Базовый образ
    base_image = config.get('base_image', 'debian:bookworm')
    dockerfile_lines.append(f"FROM {base_image}")
    dockerfile_lines.append("")
    
    # Системные пакеты
    system_packages = config.get('system_packages', [])
    if system_packages:
        # Фильтруем только включенные пакеты
        enabled_packages = [pkg for pkg in system_packages if pkg.get('enabled', True)]
        if enabled_packages:
            package_names = [pkg['name'] for pkg in enabled_packages]
            packages_str = ' '.join(package_names)
            dockerfile_lines.append(f"RUN apt-get update && apt-get install -y \\")
            dockerfile_lines.append(f"    {packages_str} \\")
            dockerfile_lines.append("    && rm -rf /var/lib/apt/lists/*")
            dockerfile_lines.append("")
    
    # Python пакеты
    python_packages = config.get('python_packages', [])
    if python_packages:
        enabled_packages = [pkg for pkg in python_packages if pkg.get('enabled', True)]
        if enabled_packages:
            pip_flags = config.get('pip_flags', '')
            if pip_flags:
                pip_flags = f" {pip_flags}"
            
            package_list = []
            for pkg in enabled_packages:
                name = pkg['name']
                version = pkg.get('version')
                if version:
                    package_list.append(f"{name}=={version}")
                else:
                    package_list.append(name)
            
            packages_str = ' '.join(package_list)
            dockerfile_lines.append(f"RUN pip3{pip_flags} install {packages_str}")
            dockerfile_lines.append("")
    
    # Переменные окружения
    env_vars = config.get('env_vars', [])
    if env_vars:
        for env in env_vars:
            if env.get('enabled', True):
                key = env.get('key', '')
                value = env.get('value', '')
                if key:
                    dockerfile_lines.append(f"ENV {key}={value}")
        if any(env.get('enabled', True) for env in env_vars):
            dockerfile_lines.append("")
    
    # Кастомные команды
    custom_commands = config.get('custom_commands', [])
    if custom_commands:
        for cmd in custom_commands:
            if cmd.get('enabled', True) and cmd.get('command'):
                dockerfile_lines.append(f"RUN {cmd['command']}")
        if any(cmd.get('enabled', True) for cmd in custom_commands):
            dockerfile_lines.append("")
    
    # Рабочая директория
    dockerfile_lines.append("WORKDIR /build")
    
    return '\n'.join(dockerfile_lines)

def get_local_base_images():
    """Получает список локальных базовых образов на сервере"""
    try:
        result = execute_ssh_command(
            "docker images --format '{{.Repository}}:{{.Tag}}' | head -50",
            check=False
        )
        if result.returncode == 0:
            images = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            return images
        return []
    except Exception as e:
        print_error(f"Ошибка получения локальных образов: {e}")
        return []


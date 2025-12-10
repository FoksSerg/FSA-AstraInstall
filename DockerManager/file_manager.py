#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с файлами (загрузка/скачивание)
Версия: V3.4.174 (2025.12.08)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import shutil
from pathlib import Path
from .config import PROJECTS, get_incoming_path, get_outgoing_path, get_project_dir
from .server_connection import (
    scp_upload, scp_download, create_remote_directory,
    remove_remote_directory, print_step, print_success, print_error, print_info
)
from .logger import get_logger

# Инициализируем логгер
_logger = get_logger("DockerManager.FileManager")

# ============================================================================
# ЗАГРУЗКА ИСХОДНИКОВ
# ============================================================================

def upload_sources(project, exclude_patterns=None):
    """Загружает исходники проекта на сервер"""
    _logger.info(f"Загрузка исходников проекта {project} на сервер")
    
    if project not in PROJECTS:
        _logger.error(f"Неизвестный проект: {project}")
        print_error(f"Неизвестный проект: {project}")
        return False
    
    project_config = PROJECTS[project]
    project_dir = get_project_dir()
    
    _logger.info(f"Директория проекта: {project_dir}")
    
    # Путь на сервере
    remote_path = get_incoming_path(project)
    _logger.info(f"Удаленный путь: {remote_path}")
    
    # Создаем папку на сервере
    if not create_remote_directory(remote_path):
        return False
    
    # Удаляем старую копию
    print_step("Очистка старой копии на сервере...")
    remove_remote_directory(remote_path)
    create_remote_directory(remote_path)
    
    # Исключаемые папки/файлы (по умолчанию)
    if exclude_patterns is None:
        exclude_patterns = [
            'bin', 'build', '__pycache__', '*.pyc', '*.x.c', '*.x',
            'History', 'Log', '.git', 'AstraPack', 'LogInstall',
            'Screenshots', 'WineTricks', 'test-environment', 'LogParser',
            'original_scripts', '*.md', project_config["output_name"]
            # НЕ исключаем DockerManager - он обрабатывается отдельно
        ]
    
    # Создаем временную папку для копирования
    import tempfile
    import os
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        print_step("Подготовка исходников для загрузки...")
        
        # Копируем файлы проекта, исключая ненужные
        def should_exclude(path):
            path_str = str(path.relative_to(project_dir))
            # DockerManager обрабатывается отдельно, не исключаем его здесь
            if path.name == 'DockerManager':
                return False  # Не исключаем, обработаем отдельно
            
            # ВАЖНО: FSA-AstraInstall.py должен быть включен (это объединенный файл)
            if path.name == f"{project_config['output_name']}.py":
                return False  # Не исключаем объединенный .py файл
            
            # КРИТИЧНО: README.md и HELPME.md должны быть включены (нужны для встраивания в бинарник)
            if path.name in ['README.md', 'HELPME.md']:
                return False  # Не исключаем эти файлы
            
            for pattern in exclude_patterns:
                # Проверяем точное совпадение имени (для бинарника без расширения)
                if path.name == pattern:
                    return True
                # Проверяем вхождение паттерна в путь
                if pattern in path_str:
                    return True
            # Исключаем бинарники с суффиксами платформ (FSA-AstraInstall-1-7, FSA-AstraInstall-1-8)
            if path.name.startswith(project_config["output_name"] + "-") and not path.name.endswith(".py"):
                return True
            return False
        
        # Копируем только нужные файлы
        copied_count = 0
        for item in project_dir.iterdir():
            if should_exclude(item):
                continue
            
            dest = temp_dir / item.name
            if item.is_dir():
                # Для DockerManager копируем только scripts и dockerfiles
                if item.name == 'DockerManager':
                    dockmanager_dest = temp_dir / 'DockerManager'
                    dockmanager_dest.mkdir(exist_ok=True)
                    # Копируем только scripts и dockerfiles
                    for subdir in ['scripts', 'dockerfiles']:
                        subdir_path = item / subdir
                        if subdir_path.exists():
                            shutil.copytree(subdir_path, dockmanager_dest / subdir, dirs_exist_ok=True)
                            copied_count += 1
                            _logger.debug(f"Скопировано: {subdir_path} → {dockmanager_dest / subdir}")
                else:
                    shutil.copytree(item, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*exclude_patterns))
                    copied_count += 1
            else:
                shutil.copy2(item, dest)
                copied_count += 1
        
        # Проверяем что DockerManager/scripts скопировался
        dockmanager_scripts = temp_dir / 'DockerManager' / 'scripts' / 'docker_build.sh'
        if dockmanager_scripts.exists():
            _logger.info(f"✅ Скрипт найден в temp: {dockmanager_scripts}")
        else:
            _logger.warning(f"⚠️ Скрипт НЕ найден в temp: {dockmanager_scripts}")
            # Показываем что есть в DockerManager
            dockmanager_dir = temp_dir / 'DockerManager'
            if dockmanager_dir.exists():
                _logger.info(f"Содержимое DockerManager в temp: {list(dockmanager_dir.iterdir())}")
            else:
                _logger.error(f"❌ Папка DockerManager не создана в temp!")
                # Пробуем скопировать вручную
                dockmanager_source = project_dir / 'DockerManager'
                if dockmanager_source.exists():
                    _logger.info(f"Попытка скопировать DockerManager вручную...")
                    dockmanager_dest = temp_dir / 'DockerManager'
                    dockmanager_dest.mkdir(exist_ok=True)
                    for subdir in ['scripts', 'dockerfiles']:
                        subdir_path = dockmanager_source / subdir
                        if subdir_path.exists():
                            shutil.copytree(subdir_path, dockmanager_dest / subdir, dirs_exist_ok=True)
                            _logger.info(f"✅ Скопировано вручную: {subdir_path} → {dockmanager_dest / subdir}")
                    # Проверяем снова
                    if (dockmanager_dest / 'scripts' / 'docker_build.sh').exists():
                        _logger.info(f"✅ Скрипт найден после ручного копирования")
                    else:
                        _logger.error(f"❌ Скрипт все еще не найден после ручного копирования")
        
        print_success(f"Подготовлено {copied_count} элементов для загрузки")
        
        # Загружаем содержимое temp_dir на сервер
        # Используем tar для передачи всех файлов одним архивом, затем распаковываем на сервере
        import tarfile
        import tempfile as tf
        tar_path = Path(tf.mkdtemp()) / "sources.tar.gz"
        
        try:
            # Создаем tar архив
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(temp_dir, arcname=".", filter=lambda tarinfo: tarinfo)
            
            _logger.debug(f"Создан архив: {tar_path}")
            
            # Загружаем архив на сервер
            remote_tar = f"{remote_path}/sources.tar.gz"
            if scp_upload(tar_path, remote_tar, recursive=False):
                # Распаковываем архив на сервере
                from .server_connection import execute_ssh_command
                cmd = f"cd {remote_path} && tar -xzf sources.tar.gz && rm -f sources.tar.gz"
                execute_ssh_command(cmd, check=True)
                _logger.info("Архив распакован на сервере")
                print_success(f"Исходники проекта {project} загружены на сервер")
                return True
            else:
                return False
        finally:
            # Удаляем локальный архив
            if tar_path.exists():
                tar_path.unlink()
            
    finally:
        # Удаляем временную папку
        shutil.rmtree(temp_dir, ignore_errors=True)

# ============================================================================
# СКАЧИВАНИЕ РЕЗУЛЬТАТОВ
# ============================================================================

def download_build(project, platform, local_path=None):
    """Скачивает готовую сборку с сервера"""
    _logger.info(f"Скачивание сборки проекта {project} для платформы {platform}")
    
    if project not in PROJECTS:
        _logger.error(f"Неизвестный проект: {project}")
        print_error(f"Неизвестный проект: {project}")
        return False
    
    project_config = PROJECTS[project]
    output_name = project_config["output_name"]
    
    # Определяем имя файла с суффиксом платформы
    # Заменяем точку на дефис, чтобы избежать проблем с расширением файла
    platform_version = platform.replace("astra-", "").replace(".", "-")
    output_name_with_platform = f"{output_name}-{platform_version}"
    
    # Путь на сервере
    remote_path = f"{get_outgoing_path(project, platform)}/{output_name_with_platform}"
    _logger.info(f"Удаленный путь: {remote_path}")
    
    # Локальный путь
    if local_path is None:
        local_path = get_project_dir() / output_name_with_platform
    else:
        local_path = Path(local_path)
    
    _logger.info(f"Локальный путь: {local_path}")
    
    # Скачиваем файл
    _logger.info(f"Скачивание файла: {remote_path} → {local_path}")
    if scp_download(remote_path, local_path):
        # Устанавливаем права на выполнение
        import os
        os.chmod(local_path, 0o755)
        
        # Получаем и устанавливаем время модификации с сервера
        try:
            from .server_connection import execute_ssh_command
            result = execute_ssh_command(f"stat -c %Y {remote_path}", check=False)
            if result.returncode == 0 and result.stdout.strip():
                remote_mtime = float(result.stdout.strip())
                os.utime(local_path, (remote_mtime, remote_mtime))
        except Exception:
            pass  # Игнорируем ошибки, файл уже скачан
        
        size = local_path.stat().st_size / (1024 * 1024)  # MB
        _logger.info(f"Сборка успешно скачана: {local_path} ({size:.2f} MB)")
        print_success(f"Сборка скачана: {local_path}")
        return True
    else:
        _logger.error("Не удалось скачать сборку с сервера")
        return False

def list_builds(project, platform=None):
    """Получает список готовых сборок на сервере"""
    from .server_connection import list_remote_directory
    
    if platform:
        remote_path = get_outgoing_path(project, platform)
    else:
        remote_path = get_outgoing_path(project)
    
    result = list_remote_directory(remote_path)
    return result

# ============================================================================
# РАБОТА С ОБЪЕДИНЕННЫМ ФАЙЛОМ
# ============================================================================

def check_unified_file(project):
    """Проверяет наличие готового входного файла"""
    if project not in PROJECTS:
        print_error(f"Неизвестный проект: {project}")
        return False
    
    project_config = PROJECTS[project]
    project_dir = get_project_dir()
    input_file = project_config.get('input_file', f"{project_config['output_name']}.py")
    output_file = project_dir / input_file
    
    if output_file.exists():
        print_success(f"Входной файл найден: {output_file.name}")
        return True
    else:
        print_error(f"Входной файл не найден: {output_file}")
        print_info(f"Убедитесь, что файл {input_file} существует в корне проекта")
        return False


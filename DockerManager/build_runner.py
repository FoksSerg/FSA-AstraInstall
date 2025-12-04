#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для запуска сборок (локально и удаленно)
Версия: V2.7.143 (2025.12.04)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import sys
import subprocess
import platform
import threading
from pathlib import Path
from .config import (
    PROJECTS, BUILD_PLATFORMS, DOCKER_CONFIG,
    get_project_dir, get_dockmanager_dir, get_scripts_dir,
    get_incoming_path, get_outgoing_path
)
from .docker_manager import (
    check_docker, wait_for_docker, check_image_exists, build_image,
    check_remote_image_exists, build_remote_image, get_dockerfile_path
)
from .file_manager import upload_sources, download_build, check_unified_file
from .server_connection import (
    execute_ssh_command, create_remote_directory,
    test_connection,
    print_step, print_success, print_error, print_info
)
from .logger import get_logger

# Инициализируем логгер
_logger = get_logger("DockerManager.BuildRunner")

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

HOST_PLATFORM = platform.system().lower()

def check_platform():
    """Проверяет что сборка запущена на macOS"""
    if HOST_PLATFORM != "darwin":
        print_error("Сборка должна запускаться на macOS!")
        return False
    
    if not check_docker():
        print_error("Docker не найден!")
        print_info("Установите Docker Desktop: https://www.docker.com/products/docker-desktop")
        return False
    
    docker_ready = False
    try:
        result = subprocess.run(["docker", "ps"], 
                              capture_output=True, text=True, timeout=3)
        if result.returncode == 0 and "Cannot connect" not in result.stderr:
            docker_ready = True
    except:
        pass
    
    if not docker_ready:
        if not wait_for_docker():
            return False
    
    print_success("Docker доступен")
    return True

# ============================================================================
# ЛОКАЛЬНАЯ СБОРКА
# ============================================================================

def build_local(project, platform_name):
    """Запускает локальную сборку"""
    _logger.info(f"Запуск локальной сборки: {project} для {platform_name}")
    
    if project not in PROJECTS:
        _logger.error(f"Неизвестный проект: {project}")
        print_error(f"Неизвестный проект: {project}")
        return False
    
    if platform_name not in BUILD_PLATFORMS:
        _logger.error(f"Неизвестная платформа: {platform_name}")
        print_error(f"Неизвестная платформа: {platform_name}")
        return False
    
    project_config = PROJECTS[project]
    platform_config = BUILD_PLATFORMS[platform_name]
    project_dir = get_project_dir()
    
    _logger.info(f"Конфигурация проекта: {project_config}")
    _logger.info(f"Конфигурация платформы: {platform_config}")
    _logger.info(f"Директория проекта: {project_dir}")
    
    # Проверяем платформу
    _logger.info("Проверка платформы...")
    if not check_platform():
        _logger.error("Проверка платформы не пройдена")
        return False
    
    # Проверяем наличие готового объединенного файла
    _logger.info("Проверка объединенного файла...")
    if not check_unified_file(project):
        _logger.error("Объединенный файл не найден")
        return False
    
    # Получаем Dockerfile
    _logger.info("Получение Dockerfile...")
    dockerfile_path = get_dockerfile_path(platform_name)
    if not dockerfile_path:
        _logger.error("Dockerfile не найден")
        return False
    _logger.info(f"Dockerfile: {dockerfile_path}")
    
    # Имя образа
    image_name = platform_config["image_name"]
    _logger.info(f"Имя образа: {image_name}")
    
    # Проверяем/создаем образ
    _logger.info(f"Проверка существования образа: {image_name}")
    if not check_image_exists(image_name):
        _logger.info("Образ не найден, запуск сборки...")
        print_step("Сборка Docker образа...")
        if not build_image(dockerfile_path, image_name, project_dir, DOCKER_CONFIG["platform"]):
            _logger.error("Не удалось собрать Docker образ")
            return False
    else:
        _logger.info(f"Docker образ {image_name} уже существует")
        print_success(f"Docker образ {image_name} уже существует")
    
    # Запускаем сборку в контейнере
    container_name = f"fsa-builder-{platform_name}-temp"
    _logger.info(f"Имя контейнера: {container_name}")
    
    try:
        # Удаляем старый контейнер если есть
        _logger.debug(f"Удаление старого контейнера: {container_name}")
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        
        # Запускаем сборку
        _logger.info("Запуск сборки в Docker контейнере...")
        print_step("Запуск сборки в Docker...")
        scripts_dir = get_scripts_dir()
        build_script = scripts_dir / "docker_build.sh"
        input_file = project_config.get('input_file', f"{project_config['output_name']}.py")
        
        docker_cmd = [
            "docker", "run",
            "--platform", DOCKER_CONFIG["platform"],
            "--name", container_name,
            "-v", f"{project_dir}:/build",
            "-e", f"INPUT_FILE={input_file}",
            "-e", f"OUTPUT_NAME={project_config['output_name']}",
            image_name,
            "bash", f"/build/DockerManager/scripts/docker_build.sh"
        ]
        _logger.info(f"Docker команда: {' '.join(docker_cmd)}")
        
        # Запускаем Docker с перехватом вывода в реальном времени
        import threading
        process = subprocess.Popen(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Читаем вывод построчно в реальном времени
        def read_output(pipe, log_func, prefix, original_stream):
            try:
                for line in iter(pipe.readline, ''):
                    if line.strip():
                        log_func(f"Docker {prefix}: {line.rstrip()}")
                        # Также выводим в терминал
                        original_stream.write(line)
                        original_stream.flush()
                pipe.close()
            except:
                pass
        
        # Запускаем чтение в отдельных потоках
        stdout_thread = threading.Thread(
            target=read_output,
            args=(process.stdout, _logger.info, "stdout", sys.stdout),
            daemon=True
        )
        stderr_thread = threading.Thread(
            target=read_output,
            args=(process.stderr, _logger.warning, "stderr", sys.stderr),
            daemon=True
        )
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Ждем завершения процесса
        return_code = process.wait()
        
        # Ждем завершения потоков чтения
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, docker_cmd)
        
        _logger.info("Docker сборка завершена успешно")
        
        # Копируем результаты
        _logger.info("Копирование результатов из контейнера...")
        print_step("Копирование результатов...")
        output_file = project_dir / project_config["output_name"]
        result = subprocess.run([
            "docker", "cp", f"{container_name}:/build/{project_config['output_name']}", str(output_file)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            os.chmod(output_file, 0o755)
            size = output_file.stat().st_size / (1024 * 1024)  # MB
            _logger.info(f"Сборка завершена успешно: {output_file} ({size:.2f} MB)")
            print_success("Сборка завершена успешно")
            return True
        else:
            _logger.error(f"Ошибка копирования: {result.stderr}")
            print_error(f"Ошибка копирования: {result.stderr}")
            return False
            
    except subprocess.CalledProcessError as e:
        _logger.exception(f"Ошибка сборки: {e}")
        print_error(f"Ошибка сборки: {e}")
        return False
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

# ============================================================================
# УДАЛЕННАЯ СБОРКА
# ============================================================================

def build_remote(project, platform_name):
    """Запускает удаленную сборку на сервере"""
    _logger.info(f"Запуск удаленной сборки: {project} для {platform_name}")
    
    if project not in PROJECTS:
        _logger.error(f"Неизвестный проект: {project}")
        print_error(f"Неизвестный проект: {project}")
        return False
    
    if platform_name not in BUILD_PLATFORMS:
        _logger.error(f"Неизвестная платформа: {platform_name}")
        print_error(f"Неизвестная платформа: {platform_name}")
        return False
    
    project_config = PROJECTS[project]
    platform_config = BUILD_PLATFORMS[platform_name]
    
    _logger.info(f"Конфигурация проекта: {project_config}")
    _logger.info(f"Конфигурация платформы: {platform_config}")
    
    # Проверяем подключение к серверу
    _logger.info("Проверка подключения к серверу...")
    if not test_connection():
        _logger.error("Не удалось подключиться к серверу")
        return False
    
    # Проверяем наличие готового объединенного файла
    _logger.info("Проверка объединенного файла...")
    if not check_unified_file(project):
        _logger.error("Объединенный файл не найден")
        return False
    
    # Загружаем исходники на сервер
    _logger.info("Загрузка исходников на сервер...")
    print_step("Загрузка исходников на сервер...")
    if not upload_sources(project):
        _logger.error("Не удалось загрузить исходники на сервер")
        return False
    
    # Пути на сервере
    incoming_path = get_incoming_path(project)
    outgoing_path = get_outgoing_path(project, platform_name)
    
    # Создаем папку для результатов
    create_remote_directory(outgoing_path)
    
    # Имя образа
    image_name = platform_config["image_name"]
    
    # Проверяем/создаем образ на сервере
    _logger.info(f"Проверка существования образа на сервере: {image_name}")
    if not check_remote_image_exists(image_name):
        _logger.info("Образ не найден на сервере, запуск сборки...")
        print_step("Сборка Docker образа на сервере...")
        dockerfile_path = get_dockerfile_path(platform_name)
        if not dockerfile_path:
            _logger.error("Dockerfile не найден")
            return False
        
        _logger.info(f"Dockerfile: {dockerfile_path}")
        
        # Загружаем Dockerfile на сервер
        from .server_connection import scp_upload
        remote_dockerfile = f"{incoming_path}/{dockerfile_path.name}"
        _logger.info(f"Загрузка Dockerfile на сервер: {remote_dockerfile}")
        if not scp_upload(dockerfile_path, remote_dockerfile):
            _logger.error("Не удалось загрузить Dockerfile на сервер")
            return False
        
        # Собираем образ
        _logger.info(f"Сборка образа на сервере: {image_name}")
        if not build_remote_image(
            remote_dockerfile,
            image_name,
            incoming_path,
            DOCKER_CONFIG["platform"]
        ):
            _logger.error("Не удалось собрать образ на сервере")
            return False
    else:
        _logger.info(f"Docker образ {image_name} уже существует на сервере")
        print_success(f"Docker образ {image_name} уже существует на сервере")
    
    # Запускаем сборку на сервере
    print_step("Запуск сборки на сервере...")
    container_name = f"fsa-builder-{platform_name}-temp"
    output_name = project_config["output_name"]
    
    # Команда сборки
    input_file = project_config.get('input_file', f"{project_config['output_name']}.py")
    build_cmd = f"""
cd {incoming_path} && \
docker run --rm \
  --platform {DOCKER_CONFIG['platform']} \
  --name {container_name} \
  -v $(pwd):/build \
  -e INPUT_FILE={input_file} \
  -e OUTPUT_NAME={output_name} \
  {image_name} \
  bash /build/DockerManager/scripts/docker_build.sh && \
cp {output_name} {outgoing_path}/ && \
chmod +x {outgoing_path}/{output_name}
"""
    
    try:
        result = execute_ssh_command(build_cmd, check=True, capture_output=False)
        print_success("Сборка завершена на сервере")
        
        # Скачиваем результат
        if download_build(project, platform_name):
            print_success("Сборка завершена успешно")
            return True
        else:
            print_error("Не удалось скачать результат")
            return False
            
    except Exception as e:
        print_error(f"Ошибка сборки на сервере: {e}")
        return False

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def build(project, platform_name, remote=False):
    """Главная функция сборки"""
    _logger.info("=" * 60)
    _logger.info(f"=== Сборка {project} для {platform_name} ({'удаленно' if remote else 'локально'}) ===")
    _logger.info("=" * 60)
    print("=" * 60)
    print(f"=== Сборка {project} для {platform_name} ===")
    print("=" * 60)
    
    try:
        if remote:
            result = build_remote(project, platform_name)
        else:
            result = build_local(project, platform_name)
        
        if result:
            _logger.info("Сборка завершена успешно")
        else:
            _logger.error("Сборка завершена с ошибками")
        
        return result
    except Exception as e:
        _logger.exception(f"Критическая ошибка при сборке: {e}")
        raise


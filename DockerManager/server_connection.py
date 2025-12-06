#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с удаленным сервером через SSH/SCP
Версия: V3.1.162 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import subprocess
import shutil
import threading
from pathlib import Path
from .config import REMOTE_SERVER
from .logger import get_logger

# Инициализируем логгер
_logger = get_logger("DockerManager.ServerConnection")

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def print_step(message):
    _logger.info(f"[#] {message}")
    print(f"\n[#] {message}")

def print_success(message):
    _logger.info(f"[OK] {message}")
    print(f"[OK] {message}")

def print_error(message):
    _logger.error(f"[ERROR] {message}")
    print(f"[ERROR] {message}")

def print_info(message):
    _logger.info(f"[i] {message}")
    print(f"[i] {message}")

# ============================================================================
# SSH ОПЕРАЦИИ
# ============================================================================

def get_ssh_command(command, use_sudo=False):
    """Формирует SSH команду"""
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        f"{REMOTE_SERVER['user']}@{REMOTE_SERVER['host']}"
    ]
    if use_sudo:
        command = f"sudo {command}"
    ssh_cmd.append(command)
    _logger.debug(f"SSH команда: {' '.join(ssh_cmd)}")
    return ssh_cmd

def execute_ssh_command(command, use_sudo=False, check=True, capture_output=True):
    """Выполняет команду на удаленном сервере через SSH"""
    _logger.info(f"SSH команда: {command} (sudo={use_sudo})")
    ssh_cmd = get_ssh_command(command, use_sudo)
    try:
        if capture_output:
            # Захватываем вывод для логирования
            result = subprocess.run(
                ssh_cmd,
                check=check,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.stdout:
                # Логируем весь stdout построчно
                for line in result.stdout.rstrip().split('\n'):
                    if line.strip():
                        _logger.info(f"SSH stdout: {line}")
            if result.stderr:
                # Логируем весь stderr построчно
                for line in result.stderr.rstrip().split('\n'):
                    if line.strip():
                        _logger.warning(f"SSH stderr: {line}")
        else:
            # Если capture_output=False, используем Popen для построчного чтения
            # чтобы видеть вывод в реальном времени и логировать его
            import select
            process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Читаем вывод построчно в реальном времени
            import threading
            def read_output(pipe, log_func, prefix):
                try:
                    for line in iter(pipe.readline, ''):
                        if line.strip():
                            log_func(f"SSH {prefix}: {line.rstrip()}")
                            # Также выводим в терминал
                            print(line, end='')
                    pipe.close()
                except:
                    pass
            
            # Запускаем чтение в отдельных потоках
            stdout_thread = threading.Thread(
                target=read_output, 
                args=(process.stdout, _logger.info, "stdout"),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_output,
                args=(process.stderr, _logger.warning, "stderr"),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Ждем завершения процесса
            return_code = process.wait(timeout=300)
            
            # Ждем завершения потоков чтения
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            
            # Создаем объект результата для совместимости
            class Result:
                def __init__(self, returncode):
                    self.returncode = returncode
                    self.stdout = ""
                    self.stderr = ""
            
            result = Result(return_code)
            
            if check and return_code != 0:
                raise subprocess.CalledProcessError(return_code, ssh_cmd)
        
        _logger.info(f"SSH команда выполнена успешно (код: {result.returncode})")
        return result
    except subprocess.CalledProcessError as e:
        _logger.error(f"Ошибка выполнения SSH команды: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            # Логируем весь stderr построчно
            for line in str(e.stderr).rstrip().split('\n'):
                if line.strip():
                    _logger.error(f"SSH stderr: {line}")
            print_error(str(e.stderr))
        if hasattr(e, 'stdout') and e.stdout:
            # Логируем stdout даже при ошибке
            for line in str(e.stdout).rstrip().split('\n'):
                if line.strip():
                    _logger.info(f"SSH stdout: {line}")
        print_error(f"Ошибка выполнения SSH команды: {e}")
        raise
    except subprocess.TimeoutExpired:
        _logger.error("Таймаут выполнения SSH команды (300 сек)")
        print_error("Таймаут выполнения SSH команды")
        raise

def test_connection():
    """Проверяет подключение к серверу"""
    _logger.info(f"Проверка подключения к серверу {REMOTE_SERVER['user']}@{REMOTE_SERVER['host']}")
    print_step("Проверка подключения к серверу...")
    try:
        result = execute_ssh_command("echo 'OK'", check=True)
        if result.stdout.strip() == "OK":
            _logger.info("Подключение к серверу установлено успешно")
            print_success("Подключение к серверу установлено")
            return True
        else:
            _logger.warning(f"Неожиданный ответ от сервера: {result.stdout}")
    except Exception as e:
        _logger.exception(f"Ошибка подключения к серверу: {e}")
        print_error(f"Не удалось подключиться к серверу: {e}")
        return False
    return False

# ============================================================================
# SCP ОПЕРАЦИИ
# ============================================================================

def scp_upload(local_path, remote_path, recursive=False):
    """Загружает файл/папку на сервер через SCP"""
    if not Path(local_path).exists():
        print_error(f"Локальный путь не существует: {local_path}")
        return False
    
    scp_cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10"
    ]
    if recursive:
        scp_cmd.append("-r")
    scp_cmd.extend([
        str(local_path),
        f"{REMOTE_SERVER['user']}@{REMOTE_SERVER['host']}:{remote_path}"
    ])
    
    try:
        _logger.info(f"SCP загрузка: {local_path} → {remote_path}")
        print_step(f"Загрузка {local_path} → {remote_path}...")
        result = subprocess.run(
            scp_cmd,
            check=True,
            capture_output=True,
            text=True
        )
        _logger.info(f"Файл успешно загружен: {local_path}")
        print_success("Файл загружен")
        return True
    except subprocess.CalledProcessError as e:
        _logger.error(f"Ошибка SCP загрузки: {e}")
        if e.stderr:
            _logger.error(f"SCP stderr: {e.stderr}")
            print_error(e.stderr)
        print_error(f"Ошибка загрузки файла: {e}")
        return False

def scp_download(remote_path, local_path, recursive=False):
    """Скачивает файл/папку с сервера через SCP"""
    scp_cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10"
    ]
    if recursive:
        scp_cmd.append("-r")
    scp_cmd.extend([
        f"{REMOTE_SERVER['user']}@{REMOTE_SERVER['host']}:{remote_path}",
        str(local_path)
    ])
    
    try:
        _logger.info(f"SCP скачивание: {remote_path} → {local_path}")
        print_step(f"Скачивание {remote_path} → {local_path}...")
        # Используем capture_output=False чтобы видеть прогресс в реальном времени
        result = subprocess.run(
            scp_cmd,
            check=True,
            capture_output=False,
            text=True
        )
        _logger.info(f"Файл успешно скачан: {local_path}")
        print_success("Файл скачан")
        return True
    except subprocess.CalledProcessError as e:
        _logger.error(f"Ошибка SCP скачивания: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            for line in e.stderr.rstrip().split('\n'):
                if line.strip():
                    _logger.error(f"SCP stderr: {line}")
            print_error(e.stderr)
        print_error(f"Ошибка скачивания файла: {e}")
        return False

# ============================================================================
# РАБОТА С ПАПКАМИ НА СЕРВЕРЕ
# ============================================================================

def create_remote_directory(remote_path):
    """Создает папку на сервере"""
    try:
        execute_ssh_command(f"mkdir -p {remote_path}", check=True)
        return True
    except Exception as e:
        print_error(f"Не удалось создать папку {remote_path}: {e}")
        return False

def list_remote_directory(remote_path):
    """Списывает содержимое папки на сервере"""
    try:
        result = execute_ssh_command(f"ls -la {remote_path}", check=False)
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception as e:
        print_error(f"Не удалось получить список файлов: {e}")
        return None

def remove_remote_file(remote_path):
    """Удаляет файл на сервере"""
    try:
        execute_ssh_command(f"rm -f {remote_path}", check=True)
        return True
    except Exception as e:
        print_error(f"Не удалось удалить файл: {e}")
        return False

def remove_remote_directory(remote_path):
    """Удаляет папку на сервере"""
    try:
        execute_ssh_command(f"rm -rf {remote_path}", check=True)
        return True
    except Exception as e:
        print_error(f"Не удалось удалить папку: {e}")
        return False


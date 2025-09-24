#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-AstraInstall Automation - Единый исполняемый файл
Автоматически распаковывает компоненты и запускает автоматизацию astra-setup.sh
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import tempfile
import subprocess
import shutil

# Встроенные компоненты (будут добавлены автоматически)
EMBEDDED_FILES = {
    'automation/repo_checker.py': '',
    'config/auto_responses.json': ''
}

def create_embedded_data():
    """Создание встроенных данных из файлов проекта"""
    embedded_data = {}
    
    # Читаем файлы проекта
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # automation/repo_checker.py
    repo_checker_path = os.path.join(project_root, 'automation', 'repo_checker.py')
    if os.path.exists(repo_checker_path):
        with open(repo_checker_path, 'r') as f:
            embedded_data['automation/repo_checker.py'] = f.read()
    
    # config/auto_responses.json
    config_path = os.path.join(project_root, 'config', 'auto_responses.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            embedded_data['config/auto_responses.json'] = f.read()
    
    return embedded_data

def extract_embedded_files():
    """Извлечение встроенных файлов во временную папку"""
    print("📦 Извлечение компонентов...")
    
    # Создаем временную папку
    temp_dir = tempfile.mkdtemp(prefix='astra-automation-')
    print("   Временная папка: %s" % temp_dir)
    
    # Получаем встроенные данные
    embedded_data = create_embedded_data()
    
    # Создаем структуру папок
    automation_dir = os.path.join(temp_dir, 'automation')
    config_dir = os.path.join(temp_dir, 'config')
    os.makedirs(automation_dir)
    os.makedirs(config_dir)
    
    # Извлекаем файлы
    for file_path, content in embedded_data.items():
        full_path = os.path.join(temp_dir, file_path)
        with open(full_path, 'w') as f:
            f.write(content)
        
        # Делаем исполняемым для Python файлов
        if file_path.endswith('.py'):
            os.chmod(full_path, 0755)
        
        print("   ✅ Извлечен: %s" % file_path)
    
    return temp_dir

def check_system_requirements():
    """Проверка системных требований"""
    print("🔍 Проверка системных требований...")
    
    # Проверяем права root
    if os.geteuid() != 0:
        print("❌ Требуются права root для работы с системными файлами")
        print("   Запустите: sudo python astra-automation.py")
        return False
    
    # Проверяем Python версию
    if sys.version_info[0] != 2 or sys.version_info[1] < 7:
        print("❌ Требуется Python 2.7+")
        print("   Текущая версия: %s" % sys.version)
        return False
    
    # Проверяем наличие apt-get
    try:
        subprocess.check_call(['which', 'apt-get'], 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
        print("✅ apt-get найден")
    except subprocess.CalledProcessError:
        print("❌ apt-get не найден - возможно не Debian/Ubuntu система")
        return False
    
    # Проверяем наличие sources.list
    sources_list = '/etc/apt/sources.list'
    if not os.path.exists(sources_list):
        print("❌ Файл %s не найден" % sources_list)
        return False
    
    print("✅ Все требования выполнены")
    return True

def run_repo_checker(temp_dir):
    """Запуск модуля проверки репозиториев"""
    print("\n🚀 Запуск автоматизации проверки репозиториев...")
    
    repo_checker_path = os.path.join(temp_dir, 'automation', 'repo_checker.py')
    
    if not os.path.exists(repo_checker_path):
        print("❌ Модуль repo_checker.py не найден")
        return False
    
    try:
        # Запускаем модуль проверки репозиториев
        result = subprocess.call([sys.executable, repo_checker_path])
        
        if result == 0:
            print("✅ Автоматизация завершена успешно!")
            return True
        else:
            print("❌ Ошибка выполнения автоматизации")
            return False
            
    except Exception as e:
        print("❌ Ошибка запуска: %s" % str(e))
        return False

def cleanup_temp_files(temp_dir):
    """Очистка временных файлов"""
    try:
        shutil.rmtree(temp_dir)
        print("🧹 Временные файлы очищены")
    except Exception as e:
        print("⚠ Предупреждение: не удалось очистить временные файлы: %s" % str(e))

def main():
    """Основная функция"""
    print("=" * 60)
    print("FSA-AstraInstall Automation")
    print("Автоматизация установки Astra.IDE")
    print("=" * 60)
    
    temp_dir = None
    
    try:
        # Проверяем системные требования
        if not check_system_requirements():
            sys.exit(1)
        
        # Извлекаем встроенные файлы
        temp_dir = extract_embedded_files()
        
        # Запускаем автоматизацию
        success = run_repo_checker(temp_dir)
        
        if success:
            print("\n🎉 Автоматизация завершена успешно!")
        else:
            print("\n💥 Автоматизация завершена с ошибками")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹ Остановлено пользователем")
        sys.exit(1)
    except Exception as e:
        print("\n💥 Критическая ошибка: %s" % str(e))
        sys.exit(1)
    finally:
        # Очищаем временные файлы
        if temp_dir:
            cleanup_temp_files(temp_dir)

if __name__ == '__main__':
    main()

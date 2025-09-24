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

def get_embedded_repo_checker():
    """Встроенный код repo_checker.py"""
    return '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль автоматизации проверки репозиториев для astra-setup.sh
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import subprocess
import tempfile
import shutil
from collections import defaultdict

class RepoChecker(object):
    """Класс для проверки и настройки репозиториев APT"""
    
    def __init__(self):
        self.sources_list = '/etc/apt/sources.list'
        self.backup_file = '/etc/apt/sources.list.backup'
        self.activated_count = 0
        self.deactivated_count = 0
        self.working_repos = []
        self.broken_repos = []
    
    def backup_sources_list(self):
        """Создание backup файла репозиториев"""
        try:
            if os.path.exists(self.sources_list):
                shutil.copy2(self.sources_list, self.backup_file)
                print("✅ Backup создан: %s" % self.backup_file)
                return True
            else:
                print("❌ Файл sources.list не найден: %s" % self.sources_list)
                return False
        except Exception as e:
            print("❌ Ошибка создания backup: %s" % str(e))
            return False
    
    def check_repo_availability(self, repo_line):
        """Проверка доступности одного репозитория"""
        try:
            # Создаем временный файл с одним репозиторием
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_file.write(repo_line + '\\n')
            temp_file.close()
            
            # Проверяем доступность через apt-get update
            cmd = [
                'apt-get', 'update',
                '-o', 'Dir::Etc::sourcelist=%s' % temp_file.name,
                '-o', 'Dir::Etc::sourceparts=-',
                '-o', 'APT::Get::List-Cleanup=0'
            ]
            
            result = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setpgrp
            )
            stdout, stderr = result.communicate()
            
            # Удаляем временный файл
            os.unlink(temp_file.name)
            
            if result.returncode == 0:
                repo_name = repo_line.split()[1] if len(repo_line.split()) > 1 else repo_line
                print("✅ Рабочий: %s" % repo_name)
                return True
            else:
                repo_name = repo_line.split()[1] if len(repo_line.split()) > 1 else repo_line
                print("❌ Не доступен: %s" % repo_name)
                return False
                
        except Exception as e:
            print("❌ Ошибка проверки репозитория: %s" % str(e))
            return False
    
    def process_all_repos(self):
        """Обработка всех репозиториев из sources.list"""
        print("\\n2. Проверка репозиториев...")
        print("==========================")
        
        try:
            with open(self.sources_list, 'r') as f:
                lines = f.readlines()
            
            # Создаем временный файл для нового sources.list
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_file.write("# Astra Linux repositories - auto configured\\n")
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('#deb') or line.startswith('deb'):
                    # Обрабатываем репозиторий
                    if line.startswith('#'):
                        # Закомментированный репозиторий
                        clean_line = line[1:].strip()
                        if self.check_repo_availability(clean_line):
                            temp_file.write(clean_line + '\\n')
                            self.activated_count += 1
                            self.working_repos.append(clean_line)
                        else:
                            temp_file.write(line + '\\n')
                            self.deactivated_count += 1
                            self.broken_repos.append(clean_line)
                    else:
                        # Активный репозиторий
                        if self.check_repo_availability(line):
                            temp_file.write(line + '\\n')
                            self.activated_count += 1
                            self.working_repos.append(line)
                        else:
                            temp_file.write('# ' + line + '\\n')
                            self.deactivated_count += 1
                            self.broken_repos.append(line)
                else:
                    # Комментарии и пустые строки
                    temp_file.write(line + '\\n')
            
            temp_file.close()
            
            # Удаляем дубликаты
            self._remove_duplicates(temp_file.name)
            
            return temp_file.name
            
        except Exception as e:
            print("❌ Ошибка обработки репозиториев: %s" % str(e))
            return None
    
    def _remove_duplicates(self, temp_file):
        """Удаление дубликатов из временного файла"""
        try:
            with open(temp_file, 'r') as f:
                lines = f.readlines()
            
            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            
            with open(temp_file, 'w') as f:
                f.writelines(unique_lines)
                
        except Exception as e:
            print("⚠ Предупреждение: не удалось удалить дубликаты: %s" % str(e))
    
    def get_statistics(self):
        """Получение статистики по репозиториям"""
        return {
            'activated': self.activated_count,
            'deactivated': self.deactivated_count,
            'working_repos': self.working_repos,
            'broken_repos': self.broken_repos
        }
    
    def apply_changes(self, temp_file):
        """Применение изменений к sources.list"""
        try:
            shutil.copy2(temp_file, self.sources_list)
            print("\\n✅ Изменения применены к sources.list")
            
            print("\\nАктивированные репозитории:")
            with open(self.sources_list, 'r') as f:
                for line in f:
                    if line.strip().startswith('deb '):
                        print("   • %s" % line.strip())
            
            return True
        except Exception as e:
            print("❌ Ошибка применения изменений: %s" % str(e))
            return False

def main():
    """Основная функция для тестирования"""
    print("==================================================")
    print("Тест модуля проверки репозиториев")
    print("==================================================")
    
    checker = RepoChecker()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("❌ Требуются права root для работы с /etc/apt/sources.list")
        print("Запустите: sudo python repo_checker.py")
        sys.exit(1)
    
    # Создаем backup
    if not checker.backup_sources_list():
        sys.exit(1)
    
    # Обрабатываем репозитории
    temp_file = checker.process_all_repos()
    if not temp_file:
        sys.exit(1)
    
    # Показываем статистику
    stats = checker.get_statistics()
    print("\\nСТАТИСТИКА РЕПОЗИТОРИЕВ:")
    print("=========================")
    print("📡 Репозитории:")
    print("   • Активировано: %d рабочих" % stats['activated'])
    print("   • Деактивировано: %d нерабочих" % stats['deactivated'])
    
    # Применяем изменения
    if checker.apply_changes(temp_file):
        print("\\n✅ Тест завершен успешно!")
    else:
        print("\\n❌ Ошибка применения изменений")
    
    # Очистка
    try:
        os.unlink(temp_file)
    except:
        pass

if __name__ == '__main__':
    main()
'''

def get_embedded_config():
    """Встроенная конфигурация auto_responses.json"""
    return '''{
    "description": "Правила автоматических ответов на интерактивные запросы системы",
    "rules": {
        "openssl.cnf": "N",
        "keyboard-configuration": "Y", 
        "default": "N"
    },
    "interactive_patterns": {
        "dpkg_config": "\\\\*\\\\*\\\\* .* \\\\(Y/I/N/O/D/Z\\\\) \\\\[.*\\\\] \\\\?",
        "apt_config": "Настройка пакета",
        "keyboard_config": "Выберите подходящую раскладку клавиатуры"
    }
}'''

def create_embedded_data():
    """Создание встроенных данных из файлов проекта"""
    print("🔍 Поиск файлов проекта...")
    embedded_data = {}
    
    # Читаем файлы проекта
    project_root = os.path.dirname(os.path.abspath(__file__))
    print("   Текущая папка: %s" % project_root)
    
    # automation/repo_checker.py
    repo_checker_path = os.path.join(project_root, 'automation', 'repo_checker.py')
    print("   Ищем: %s" % repo_checker_path)
    if os.path.exists(repo_checker_path):
        print("   ✅ Найден файл проекта, читаем...")
        with open(repo_checker_path, 'r') as f:
            embedded_data['automation/repo_checker.py'] = f.read()
        print("   ✅ Файл прочитан (%d символов)" % len(embedded_data['automation/repo_checker.py']))
    else:
        print("   ❌ Файл не найден, используем встроенную версию")
        embedded_data['automation/repo_checker.py'] = get_embedded_repo_checker()
        print("   ✅ Встроенная версия загружена (%d символов)" % len(embedded_data['automation/repo_checker.py']))
    
    # config/auto_responses.json
    config_path = os.path.join(project_root, 'config', 'auto_responses.json')
    print("   Ищем: %s" % config_path)
    if os.path.exists(config_path):
        print("   ✅ Найден файл проекта, читаем...")
        with open(config_path, 'r') as f:
            embedded_data['config/auto_responses.json'] = f.read()
        print("   ✅ Файл прочитан (%d символов)" % len(embedded_data['config/auto_responses.json']))
    else:
        print("   ❌ Файл не найден, используем встроенную версию")
        embedded_data['config/auto_responses.json'] = get_embedded_config()
        print("   ✅ Встроенная версия загружена (%d символов)" % len(embedded_data['config/auto_responses.json']))
    
    print("📋 Итого подготовлено файлов: %d" % len(embedded_data))
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
    print("   Создаем папки: %s, %s" % (automation_dir, config_dir))
    os.makedirs(automation_dir)
    os.makedirs(config_dir)
    
    # Извлекаем файлы
    print("   Извлекаем файлы...")
    for file_path, content in embedded_data.items():
        full_path = os.path.join(temp_dir, file_path)
        print("     Записываем: %s (%d символов)" % (file_path, len(content)))
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        # Делаем исполняемым для Python файлов
        if file_path.endswith('.py'):
            os.chmod(full_path, 0755)
            print("     ✅ Сделано исполняемым: %s" % file_path)
        else:
            print("     ✅ Извлечен: %s" % file_path)
    
    print("📁 Структура временной папки:")
    for root, dirs, files in os.walk(temp_dir):
        level = root.replace(temp_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print("   %s%s/" % (indent, os.path.basename(root)))
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print("   %s%s" % (subindent, file))
    
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
    print("   Путь к модулю: %s" % repo_checker_path)
    
    if not os.path.exists(repo_checker_path):
        print("❌ Модуль repo_checker.py не найден")
        print("   Проверяем содержимое папки automation:")
        automation_dir = os.path.join(temp_dir, 'automation')
        if os.path.exists(automation_dir):
            for file in os.listdir(automation_dir):
                print("     - %s" % file)
        else:
            print("     Папка automation не существует!")
        return False
    
    print("   ✅ Модуль найден, запускаем...")
    print("   Команда: %s %s" % (sys.executable, repo_checker_path))
    
    try:
        # Запускаем модуль проверки репозиториев
        result = subprocess.call([sys.executable, repo_checker_path])
        
        print("   Код возврата: %d" % result)
        
        if result == 0:
            print("✅ Автоматизация завершена успешно!")
            return True
        else:
            print("❌ Ошибка выполнения автоматизации (код: %d)" % result)
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

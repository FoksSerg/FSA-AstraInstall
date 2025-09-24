#!/usr/bin/env python
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
    
    def backup_sources_list(self, dry_run=False):
        """Создание backup файла репозиториев"""
        try:
            if os.path.exists(self.sources_list):
                if dry_run:
                    print("⚠️ РЕЖИМ ТЕСТИРОВАНИЯ: backup НЕ создан (только симуляция)")
                    print("✅ Backup будет создан: %s" % self.backup_file)
                else:
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
            temp_file.write(repo_line + '\n')
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
        print("\n2. Проверка репозиториев...")
        print("==========================")
        
        try:
            with open(self.sources_list, 'r') as f:
                lines = f.readlines()
            
            # Создаем временный файл для нового sources.list
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_file.write("# Astra Linux repositories - auto configured\n")
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('#deb') or line.startswith('deb'):
                    # Обрабатываем репозиторий
                    if line.startswith('#'):
                        # Закомментированный репозиторий
                        clean_line = line[1:].strip()
                        if self.check_repo_availability(clean_line):
                            temp_file.write(clean_line + '\n')
                            self.activated_count += 1
                            self.working_repos.append(clean_line)
                        else:
                            temp_file.write(line + '\n')
                            self.deactivated_count += 1
                            self.broken_repos.append(clean_line)
                    else:
                        # Активный репозиторий
                        if self.check_repo_availability(line):
                            temp_file.write(line + '\n')
                            self.activated_count += 1
                            self.working_repos.append(line)
                        else:
                            temp_file.write('# ' + line + '\n')
                            self.deactivated_count += 1
                            self.broken_repos.append(line)
                else:
                    # Комментарии и пустые строки
                    temp_file.write(line + '\n')
            
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
    
    def apply_changes(self, temp_file, dry_run=False):
        """Применение изменений к sources.list"""
        try:
            if dry_run:
                print("\n⚠️ РЕЖИМ ТЕСТИРОВАНИЯ: изменения НЕ применены к sources.list")
                print("✅ Изменения будут применены к sources.list")
                
                print("\nАктивированные репозитории (будут активированы):")
                with open(temp_file, 'r') as f:
                    for line in f:
                        if line.strip().startswith('deb '):
                            print("   • %s" % line.strip())
            else:
                shutil.copy2(temp_file, self.sources_list)
                print("\n✅ Изменения применены к sources.list")
                
                print("\nАктивированные репозитории:")
                with open(self.sources_list, 'r') as f:
                    for line in f:
                        if line.strip().startswith('deb '):
                            print("   • %s" % line.strip())
            
            return True
        except Exception as e:
            print("❌ Ошибка применения изменений: %s" % str(e))
            return False

def main(dry_run=False):
    """Основная функция для тестирования"""
    checker = RepoChecker()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("❌ Требуются права root для работы с /etc/apt/sources.list")
        print("Запустите: sudo python repo_checker.py")
        return False
    
    # Создаем backup
    if not checker.backup_sources_list(dry_run):
        return False
    
    # Обрабатываем репозитории
    temp_file = checker.process_all_repos()
    if not temp_file:
        return False
    
    # Показываем статистику
    stats = checker.get_statistics()
    print("\nСТАТИСТИКА РЕПОЗИТОРИЕВ:")
    print("=========================")
    print("📡 Репозитории:")
    print("   • Активировано: %d рабочих" % stats['activated'])
    print("   • Деактивировано: %d нерабочих" % stats['deactivated'])
    
    # Применяем изменения
    if checker.apply_changes(temp_file, dry_run):
        if dry_run:
            print("\n✅ Тест завершен успешно! (РЕЖИМ ТЕСТИРОВАНИЯ)")
        else:
            print("\n✅ Тест завершен успешно!")
    else:
        print("\n❌ Ошибка применения изменений")
        return False
    
    # Очистка
    try:
        os.unlink(temp_file)
    except:
        pass
    
    return True

if __name__ == '__main__':
    # Проверяем аргументы командной строки
    dry_run = False
    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        dry_run = True
    
    print("==================================================")
    if dry_run:
        print("Тест модуля проверки репозиториев (РЕЖИМ ТЕСТИРОВАНИЯ)")
    else:
        print("Тест модуля проверки репозиториев")
    print("==================================================")
    
    success = main(dry_run)
    
    if not success:
        sys.exit(1)
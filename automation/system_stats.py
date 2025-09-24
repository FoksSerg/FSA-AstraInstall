#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль анализа статистики системы для astra-setup.sh
Совместимость: Python 2.7.16
"""

from __future__ import print_function
import os
import sys
import subprocess
import re

class SystemStats(object):
    """Класс для анализа статистики системы и пакетов"""
    
    def __init__(self):
        self.updatable_packages = 0
        self.packages_to_update = 0
        self.packages_to_remove = 0
        self.updatable_list = []
        self.packages_to_install = {
            'python': 4,
            'utilities': 5,
            'wine': 3,
            'total': 12
        }
    
    def get_updatable_packages(self):
        """Анализ доступных обновлений"""
        print("📦 Анализ доступных обновлений...")
        
        try:
            # Получаем список обновляемых пакетов
            cmd = ['apt', 'list', '--upgradable']
            result = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = result.communicate()
            
            if result.returncode == 0:
                lines = stdout.strip().split('\n')
                # Первая строка - заголовок, остальные - пакеты
                self.updatable_packages = len(lines) - 1 if len(lines) > 1 else 0
                self.packages_to_update = self.updatable_packages
                
                # Сохраняем первые несколько пакетов для показа
                self.updatable_list = lines[1:6] if len(lines) > 1 else []
                
                print("   ✅ Найдено %d пакетов для обновления" % self.packages_to_update)
                return True
            else:
                print("   ❌ Ошибка получения списка обновлений: %s" % stderr.strip())
                return False
                
        except Exception as e:
            print("   ❌ Ошибка анализа обновлений: %s" % str(e))
            return False
    
    def get_autoremove_packages(self):
        """Анализ пакетов для автоудаления"""
        print("🗑️ Анализ пакетов для автоудаления...")
        
        try:
            # Симулируем автоудаление
            cmd = ['apt-get', 'autoremove', '--simulate']
            result = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = result.communicate()
            
            if result.returncode == 0:
                # Ищем строку с количеством пакетов для удаления
                output = stdout.decode('utf-8', errors='ignore')
                
                # Паттерны для поиска количества пакетов
                patterns = [
                    r'(\d+)\s+пакетов?\s+будет\s+удалено',
                    r'(\d+)\s+packages?\s+will\s+be\s+removed',
                    r'(\d+)\s+пакетов?\s+будет\s+удалено',
                    r'(\d+)\s+пакетов?\s+будут\s+удалены'
                ]
                
                self.packages_to_remove = 0
                for pattern in patterns:
                    match = re.search(pattern, output, re.IGNORECASE)
                    if match:
                        self.packages_to_remove = int(match.group(1))
                        break
                
                print("   ✅ Найдено %d пакетов для удаления" % self.packages_to_remove)
                return True
            else:
                print("   ❌ Ошибка симуляции автоудаления: %s" % stderr.strip())
                return False
                
        except Exception as e:
            print("   ❌ Ошибка анализа автоудаления: %s" % str(e))
            return False
    
    def calculate_install_stats(self):
        """Подсчет пакетов для установки"""
        print("📋 Подсчет пакетов для установки...")
        
        # Python и зависимости
        python_packages = ['python3', 'python3-pip', 'python3-apt', 'python3-venv']
        
        # Системные утилиты
        utility_packages = ['wget', 'curl', 'git', 'nano', 'htop']
        
        # Wine компоненты
        wine_packages = ['wine', 'winetricks', 'libgl1-mesa-dri', 'libgl1-mesa-glx']
        
        # Проверяем доступность пакетов
        python_count = self._check_packages_availability(python_packages)
        utility_count = self._check_packages_availability(utility_packages)
        wine_count = self._check_packages_availability(wine_packages)
        
        self.packages_to_install = {
            'python': python_count,
            'utilities': utility_count,
            'wine': wine_count,
            'total': python_count + utility_count + wine_count
        }
        
        print("   ✅ Python: %d пакетов" % python_count)
        print("   ✅ Утилиты: %d пакетов" % utility_count)
        print("   ✅ Wine: %d пакетов" % wine_count)
        print("   ✅ Итого: %d пакетов" % self.packages_to_install['total'])
        
        return True
    
    def _check_packages_availability(self, packages):
        """Проверка доступности пакетов в репозиториях"""
        try:
            cmd = ['apt-cache', 'show'] + packages
            result = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = result.communicate()
            
            # Подсчитываем количество найденных пакетов
            if result.returncode == 0:
                # Каждый пакет начинается с "Package:"
                package_count = stdout.count('Package:')
                return package_count
            else:
                # Если команда не сработала, возвращаем примерное количество
                return len(packages)
                
        except Exception as e:
            # В случае ошибки возвращаем примерное количество
            return len(packages)
    
    def display_statistics(self):
        """Отображение статистики операций"""
        print("\nСТАТИСТИКА ОПЕРАЦИЙ:")
        print("====================")
        
        # Репозитории (будет заполнено извне)
        print("📡 Репозитории:")
        print("   • Активировано: [будет заполнено из repo_checker]")
        print("   • Деактивировано: [будет заполнено из repo_checker]")
        
        # Обновление системы
        print("\n📦 Обновление системы:")
        print("   • Пакетов для обновления: %d" % self.packages_to_update)
        
        if self.packages_to_update > 0 and self.updatable_list:
            print("   • Первые пакеты:")
            for package in self.updatable_list:
                if package.strip():
                    print("     - %s" % package.strip())
        
        # Очистка системы
        print("\n🗑️ Очистка системы:")
        print("   • Пакетов для удаления: %d" % self.packages_to_remove)
        
        # Установка новых пакетов
        print("\n📦 Установка новых пакетов:")
        print("   • Python и зависимости: %d пакетов" % self.packages_to_install['python'])
        print("   • Системные утилиты: %d пакетов" % self.packages_to_install['utilities'])
        print("   • Wine и компоненты: %d пакетов" % self.packages_to_install['wine'])
        print("   • ИТОГО: %d пакетов" % self.packages_to_install['total'])
    
    def get_full_statistics(self):
        """Получение полной статистики"""
        return {
            'updatable_packages': self.updatable_packages,
            'packages_to_update': self.packages_to_update,
            'packages_to_remove': self.packages_to_remove,
            'packages_to_install': self.packages_to_install,
            'updatable_list': self.updatable_list
        }

def main(dry_run=False):
    """Основная функция для тестирования"""
    stats = SystemStats()
    
    # Проверяем права доступа
    if os.geteuid() != 0:
        print("❌ Требуются права root для работы с системными пакетами")
        print("Запустите: sudo python system_stats.py")
        return False
    
    # Анализируем обновления
    if not stats.get_updatable_packages():
        print("⚠ Предупреждение: не удалось получить список обновлений")
    
    # Анализируем автоудаление
    if not stats.get_autoremove_packages():
        print("⚠ Предупреждение: не удалось проанализировать автоудаление")
    
    # Подсчитываем пакеты для установки
    if not stats.calculate_install_stats():
        print("⚠ Предупреждение: не удалось подсчитать пакеты для установки")
    
    # Показываем статистику
    stats.display_statistics()
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("Тест модуля статистики системы")
    print("=" * 60)
    
    success = main()
    
    if success:
        print("\n✅ Тест модуля статистики завершен!")
    else:
        print("\n❌ Ошибка теста модуля статистики")
        sys.exit(1)

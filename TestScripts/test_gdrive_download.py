#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки скачивания из Google Drive
Версия: V3.7.210 (2025.12.30)
Компания: ООО "НПА Вира-Реалтайм"
"""

import sys
import os
import importlib.util

# Загружаем основной модуль
script_dir = os.path.dirname(os.path.abspath(__file__))
module_path = os.path.join(script_dir, 'FSA-AstraInstall.py')

spec = importlib.util.spec_from_file_location("FSA_AstraInstall", module_path)
if spec is None or spec.loader is None:
    print(f"[ERROR] Не удалось загрузить модуль: {module_path}", file=sys.stderr)
    sys.exit(1)

FSA_AstraInstall = importlib.util.module_from_spec(spec)
sys.modules["FSA_AstraInstall"] = FSA_AstraInstall
spec.loader.exec_module(FSA_AstraInstall)

# Импортируем нужные классы и функции
ComponentHandler = FSA_AstraInstall.ComponentHandler
GDRIVE_BASE_FOLDER_ID = FSA_AstraInstall.GDRIVE_BASE_FOLDER_ID

# Создаем простой mock класс для тестирования методов ComponentHandler
class TestComponentHandler(ComponentHandler):
    """Минимальная реализация ComponentHandler для тестирования"""
    def __init__(self):
        """Инициализация с обработкой возможных ошибок"""
        try:
            super().__init__()
        except Exception as e:
            # Обработка ошибок при инициализации (например, проблемы с pwd на некоторых системах)
            print(f"[WARNING] Ошибка при инициализации ComponentHandler: {e}", file=sys.stderr)
            # Устанавливаем базовые атрибуты вручную
            self.astrapack_dir = None
            self.logger = None
            self.callback = None
            self.universal_runner = None
            self.progress_manager = None
            self.dual_logger = None
            self.status_manager = None
            self.home = os.path.expanduser("~")
            self.wineprefix = os.path.join(self.home, ".wine-astraregul")
    
    def check_status(self):
        return 'ok'
    
    def get_category(self):
        return 'test'
    
    def install(self):
        pass
    
    def uninstall(self):
        pass

def test_gdrive_download():
    """Тестирование скачивания всех файлов из Google Drive по очереди (от маленьких к большим)"""
    
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ СКАЧИВАНИЯ ВСЕХ ФАЙЛОВ ИЗ GOOGLE DRIVE")
    print("=" * 80)
    
    # Создаем экземпляр ComponentHandler для теста
    handler = TestComponentHandler()
    
    # Список всех файлов для тестирования (от маленьких к большим по предполагаемому размеру)
    # Порядок: CountPack (самый маленький), Winetricks, Wine, AstraPack (самый большой)
    test_files = [
        {
            'name': 'CountPack.tar.gz',
            'folder_path': 'Count',
            'sha256': 'a247cba034871ad74eddafe3327867230d7a1a2a50170c1fa91f09d999441c56',
            'component_id': 'test_count'
        },
        {
            'name': 'winetricks_packages.tar.gz',
            'folder_path': 'Winetricks',
            'sha256': 'b29d28be92701d10f7425854d94e6629e3d600deee808cf8c3f24af65a398a4e',
            'component_id': 'test_winetricks'
        },
        {
            'name': 'wine_packages.tar.gz',
            'folder_path': 'Wine',
            'sha256': '05dddf8c1618835469cef9cebaf87a636e9e8c470332658149ea1dc396da4870',
            'component_id': 'test_wine'
        },
        {
            'name': 'AstraPack.tar.gz',
            'folder_path': 'Astra',
            'sha256': '763be94c419533342e87f61944bda7e2f61556a052f52cc340d90b28de1373bd',
            'component_id': 'test_astra'
        }
    ]
    
    print(f"\n[INFO] Будет протестировано {len(test_files)} файлов")
    print(f"[INFO] Глобальная базовая папка: {GDRIVE_BASE_FOLDER_ID}")
    print(f"[INFO] Порядок тестирования: от маленьких к большим файлам\n")
    
    results = []
    
    # Тестируем каждый файл
    for idx, file_info in enumerate(test_files, 1):
        print("\n" + "=" * 80)
        print(f"[TEST {idx}/{len(test_files)}] Скачивание {file_info['name']} из папки {file_info['folder_path']}")
        print("=" * 80)
        
        test_config = {
            'type': 'gdrive',
            'folder_path': file_info['folder_path'],
            'file_name': file_info['name'],
            'sha256': file_info['sha256']
        }
        
        print(f"[INFO] Конфигурация: {test_config}")
        
        try:
            result = handler._download_from_gdrive(test_config, component_id=file_info['component_id'])
        except Exception as e:
            print(f"\n[ERROR] Исключение при скачивании {file_info['name']}: {e}")
            results.append({
                'file': file_info['name'],
                'status': 'EXCEPTION',
                'size': 0
            })
            continue
        
        # Безопасная проверка результата
        if result and len(result) == 2 and result[1]:
            file_path = result[0]
            if file_path and os.path.exists(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                    print(f"\n[OK] Файл скачан: {file_path}")
                    print(f"[INFO] Размер файла: {file_size:,} байт ({file_size/1024/1024:.2f} МБ)")
                    
                    # Проверяем целостность
                    print("[INFO] Проверка целостности файла...")
                    try:
                        if handler._verify_archive_checksum(file_path, test_config):
                            print("[OK] Проверка целостности пройдена - SHA256 совпадает")
                            results.append({
                                'file': file_info['name'],
                                'status': 'OK',
                                'size': file_size,
                                'size_mb': file_size / 1024 / 1024
                            })
                        else:
                            print("[ERROR] Проверка целостности не пройдена - SHA256 не совпадает")
                            results.append({
                                'file': file_info['name'],
                                'status': 'CHECKSUM_FAILED',
                                'size': file_size
                            })
                    except Exception as e:
                        print(f"[ERROR] Ошибка при проверке целостности: {e}")
                        results.append({
                            'file': file_info['name'],
                            'status': 'CHECKSUM_ERROR',
                            'size': file_size
                        })
                except Exception as e:
                    print(f"[ERROR] Ошибка при получении размера файла: {e}")
                    results.append({
                        'file': file_info['name'],
                        'status': 'SIZE_ERROR',
                        'size': 0
                    })
            else:
                print(f"\n[ERROR] Файл не найден по пути: {file_path}")
                results.append({
                    'file': file_info['name'],
                    'status': 'FILE_NOT_FOUND',
                    'size': 0
                })
        else:
            print(f"\n[ERROR] Не удалось скачать файл {file_info['name']}")
            results.append({
                'file': file_info['name'],
                'status': 'FAILED',
                'size': 0
            })
    
    # Итоговая сводка
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ СВОДКА ТЕСТИРОВАНИЯ")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r['status'] == 'OK')
    failed_count = len(results) - success_count
    
    print(f"\nВсего файлов протестировано: {len(results)}")
    print(f"Успешно скачано: {success_count}")
    print(f"Ошибок: {failed_count}")
    
    print("\nДетали по файлам:")
    for r in results:
        status_icon = "✓" if r['status'] == 'OK' else "✗"
        size_info = f"{r.get('size_mb', 0):.2f} МБ" if 'size_mb' in r else "N/A"
        print(f"  {status_icon} {r['file']}: {r['status']} ({size_info})")
    
    print("\n" + "=" * 80)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 80)
    
    return success_count == len(results)

if __name__ == '__main__':
    success = test_gdrive_download()
    sys.exit(0 if success else 1)


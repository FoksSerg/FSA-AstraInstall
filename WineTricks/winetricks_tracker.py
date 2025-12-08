#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обертка для winetricks с логированием всех операций установки
и генерацией скрипта деинсталляции
Версия: V3.3.166 (2025.12.03)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import json
import os
import subprocess
import sys
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
import hashlib

class WinetricksTracker:
    def __init__(self, component_name, winetricks_path=None, log_dir=None):
        self.component_name = component_name
        self.winetricks_path = winetricks_path or 'winetricks'
        self.log_dir = Path(log_dir) if log_dir else Path.cwd() / 'install_logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.component_log_dir = self.log_dir / component_name
        self.component_log_dir.mkdir(exist_ok=True)
        
        self.manifest_file = self.component_log_dir / f"{component_name}_manifest.json"
        self.uninstall_script = self.component_log_dir / f"uninstall_{component_name}.sh"
        
        self.manifest = {
            'component': component_name,
            'timestamp': datetime.now().isoformat(),
            'wineprefix': os.environ.get('WINEPREFIX', '~/.wine'),
            'files_before': [],
            'files_after': [],
            'files_added': [],
            'files_modified': [],
            'registry_before': None,
            'registry_after': None,
            'registry_changes': [],
            'dll_overrides_before': {},
            'dll_overrides_after': {},
            'dll_overrides_added': [],
            'directories_created': [],
            'winetricks_output': []
        }
    
    def get_wineprefix(self):
        """Получает путь к WINEPREFIX"""
        wineprefix = os.environ.get('WINEPREFIX', os.path.expanduser('~/.wine'))
        return Path(os.path.expanduser(wineprefix))
    
    def get_system32_path(self):
        """Получает путь к system32"""
        wineprefix = self.get_wineprefix()
        return wineprefix / 'drive_c' / 'windows' / 'system32'
    
    def get_system64_path(self):
        """Получает путь к system64 (для win64)"""
        wineprefix = self.get_wineprefix()
        return wineprefix / 'drive_c' / 'windows' / 'syswow64'
    
    def get_fonts_path(self):
        """Получает путь к Fonts"""
        wineprefix = self.get_wineprefix()
        return wineprefix / 'drive_c' / 'windows' / 'Fonts'
    
    def scan_filesystem(self, paths=None):
        """Сканирует файловую систему и возвращает список файлов"""
        if paths is None:
            paths = [
                self.get_system32_path(),
                self.get_system64_path(),
                self.get_fonts_path()
            ]
        
        files = []
        for path in paths:
            if path.exists():
                for root, dirs, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = Path(root) / filename
                        try:
                            stat = filepath.stat()
                            files.append({
                                'path': str(filepath),
                                'size': stat.st_size,
                                'mtime': stat.st_mtime,
                                'sha256': self.get_file_hash(filepath)
                            })
                        except (OSError, PermissionError):
                            pass
        
        return files
    
    def get_file_hash(self, filepath):
        """Вычисляет SHA256 хеш файла"""
        try:
            sha256_hash = hashlib.sha256()
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except (OSError, PermissionError):
            return None
    
    def export_registry(self, output_file):
        """Экспортирует реестр Wine в файл"""
        wineprefix = self.get_wineprefix()
        reg_file = wineprefix / 'user.reg'
        
        if reg_file.exists():
            shutil.copy2(reg_file, output_file)
            return True
        return False
    
    def get_dll_overrides(self):
        """Извлекает DLL overrides из реестра через wine reg"""
        overrides = {}
        
        try:
            # Используем wine reg для чтения реестра (более надежно)
            wine = os.environ.get('WINE', 'wine')
            cmd = [wine, 'reg', 'query', 
                   'HKEY_CURRENT_USER\\Software\\Wine\\DllOverrides']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=dict(os.environ, WINEPREFIX=str(self.get_wineprefix()))
            )
            
            if result.returncode == 0:
                # Парсим вывод wine reg
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and 'REG_SZ' in line:
                        # Формат: "dllname"    REG_SZ    "mode"
                        parts = line.split('REG_SZ')
                        if len(parts) == 2:
                            dll_name = parts[0].strip().strip('"')
                            mode = parts[1].strip().strip('"')
                            if dll_name and mode:
                                overrides[dll_name] = mode
        except Exception as e:
            # Если wine reg не работает, пробуем читать файл напрямую
            wineprefix = self.get_wineprefix()
            reg_file = wineprefix / 'user.reg'
            
            if reg_file.exists():
                try:
                    # Пробуем разные кодировки
                    for encoding in ['utf-16le', 'utf-16', 'utf-8']:
                        try:
                            with open(reg_file, 'r', encoding=encoding, errors='ignore') as f:
                                content = f.read()
                            
                            # Ищем секцию DllOverrides
                            in_dll_overrides = False
                            for line in content.split('\n'):
                                if '[Software\\Wine\\DllOverrides]' in line or '[Software\\\\Wine\\\\DllOverrides]' in line:
                                    in_dll_overrides = True
                                    continue
                                elif line.strip().startswith('[') and in_dll_overrides:
                                    break
                                
                                if in_dll_overrides and '=' in line:
                                    # Парсим строку вида: "dllname"="mode" или "dllname"=dword:...
                                    line_clean = line.strip()
                                    if line_clean.startswith('"') and '=' in line_clean:
                                        # Извлекаем имя DLL и значение
                                        try:
                                            # Формат: "dllname"="mode"
                                            end_quote = line_clean.find('"', 1)
                                            if end_quote > 0:
                                                dll_name = line_clean[1:end_quote]
                                                value_part = line_clean[end_quote+1:].strip()
                                                if value_part.startswith('='):
                                                    value_part = value_part[1:].strip().strip('"')
                                                    if value_part:
                                                        overrides[dll_name] = value_part
                                        except:
                                            pass
                            break  # Успешно прочитали
                        except UnicodeDecodeError:
                            continue
                except Exception as e2:
                    print(f"  ⚠ Не удалось прочитать DLL overrides: {e2}", file=sys.stderr)
        
        return overrides
    
    def capture_state_before(self):
        """Захватывает состояние системы до установки"""
        print("📸 Захват состояния системы до установки...")
        
        # Сканируем файловую систему
        self.manifest['files_before'] = self.scan_filesystem()
        
        # Экспортируем реестр
        registry_before_file = self.component_log_dir / 'registry_before.reg'
        if self.export_registry(registry_before_file):
            self.manifest['registry_before'] = str(registry_before_file)
        
        # Получаем DLL overrides
        self.manifest['dll_overrides_before'] = self.get_dll_overrides()
        
        print(f"  ✓ Файлов просканировано: {len(self.manifest['files_before'])}")
        print(f"  ✓ DLL overrides найдено: {len(self.manifest['dll_overrides_before'])}")
    
    def capture_state_after(self):
        """Захватывает состояние системы после установки"""
        print("\n📸 Захват состояния системы после установки...")
        
        # Сканируем файловую систему
        self.manifest['files_after'] = self.scan_filesystem()
        
        # Экспортируем реестр
        registry_after_file = self.component_log_dir / 'registry_after.reg'
        if self.export_registry(registry_after_file):
            self.manifest['registry_after'] = str(registry_after_file)
        
        # Получаем DLL overrides
        self.manifest['dll_overrides_after'] = self.get_dll_overrides()
        
        print(f"  ✓ Файлов просканировано: {len(self.manifest['files_after'])}")
        print(f"  ✓ DLL overrides найдено: {len(self.manifest['dll_overrides_after'])}")
    
    def analyze_changes(self):
        """Анализирует изменения между до и после"""
        print("\n🔍 Анализ изменений...")
        
        # Создаем словари для быстрого поиска
        files_before_dict = {f['path']: f for f in self.manifest['files_before']}
        files_after_dict = {f['path']: f for f in self.manifest['files_after']}
        
        # Находим новые файлы
        for path, file_info in files_after_dict.items():
            if path not in files_before_dict:
                self.manifest['files_added'].append(file_info)
        
        # Находим измененные файлы
        for path, file_after in files_after_dict.items():
            if path in files_before_dict:
                file_before = files_before_dict[path]
                if file_after['sha256'] != file_before['sha256']:
                    self.manifest['files_modified'].append({
                        'path': path,
                        'before': file_before,
                        'after': file_after
                    })
        
        # Находим новые DLL overrides
        for dll, mode in self.manifest['dll_overrides_after'].items():
            if dll not in self.manifest['dll_overrides_before']:
                self.manifest['dll_overrides_added'].append({
                    'dll': dll,
                    'mode': mode
                })
        
        print(f"  ✓ Новых файлов: {len(self.manifest['files_added'])}")
        print(f"  ✓ Измененных файлов: {len(self.manifest['files_modified'])}")
        print(f"  ✓ Новых DLL overrides: {len(self.manifest['dll_overrides_added'])}")
    
    def run_winetricks(self, extra_args=None):
        """Запускает winetricks с перехватом вывода"""
        print(f"\n🚀 Запуск winetricks для установки '{self.component_name}'...")
        
        cmd = [self.winetricks_path, self.component_name]
        if extra_args:
            cmd.extend(extra_args)
        
        print(f"  Команда: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Сохраняем вывод
            self.manifest['winetricks_output'] = {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
            # Выводим результат
            if result.stdout:
                print("\n  Вывод winetricks:")
                for line in result.stdout.split('\n')[:20]:  # Первые 20 строк
                    if line.strip():
                        print(f"    {line}")
            
            if result.returncode != 0:
                print(f"\n  ⚠ Winetricks завершился с кодом {result.returncode}")
                if result.stderr:
                    print("  Ошибки:")
                    for line in result.stderr.split('\n')[:10]:
                        if line.strip():
                            print(f"    {line}")
            
            return result.returncode == 0
            
        except FileNotFoundError:
            print(f"  ✗ Ошибка: winetricks не найден по пути: {self.winetricks_path}")
            return False
        except Exception as e:
            print(f"  ✗ Ошибка при запуске winetricks: {e}")
            return False
    
    def save_manifest(self):
        """Сохраняет манифест установки"""
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Манифест сохранен: {self.manifest_file}")
    
    def generate_uninstall_script(self):
        """Генерирует скрипт деинсталляции"""
        print("\n📝 Генерация скрипта деинсталляции...")
        
        script_content = f"""#!/bin/bash
# Автоматически сгенерированный скрипт деинсталляции
# Компонент: {self.component_name}
# Дата установки: {self.manifest['timestamp']}
# Сгенерировано: {datetime.now().isoformat()}

set -e

WINEPREFIX="${{WINEPREFIX:-{self.manifest['wineprefix']}}}"
WINE="${{WINE:-wine}}"
WINE64="${{WINE64:-wine64}}"

echo "=========================================="
echo "Удаление компонента: {self.component_name}"
echo "=========================================="
echo ""

# Проверка существования WINEPREFIX
if [ ! -d "$WINEPREFIX" ]; then
    echo "Ошибка: WINEPREFIX не найден: $WINEPREFIX"
    exit 1
fi

echo "WINEPREFIX: $WINEPREFIX"
echo ""

"""
        
        # Удаление файлов
        if self.manifest['files_added']:
            script_content += "# Удаление добавленных файлов\n"
            script_content += "echo 'Удаление файлов...'\n"
            
            for file_info in self.manifest['files_added']:
                filepath = file_info['path']
                script_content += f"""
if [ -f "{filepath}" ]; then
    echo "  Удаление: {filepath}"
    rm -f "{filepath}"
else
    echo "  Файл не найден (уже удален?): {filepath}"
fi
"""
            script_content += "echo ''\n"
        
        # Удаление DLL overrides
        if self.manifest['dll_overrides_added']:
            script_content += "# Удаление DLL overrides из реестра\n"
            script_content += "echo 'Удаление DLL overrides...'\n"
            
            for override in self.manifest['dll_overrides_added']:
                dll = override['dll']
                script_content += f"""
echo "  Удаление override для: {dll}"
"$WINE" reg delete "HKEY_CURRENT_USER\\\\Software\\\\Wine\\\\DllOverrides" /v "{dll}" /f 2>/dev/null || true
"""
            script_content += "echo ''\n"
        
        # Отмена регистрации DLL (для файлов, которые были зарегистрированы)
        # Это сложнее определить автоматически, но можно попробовать для .dll файлов
        dll_files = [f for f in self.manifest['files_added'] if f['path'].lower().endswith('.dll')]
        if dll_files:
            script_content += "# Отмена регистрации DLL (опционально)\n"
            script_content += "echo 'Отмена регистрации DLL...'\n"
            
            for file_info in dll_files[:10]:  # Ограничиваем количество
                filepath = file_info['path']
                # Конвертируем Unix путь в Windows путь для regsvr32
                win_path = filepath.replace(str(self.get_wineprefix()), 'C:')
                win_path = win_path.replace('/', '\\')
                script_content += f"""
# Попытка отменить регистрацию: {filepath}
"$WINE" regsvr32 /u "{win_path}" 2>/dev/null || echo "    (не удалось отменить регистрацию, возможно не было зарегистрировано)"
"""
            script_content += "echo ''\n"
        
        # Удаление из winetricks.log
        script_content += f"""
# Удаление из winetricks.log
if [ -f "$WINEPREFIX/winetricks.log" ]; then
    echo "Удаление записи из winetricks.log..."
    if grep -q "^{self.component_name}$" "$WINEPREFIX/winetricks.log" 2>/dev/null; then
        sed -i.bak '/^{self.component_name}$/d' "$WINEPREFIX/winetricks.log"
        echo "  ✓ Запись удалена из winetricks.log"
    else
        echo "  (запись не найдена в winetricks.log)"
    fi
    echo ""
fi

echo "=========================================="
echo "Компонент '{self.component_name}' успешно удален!"
echo "=========================================="
"""
        
        with open(self.uninstall_script, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        os.chmod(self.uninstall_script, 0o755)
        print(f"  ✓ Скрипт создан: {self.uninstall_script}")
    
    def install(self, extra_args=None):
        """Выполняет полный цикл установки с отслеживанием"""
        print("=" * 60)
        print(f"Установка компонента: {self.component_name}")
        print("=" * 60)
        
        # Захватываем состояние до установки
        self.capture_state_before()
        
        # Запускаем winetricks
        success = self.run_winetricks(extra_args)
        
        if not success:
            print("\n⚠ Установка завершилась с ошибками, но продолжаем анализ...")
        
        # Захватываем состояние после установки
        self.capture_state_after()
        
        # Анализируем изменения
        self.analyze_changes()
        
        # Сохраняем манифест
        self.save_manifest()
        
        # Генерируем скрипт деинсталляции
        self.generate_uninstall_script()
        
        print("\n" + "=" * 60)
        print("✅ Отслеживание установки завершено!")
        print("=" * 60)
        print(f"\n📁 Логи сохранены в: {self.component_log_dir}")
        print(f"📄 Манифест: {self.manifest_file}")
        print(f"🗑️  Скрипт деинсталляции: {self.uninstall_script}")
        print(f"\nДля удаления выполните: bash {self.uninstall_script}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Обертка для winetricks с отслеживанием установки и генерацией деинсталлятора'
    )
    parser.add_argument('component', help='Название компонента для установки')
    parser.add_argument('--winetricks', default='winetricks',
                       help='Путь к winetricks (по умолчанию: winetricks)')
    parser.add_argument('--log-dir', default=None,
                       help='Директория для логов (по умолчанию: install_logs)')
    parser.add_argument('--force', action='store_true',
                       help='Передать --force в winetricks')
    
    args = parser.parse_args()
    
    # Определяем путь к winetricks относительно скрипта
    script_dir = Path(__file__).parent
    if args.winetricks == 'winetricks':
        winetricks_path = script_dir / 'winetricks'
        if not winetricks_path.exists():
            winetricks_path = 'winetricks'  # Используем системный
    else:
        winetricks_path = args.winetricks
    
    # Подготавливаем аргументы для winetricks
    extra_args = []
    if args.force:
        extra_args.append('--force')
    
    # Создаем трекер и запускаем установку
    tracker = WinetricksTracker(
        component_name=args.component,
        winetricks_path=str(winetricks_path),
        log_dir=args.log_dir
    )
    
    tracker.install(extra_args=extra_args)

if __name__ == '__main__':
    main()


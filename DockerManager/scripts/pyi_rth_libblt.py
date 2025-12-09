# -*- coding: utf-8 -*-
"""
PyInstaller Runtime Hook для предзагрузки libBLT с RTLD_GLOBAL
и настройки путей Tcl/Tk для tkinter
Этот hook выполняется ДО импорта tkinter, что позволяет предзагрузить libBLT
с флагом RTLD_GLOBAL и настроить переменные окружения TCL_LIBRARY и TK_LIBRARY

Версия: V3.3.171 (2025.12.07)
Компания: ООО "НПА Вира-Реалтайм"
Разработчик: @FoksSegr & AI Assistant (@LLM)
"""

import os
import sys
import platform

# КРИТИЧНО: Этот hook выполняется ДО импорта tkinter
# Поэтому мы можем настроить пути Tcl/Tk и предзагрузить libBLT с RTLD_GLOBAL здесь

def _setup_tcl_tk_paths():
    """Настройка путей Tcl/Tk для tkinter в PyInstaller frozen приложении
    Находит поддиректории с init.tcl и tk.tcl в _tcl_data и _tk_data
    и устанавливает TCL_LIBRARY и TK_LIBRARY на эти поддиректории
    """
    # Проверяем, что мы в PyInstaller frozen приложении
    if not hasattr(sys, '_MEIPASS'):
        return  # Не frozen приложение, ничего не делаем
    
    # КРИТИЧНО: На Linux проверяем UID - если не root (не sudo), ничего не делаем
    # Процесс пользователя завершится, и runtime hook выполнится в процессе sudo
    try:
        if os.name == 'posix':  # Unix-подобная система
            current_uid = os.geteuid()
            if current_uid != 0:  # Не root - это процесс пользователя
                return  # Пропускаем в процессе пользователя на Linux
    except (OSError, ImportError):
        # Если не удалось проверить UID, продолжаем (на всякий случай)
        pass
    
    base_path = sys._MEIPASS
    
    # КРИТИЧНО: Выводим в stderr (до инициализации логирования)
    sys.stderr.write(f"[RUNTIME_HOOK] Настройка Tcl/Tk путей, base_path={base_path}\n")
    sys.stderr.flush()
    
    # Ищем init.tcl в _tcl_data
    tcl_library = None
    tcl_data_path = os.path.join(base_path, '_tcl_data')
    
    # КРИТИЧНО: Проверяем существование директории
    if not os.path.exists(tcl_data_path):
        sys.stderr.write(f"[RUNTIME_HOOK] ❌ КРИТИЧНО: Директория _tcl_data НЕ СУЩЕСТВУЕТ: {tcl_data_path}\n")
        sys.stderr.write(f"[RUNTIME_HOOK] ❌ PyInstaller не включил скрипты Tcl в бинарник!\n")
        sys.stderr.flush()
    else:
        sys.stderr.write(f"[RUNTIME_HOOK] ✓ Директория _tcl_data найдена: {tcl_data_path}\n")
        sys.stderr.write(f"[RUNTIME_HOOK] Поиск init.tcl в {tcl_data_path}\n")
        sys.stderr.flush()
        for root, dirs, files in os.walk(tcl_data_path):
            if 'init.tcl' in files:
                tcl_library = root
                sys.stderr.write(f"[RUNTIME_HOOK] ✓ init.tcl найден в: {tcl_library}\n")
                sys.stderr.flush()
                break
        
        if not tcl_library:
            sys.stderr.write(f"[RUNTIME_HOOK] ❌ init.tcl НЕ найден в _tcl_data (директория существует, но файла нет)!\n")
            sys.stderr.flush()
    
    # Ищем tk.tcl в _tk_data
    tk_library = None
    tk_data_path = os.path.join(base_path, '_tk_data')
    
    # КРИТИЧНО: Проверяем существование директории
    if not os.path.exists(tk_data_path):
        sys.stderr.write(f"[RUNTIME_HOOK] ❌ КРИТИЧНО: Директория _tk_data НЕ СУЩЕСТВУЕТ: {tk_data_path}\n")
        sys.stderr.write(f"[RUNTIME_HOOK] ❌ PyInstaller не включил скрипты Tk в бинарник!\n")
        sys.stderr.flush()
    else:
        sys.stderr.write(f"[RUNTIME_HOOK] ✓ Директория _tk_data найдена: {tk_data_path}\n")
        sys.stderr.write(f"[RUNTIME_HOOK] Поиск tk.tcl в {tk_data_path}\n")
        sys.stderr.flush()
        for root, dirs, files in os.walk(tk_data_path):
            if 'tk.tcl' in files:
                tk_library = root
                sys.stderr.write(f"[RUNTIME_HOOK] ✓ tk.tcl найден в: {tk_library}\n")
                sys.stderr.flush()
                break
        
        if not tk_library:
            sys.stderr.write(f"[RUNTIME_HOOK] ❌ tk.tcl НЕ найден в _tk_data (директория существует, но файла нет)!\n")
            sys.stderr.flush()
    
    # Устанавливаем переменные окружения на найденные поддиректории
    # КРИТИЧНО: ВСЕГДА перезаписываем, даже если уже установлены
    if tcl_library:
        os.environ['TCL_LIBRARY'] = tcl_library
        sys.stderr.write(f"[RUNTIME_HOOK] ✓ TCL_LIBRARY установлен: {tcl_library}\n")
    else:
        sys.stderr.write(f"[RUNTIME_HOOK] ❌ TCL_LIBRARY НЕ установлен (init.tcl не найден)!\n")
    
    if tk_library:
        os.environ['TK_LIBRARY'] = tk_library
        sys.stderr.write(f"[RUNTIME_HOOK] ✓ TK_LIBRARY установлен: {tk_library}\n")
    else:
        sys.stderr.write(f"[RUNTIME_HOOK] ❌ TK_LIBRARY НЕ установлен (tk.tcl не найден)!\n")
    
    sys.stderr.flush()

def _preload_libblt():
    """Предзагрузка libBLT с RTLD_GLOBAL для tkinter"""
    # Проверяем, что мы в PyInstaller frozen приложении
    if not hasattr(sys, '_MEIPASS'):
        return  # Не frozen приложение, ничего не делаем
    
    base_path = sys._MEIPASS
    
    # Ищем libBLT в _MEIPASS
    blt_path = None
    for item in os.listdir(base_path):
        if item.startswith('libBLT') and (item.endswith('.so') or '.so.' in item):
            blt_path = os.path.join(base_path, item)
            break
    
    if not blt_path or not os.path.exists(blt_path):
        return  # libBLT не найдена, ничего не делаем
    
    # КРИТИЧНО: Устанавливаем LD_LIBRARY_PATH ДО попытки загрузки
    if 'LD_LIBRARY_PATH' in os.environ:
        if base_path not in os.environ['LD_LIBRARY_PATH'].split(':'):
            os.environ['LD_LIBRARY_PATH'] = f"{base_path}:{os.environ['LD_LIBRARY_PATH']}"
    else:
        os.environ['LD_LIBRARY_PATH'] = base_path
    
    # КРИТИЧНО: Предзагружаем зависимости libBLT (libtcl8.6.so и libtk8.6.so) с RTLD_GLOBAL
    # Затем предзагружаем libBLT с RTLD_GLOBAL
    try:
        import ctypes
        
        # Загружаем libdl для dlopen
        try:
            libdl = ctypes.CDLL("libdl.so.2")
        except OSError:
            # Пробуем альтернативные пути
            libdl_paths = [
                "/lib/x86_64-linux-gnu/libdl.so.2",
                "/lib64/libdl.so.2",
                "/usr/lib/x86_64-linux-gnu/libdl.so.2",
            ]
            libdl = None
            for path in libdl_paths:
                if os.path.exists(path):
                    try:
                        libdl = ctypes.CDLL(path)
                        break
                    except OSError:
                        continue
            
            if libdl is None:
                return  # Не можем загрузить libdl
        
        # Константы для dlopen
        RTLD_GLOBAL = 0x00100
        RTLD_NOW = 0x00002
        
        # Настраиваем dlopen
        dlopen = libdl.dlopen
        dlopen.argtypes = [ctypes.c_char_p, ctypes.c_int]
        dlopen.restype = ctypes.c_void_p
        
        # КРИТИЧНО: Сначала загружаем зависимости libBLT с RTLD_GLOBAL
        # libBLT зависит от libtcl8.6.so и libtk8.6.so
        for dep_name in ['libtcl8.6.so', 'libtk8.6.so']:
            dep_path = os.path.join(base_path, dep_name)
            if os.path.exists(dep_path):
                try:
                    handle = dlopen(dep_path.encode('utf-8'), RTLD_GLOBAL | RTLD_NOW)
                    if not handle:
                        # Пробуем по имени
                        handle = dlopen(dep_name.encode('utf-8'), RTLD_GLOBAL | RTLD_NOW)
                except Exception:
                    pass  # Игнорируем ошибки загрузки зависимостей
        
        # КРИТИЧНО: Теперь загружаем libBLT с RTLD_GLOBAL
        blt_name = os.path.basename(blt_path)
        
        # Пробуем загрузить по имени (через LD_LIBRARY_PATH)
        handle = dlopen(blt_name.encode('utf-8'), RTLD_GLOBAL | RTLD_NOW)
        
        if not handle:
            # Если не получилось по имени, пробуем прямой путь
            handle = dlopen(blt_path.encode('utf-8'), RTLD_GLOBAL | RTLD_NOW)
        
        # Если handle не NULL, библиотека успешно предзагружена с RTLD_GLOBAL
    except Exception:
        # Игнорируем ошибки - если не получилось предзагрузить, tkinter попробует сам
        pass

# КРИТИЧНО: Сначала настраиваем пути Tcl/Tk, затем предзагружаем libBLT
_setup_tcl_tk_paths()
_preload_libblt()


# План реализации удаленных источников для компонентов

**Версия документа:** 2.0.0  
**Дата создания:** 2025.12.30  
**Дата обновления:** 2025.12.30  
**Проект:** FSA-AstraInstall  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Текущая версия проекта:** V3.7.209 (2025.12.30)  
**Статус:** 📝 ПЛАН ОБНОВЛЕН - ГОТОВ К РЕАЛИЗАЦИИ

**Изменения в версии 2.0.0:**
- ✅ Переработана архитектура: вместо отдельных классов `RemoteSourceManager` и `CredentialManager` используются методы в `ComponentHandler` и вспомогательные функции
- ✅ Упрощена структура: учетные данные управляются через функции, а не класс
- ✅ Интеграция в существующую архитектуру: методы добавляются в `ComponentHandler`, переиспользуется код из `SystemUpdater`
- ✅ Обновлен формат конфигурации `remote_source` для Google Drive (реализован)

---

## 📋 Оглавление

1. [Цель реализации](#цель-реализации)
2. [Текущее состояние](#текущее-состояние)
3. [Проблема](#проблема)
4. [Архитектура решения](#архитектура-решения)
5. [Поддерживаемые протоколы](#поддерживаемые-протоколы)
6. [Структура данных](#структура-данных)
7. [Пошаговый план реализации](#пошаговый-план-реализации)
8. [Детальные изменения кода](#детальные-изменения-кода)
9. [Интеграция с GUI](#интеграция-с-gui)
10. [Примеры использования](#примеры-использования)
11. [Тестирование](#тестирование)
12. [Риски и митигация](#риски-и-митигация)

---

## 🎯 Цель реализации

Создать систему работы с удаленными источниками архивов компонентов, которая:

- ✅ Позволяет указывать удаленные источники в конфигурации компонентов
- ✅ Поддерживает множественные протоколы (SMB, HTTP/HTTPS, FTP, SSH/SCP, Google Drive)
- ✅ Предоставляет выбор: скачать в локальную папку или использовать напрямую
- ✅ Сохраняет учетные данные для аутентификации (с шифрованием)
- ✅ Выполняет проверку целостности (SHA256/MD5)
- ✅ Повторяет попытки скачивания при ошибках (3 попытки)
- ✅ Не использует частично скачанные файлы

---

## 📊 Текущее состояние

### Существующая функциональность:

| Компонент | Описание | Файл | Строки |
|-----------|----------|------|--------|
| `_resolve_single_file()` | Работа с файлами из разных источников | FSA-AstraInstall.py | 2758-3000 |
| `_find_archive()` | Поиск архивов в локальной папке | FSA-AstraInstall.py | 4162-4257 |
| `_resolve_archive_path_with_dialog()` | Диалог выбора архива | FSA-AstraInstall.py | 4259-4400 |
| Поддержка HTTP/HTTPS | Скачивание файлов по URL | FSA-AstraInstall.py | 2842-2898 |
| Проверка SHA256 | Валидация целостности | FSA-AstraInstall.py | 2876-2890 |

### Ограничения:

- ❌ Нет поддержки SMB, FTP, SSH/SCP
- ❌ Нет поддержки Google Drive
- ❌ Нет сохранения учетных данных
- ❌ Нет выбора стратегии (скачать/использовать напрямую)
- ❌ Нет повторных попыток при ошибках
- ❌ Нет проверки частично скачанных файлов

---

## 🔍 Проблема

### Проблема 1: Отсутствие локальных архивов

**Симптомы:**
- Архивы компонентов могут отсутствовать в локальной папке `AstraPack/`
- Необходимо вручную копировать архивы перед установкой
- Нет автоматического доступа к удаленным хранилищам

### Проблема 2: Разные источники данных

**Факторы:**
- Архивы могут находиться на SMB серверах
- Архивы могут быть в Google Drive
- Архивы могут быть на FTP/SSH серверах
- Нужна единая система работы со всеми источниками

### Проблема 3: Безопасность учетных данных

**Требования:**
- Хранение паролей в зашифрованном виде
- Индивидуальные учетные данные для каждого источника
- Безопасное хранение в локальном файле

---

## 🏗️ Архитектура решения

### Обзор

Система удаленных источников интегрируется в существующую архитектуру:

1. **Методы в ComponentHandler** — добавление методов для работы с удаленными источниками
2. **Вспомогательные функции** — функции для управления учетными данными (не классы)
3. **Модифицированный _find_archive()** — проверка remote_source при отсутствии локального архива
4. **Переиспользование существующего кода** — адаптация методов из SystemUpdater для SMB/Git

### Схема работы

```
┌─────────────────────────────────────────────────────────────────┐
│         ПОПЫТКА УСТАНОВКИ КОМПОНЕНТА                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │ Поиск локального     │
                   │ архива в AstraPack/  │
                   └──────────┬───────────┘
                              │
                      ┌───────┴────────┐
                      │                │
                   НАЙДЕН          НЕ НАЙДЕН
                      │                │
                      ▼                ▼
              ┌──────────────┐  ┌──────────────────────┐
              │ Установка из │  │ Проверка remote_source│
              │ локального   │  │ в конфигурации        │
              │ архива       │  └──────┬───────────────┘
              └──────────────┘         │
                                  ┌────┴────┐
                                  │          │
                              ЕСТЬ      НЕТ
                                  │          │
                                  ▼          ▼
                    ┌─────────────────────┐ ┌──────────────┐
                    │ Проверка настройки  │ │ Диалог выбора│
                    │ download_to_local   │ │ файла        │
                    │ в конфигурации      │ │ (как сейчас) │
                    └──────┬──────────────┘ └──────────────┘
                           │
                  ┌────────┴────────┐
                  │                 │
              TRUE (скачать)    FALSE (напрямую)
                  │                 │
                  ▼                 ▼
    ┌──────────────────────┐ ┌──────────────────────┐
    │ Диалог подтверждения │ │ Скачивание во       │
    │ (если нужно)         │ │ временную папку      │
    │                      │ │                      │
    │ ☐ Скачать в          │ │ Проверка целостности│
    │   локальную папку    │ │ (SHA256/MD5)         │
    │                      │ │                      │
    │ ☐ Использовать       │ │ Установка из         │
    │   напрямую           │ │ временного файла     │
    └──────┬───────────────┘ └──────────────────────┘
           │
      ВЫБРАНО
      "Скачать"
           │
           ▼
    ┌──────────────────────┐
    │ Скачивание архива    │
    │ (3 попытки)          │
    │                      │
    │ Проверка целостности│
    │ (SHA256/MD5)         │
    │                      │
    │ Копирование в        │
    │ AstraPack/.../       │
    │                      │
    │ Установка из         │
    │ локального архива    │
    └──────────────────────┘
```

---

## 🔌 Поддерживаемые протоколы

### 1. SMB (Server Message Block)

**Формат URL:**
```
smb://server/share/path/file.tar.gz
smb://user@server/share/path/file.tar.gz
smb://user:password@server/share/path/file.tar.gz
```

**Особенности:**
- Требует аутентификации (логин/пароль)
- Может требовать домен (workgroup)
- Поддержка через `smbclient` или монтирование

---

### 2. HTTP/HTTPS

**Формат URL:**
```
http://server/path/file.tar.gz
https://server/path/file.tar.gz
```

**Особенности:**
- Уже частично реализовано
- Может требовать Basic Auth
- Поддержка через `urllib` или `requests`

---

### 3. FTP

**Формат URL:**
```
ftp://server/path/file.tar.gz
ftp://user@server/path/file.tar.gz
ftp://user:password@server/path/file.tar.gz
```

**Особенности:**
- Требует аутентификации
- Поддержка через `ftplib` или `curl`

---

### 4. SSH/SCP

**Формат URL:**
```
scp://user@server:/path/file.tar.gz
ssh://user@server:/path/file.tar.gz
```

**Особенности:**
- Требует SSH ключи или пароль
- Поддержка через `paramiko` или `scp` команду

---

### 5. Google Drive

**Формат конфигурации (реализован):**
```python
'remote_source': {
    'type': 'gdrive',
    'base_folder_id': '1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW',
    'folder_path': 'Wine',  # Имя подпапки
    'file_name': 'wine_packages.tar.gz'
}
```

**Особенности:**
- Для публичных папок работает без API ключа через `gdown`
- Использует структуру: базовая папка → подпапка → файл
- Поддержка через библиотеку `gdown` (уже используется в проекте)
- Автоматическое определение ID файла внутри папки

**Реальная структура (проверена):**
```
Google Drive: 1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW (базовая папка)
├── Astra/ (ID: 1AsTk3DiGfEo3-EOlJo79j6iPJy6Ax5gu)
│   └── AstraPack.tar.gz (8147.76 МБ, SHA256: 763be94c419533342e87f61944bda7e2f61556a052f52cc340d90b28de1373bd)
├── Count/ (ID: 1e0-DhlgiFvtmx2FX0E00sPWTXH_rUD59)
│   └── CountPack.tar.gz (4411.03 МБ, SHA256: a247cba034871ad74eddafe3327867230d7a1a2a50170c1fa91f09d999441c56)
├── Wine/ (ID: 1wpI5WgbU6zERBWlKmW-8HfNG0h23funw)
│   └── wine_packages.tar.gz (110.49 МБ, SHA256: 05dddf8c1618835469cef9cebaf87a636e9e8c470332658149ea1dc396da4870)
└── Winetricks/ (ID: 1F1cqcg2t4rbOtuiRLLWQSWVEBdl3G00o)
    └── winetricks_packages.tar.gz (416.30 МБ, SHA256: b29d28be92701d10f7425854d94e6629e3d600deee808cf8c3f24af65a398a4e)
```

---

## 📁 Структура данных

### Конфигурация компонента (расширенная)

**Формат для Google Drive (реализован):**
```python
{
    'component_id': 'cont_designer',
    'source_dir': 'CountPack',
    'archive_group': 'Cont',
    
    # НОВОЕ: Удаленный источник
    'remote_source': {
        'type': 'gdrive',
        'base_folder_id': '1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW',
        'folder_path': 'Count',  # Относительно базовой папки
        'file_name': 'CountPack.tar.gz',
        'download_to_local': True,  # Скачать в локальную папку или использовать напрямую
        'local_path': 'AstraPack/Cont/CountPack.tar.gz',  # Куда сохранить
        'sha256': 'a247cba034871ad74eddafe3327867230d7a1a2a50170c1fa91f09d999441c56'
    }
}
```

**Формат для других протоколов (будущее расширение):**
```python
{
    'remote_source': {
        'type': 'smb',  # или 'http', 'https', 'ftp', 'scp', 'ssh'
        'url': 'smb://10.10.55.77/Install/AstraPack/Wine/wine_packages.tar.gz',
        # или для HTTP/HTTPS
        'url': 'https://server.example.com/archives/wine_packages.tar.gz',
        
        # Настройки скачивания
        'download_to_local': True,
        'local_path': 'AstraPack/Wine/wine_packages.tar.gz',
        'sha256': '05dddf8c1618835469cef9cebaf87a636e9e8c470332658149ea1dc396da4870',
        
        # Настройки аутентификации (опционально)
        'auth': {
            'username': 'user',  # Или None для использования сохраненных
            'password': None,  # Никогда не хранить в конфиге! Используется _load_credentials()
            'domain': None,  # Для SMB
            'key_file': None  # Для SSH
        },
        
        # Настройки повторных попыток
        'retry': {
            'max_attempts': 3,
            'delay_seconds': 5
        }
    }
}
```

### Файл учетных данных

**Расположение:** `~/.fsa-credentials.json` (зашифрованный)

**Структура:**
```json
{
    "version": "1.0",
    "credentials": {
        "smb://10.10.55.77": {
            "username": "user",
            "password": "encrypted_password",
            "domain": "WORKGROUP",
            "encrypted": true
        },
        "gdrive://1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW": {
            "api_key": "encrypted_api_key",
            "encrypted": true
        }
    }
}
```

**Безопасность:**
- Файл с правами 600 (только владелец)
- Пароли зашифрованы через ключ, производный от системной информации
- Ключ не хранится в открытом виде

**Реализация:**
- Вспомогательные функции (не класс): `_load_credentials()`, `_save_credentials()`, `_encrypt_password()`, `_decrypt_password()`
- Размещение: в начале файла FSA-AstraInstall.py, рядом с другими вспомогательными функциями

---

## 📝 Пошаговый план реализации

### Этап 1: Вспомогательные функции для учетных данных ⏱️ 2-3 часа

**Цель:** Реализовать безопасное хранение учетных данных.

**Файл:** FSA-AstraInstall.py (вспомогательные функции, не класс)

**Расположение:** В начале файла, после импортов, рядом с другими вспомогательными функциями

**Задачи:**
1. Реализовать функцию `_load_credentials()` — загрузка из файла
2. Реализовать функцию `_save_credentials()` — сохранение в файл
3. Реализовать функцию `_encrypt_password()` — шифрование пароля
4. Реализовать функцию `_decrypt_password()` — расшифровка пароля
5. Реализовать функцию `_get_encryption_key()` — генерация ключа из системной информации
6. Реализовать функцию `_normalize_source_url()` — нормализация URL для ключа
7. Добавить проверку прав доступа к файлу (600)
8. Создать файл `~/.fsa-credentials.json` при первом использовании

---

### Этап 2: Методы в ComponentHandler ⏱️ 4-5 часов

**Цель:** Добавить методы для работы с удаленными источниками в ComponentHandler.

**Файл:** FSA-AstraInstall.py (модификация класса ComponentHandler)

**Задачи:**
1. Добавить метод `_download_from_remote_source()` — универсальное скачивание
2. Добавить метод `_download_from_gdrive()` — скачивание из Google Drive (приоритет)
3. Добавить метод `_download_from_smb()` — скачивание из SMB (адаптировать из SystemUpdater)
4. Добавить метод `_download_from_http()` — расширить существующий `_resolve_single_file()`
5. Добавить метод `_download_from_ftp()` — скачивание из FTP
6. Добавить метод `_download_from_ssh()` — скачивание из SSH/SCP
7. Добавить метод `_verify_archive_checksum()` — проверка целостности (вынести из `_resolve_single_file()`)
8. Добавить метод `_download_with_retry()` — повторные попытки (3 попытки)
9. Добавить обработку частично скачанных файлов (удаление при ошибке)

---

### Этап 3: Модификация _find_archive() ⏱️ 1-2 часа

**Цель:** Интегрировать проверку remote_source в процесс поиска архивов.

**Файл:** FSA-AstraInstall.py (модификация метода ComponentHandler._find_archive())

**Задачи:**
1. Модифицировать метод `_find_archive()` — добавить проверку `remote_source` после локального поиска
2. Если локальный архив не найден и есть `remote_source`:
   - Проверить настройку `download_to_local`
   - Если True — скачать в `local_path` через `_download_from_remote_source()`
   - Если False — скачать во временную папку и использовать напрямую
3. Если `remote_source` не указан или скачивание не удалось — показать диалог выбора (существующая логика)
4. Сохранить логику поиска локальных архивов без изменений

---

### Этап 4: Интеграция с GUI (опционально) ⏱️ 1-2 часа

**Цель:** Добавить элементы управления удаленными источниками (если потребуется).

**Файл:** FSA-AstraInstall.py (модификация класса FSAAstraGUI)

**Задачи:**
1. Добавить диалог ввода учетных данных (если требуется аутентификация)
2. Добавить прогресс-бар для скачивания (использовать существующий UniversalProgressManager)
3. Добавить индикацию источника (локальный/удаленный) в статусе компонента
4. Опционально: диалог выбора стратегии (скачать/напрямую) — можно реализовать позже

**Примечание:** Базовая функциональность работает без GUI изменений — скачивание происходит автоматически при отсутствии локального архива.

---

### Этап 5: Тестирование ⏱️ 2-3 часа

**Цель:** Проверить работоспособность всех протоколов.

**Тесты (приоритет):**
1. ✅ Скачивание из Google Drive (реализовано и протестировано)
2. Проверка целостности SHA256 для Google Drive
3. Установка компонента из скачанного архива
4. Поведение при отсутствии локального архива и наличии remote_source

**Тесты (будущее расширение):**
5. Скачивание из SMB с аутентификацией
6. Скачивание из HTTP/HTTPS (расширение существующего)
7. Скачивание из FTP
8. Скачивание из SSH/SCP
9. Повторные попытки при ошибках
10. Удаление частично скачанных файлов
11. Сохранение и использование учетных данных

---

### Этап 6: Документирование ⏱️ 1 час

**Цель:** Обновить документацию проекта.

**Файлы:**
- README.md — добавить раздел об удаленных источниках
- HELPME.md — добавить инструкцию по использованию
- CHRONOLOGY.md — добавить запись о реализации

---

## 💻 Детальные изменения кода

### Изменение 1: Вспомогательные функции для учетных данных

**Расположение:** FSA-AstraInstall.py, после импортов, рядом с другими вспомогательными функциями (например, после `_get_start_dir()`)

**Примечание:** Это функции, а не класс, для простоты и отсутствия необходимости в экземплярах.

```python
# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ УЧЕТНЫХ ДАННЫХ
# ============================================================================

# Константа для файла учетных данных
CREDENTIALS_FILE = os.path.expanduser('~/.fsa-credentials.json')

def _ensure_credentials_file():
    """Создание файла учетных данных если не существует"""
    if not os.path.exists(CREDENTIALS_FILE):
        try:
            # Создаем пустой файл с правильными правами
            with open(CREDENTIALS_FILE, 'w') as f:
                json.dump({
                    'version': '1.0',
                    'credentials': {}
                }, f, indent=2)
            
            # Устанавливаем права 600 (только владелец)
            os.chmod(CREDENTIALS_FILE, 0o600)
            print(f"[INFO] Создан файл учетных данных: {CREDENTIALS_FILE}")
        except Exception as e:
            print(f"[ERROR] Не удалось создать файл учетных данных: {e}")
    else:
        # Проверяем права доступа
        stat_info = os.stat(CREDENTIALS_FILE)
        mode = stat_info.st_mode & 0o777
        if mode != 0o600:
            print(f"[WARNING] Файл учетных данных имеет неправильные права ({oct(mode)}), исправляем...")
            try:
                os.chmod(CREDENTIALS_FILE, 0o600)
            except Exception as e:
                print(f"[ERROR] Не удалось исправить права: {e}")

def _get_encryption_key():
        """
        Генерация ключа шифрования на основе системной информации
        
        Returns:
            bytes: Ключ для Fernet
        """
        try:
            # Используем системную информацию для генерации ключа
            system_info = {
                'hostname': socket.gethostname(),
                'user': os.getenv('USER', 'unknown'),
                'home': os.path.expanduser('~')
            }
            
            # Создаем соль из системной информации
            salt = hashlib.sha256(
                f"{system_info['hostname']}:{system_info['user']}:{system_info['home']}".encode()
            ).digest()
            
            # Генерируем ключ через PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            # Используем фиксированный пароль (производный от системы)
            password = f"{system_info['hostname']}{system_info['user']}".encode()
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            return key
            
        except Exception as e:
            print(f"[ERROR] Ошибка генерации ключа шифрования: {e}")
            # Fallback: используем простой ключ (менее безопасно)
            return base64.urlsafe_b64encode(b'fsa-astra-install-default-key-32bytes!!')
    
def _encrypt_password(password):
        """
        Шифрование пароля
        
        Args:
            password: Пароль в открытом виде
        
        Returns:
            str: Зашифрованный пароль (base64)
        """
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            encrypted = fernet.encrypt(password.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            print(f"[ERROR] Ошибка шифрования пароля: {e}")
            return None
    
def _decrypt_password(encrypted_password):
        """
        Расшифровка пароля
        
        Args:
            encrypted_password: Зашифрованный пароль (base64)
        
        Returns:
            str: Пароль в открытом виде или None
        """
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            encrypted_bytes = base64.b64decode(encrypted_password.encode())
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            print(f"[ERROR] Ошибка расшифровки пароля: {e}")
            return None
    
def _save_credentials_to_file(source_url, username=None, password=None, domain=None, api_key=None):
        """
        Сохранение учетных данных для источника
        
        Args:
            source_url: URL источника (например, smb://server или gdrive://folder_id)
            username: Имя пользователя (для SMB, FTP, SSH)
            password: Пароль (будет зашифрован)
            domain: Домен (для SMB)
            api_key: API ключ (для Google Drive)
        
        Returns:
            bool: True если сохранено успешно, False в случае ошибки
        """
        try:
            # Читаем существующие учетные данные
            credentials_data = self._load_credentials()
            
            # Нормализуем URL (убираем путь, оставляем только сервер/источник)
            normalized_url = self._normalize_source_url(source_url)
            
            # Подготавливаем данные для сохранения
            cred_data = {
                'encrypted': True
            }
            
            if username:
                cred_data['username'] = username
            if password:
                cred_data['password'] = self._encrypt_password(password)
            if domain:
                cred_data['domain'] = domain
            if api_key:
                cred_data['api_key'] = self._encrypt_password(api_key)
            
            # Сохраняем
            credentials_data['credentials'][normalized_url] = cred_data
            
            # Записываем обратно
            return self._save_credentials(credentials_data)
            
        except Exception as e:
            print(f"[ERROR] Ошибка сохранения учетных данных: {e}")
            return False
    
def _load_credentials_from_file(source_url):
        """
        Получение учетных данных для источника
        
        Args:
            source_url: URL источника
        
        Returns:
            dict: {
                'username': str или None,
                'password': str или None (расшифрованный),
                'domain': str или None,
                'api_key': str или None (расшифрованный)
            } или None если не найдено
        """
        try:
            credentials_data = self._load_credentials()
            normalized_url = self._normalize_source_url(source_url)
            
            if normalized_url not in credentials_data.get('credentials', {}):
                return None
            
            cred_data = credentials_data['credentials'][normalized_url]
            
            result = {}
            
            if 'username' in cred_data:
                result['username'] = cred_data['username']
            if 'password' in cred_data:
                result['password'] = self._decrypt_password(cred_data['password'])
            if 'domain' in cred_data:
                result['domain'] = cred_data['domain']
            if 'api_key' in cred_data:
                result['api_key'] = self._decrypt_password(cred_data['api_key'])
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Ошибка получения учетных данных: {e}")
            return None
    
    def delete_credentials(self, source_url):
        """
        Удаление учетных данных для источника
        
        Args:
            source_url: URL источника
        
        Returns:
            bool: True если удалено успешно, False в случае ошибки
        """
        try:
            credentials_data = self._load_credentials()
            normalized_url = self._normalize_source_url(source_url)
            
            if normalized_url in credentials_data.get('credentials', {}):
                del credentials_data['credentials'][normalized_url]
                return self._save_credentials(credentials_data)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка удаления учетных данных: {e}")
            return False
    
def _normalize_source_url(source_url):
        """
        Нормализация URL источника (убираем путь, оставляем только сервер/источник)
        
        Args:
            source_url: Полный URL
        
        Returns:
            str: Нормализованный URL
        """
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(source_url)
            
            # Для разных протоколов формируем нормализованный URL
            if parsed.scheme == 'smb':
                # smb://server/share -> smb://server
                return f"{parsed.scheme}://{parsed.netloc.split('/')[0]}"
            elif parsed.scheme in ['http', 'https', 'ftp']:
                # http://server/path -> http://server
                return f"{parsed.scheme}://{parsed.netloc}"
            elif parsed.scheme in ['scp', 'ssh']:
                # scp://user@server:/path -> scp://server
                host = parsed.netloc.split('@')[-1].split(':')[0]
                return f"{parsed.scheme}://{host}"
            elif parsed.scheme == 'gdrive':
                # gdrive://folder_id/file -> gdrive://folder_id
                path_parts = parsed.path.strip('/').split('/')
                if path_parts:
                    return f"{parsed.scheme}://{path_parts[0]}"
            else:
                # Для неизвестных протоколов возвращаем как есть
                return source_url
                
        except Exception as e:
            print(f"[WARNING] Ошибка нормализации URL: {e}, используем как есть")
            return source_url
    
def _load_credentials_data():
    """Загрузка всех учетных данных из файла"""
    try:
        _ensure_credentials_file()  # Убеждаемся что файл существует
        if not os.path.exists(CREDENTIALS_FILE):
            return {'version': '1.0', 'credentials': {}}
        
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
            
    except Exception as e:
        print(f"[ERROR] Ошибка загрузки учетных данных: {e}")
        return {'version': '1.0', 'credentials': {}}

def _save_credentials_data(credentials_data):
    """Сохранение всех учетных данных в файл"""
    try:
        # Создаем резервную копию
        if os.path.exists(CREDENTIALS_FILE):
            backup_file = CREDENTIALS_FILE + '.bak'
            shutil.copy2(CREDENTIALS_FILE, backup_file)
        
        # Сохраняем
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials_data, f, indent=2)
        
        # Устанавливаем права 600
        os.chmod(CREDENTIALS_FILE, 0o600)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка сохранения учетных данных: {e}")
        return False
```

---

### Изменение 2: Методы в ComponentHandler

**Расположение:** FSA-AstraInstall.py, в классе ComponentHandler (после метода `_resolve_single_file()`)

**Примечание:** Методы добавляются в существующий класс ComponentHandler, не создается новый класс.

```python
# В классе ComponentHandler добавить методы:

def _download_from_remote_source(self, remote_source_config, component_id=None):
    """
    Скачивание архива из удаленного источника
    
    Args:
        remote_source_config: Конфигурация remote_source из компонента
        component_id: ID компонента (для логирования)
    
    Returns:
        str или None: Путь к скачанному файлу или None при ошибке
    """
        """
        Скачивание файла из удаленного источника
        
        Args:
            remote_source_config: Конфигурация удаленного источника (dict)
            local_path: Локальный путь для сохранения (если None - временный файл)
            progress_callback: Функция для обновления прогресса (bytes_downloaded, total_bytes)
        
        Returns:
            tuple: (путь_к_файлу, успех) или (None, False) в случае ошибки
        """
        try:
            url = remote_source_config.get('url')
            if not url:
                print("[ERROR] URL удаленного источника не указан")
                return None, False
            
            # Определяем протокол
            protocol = self._get_protocol(url)
            
            if not protocol:
                print(f"[ERROR] Неподдерживаемый протокол в URL: {url}")
                return None, False
            
            # Получаем учетные данные
            credentials = self._get_credentials_for_url(url, remote_source_config)
            
            # Настройки повторных попыток
            max_attempts = remote_source_config.get('retry', {}).get('max_attempts', self.max_retry_attempts)
            delay = remote_source_config.get('retry', {}).get('delay_seconds', self.retry_delay_seconds)
            
            # Выполняем скачивание с повторными попытками
            for attempt in range(1, max_attempts + 1):
                try:
                    print(f"[INFO] Попытка скачивания {attempt}/{max_attempts}: {url}")
                    
                    # Скачиваем файл
                    if protocol == 'smb':
                        result = self._download_from_smb(url, local_path, credentials, progress_callback)
                    elif protocol in ['http', 'https']:
                        result = self._download_from_http(url, local_path, credentials, progress_callback)
                    elif protocol == 'ftp':
                        result = self._download_from_ftp(url, local_path, credentials, progress_callback)
                    elif protocol in ['scp', 'ssh']:
                        result = self._download_from_ssh(url, local_path, credentials, progress_callback)
                    elif protocol == 'gdrive':
                        result = self._download_from_gdrive(url, local_path, credentials, progress_callback)
                    else:
                        print(f"[ERROR] Протокол {protocol} не реализован")
                        return None, False
                    
                    if result[1]:  # Успешно скачано
                        downloaded_path = result[0]
                        
                        # Проверяем целостность
                        if not self._verify_checksum(downloaded_path, remote_source_config):
                            print(f"[ERROR] Проверка целостности не пройдена, удаляем файл")
                            if os.path.exists(downloaded_path):
                                os.remove(downloaded_path)
                            
                            if attempt < max_attempts:
                                print(f"[INFO] Повторная попытка через {delay} секунд...")
                                time.sleep(delay)
                                continue
                            else:
                                return None, False
                        
                        print(f"[OK] Файл успешно скачан: {downloaded_path}")
                        return downloaded_path, True
                    else:
                        # Ошибка скачивания
                        if attempt < max_attempts:
                            print(f"[WARNING] Ошибка скачивания, повторная попытка через {delay} секунд...")
                            time.sleep(delay)
                        else:
                            print(f"[ERROR] Не удалось скачать файл после {max_attempts} попыток")
                            return None, False
                
                except Exception as e:
                    print(f"[ERROR] Ошибка при попытке {attempt}: {e}")
                    if attempt < max_attempts:
                        print(f"[INFO] Повторная попытка через {delay} секунд...")
                        time.sleep(delay)
                    else:
                        return None, False
            
            return None, False
            
        except Exception as e:
            print(f"[ERROR] Критическая ошибка скачивания: {e}")
            import traceback
            traceback.print_exc()
            return None, False
    
    def _get_protocol(self, url):
        """Определение протокола из URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.scheme.lower()
        except:
            return None
    
    def _get_credentials_for_url(self, url, remote_source_config):
        """Получение учетных данных для URL"""
        # Сначала проверяем в конфигурации
        auth_config = remote_source_config.get('auth', {})
        if auth_config.get('username') or auth_config.get('password'):
            return {
                'username': auth_config.get('username'),
                'password': auth_config.get('password'),
                'domain': auth_config.get('domain'),
                'api_key': auth_config.get('api_key')
            }
        
        # Затем проверяем в сохраненных учетных данных
        saved_creds = self.credential_manager.get_credentials(url)
        if saved_creds:
            return saved_creds
        
        return {}
    
    def _verify_checksum(self, file_path, remote_source_config):
        """
        Проверка целостности файла
        
        Args:
            file_path: Путь к файлу
            remote_source_config: Конфигурация удаленного источника
        
        Returns:
            bool: True если проверка пройдена, False в случае ошибки
        """
        try:
            checksum_config = remote_source_config.get('checksum')
            if not checksum_config:
                print("[INFO] Проверка целостности не требуется")
                return True
            
            checksum_type = checksum_config.get('type', 'sha256').lower()
            expected_value = checksum_config.get('value', '').lower()
            
            if not expected_value:
                print("[WARNING] Значение checksum не указано, пропускаем проверку")
                return True
            
            print(f"[INFO] Проверка целостности ({checksum_type})...")
            
            # Вычисляем хеш файла
            if checksum_type == 'sha256':
                actual_value = self._calculate_sha256(file_path)
            elif checksum_type == 'md5':
                actual_value = self._calculate_md5(file_path)
            else:
                print(f"[ERROR] Неподдерживаемый тип checksum: {checksum_type}")
                return False
            
            if actual_value.lower() == expected_value.lower():
                print(f"[OK] Проверка целостности пройдена: {actual_value}")
                return True
            else:
                print(f"[ERROR] Проверка целостности не пройдена!")
                print(f"[ERROR] Ожидалось: {expected_value}")
                print(f"[ERROR] Получено: {actual_value}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Ошибка проверки целостности: {e}")
            return False
    
    def _calculate_sha256(self, file_path):
        """Вычисление SHA256 хеша файла"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _calculate_md5(self, file_path):
        """Вычисление MD5 хеша файла"""
        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def _download_from_smb(self, url, local_path, credentials, progress_callback):
        """
        Скачивание файла из SMB источника
        
        Args:
            url: SMB URL (smb://server/share/path/file.tar.gz)
            local_path: Локальный путь для сохранения
            credentials: Учетные данные {'username': ..., 'password': ..., 'domain': ...}
            progress_callback: Функция для обновления прогресса
        
        Returns:
            tuple: (путь_к_файлу, успех)
        """
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            server = parsed.netloc.split('/')[0]
            share_path = parsed.path.strip('/')
            
            # Определяем локальный путь
            if not local_path:
                temp_dir = tempfile.mkdtemp(prefix='smb_download_')
                filename = os.path.basename(share_path)
                local_path = os.path.join(temp_dir, filename)
            else:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            print(f"[INFO] Скачивание из SMB: {server}/{share_path}")
            
            # Используем smbclient для скачивания
            username = credentials.get('username', 'guest')
            password = credentials.get('password', '')
            domain = credentials.get('domain', '')
            
            # Формируем команду smbclient
            smb_path = f"//{server}/{share_path}"
            
            # Если указан домен, добавляем его
            if domain:
                username = f"{domain}\\{username}"
            
            # Команда для скачивания через smbclient
            cmd = [
                'smbclient',
                smb_path,
                '-U', username,
                '-c', f'get {os.path.basename(share_path)} {local_path}'
            ]
            
            # Если пароль указан, передаем через переменную окружения
            env = os.environ.copy()
            if password:
                env['PASSWORD'] = password
                cmd.extend(['-N'])  # Не запрашивать пароль
            
            result = subprocess.run(
                cmd,
                input=password.encode() if password else None,
                capture_output=True,
                text=True,
                timeout=3600,
                env=env
            )
            
            if result.returncode == 0 and os.path.exists(local_path):
                print(f"[OK] Файл скачан из SMB: {local_path}")
                return local_path, True
            else:
                print(f"[ERROR] Ошибка скачивания из SMB: {result.stderr}")
                if os.path.exists(local_path):
                    os.remove(local_path)  # Удаляем частично скачанный файл
                return None, False
                
        except subprocess.TimeoutExpired:
            print("[ERROR] Таймаут при скачивании из SMB")
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
            return None, False
        except Exception as e:
            print(f"[ERROR] Ошибка скачивания из SMB: {e}")
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
            return None, False
    
    def _download_from_http(self, url, local_path, credentials, progress_callback):
        """
        Скачивание файла из HTTP/HTTPS источника
        
        Args:
            url: HTTP/HTTPS URL
            local_path: Локальный путь для сохранения
            credentials: Учетные данные (для Basic Auth)
            progress_callback: Функция для обновления прогресса
        
        Returns:
            tuple: (путь_к_файлу, успех)
        """
        try:
            # Определяем локальный путь
            if not local_path:
                temp_dir = tempfile.mkdtemp(prefix='http_download_')
                filename = os.path.basename(urllib.parse.urlparse(url).path) or 'downloaded_file'
                local_path = os.path.join(temp_dir, filename)
            else:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            print(f"[INFO] Скачивание из HTTP/HTTPS: {url}")
            
            # Создаем opener с поддержкой Basic Auth
            if credentials.get('username') and credentials.get('password'):
                password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
                password_mgr.add_password(None, url, credentials['username'], credentials['password'])
                auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
                opener = urllib.request.build_opener(auth_handler)
            else:
                opener = urllib.request.build_opener()
            
            # Обработка SSL (для самоподписанных сертификатов)
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                https_handler = urllib.request.HTTPSHandler(context=ssl_context)
                opener = urllib.request.build_opener(https_handler)
            except:
                pass
            
            urllib.request.install_opener(opener)
            
            # Скачиваем файл
            urllib.request.urlretrieve(url, local_path)
            
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                print(f"[OK] Файл скачан из HTTP/HTTPS: {local_path}")
                return local_path, True
            else:
                print(f"[ERROR] Файл не скачан или пустой")
                if os.path.exists(local_path):
                    os.remove(local_path)
                return None, False
                
        except Exception as e:
            print(f"[ERROR] Ошибка скачивания из HTTP/HTTPS: {e}")
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
            return None, False
    
    def _download_from_ftp(self, url, local_path, credentials, progress_callback):
        """
        Скачивание файла из FTP источника
        
        Args:
            url: FTP URL (ftp://server/path/file.tar.gz)
            local_path: Локальный путь для сохранения
            credentials: Учетные данные {'username': ..., 'password': ...}
            progress_callback: Функция для обновления прогресса
        
        Returns:
            tuple: (путь_к_файлу, успех)
        """
        try:
            from urllib.parse import urlparse
            import ftplib
            
            parsed = urlparse(url)
            server = parsed.hostname
            port = parsed.port or 21
            remote_path = parsed.path
            
            # Определяем локальный путь
            if not local_path:
                temp_dir = tempfile.mkdtemp(prefix='ftp_download_')
                filename = os.path.basename(remote_path) or 'downloaded_file'
                local_path = os.path.join(temp_dir, filename)
            else:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            print(f"[INFO] Скачивание из FTP: {server}{remote_path}")
            
            # Подключаемся к FTP серверу
            ftp = ftplib.FTP()
            ftp.connect(server, port)
            
            username = credentials.get('username', 'anonymous')
            password = credentials.get('password', 'anonymous@')
            ftp.login(username, password)
            
            # Переходим в директорию (если указана)
            remote_dir = os.path.dirname(remote_path).strip('/')
            if remote_dir:
                ftp.cwd(remote_dir)
            
            # Скачиваем файл
            filename = os.path.basename(remote_path)
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {filename}', f.write)
            
            ftp.quit()
            
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                print(f"[OK] Файл скачан из FTP: {local_path}")
                return local_path, True
            else:
                print(f"[ERROR] Файл не скачан или пустой")
                if os.path.exists(local_path):
                    os.remove(local_path)
                return None, False
                
        except Exception as e:
            print(f"[ERROR] Ошибка скачивания из FTP: {e}")
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
            return None, False
    
    def _download_from_ssh(self, url, local_path, credentials, progress_callback):
        """
        Скачивание файла из SSH/SCP источника
        
        Args:
            url: SCP/SSH URL (scp://user@server:/path/file.tar.gz)
            local_path: Локальный путь для сохранения
            credentials: Учетные данные {'username': ..., 'password': ..., 'key_file': ...}
            progress_callback: Функция для обновления прогресса
        
        Returns:
            tuple: (путь_к_файлу, успех)
        """
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            user_host = parsed.netloc
            remote_path = parsed.path
            
            # Парсим user@host
            if '@' in user_host:
                username, host = user_host.split('@', 1)
            else:
                username = credentials.get('username', os.getenv('USER', 'root'))
                host = user_host
            
            # Убираем порт если указан
            if ':' in host:
                host, port = host.split(':', 1)
                port = int(port)
            else:
                port = 22
            
            # Определяем локальный путь
            if not local_path:
                temp_dir = tempfile.mkdtemp(prefix='scp_download_')
                filename = os.path.basename(remote_path) or 'downloaded_file'
                local_path = os.path.join(temp_dir, filename)
            else:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            print(f"[INFO] Скачивание из SCP: {username}@{host}:{remote_path}")
            
            # Используем scp команду
            scp_cmd = ['scp', '-P', str(port)]
            
            # Если указан ключ, используем его
            if credentials.get('key_file'):
                scp_cmd.extend(['-i', credentials['key_file']])
            
            # Формируем путь для scp
            scp_path = f"{username}@{host}:{remote_path}"
            scp_cmd.extend([scp_path, local_path])
            
            # Если указан пароль, используем sshpass
            password = credentials.get('password')
            if password:
                # Проверяем наличие sshpass
                if subprocess.run(['which', 'sshpass'], capture_output=True).returncode == 0:
                    scp_cmd = ['sshpass', '-p', password] + scp_cmd
                else:
                    print("[WARNING] sshpass не установлен, пароль не может быть передан автоматически")
                    print("[INFO] Используйте SSH ключи или установите sshpass")
            
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode == 0 and os.path.exists(local_path):
                print(f"[OK] Файл скачан из SCP: {local_path}")
                return local_path, True
            else:
                print(f"[ERROR] Ошибка скачивания из SCP: {result.stderr}")
                if os.path.exists(local_path):
                    os.remove(local_path)
                return None, False
                
        except subprocess.TimeoutExpired:
            print("[ERROR] Таймаут при скачивании из SCP")
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
            return None, False
        except Exception as e:
            print(f"[ERROR] Ошибка скачивания из SCP: {e}")
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
            return None, False
    
    def _download_from_gdrive(self, url, local_path, credentials, progress_callback):
        """
        Скачивание файла из Google Drive
        
        Args:
            url: Google Drive URL (gdrive://root_folder_id:subfolder_name:file_name.tar.gz)
                 Или упрощенный формат: gdrive://root_folder_id:file_name.tar.gz (поиск во всех подпапках)
            local_path: Локальный путь для сохранения
            credentials: Учетные данные {'api_key': ...}
            progress_callback: Функция для обновления прогресса
        
        Returns:
            tuple: (путь_к_файлу, успех)
        """
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            # Формат: gdrive://root_folder_id:subfolder_name:file_name
            # Или: gdrive://root_folder_id:file_name (поиск во всех подпапках)
            path_parts = parsed.path.strip('/').split(':')
            
            if len(path_parts) < 2:
                print("[ERROR] Неверный формат Google Drive URL: должен быть gdrive://root_folder_id:subfolder:file_name или gdrive://root_folder_id:file_name")
                return None, False
            
            root_folder_id = path_parts[0]
            
            # Определяем формат: с подпапкой или без
            if len(path_parts) == 3:
                # Формат: root_folder_id:subfolder_name:file_name
                subfolder_name = path_parts[1]
                file_name = path_parts[2]
                search_in_subfolder = True
            else:
                # Формат: root_folder_id:file_name (поиск во всех подпапках)
                file_name = path_parts[1]
                subfolder_name = None
                search_in_subfolder = False
            
            # Определяем локальный путь
            if not local_path:
                temp_dir = tempfile.mkdtemp(prefix='gdrive_download_')
                local_path = os.path.join(temp_dir, file_name)
            else:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            print(f"[INFO] Скачивание из Google Drive: root_folder={root_folder_id}, subfolder={subfolder_name}, file={file_name}")
            
            # Метод 1: Используем Google Drive API для поиска файла
            try:
                import requests
                
                api_key = credentials.get('api_key')
                
                # Шаг 1: Если указана подпапка, сначала находим её ID
                target_folder_id = root_folder_id
                if search_in_subfolder and subfolder_name:
                    print(f"[INFO] Поиск подпапки '{subfolder_name}' в папке {root_folder_id}...")
                    search_url = f"https://www.googleapis.com/drive/v3/files"
                    params = {
                        'q': f"'{root_folder_id}' in parents and name='{subfolder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                        'key': api_key if api_key else None,
                        'fields': 'files(id, name)'
                    }
                    
                    if api_key:
                        response = requests.get(search_url, params=params, timeout=30)
                        if response.status_code == 200:
                            folders = response.json().get('files', [])
                            if folders:
                                target_folder_id = folders[0]['id']
                                print(f"[OK] Подпапка найдена: {subfolder_name} (ID: {target_folder_id})")
                            else:
                                print(f"[ERROR] Подпапка '{subfolder_name}' не найдена в папке {root_folder_id}")
                                return None, False
                        else:
                            print(f"[ERROR] Ошибка поиска подпапки: {response.status_code} - {response.text}")
                            return None, False
                    else:
                        # Без API ключа пробуем альтернативный метод
                        print("[WARNING] API ключ не указан, пробуем альтернативный метод...")
                        # Продолжаем с root_folder_id, но поиск может не сработать
                
                # Шаг 2: Ищем файл в целевой папке
                print(f"[INFO] Поиск файла '{file_name}' в папке {target_folder_id}...")
                search_url = f"https://www.googleapis.com/drive/v3/files"
                params = {
                    'q': f"'{target_folder_id}' in parents and name='{file_name}' and trashed=false",
                    'key': api_key if api_key else None,
                    'fields': 'files(id, name, size)'
                }
                    
                    response = requests.get(search_url, params=params, timeout=30)
                    if response.status_code == 200:
                        files = response.json().get('files', [])
                        if files:
                            file_id = files[0]['id']
                            
                            # Скачиваем файл
                            download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={api_key}"
                            response = requests.get(download_url, stream=True, timeout=3600)
                            
                            if response.status_code == 200:
                                total_size = int(response.headers.get('content-length', 0))
                                downloaded = 0
                                
                                with open(local_path, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                            downloaded += len(chunk)
                                            if progress_callback:
                                                progress_callback(downloaded, total_size)
                                
                                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                                    print(f"[OK] Файл скачан из Google Drive: {local_path}")
                                    return local_path, True
                    
                    print("[ERROR] Не удалось найти или скачать файл через Google Drive API")
                    return None, False
                else:
                    # Без API ключа пробуем через gdown (для публичных файлов)
                    # Но gdown требует прямую ссылку на файл, а не папку
                    print("[WARNING] API ключ не указан, пробуем альтернативный метод...")
                    return None, False
                    
            except ImportError:
                print("[WARNING] Библиотека gdown не установлена")
                print("[INFO] Для работы с Google Drive установите: pip install gdown")
                return None, False
            except Exception as e:
                print(f"[ERROR] Ошибка скачивания из Google Drive: {e}")
                if local_path and os.path.exists(local_path):
                    os.remove(local_path)
                return None, False
                
        except Exception as e:
            print(f"[ERROR] Критическая ошибка работы с Google Drive: {e}")
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
            return None, False
```

---

### Изменение 3: Модификация _find_archive() в ComponentHandler

**Расположение:** FSA-AstraInstall.py, класс ComponentHandler, метод `_find_archive()` (строки 4207-4302)

**Модифицировать метод `_find_archive()`:**

```python
def _find_archive(self, astrapack_dir, archive_name=None, search_dir=None, component_id=None):
    """
    Универсальный поиск архива в указанной папке
    
    Поддерживает:
    - Поиск в локальной папке (как раньше)
    - Поиск в удаленных источниках (НОВОЕ)
    
    Args:
        astrapack_dir: Путь к директории AstraPack
        archive_name: Имя архива (если указано, используется оно, иначе поиск по расширению)
        search_dir: Имя папки для поиска (например, 'Winetricks', 'AstraPack', 'CountPack')
        component_id: ID компонента (для получения конфигурации и remote_source)
    
    Returns:
        str или None: Путь к найденному архиву или None
    """
    print(f"[INSTALL LOG] ========== ПОИСК АРХИВА ==========", level='INFO')
    print(f"[INSTALL LOG] Компонент: {component_id}", level='INFO')
    
    # Сначала ищем в локальной папке (существующая логика)
    local_archive = self._find_local_archive(astrapack_dir, archive_name, search_dir, component_id)
    if local_archive:
        return local_archive
    
    # Если локальный архив не найден, проверяем remote_source
    print(f"[INSTALL LOG] Локальный архив не найден, проверяем remote_source...", level='INFO')
    
    if component_id:
        try:
            component_config = get_component_data(component_id)
            remote_source_config = component_config.get('remote_source')
            
            if remote_source_config:
                print(f"[INSTALL LOG] Найден remote_source в конфигурации", level='INFO')
                
                # Проверяем настройку download_to_local
                download_to_local = remote_source_config.get('download_to_local', False)
                
                if download_to_local:
                    # Скачиваем в локальную папку
                    print(f"[INSTALL LOG] Настройка download_to_local=True, скачиваем в локальную папку", level='INFO')
                    return self._download_remote_archive_to_local(
                        remote_source_config, astrapack_dir, archive_name, search_dir, component_id
                    )
                else:
                    # Используем напрямую (возвращаем специальный маркер)
                    print(f"[INSTALL LOG] Настройка download_to_local=False, используем напрямую", level='INFO')
                    return f"REMOTE:{json.dumps(remote_source_config)}"
            else:
                print(f"[INSTALL LOG] remote_source не указан в конфигурации", level='INFO')
        except Exception as e:
            print(f"[INSTALL LOG] Ошибка проверки remote_source: {e}", level='ERROR')
    
    return None

def _find_local_archive(self, astrapack_dir, archive_name=None, search_dir=None, component_id=None):
    """
    Поиск архива в локальной папке (существующая логика из _find_archive)
    """
    # ... существующий код метода _find_archive() ...
    # (копируем всю логику поиска в локальной папке)
    pass

def _download_remote_archive_to_local(self, remote_source_config, astrapack_dir, archive_name, search_dir, component_id):
    """
    Скачивание удаленного архива в локальную папку
    
    Args:
        remote_source_config: Конфигурация удаленного источника
        astrapack_dir: Путь к директории AstraPack
        archive_name: Имя архива
        search_dir: Папка для сохранения
        component_id: ID компонента
    
    Returns:
        str или None: Путь к скачанному архиву или None
    """
    try:
        print(f"[INSTALL LOG] Начинаем скачивание удаленного архива...", level='INFO')
        
        # Определяем путь для сохранения
        if search_dir:
            target_dir = os.path.join(astrapack_dir, search_dir)
        else:
            component_config = get_component_data(component_id)
            source_dir = component_config.get('source_dir')
            if source_dir:
                target_dir = os.path.join(astrapack_dir, source_dir)
            else:
                target_dir = astrapack_dir
        
        os.makedirs(target_dir, exist_ok=True)
        
        # Определяем имя файла
        if not archive_name:
            # Пытаемся извлечь из URL
            url = remote_source_config.get('url', '')
            archive_name = os.path.basename(urllib.parse.urlparse(url).path) or 'downloaded_archive.tar.gz'
        
        local_path = os.path.join(target_dir, archive_name)
        
        # Скачиваем файл
        remote_manager = RemoteSourceManager()
        downloaded_path, success = remote_manager.download_file(
            remote_source_config,
            local_path=local_path
        )
        
        if success and downloaded_path:
            print(f"[INSTALL LOG] Архив успешно скачан: {downloaded_path}", level='INFO')
            return downloaded_path
        else:
            print(f"[INSTALL LOG] Не удалось скачать архив", level='ERROR')
            return None
            
    except Exception as e:
        print(f"[INSTALL LOG] Ошибка скачивания удаленного архива: {e}", level='ERROR')
        import traceback
        traceback.print_exc()
        return None
```

**Модифицировать метод `_resolve_archive_path_with_dialog()`:**

Добавить проверку на маркер `REMOTE:` и показывать диалог выбора стратегии.

---

## 📚 Примеры использования

### Пример 1: Конфигурация с Google Drive

```python
{
    'component_id': 'wine_9',
    'archive_name': 'wine_packages.tar.gz',
    'source_dir': 'Wine',
    'remote_source': {
        'url': 'gdrive://1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW:Wine:wine_packages.tar.gz',
        'download_to_local': True,
        'checksum': {
            'type': 'sha256',
            'value': 'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456'
        },
        'retry': {
            'max_attempts': 3,
            'delay_seconds': 5
        }
    }
}
```

**Формат URL:** `gdrive://ROOT_FOLDER_ID:SUBFOLDER_NAME:FILE_NAME`
- `ROOT_FOLDER_ID` - ID корневой папки (1lSi8ih1snPY700TzfZpwWbl1IKQu-DBW)
- `SUBFOLDER_NAME` - Имя подпапки (Wine, Astra, Count, Winetricks)
- `FILE_NAME` - Имя файла (wine_packages.tar.gz)

### Пример 2: Конфигурация с SMB

```python
{
    'component_id': 'astra_ide',
    'archive_name': 'astra_packages.tar.gz',
    'source_dir': 'Astra',
    'remote_source': {
        'url': 'smb://10.10.55.77/Install/AstraPack/Astra/astra_packages.tar.gz',
        'download_to_local': False,  # Использовать напрямую
        'auth': {
            'type': 'smb',
            'username': 'user',  # Или None для использования сохраненных
            'domain': 'WORKGROUP'
        },
        'checksum': {
            'type': 'sha256',
            'value': '...'
        }
    }
}
```

---

## 🧪 Тестирование

### Тест 1: Скачивание из Google Drive

**Цель:** Проверить скачивание архива из Google Drive в локальную папку

**Шаги:**
1. Настроить компонент с `remote_source` на Google Drive
2. Установить `download_to_local: True`
3. Запустить установку компонента

**Ожидаемый результат:**
- Архив скачан в `AstraPack/Wine/wine_packages.tar.gz`
- Проверка целостности пройдена
- Установка выполнена из локального архива

---

### Тест 2: Использование напрямую из SMB

**Цель:** Проверить установку напрямую из SMB без скачивания

**Шаги:**
1. Настроить компонент с `remote_source` на SMB
2. Установить `download_to_local: False`
3. Ввести учетные данные при запросе
4. Запустить установку компонента

**Ожидаемый результат:**
- Учетные данные сохранены в `~/.fsa-credentials.json`
- Установка выполнена напрямую из SMB
- Локальный архив не создан

---

### Тест 3: Повторные попытки при ошибке

**Цель:** Проверить повторные попытки скачивания

**Шаги:**
1. Настроить компонент с неверным URL
2. Запустить установку

**Ожидаемый результат:**
- Выполнено 3 попытки скачивания
- После каждой неудачи - пауза 5 секунд
- Частично скачанные файлы удалены
- После 3 неудач - ошибка установки

---

### Тест 4: Проверка целостности

**Цель:** Проверить валидацию SHA256/MD5

**Шаги:**
1. Настроить компонент с неверным checksum
2. Запустить установку

**Ожидаемый результат:**
- Файл скачан
- Проверка целостности не пройдена
- Файл удален
- Выполнена повторная попытка

---

## ⚠️ Риски и митигация

### Риск 1: Утечка учетных данных

**Описание:** Пароли могут быть скомпрометированы

**Вероятность:** Средняя  
**Влияние:** Критическое

**Митигация:**
- Шифрование паролей через Fernet
- Ключ шифрования на основе системной информации
- Права доступа 600 на файл учетных данных
- Пароли никогда не хранятся в конфигурации компонентов

---

### Риск 2: Недоступность удаленного источника

**Описание:** Удаленный сервер недоступен во время установки

**Вероятность:** Средняя  
**Влияние:** Высокое

**Митигация:**
- Повторные попытки (3 раза)
- Fallback на локальный архив если доступен
- Информативные сообщения об ошибках
- Возможность ручного выбора файла

---

### Риск 3: Частично скачанные файлы

**Описание:** Скачивание прервалось, файл поврежден

**Вероятность:** Средняя  
**Влияние:** Высокое

**Митигация:**
- Удаление частично скачанных файлов при ошибке
- Проверка целостности перед использованием
- Повторные попытки с чистого листа

---

## 📊 Оценка трудозатрат

| Этап | Задача | Часы | Приоритет |
|------|--------|------|-----------|
| 1 | Класс CredentialManager | 2-3 | Высокий |
| 2 | Класс RemoteSourceManager | 4-5 | Высокий |
| 3 | Модификация ComponentInstaller | 2-3 | Высокий |
| 4 | Интеграция с GUI | 1-2 | Средний |
| 5 | Тестирование | 2-3 | Высокий |
| 6 | Документирование | 1 | Средний |
| **ИТОГО** | | **12-18** | |

---

## 📝 Чеклист реализации

### Этап 1: CredentialManager
- [ ] Создать класс CredentialManager
- [ ] Реализовать _get_encryption_key()
- [ ] Реализовать _encrypt_password()
- [ ] Реализовать _decrypt_password()
- [ ] Реализовать save_credentials()
- [ ] Реализовать get_credentials()
- [ ] Реализовать delete_credentials()
- [ ] Добавить проверку прав доступа (600)

### Этап 2: RemoteSourceManager
- [ ] Создать класс RemoteSourceManager
- [ ] Реализовать download_file()
- [ ] Реализовать _download_from_smb()
- [ ] Реализовать _download_from_http()
- [ ] Реализовать _download_from_ftp()
- [ ] Реализовать _download_from_ssh()
- [ ] Реализовать _download_from_gdrive()
- [ ] Реализовать _verify_checksum()
- [ ] Реализовать _download_with_retry()
- [ ] Добавить удаление частично скачанных файлов

### Этап 3: Модификация ComponentInstaller
- [ ] Модифицировать _find_archive()
- [ ] Добавить _find_local_archive()
- [ ] Добавить _download_remote_archive_to_local()
- [ ] Модифицировать _resolve_archive_path_with_dialog()
- [ ] Добавить обработку маркера REMOTE:

### Этап 4: GUI интеграция
- [ ] Диалог выбора стратегии
- [ ] Диалог ввода учетных данных
- [ ] Прогресс-бар скачивания
- [ ] Индикация источника

### Этап 5: Тестирование
- [ ] Тест: Google Drive
- [ ] Тест: SMB
- [ ] Тест: HTTP/HTTPS
- [ ] Тест: Проверка целостности
- [ ] Тест: Повторные попытки
- [ ] Тест: Сохранение учетных данных

---

## 🎯 Критерии готовности

1. ✅ CredentialManager реализован и протестирован
2. ✅ RemoteSourceManager поддерживает все протоколы
3. ✅ ComponentInstaller интегрирован с удаленными источниками
4. ✅ Проверка целостности работает
5. ✅ Повторные попытки работают
6. ✅ Частично скачанные файлы удаляются
7. ✅ Учетные данные хранятся безопасно
8. ✅ Все тесты пройдены
9. ✅ Документация обновлена

---

**Дата создания документа:** 2025.12.30  
**Автор:** AI Assistant (@LLM)  
**Статус:** Готов к реализации


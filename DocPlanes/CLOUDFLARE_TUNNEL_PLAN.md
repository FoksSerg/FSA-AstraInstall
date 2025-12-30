# План реализации безопасного доступа к архивам через Cloudflare Tunnel

**Версия документа:** 1.0.0  
**Дата создания:** 2025.12.30  
**Проект:** FSA-AstraInstall  
**Компания:** ООО "НПА Вира-Реалтайм"  
**Текущая версия проекта:** V3.7.210 (2025.12.31)  
**Статус:** 📝 ПЛАН ГОТОВ К РЕАЛИЗАЦИИ

---

## 📋 Оглавление

1. [Цель реализации](#цель-реализации)
2. [Текущее состояние](#текущее-состояние)
3. [Проблема](#проблема)
4. [Архитектура решения](#архитектура-решения)
5. [Безопасность решения](#безопасность-решения)
6. [Схема работы](#схема-работы)
7. [Пошаговый план реализации](#пошаговый-план-реализации)
8. [Настройка сервера](#настройка-сервера)
9. [Интеграция в проект](#интеграция-в-проект)
10. [Конфигурация компонентов](#конфигурация-компонентов)
11. [Тестирование](#тестирование)
12. [Риски и митигация](#риски-и-митигация)

---

## 🎯 Цель реализации

Создать безопасную систему доступа к архивам компонентов через Cloudflare Tunnel, которая:

- ✅ **Не требует установки ПО на клиенте** - работает через стандартный HTTPS
- ✅ **Обеспечивает шифрование** - TLS 1.3 через Cloudflare
- ✅ **Изолирует доступ** - только к указанному сервису, остальная локальная сеть недоступна
- ✅ **Аутентификация** - через Cloudflare Access (email/2FA/токены)
- ✅ **Защита от атак** - DDoS защита, rate limiting, логирование
- ✅ **Скрывает реальный IP** - сервер недоступен напрямую из интернета
- ✅ **Работает из любой точки мира** - без необходимости белого IP

---

## 📊 Текущее состояние

### Существующая функциональность скачивания:

| Компонент | Описание | Файл | Строки |
|-----------|----------|------|--------|
| `_download_from_remote_source()` | Универсальный метод скачивания | FSA-AstraInstall.py | 5081-5215 |
| `_download_from_gdrive()` | Скачивание из Google Drive | FSA-AstraInstall.py | 5433-5984 |
| `_download_from_http()` | Скачивание через HTTP/HTTPS | FSA-AstraInstall.py | 6041-6300 |
| `_download_from_smb()` | Скачивание из SMB | FSA-AstraInstall.py | 6036-6040 |
| `_verify_archive_checksum()` | Проверка целостности (SHA256) | FSA-AstraInstall.py | 5986-6020 |

### Поддерживаемые источники:

- ✅ Google Drive (с ограничениями квоты)
- ✅ SMB (для внутренних сетей)
- ✅ HTTP/HTTPS (базовая поддержка)
- ✅ FTP
- ✅ SSH/SCP

### Проблемы текущей реализации:

1. **Google Drive** - ограничения квоты, проблемы с подтверждением форм
2. **HTTP/HTTPS** - нет поддержки аутентификации, нет проверки SSL сертификатов
3. **SMB** - требует доступа к внутренней сети
4. **Нет централизованного безопасного источника** для публичного доступа

---

## ⚠️ Проблема

### Текущие ограничения:

1. **Google Drive:**
   - Ограничение квоты ("Too many users")
   - Проблемы с обработкой форм подтверждения
   - Нестабильная работа для больших файлов

2. **Публичный доступ:**
   - Нет безопасного способа предоставить публичный доступ к архивам
   - Требуется белый IP для прямого доступа
   - Нет защиты от DDoS и атак

3. **Безопасность:**
   - Нет изоляции доступа к локальной сети
   - Нет аутентификации для публичного доступа
   - Нет шифрования для некоторых протоколов

4. **Удобство:**
   - Клиенты должны иметь доступ к внутренней сети (SMB)
   - Или использовать нестабильный Google Drive

---

## 🏗️ Архитектура решения

### Общая схема:

```
┌─────────────────────────────────────────────────────────────┐
│                    КЛИЕНТ (любое место)                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         FSA-AstraInstall (бинарник)                  │  │
│  │                                                        │  │
│  │  1. Проверяет наличие архивов                        │  │
│  │  2. Если нет - делает HTTPS запрос                    │  │
│  │  3. Скачивает архивы через Cloudflare Tunnel         │  │
│  │  4. Сохраняет рядом с бинарником                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓ HTTPS (TLS 1.3)                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE (облако)                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Cloudflare Tunnel                       │  │
│  │  - Проверка аутентификации (Access)                 │  │
│  │  - DDoS защита                                       │  │
│  │  - Rate limiting                                     │  │
│  │  - Логирование                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓ Зашифрованный туннель           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              ВАШ СЕРВЕР (локальная сеть)                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         cloudflared (туннель)                         │  │
│  │  - Подключение к Cloudflare                          │  │
│  │  - Проксирование только порта 8080                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         HTTP сервер (порт 8080)                      │  │
│  │  - Только папка с архивами                           │  │
│  │  - /var/www/astra-files/                             │  │
│  │    ├── Cont/                                         │  │
│  │    ├── Wine/                                         │  │
│  │    ├── Winetricks/                                   │  │
│  │    └── Astra/                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ⚠️ Остальная локальная сеть НЕДОСТУПНА                     │
└─────────────────────────────────────────────────────────────┘
```

### Компоненты системы:

1. **HTTP сервер на вашем сервере**
   - Простой Python HTTP сервер или Nginx
   - Обслуживает только папку с архивами
   - Работает на localhost:8080

2. **Cloudflare Tunnel (cloudflared)**
   - Устанавливается только на сервере
   - Создает зашифрованный туннель к Cloudflare
   - Проксирует только указанный сервис (порт 8080)

3. **Cloudflare Access**
   - Аутентификация пользователей
   - Email/2FA/токены
   - IP whitelist (опционально)

4. **Бинарник FSA-AstraInstall**
   - Делает обычные HTTPS запросы
   - Не требует установки дополнительного ПО
   - Проверяет SSL сертификаты
   - Проверяет SHA256 целостность

---

## 🔒 Безопасность решения

### Уровни защиты:

#### 1. Шифрование соединения
- ✅ **TLS 1.3** - современное шифрование
- ✅ **Сертификат от Cloudflare** - автоматически обновляется
- ✅ **Проверка сертификата в коде** - защита от MITM атак

#### 2. Аутентификация
- ✅ **Cloudflare Access** - проверка доступа перед подключением
- ✅ **Email аутентификация** - только авторизованные пользователи
- ✅ **Двухфакторная аутентификация** - дополнительная защита
- ✅ **Токены доступа** - для программного доступа

#### 3. Изоляция доступа
- ✅ **Только указанный сервис** - доступ только к порту 8080
- ✅ **Остальная локальная сеть недоступна** - полная изоляция
- ✅ **Реальный IP скрыт** - сервер недоступен напрямую

#### 4. Защита от атак
- ✅ **DDoS защита** - автоматическая защита Cloudflare
- ✅ **Rate limiting** - ограничение запросов
- ✅ **Логирование** - все запросы логируются
- ✅ **WAF (Web Application Firewall)** - защита от веб-атак

#### 5. Целостность данных
- ✅ **SHA256 проверка** - проверка целостности файлов
- ✅ **HTTPS** - защита от модификации в пути

---

## 🔄 Схема работы

### Сценарий 1: Первый запуск клиента

```
1. Клиент получает бинарник FSA-AstraInstall-1-8
   Размер: ~50-100 МБ
   Архивов нет

2. Клиент запускает бинарник
   ./FSA-AstraInstall-1-8

3. Бинарник проверяет наличие архивов
   Проверяет папку AstraPack/
   Если нет - начинает скачивание

4. Бинарник читает конфигурацию компонентов
   Находит remote_source с типом 'https'
   URL: https://files.yourdomain.com/Cont/CountPack.tar.gz

5. Бинарник делает HTTPS запрос
   requests.get(url, verify=True)  # Проверка SSL
   
6. Cloudflare проверяет доступ
   Cloudflare Access проверяет аутентификацию
   Если авторизован - пропускает запрос

7. Cloudflare Tunnel проксирует запрос
   Зашифрованный туннель к вашему серверу
   Только порт 8080, остальное недоступно

8. HTTP сервер отдает файл
   /var/www/astra-files/Cont/CountPack.tar.gz
   Только эта папка доступна

9. Бинарник получает файл
   Проверяет SHA256
   Сохраняет в AstraPack/Cont/CountPack.tar.gz

10. Установка продолжается
    Архивы на месте, можно устанавливать компоненты
```

### Сценарий 2: Повторный запуск

```
1. Клиент запускает бинарник
   ./FSA-AstraInstall-1-8

2. Бинарник проверяет наличие архивов
   Находит AstraPack/Cont/CountPack.tar.gz
   Проверяет SHA256

3. Если архив корректен - использует локальный
   Не делает запрос к серверу
   Быстрая установка

4. Если архив поврежден или отсутствует
   Скачивает заново через Cloudflare Tunnel
```

---

## 📝 Пошаговый план реализации

### Этап 1: Настройка сервера (2-3 часа)

#### Шаг 1.1: Подготовка структуры папок
```bash
# Создаем папку для архивов
sudo mkdir -p /var/www/astra-files
sudo chown $USER:$USER /var/www/astra-files

# Создаем структуру папок
mkdir -p /var/www/astra-files/{Cont,Wine,Winetricks,Astra}

# Копируем архивы
cp AstraPack/Cont/CountPack.tar.gz /var/www/astra-files/Cont/
cp AstraPack/Wine/wine_packages.tar.gz /var/www/astra-files/Wine/
cp AstraPack/Winetricks/winetricks_packages.tar.gz /var/www/astra-files/Winetricks/
cp AstraPack/Astra/AstraPack.tar.gz /var/www/astra-files/Astra/
```

#### Шаг 1.2: Настройка HTTP сервера
```bash
# Вариант A: Простой Python HTTP сервер
cd /var/www/astra-files
python3 -m http.server 8080

# Вариант B: Nginx (рекомендуется для продакшена)
# Создаем конфигурацию nginx
sudo nano /etc/nginx/sites-available/astra-files
```

Конфигурация Nginx:
```nginx
server {
    listen 8080;
    server_name localhost;
    
    root /var/www/astra-files;
    index index.html;
    
    # Только GET запросы
    limit_except GET {
        deny all;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=download:10m rate=10r/m;
    limit_req zone=download burst=5;
    
    # Логирование
    access_log /var/log/nginx/astra-files-access.log;
    error_log /var/log/nginx/astra-files-error.log;
    
    location / {
        autoindex off;
        try_files $uri =404;
    }
}
```

#### Шаг 1.3: Установка Cloudflare Tunnel
```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
```

#### Шаг 1.4: Создание туннеля
```bash
# Авторизация в Cloudflare
cloudflared tunnel login

# Создание туннеля
cloudflared tunnel create astra-files

# Получаем UUID туннеля (сохранить!)
# Например: 12345678-1234-1234-1234-123456789abc
```

#### Шаг 1.5: Настройка конфигурации туннеля
```bash
# Создаем директорию для конфигурации
mkdir -p ~/.cloudflared

# Создаем config.yml
nano ~/.cloudflared/config.yml
```

Содержимое `config.yml`:
```yaml
tunnel: astra-files
credentials-file: /Users/username/.cloudflared/12345678-1234-1234-1234-123456789abc.json

ingress:
  # Основной сервис - HTTP сервер с архивами
  - hostname: files.yourdomain.com
    service: http://localhost:8080
    originRequest:
      connectTimeout: 30s
      tcpKeepAlive: 30s
      keepAliveConnections: 100
      keepAliveTimeout: 90s
      httpHostHeader: localhost:8080
      # Важно: изоляция - только этот сервис
      noHappyEyeballs: true
  
  # Блокируем все остальное
  - service: http_status:404
```

#### Шаг 1.6: Настройка DNS
```bash
# Создаем DNS запись через Cloudflare
cloudflared tunnel route dns astra-files files.yourdomain.com

# Или вручную в панели Cloudflare:
# Тип: CNAME
# Имя: files
# Целевой: 12345678-1234-1234-1234-123456789abc.cfargotunnel.com
```

#### Шаг 1.7: Настройка Cloudflare Access (опционально, но рекомендуется)

1. В панели Cloudflare: Zero Trust → Access → Applications
2. Создать новое приложение:
   - Application name: `Astra Files`
   - Application domain: `files.yourdomain.com`
   - Session duration: `24 hours`
3. Настроить политику доступа:
   - Policy name: `Authorized Users`
   - Action: `Allow`
   - Include: `Emails` (указать разрешенные email)
   - Require: `Two-factor authentication` (опционально)
4. Сохранить

#### Шаг 1.8: Запуск туннеля
```bash
# Тестовый запуск
cloudflared tunnel --config ~/.cloudflared/config.yml run astra-files

# Запуск как сервис (Linux)
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Запуск как сервис (macOS)
# Создать LaunchAgent (см. документацию Cloudflare)
```

### Этап 2: Интеграция в проект (3-4 часа)

#### Шаг 2.1: Улучшение HTTP/HTTPS скачивания

**Файл:** `FSA-AstraInstall.py`  
**Функция:** `_download_from_http()`

**Изменения:**
1. Добавить проверку SSL сертификатов
2. Добавить поддержку заголовков аутентификации
3. Улучшить обработку ошибок
4. Добавить retry логику

**Код:**
```python
def _download_from_http(self, remote_source_config, local_path=None, cred_manager=None, component_id=None):
    """
    Скачивание через HTTP/HTTPS с улучшенной безопасностью
    
    Поддерживает:
    - Проверку SSL сертификатов
    - Аутентификацию через заголовки
    - Retry логику
    - Проверку целостности
    """
    try:
        import requests
        if not REQUESTS_AVAILABLE:
            print("[ERROR] Библиотека requests не установлена", level='ERROR')
            return None, False
        
        # Получаем URL
        url = remote_source_config.get('url')
        if not url:
            print("[ERROR] URL не указан для HTTP источника", level='ERROR')
            return None, False
        
        # Проверяем, что это HTTPS (для безопасности)
        if not url.startswith('https://'):
            print("[WARNING] Используется HTTP без шифрования. Рекомендуется HTTPS", level='WARNING')
        
        # Получаем заголовки аутентификации (если есть)
        headers = {}
        if 'headers' in remote_source_config:
            headers.update(remote_source_config['headers'])
        
        # Получаем учетные данные (если есть)
        if cred_manager:
            credentials = cred_manager.get_credentials_for_source(url)
            if credentials:
                # Поддержка Bearer токенов
                if 'token' in credentials:
                    headers['Authorization'] = f"Bearer {credentials['token']}"
                # Поддержка Basic Auth
                elif 'username' in credentials and 'password' in credentials:
                    from requests.auth import HTTPBasicAuth
                    auth = HTTPBasicAuth(credentials['username'], credentials['password'])
                else:
                    auth = None
            else:
                auth = None
        else:
            auth = None
        
        # Настройки retry
        max_attempts = remote_source_config.get('retry', {}).get('max_attempts', 3)
        delay_seconds = remote_source_config.get('retry', {}).get('delay_seconds', 5)
        
        # Определяем путь для сохранения
        if local_path:
            final_path = local_path
        else:
            temp_dir = tempfile.mkdtemp(prefix='http_download_')
            file_name = os.path.basename(url) or 'download.tar.gz'
            final_path = os.path.join(temp_dir, file_name)
        
        # Создаем директорию для сохранения
        if local_path:
            archive_dir = os.path.dirname(final_path)
            if archive_dir:
                os.makedirs(archive_dir, exist_ok=True)
                fix_permissions(archive_dir)
        
        # Скачивание с retry
        session = requests.Session()
        session.headers.update(headers)
        
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"[INFO] Попытка скачивания {attempt}/{max_attempts} из {url}", level='INFO')
                
                # Проверяем флаг отмены
                global CANCEL_OPERATION
                if CANCEL_OPERATION:
                    print("Скачивание прервано пользователем", gui_log=True)
                    return None, False
                
                # Скачиваем файл
                response = session.get(
                    url,
                    stream=True,
                    timeout=30,
                    verify=True,  # ВАЖНО: проверка SSL сертификата
                    auth=auth
                )
                
                # Проверяем статус
                if response.status_code == 200:
                    # Проверяем content-type
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' in content_type:
                        print("[ERROR] Получен HTML вместо файла. Возможно, требуется аутентификация", level='ERROR')
                        if attempt < max_attempts:
                            time.sleep(delay_seconds)
                            continue
                        return None, False
                    
                    # Скачиваем файл
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    print(f"Начало скачивания файла...", gui_log=True)
                    if total_size > 0:
                        print(f"Размер файла: {total_size / 1024 / 1024:.2f} МБ", gui_log=True)
                    
                    with open(final_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if CANCEL_OPERATION:
                                print("Скачивание прервано пользователем", gui_log=True)
                                if os.path.exists(final_path):
                                    os.remove(final_path)
                                return None, False
                            
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Показываем прогресс каждые 10 МБ
                                if total_size > 0 and downloaded % (10 * 1024 * 1024) < 8192:
                                    progress = (downloaded / total_size) * 100
                                    print(f"Прогресс: {progress:.1f}% ({downloaded / 1024 / 1024:.1f} МБ / {total_size / 1024 / 1024:.1f} МБ)", gui_log=True)
                    
                    if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
                        file_size = os.path.getsize(final_path)
                        print(f"[OK] Файл скачан: {final_path} ({file_size / 1024 / 1024:.2f} МБ)", level='INFO')
                        return final_path, True
                    else:
                        print(f"[ERROR] Файл не был скачан или имеет нулевой размер", level='ERROR')
                        return None, False
                        
                elif response.status_code == 401:
                    print("[ERROR] Требуется аутентификация. Проверьте учетные данные", level='ERROR')
                    return None, False
                elif response.status_code == 403:
                    print("[ERROR] Доступ запрещен. Проверьте права доступа", level='ERROR')
                    return None, False
                elif response.status_code == 404:
                    print("[ERROR] Файл не найден по указанному URL", level='ERROR')
                    return None, False
                else:
                    print(f"[ERROR] Ошибка HTTP: {response.status_code}", level='ERROR')
                    if attempt < max_attempts:
                        time.sleep(delay_seconds)
                        continue
                    return None, False
                    
            except requests.exceptions.SSLError as e:
                print(f"[ERROR] Ошибка SSL сертификата: {e}", level='ERROR')
                print("[ERROR] Возможно, сертификат недействителен или истек срок действия", level='ERROR')
                return None, False
            except requests.exceptions.Timeout:
                print(f"[ERROR] Таймаут при скачивании", level='ERROR')
                if attempt < max_attempts:
                    time.sleep(delay_seconds)
                    continue
                return None, False
            except Exception as e:
                print(f"[ERROR] Ошибка при скачивании: {e}", level='ERROR')
                if attempt < max_attempts:
                    time.sleep(delay_seconds)
                    continue
                return None, False
        
        return None, False
        
    except Exception as e:
        print(f"[ERROR] Критическая ошибка при скачивании через HTTP: {e}", level='ERROR')
        traceback.print_exc()
        return None, False
```

#### Шаг 2.2: Обновление конфигурации компонентов

**Файл:** `FSA-AstraInstall.py`  
**Секция:** `COMPONENTS_CONFIG`

**Изменения:**
Заменить `remote_source` с `type: 'gdrive'` на `type: 'https'` с URL через Cloudflare Tunnel.

**Пример для компонента `cont_designer`:**
```python
'cont_designer': {
    # ... остальная конфигурация ...
    'remote_source': {
        'type': 'https',  # Изменено с 'gdrive' на 'https'
        'url': 'https://files.yourdomain.com/Cont/CountPack.tar.gz',
        'sha256': 'a247cba034871ad74eddafe3327867230d7a1a2a50170c1fa91f09d999441c56',
        'retry': {
            'max_attempts': 3,
            'delay_seconds': 5
        }
        # Опционально: заголовки аутентификации
        # 'headers': {
        #     'Authorization': 'Bearer YOUR_TOKEN'
        # }
    }
}
```

**Примеры для всех компонентов:**
```python
# cont_designer
'remote_source': {
    'type': 'https',
    'url': 'https://files.yourdomain.com/Cont/CountPack.tar.gz',
    'sha256': 'a247cba034871ad74eddafe3327867230d7a1a2a50170c1fa91f09d999441c56'
}

# astra_wine_9 и astra_wine_astraregul
'remote_source': {
    'type': 'https',
    'url': 'https://files.yourdomain.com/Wine/wine_packages.tar.gz',
    'sha256': '05dddf8c1618835469cef9cebaf87a636e9e8c470332658149ea1dc396da4870'
}

# astra_wineprefix
'remote_source': {
    'type': 'https',
    'url': 'https://files.yourdomain.com/Winetricks/winetricks_packages.tar.gz',
    'sha256': 'b29d28be92701d10f7425854d94e6629e3d600deee808cf8c3f24af65a398a4e'
}

# astra_ide
'remote_source': {
    'type': 'https',
    'url': 'https://files.yourdomain.com/Astra/AstraPack.tar.gz',
    'sha256': '763be94c419533342e87f61944bda7e2f61556a052f52cc340d90b28de1373bd'
}
```

### Этап 3: Тестирование (1-2 часа)

#### Шаг 3.1: Локальное тестирование сервера
```bash
# Проверяем HTTP сервер
curl http://localhost:8080/Cont/CountPack.tar.gz

# Проверяем доступность через туннель
curl https://files.yourdomain.com/Cont/CountPack.tar.gz
```

#### Шаг 3.2: Тестирование скачивания
```python
# Создать тестовый скрипт
test_cloudflare_download.py
```

#### Шаг 3.3: Проверка безопасности
- Проверка SSL сертификата
- Проверка изоляции (попытка доступа к другим ресурсам)
- Проверка аутентификации (если настроена)

### Этап 4: Документация и развертывание (1 час)

#### Шаг 4.1: Документация для администратора
- Инструкция по настройке сервера
- Инструкция по обновлению архивов
- Инструкция по мониторингу

#### Шаг 4.2: Автоматизация обновления архивов
```bash
# Скрипт для синхронизации архивов
sync_archives.sh
```

---

## 🔧 Настройка сервера

### Полная инструкция по настройке

#### 1. Подготовка окружения

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y  # Linux
# или
brew update && brew upgrade  # macOS

# Устанавливаем необходимые пакеты
sudo apt install python3 python3-pip nginx  # Linux
# или
brew install python3 nginx  # macOS
```

#### 2. Создание структуры папок

```bash
# Создаем директорию для архивов
sudo mkdir -p /var/www/astra-files
sudo chown -R $USER:$USER /var/www/astra-files

# Создаем структуру
cd /var/www/astra-files
mkdir -p Cont Wine Winetricks Astra

# Копируем архивы из проекта
cp /path/to/FSA-AstraInstall/AstraPack/Cont/CountPack.tar.gz Cont/
cp /path/to/FSA-AstraInstall/AstraPack/Wine/wine_packages.tar.gz Wine/
cp /path/to/FSA-AstraInstall/AstraPack/Winetricks/winetricks_packages.tar.gz Winetricks/
cp /path/to/FSA-AstraInstall/AstraPack/Astra/AstraPack.tar.gz Astra/

# Устанавливаем права
chmod -R 755 /var/www/astra-files
```

#### 3. Настройка HTTP сервера (вариант A: Python)

```bash
# Создаем systemd service
sudo nano /etc/systemd/system/astra-files.service
```

Содержимое:
```ini
[Unit]
Description=Astra Files HTTP Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/var/www/astra-files
ExecStart=/usr/bin/python3 -m http.server 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Запускаем сервис
sudo systemctl daemon-reload
sudo systemctl enable astra-files
sudo systemctl start astra-files
sudo systemctl status astra-files
```

#### 4. Настройка HTTP сервера (вариант B: Nginx)

```bash
# Создаем конфигурацию
sudo nano /etc/nginx/sites-available/astra-files
```

Содержимое (см. выше в разделе "Настройка HTTP сервера")

```bash
# Активируем конфигурацию
sudo ln -s /etc/nginx/sites-available/astra-files /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 5. Установка и настройка Cloudflare Tunnel

```bash
# Установка (см. выше)
# Авторизация
cloudflared tunnel login

# Создание туннеля
cloudflared tunnel create astra-files

# Настройка конфигурации (см. выше)
# Настройка DNS (см. выше)
```

#### 6. Настройка Cloudflare Access

1. Войти в панель Cloudflare
2. Zero Trust → Access → Applications
3. Создать приложение (см. выше)
4. Настроить политики доступа

#### 7. Запуск туннеля как сервиса

**Linux:**
```bash
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

**macOS:**
```bash
# Создать LaunchAgent
mkdir -p ~/Library/LaunchAgents
nano ~/Library/LaunchAgents/com.cloudflare.cloudflared.plist
```

Содержимое:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cloudflare.cloudflared</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/cloudflared</string>
        <string>tunnel</string>
        <string>--config</string>
        <string>/Users/username/.cloudflared/config.yml</string>
        <string>run</string>
        <string>astra-files</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

```bash
# Загружаем сервис
launchctl load ~/Library/LaunchAgents/com.cloudflare.cloudflared.plist
launchctl start com.cloudflare.cloudflared
```

---

## 💻 Интеграция в проект

### Изменения в коде

#### 1. Улучшение функции `_download_from_http()`

**Файл:** `FSA-AstraInstall.py`  
**Строки:** 6041-6300

**Основные улучшения:**
- Проверка SSL сертификатов (`verify=True`)
- Поддержка заголовков аутентификации
- Улучшенная обработка ошибок
- Retry логика
- Проверка content-type

#### 2. Обновление конфигурации компонентов

**Файл:** `FSA-AstraInstall.py`  
**Строки:** 315-481

**Изменения:**
- Заменить `type: 'gdrive'` на `type: 'https'`
- Обновить URL на Cloudflare Tunnel URL
- Сохранить SHA256 для проверки целостности

#### 3. Добавление поддержки токенов (опционально)

**Файл:** `FSA-AstraInstall.py`  
**Функция:** `_download_from_http()`

Если используется токен-аутентификация:
```python
'remote_source': {
    'type': 'https',
    'url': 'https://files.yourdomain.com/Cont/CountPack.tar.gz',
    'headers': {
        'Authorization': 'Bearer YOUR_SECRET_TOKEN'
    },
    'sha256': '...'
}
```

---

## 📋 Конфигурация компонентов

### Примеры конфигураций

#### Компонент: cont_designer
```python
'cont_designer': {
    'name': 'CONT-Designer 3.0',
    'category': 'wine_application',
    'dependencies': ['cont_wineprefix'],
    'check_paths': ['drive_c/Program Files/CONT-Designer 3.0.0.0/CONT-Designer/Common/CONT-Designer.exe'],
    'install_method': 'wine_application',
    'uninstall_method': 'wine_application',
    'wineprefix_path': '~/.local/share/wineprefixes/cont',
    'source_dir': 'Cont',
    'archive_group': 'Cont',
    'archive_name': 'CountPack.tar.gz',
    'copy_method': 'replace',
    'source_priority': 'archive',
    'gui_selectable': True,
    'description': 'CONT-Designer 3.0',
    'sort_order': 5,
    'remote_source': {
        'type': 'https',  # Изменено с 'gdrive'
        'url': 'https://files.yourdomain.com/Cont/CountPack.tar.gz',
        'download_to_local': True,
        'local_path': 'AstraPack/Cont/CountPack.tar.gz',
        'sha256': 'a247cba034871ad74eddafe3327867230d7a1a2a50170c1fa91f09d999441c56',
        'retry': {
            'max_attempts': 3,
            'delay_seconds': 5
        }
    }
}
```

#### Компонент: astra_wine_9 и astra_wine_astraregul
```python
'remote_source': {
    'type': 'https',
    'url': 'https://files.yourdomain.com/Wine/wine_packages.tar.gz',
    'download_to_local': True,
    'local_path': 'AstraPack/Wine/wine_packages.tar.gz',
    'sha256': '05dddf8c1618835469cef9cebaf87a636e9e8c470332658149ea1dc396da4870',
    'retry': {
        'max_attempts': 3,
        'delay_seconds': 5
    }
}
```

#### Компонент: astra_wineprefix
```python
'remote_source': {
    'type': 'https',
    'url': 'https://files.yourdomain.com/Winetricks/winetricks_packages.tar.gz',
    'download_to_local': True,
    'local_path': 'AstraPack/Winetricks/winetricks_packages.tar.gz',
    'sha256': 'b29d28be92701d10f7425854d94e6629e3d600deee808cf8c3f24af65a398a4e',
    'retry': {
        'max_attempts': 3,
        'delay_seconds': 5
    }
}
```

#### Компонент: astra_ide
```python
'remote_source': {
    'type': 'https',
    'url': 'https://files.yourdomain.com/Astra/AstraPack.tar.gz',
    'download_to_local': True,
    'local_path': 'AstraPack/Astra/AstraPack.tar.gz',
    'sha256': '763be94c419533342e87f61944bda7e2f61556a052f52cc340d90b28de1373bd',
    'retry': {
        'max_attempts': 3,
        'delay_seconds': 5
    }
}
```

---

## 🧪 Тестирование

### Тест 1: Проверка доступности сервера

```bash
# Локальная проверка
curl -I http://localhost:8080/Cont/CountPack.tar.gz

# Проверка через Cloudflare Tunnel
curl -I https://files.yourdomain.com/Cont/CountPack.tar.gz
```

### Тест 2: Проверка скачивания

```python
# test_cloudflare_download.py
import requests
import hashlib

url = 'https://files.yourdomain.com/Cont/CountPack.tar.gz'
expected_sha256 = 'a247cba034871ad74eddafe3327867230d7a1a2a50170c1fa91f09d999441c56'

print(f"Скачивание: {url}")
response = requests.get(url, verify=True, stream=True)

if response.status_code == 200:
    # Проверяем content-type
    content_type = response.headers.get('content-type', '')
    print(f"Content-Type: {content_type}")
    
    if 'text/html' in content_type:
        print("ОШИБКА: Получен HTML вместо файла")
    else:
        # Скачиваем и проверяем SHA256
        sha256_hash = hashlib.sha256()
        for chunk in response.iter_content(chunk_size=8192):
            sha256_hash.update(chunk)
        
        actual_sha256 = sha256_hash.hexdigest()
        if actual_sha256 == expected_sha256:
            print("✓ Файл скачан и проверка SHA256 пройдена")
        else:
            print(f"✗ SHA256 не совпадает: {actual_sha256}")
else:
    print(f"ОШИБКА: HTTP {response.status_code}")
```

### Тест 3: Проверка безопасности

```bash
# Проверка SSL сертификата
openssl s_client -connect files.yourdomain.com:443 -showcerts

# Проверка изоляции (попытка доступа к другим ресурсам)
curl https://files.yourdomain.com/../../etc/passwd
# Должно вернуть 404

# Проверка аутентификации (если настроена)
curl https://files.yourdomain.com/Cont/CountPack.tar.gz
# Должно требовать аутентификацию
```

### Тест 4: Интеграционное тестирование

```python
# Использовать существующий test_gdrive_download.py
# Заменить конфигурацию на HTTPS URL
```

---

## ⚠️ Риски и митигация

### Риск 1: Отказ Cloudflare Tunnel

**Вероятность:** Низкая  
**Влияние:** Высокое  
**Митигация:**
- Настроить мониторинг туннеля
- Автоматический перезапуск при сбое
- Резервный источник (SMB для внутренних сетей)

### Риск 2: Превышение лимитов Cloudflare

**Вероятность:** Средняя  
**Влияние:** Среднее  
**Митигация:**
- Мониторинг использования
- Rate limiting на стороне сервера
- Кэширование на стороне Cloudflare

### Риск 3: Компрометация токенов

**Вероятность:** Низкая  
**Влияние:** Высокое  
**Митигация:**
- Ротация токенов
- Использование Cloudflare Access вместо токенов
- Логирование всех запросов

### Риск 4: DDoS атака

**Вероятность:** Низкая  
**Влияние:** Среднее  
**Митигация:**
- Автоматическая защита Cloudflare
- Rate limiting
- IP whitelist (опционально)

### Риск 5: Изменение структуры URL

**Вероятность:** Низкая  
**Влияние:** Среднее  
**Митигация:**
- Версионирование URL (v1, v2)
- Редиректы при изменении
- Документация изменений

---

## 📊 Оценка времени реализации

| Этап | Время | Описание |
|------|-------|----------|
| Настройка сервера | 2-3 часа | Установка, настройка, тестирование |
| Интеграция в проект | 3-4 часа | Изменения кода, обновление конфигураций |
| Тестирование | 1-2 часа | Локальное и интеграционное тестирование |
| Документация | 1 час | Инструкции, документация |
| **ИТОГО** | **7-10 часов** | Полная реализация |

---

## ✅ Чеклист реализации

### Настройка сервера
- [ ] Установлен HTTP сервер (Python/Nginx)
- [ ] Создана структура папок с архивами
- [ ] Установлен cloudflared
- [ ] Создан туннель
- [ ] Настроена конфигурация туннеля
- [ ] Настроен DNS
- [ ] Настроен Cloudflare Access (опционально)
- [ ] Запущен туннель как сервис
- [ ] Проверена доступность через HTTPS

### Интеграция в проект
- [ ] Улучшена функция `_download_from_http()`
- [ ] Добавлена проверка SSL сертификатов
- [ ] Добавлена поддержка заголовков аутентификации
- [ ] Обновлена конфигурация компонентов
- [ ] Заменены все `gdrive` на `https` с новыми URL
- [ ] Сохранены SHA256 для проверки целостности

### Тестирование
- [ ] Проверена доступность сервера
- [ ] Проверено скачивание всех файлов
- [ ] Проверена целостность (SHA256)
- [ ] Проверена безопасность (SSL, изоляция)
- [ ] Проверена работа с аутентификацией (если настроена)

### Документация
- [ ] Создана инструкция по настройке сервера
- [ ] Создана инструкция по обновлению архивов
- [ ] Создана инструкция по мониторингу
- [ ] Обновлен README проекта

---

## 📝 Примечания

1. **Домен:** Замените `files.yourdomain.com` на ваш реальный домен
2. **Аутентификация:** Cloudflare Access рекомендуется для максимальной безопасности
3. **Резервные источники:** Сохраните поддержку SMB для внутренних сетей
4. **Мониторинг:** Настройте мониторинг доступности туннеля
5. **Обновление архивов:** Создайте скрипт для автоматического обновления архивов на сервере

---

## 🔄 Миграция с Google Drive

### План миграции:

1. **Подготовка:**
   - Настроить Cloudflare Tunnel
   - Загрузить все архивы на сервер
   - Проверить доступность

2. **Обновление конфигурации:**
   - Заменить `type: 'gdrive'` на `type: 'https'`
   - Обновить URL на Cloudflare Tunnel URL
   - Сохранить SHA256

3. **Тестирование:**
   - Протестировать скачивание всех файлов
   - Проверить целостность
   - Проверить установку компонентов

4. **Развертывание:**
   - Обновить бинарники
   - Обновить документацию
   - Уведомить пользователей

---

**Дата создания:** 2025.12.30  
**Версия документа:** 1.0.0  
**Статус:** 📝 ПЛАН ГОТОВ К РЕАЛИЗАЦИИ


#!/usr/bin/env bash

if (( EUID == 0 )); then
    echo "Пожалуйста, не запускайте скрипт от рута"
    exit 1
fi

if [ "$(cat /proc/sys/kernel/yama/ptrace_scope)" = 3 ]; then
    echo "У вас в системе включена блокировка ptrace"
    echo "Для корректной работы Wine необходимо ее отключить"
    echo "Пожалуйста, отключите ее и запустите скрипт снова"
    exit 1
fi

if [ ! -f /opt/wine-astraregul/bin/wine ]; then
    echo "У вас не установлен wine-astraregul"
    echo "Установите пакет wine-astraregul_10.0-rc6-1_amd64.deb и запуcтите скрипт снова"
    exit 1
fi

if [ ! -f /opt/wine-9.0/bin/wine ]; then
    echo "У вас не установлен wine-9.0"
    echo "Установите пакет wine_9.0-1_amd64.deb и запуcтите скрипт снова"
    exit 1
fi

export WINEPREFIX="${HOME}"/.wine-astraregul
export WINEDEBUG="-all"
export WINE=/opt/wine-9.0/bin/wine

cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"

if [ ! -f "${1}" ]; then
    echo "Укажите путь до установочного файла Astra IDE"
    echo
    echo "Например:"
    echo "./install-astraregul.sh \"/home/${USER}/Astra.IDE_64_1.7.2.0.exe\""
    exit 1
fi

mkdir -p "${HOME}"/.cache/wine
mkdir -p "${HOME}"/.cache/winetricks
cp -r wine-gecko/* "${HOME}"/.cache/wine
cp -r winetricks-cache/* "${HOME}"/.cache/winetricks

echo "Установка компонентов через winetricks..."

./winetricks -q -f dotnet48 vcrun2013 vcrun2022 d3dcompiler_43 d3dcompiler_47 dxvk

sleep 5
"${WINE}"server -k

echo "Установка программы..."

cat <<EOF>"${HOME}"/start-astraide.sh
#!/bin/bash

export WINEPREFIX="\${HOME}"/.wine-astraregul
export WINE=/opt/wine-astraregul/bin/wine
export WINEDEBUG="-all"

cd "\${WINEPREFIX}"/drive_c/"Program Files"/AstraRegul/Astra.IDE_64_*/Astra.IDE/Common
"\${WINE}" Astra.IDE.exe
EOF

chmod +x "${HOME}"/start-astraide.sh

if [ ! -d "${HOME}"/Desktop ] && [ ! -L "${HOME}"/Desktop ]; then
    ln -s "${HOME}"/Desktops/Desktop1 "${HOME}"/Desktop
fi

cat <<EOF>"${HOME}"/Desktop/AstraRegul.desktop
[Desktop Entry]
Comment=
Exec="${HOME}/start-astraide.sh"
Icon=
Name=Astra IDE (Wine)
Path=
StartupNotify=true
Terminal=false
Type=Application
EOF

export WINE=/opt/wine-astraregul/bin/wine

"${WINE}" "${1}"

rm -f "${HOME}"/Desktop/"Astra.IDE 1.7.2.0.lnk" \
      "${HOME}"/Desktop/"IDE Selector.lnk" \
      "${HOME}"/Desktop/"IDE Selector.desktop"

while [ ! -f "${HOME}"/Desktop/"Astra.IDE 1.7.2.0.lnk" ]; do
    sleep 1
done

rm -f "${HOME}"/Desktop/"Astra.IDE 1.7.2.0.lnk" \
      "${HOME}"/Desktop/"IDE Selector.lnk" \
      "${HOME}"/Desktop/"IDE Selector.desktop"

echo "Ярлык для запуска добавлен на рабочий стол"
echo "Дождитесь завершения установки программы"

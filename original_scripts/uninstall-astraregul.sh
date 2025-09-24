#!/usr/bin/env bash

if (( EUID == 0 )); then
    echo "Пожалуйста, не запускайте скрипт от рута"
    exit 1
fi

export WINEPREFIX="${HOME}"/.wine-astraregul

rm -rf "${WINEPREFIX}" "${HOME}"/start-astraide.sh "${HOME}"/Desktop/AstraRegul.desktop

echo "Программа была успешно удалена"
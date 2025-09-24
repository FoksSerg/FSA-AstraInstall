#!/usr/bin/env bash

if (( EUID != 0 )); then
    echo "Пожалуйста, запустите скрипт от рута"
    exit 1
fi

cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"

apt -y install ./wine*.deb

echo "Готово"

#!/bin/bash
# new_client.sh — создаёт папку нового клиента из шаблона
#
# Использование:
#   ./scripts/new_client.sh vladimir
#   ./scripts/new_client.sh artur

set -e

if [ -z "$1" ]; then
    echo "❌ Укажи имя клиента: ./scripts/new_client.sh имя"
    exit 1
fi

CLIENT_NAME=$(echo "$1" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLIENT_DIR="$ROOT/clients/$CLIENT_NAME"

if [ -d "$CLIENT_DIR" ]; then
    echo "⚠️  Папка $CLIENT_DIR уже существует"
    exit 1
fi

# Копируем шаблон
cp -r "$ROOT/clients/_template" "$CLIENT_DIR"

# Подставляем имя в meta.md
sed -i "s/{{NAME}}/$1/g" "$CLIENT_DIR/meta.md"
sed -i "s/{{DATE}}/$(date +%Y-%m-%d)/g" "$CLIENT_DIR/meta.md"

echo "✅ Создан клиент: $CLIENT_DIR"
echo ""
echo "Дальше:"
echo "  1. Заполни meta.md (контекст про человека)"
echo "  2. Положи аудио в 01_audio/"
echo "  3. Запусти: python3 scripts/transcribe.py clients/$CLIENT_NAME/01_audio/file.mp3 -o clients/$CLIENT_NAME/02_transcript/"
echo "  4. Открой проект в Claude / Claude Code и попроси разбор"

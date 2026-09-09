#!/usr/bin/env bash
# Setup e execução automática do projeto (Linux).
# Rode com: ./setup_and_run.sh
#
# O que ele faz, na ordem:
#   1. Procura um Python 3.12, 3.11 ou o "python3" padrão do sistema.
#   2. Cria o ambiente virtual "venv" na pasta do projeto, se ainda não existir.
#   3. Instala as dependências do requirements.txt dentro do venv.
#   4. Abre a GUI (gui.py).
#
# Não mexe em nada fora desta pasta: o venv fica inteiramente dentro dela,
# e pode ser apagado a qualquer momento (e recriado rodando este script de novo).

set -e
cd "$(dirname "$0")"

PYBIN=""
for cand in python3.12 python3.11 python3; do
    if command -v "$cand" >/dev/null 2>&1; then
        PYBIN="$cand"
        break
    fi
done

if [ -z "$PYBIN" ]; then
    echo "Python 3 não encontrado. Instale com: sudo apt install python3.12 python3.12-venv python3-tk"
    exit 1
fi

echo "Usando: $PYBIN ($($PYBIN --version))"

if [ ! -d venv ]; then
    echo "Criando ambiente virtual em ./venv ..."
    "$PYBIN" -m venv venv
fi

echo "Instalando/atualizando dependências..."
venv/bin/python -m pip install --upgrade pip >/dev/null
venv/bin/python -m pip install -r requirements.txt

echo "Abrindo a aplicação..."
venv/bin/python gui.py

@echo off
REM Setup e execucao automatica do projeto (Windows).
REM Basta dar 2 cliques neste arquivo (ou rodar "setup_and_run.bat" no terminal).
REM
REM O que ele faz, na ordem:
REM   1. Procura um Python 3.12 ou 3.11 instalado (via "py launcher").
REM   2. Cria o ambiente virtual "venv" na pasta do projeto, se ainda nao existir.
REM   3. Instala as dependencias do requirements.txt dentro do venv.
REM   4. Abre a GUI (gui.py).
REM
REM Nao mexe em nada fora desta pasta: o venv fica inteiramente dentro dela,
REM e pode ser apagado a qualquer momento (e recriado rodando este script de novo).

setlocal
cd /d "%~dp0"

set "PYCMD="

py -3.12 -c "print(1)" >nul 2>nul
if not errorlevel 1 (
    set "PYCMD=py -3.12"
    goto :found
)

py -3.11 -c "print(1)" >nul 2>nul
if not errorlevel 1 (
    set "PYCMD=py -3.11"
    goto :found
)

echo.
echo Nao encontrei Python 3.12 nem 3.11 instalados (via "py launcher").
echo Baixe e instale um deles em: https://www.python.org/downloads/
echo (fio-plot depende de bibliotecas que ainda nao sao 100%% estaveis em Python 3.13+/3.14)
echo.
pause
exit /b 1

:found
echo Usando: %PYCMD%

if not exist venv (
    echo.
    echo Criando ambiente virtual em .\venv ...
    %PYCMD% -m venv venv
)

echo.
echo Instalando/atualizando dependencias...
venv\Scripts\python.exe -m pip install --upgrade pip >nul
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Falha ao instalar as dependencias. Veja a mensagem acima.
    pause
    exit /b 1
)

echo.
echo Abrindo a aplicacao...
venv\Scripts\python.exe gui.py

echo.
echo (a janela foi fechada)
pause

@echo off
setlocal
title Social Wars Server (Firebase)
color 0A

echo ============================================
echo   Social Wars Server - Firebase Edition
echo ============================================
echo.

REM Verifica se o Python esta no PATH
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale Python e adicione-o ao PATH.
    echo Download em: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [1/3] Verificando Python...
python --version
echo.

echo [2/3] Instalando dependencias...
pip install -r requirements.txt
pip install jsonpatch
echo.

REM Verifica se o arquivo de credenciais do Firebase existe
if exist "firebase-credentials.json" (
    echo [OK] firebase-credentials.json encontrado!
    echo [INFO] O servidor vai iniciar com Firebase ATIVO.
    echo [INFO] Login com email/senha + saves na nuvem.
) else (
    echo [AVISO] firebase-credentials.json NAO encontrado!
    echo [INFO] O servidor vai iniciar em MODO LOCAL.
    echo [INFO] Para ativar o Firebase, coloque o arquivo
    echo        firebase-credentials.json nesta pasta.
)
echo.

echo [3/3] Iniciando servidor...
echo.
echo ============================================
echo   Acesse no navegador: http://localhost:5055
echo ============================================
echo.

python server.py

pause
endlocal

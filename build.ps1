# Compila dist\JabsDLP.exe (un solo archivo, sin consola).
# Uso:  powershell -ExecutionPolicy Bypass -File .\build.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$python = '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host 'Creando entorno virtual .venv...'
    if (Get-Command uv -ErrorAction SilentlyContinue) { uv venv .venv --python 3.13 } else { python -m venv .venv }
}
Write-Host 'Instalando dependencias...'
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv pip install --python $python -r requirements-dev.txt
} else {
    & $python -m pip install --upgrade pip
    & $python -m pip install -r requirements-dev.txt
}

Write-Host 'Generando el logo...'
& $python scripts\generar_icono.py

Write-Host 'Ejecutando pruebas...'
& $python -m pytest -q tests -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw 'Las pruebas fallaron; no se compila.' }

Write-Host 'Compilando con PyInstaller...'
& $python -m PyInstaller --noconfirm --clean JabsDLP.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller falló.' }

Write-Host 'Revisando privacidad del código y del .exe...'
& $python scripts\revisar_privacidad.py
if ($LASTEXITCODE -ne 0) { throw 'La revisión de privacidad encontró datos personales.' }

$exe = Get-Item dist\JabsDLP.exe
Write-Host ("Listo: {0} ({1:N1} MB)" -f $exe.FullName, ($exe.Length / 1MB))

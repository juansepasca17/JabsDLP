"""Notificaciones nativas de Windows (toast) con botones "Abrir carpeta" / "Abrir archivo".

El contenido (títulos de videos, rutas) puede venir de internet, así que nunca se interpola en código de
PowerShell: el XML se escapa y se pasa dentro de una here-string entre comillas simples (@'...'@), que
PowerShell no interpreta. Para que Windows muestre el nombre y el icono de la app se registra un
AppUserModelID en HKCU (el método documentado para apps sin instalador; solo afecta al usuario actual).
"""
import os
import pathlib
import subprocess
import tempfile
import threading
import winreg
from xml.sax.saxutils import escape

from .utilidades import SIN_VENTANA

APP_ID = 'JabsDLP'
_registrado = False


def _registrar(icono):
    global _registrado
    if _registrado:
        return
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf'Software\Classes\AppUserModelId\{APP_ID}') as clave:
            winreg.SetValueEx(clave, 'DisplayName', 0, winreg.REG_SZ, APP_ID)
            if icono and os.path.isfile(icono):
                winreg.SetValueEx(clave, 'IconUri', 0, winreg.REG_SZ, icono)
        _registrado = True
    except OSError:
        pass


def _atributo(texto):
    return escape(str(texto or ''), {'"': '&quot;', "'": '&apos;'})


def _uri(ruta):
    try:
        return pathlib.Path(ruta).resolve().as_uri()
    except (ValueError, OSError):
        return ''


def construir_xml(titulo, mensaje, archivo=None, carpeta=None, textos=None):
    textos = textos or {}
    acciones = []
    if carpeta and os.path.isdir(carpeta):
        acciones.append((textos.get('carpeta', 'Abrir carpeta'), _uri(carpeta)))
    if archivo and os.path.isfile(archivo):
        acciones.append((textos.get('archivo', 'Abrir archivo'), _uri(archivo)))
    lanzar = acciones[-1][1] if acciones else ''
    botones = ''.join(f'<action content="{_atributo(t)}" activationType="protocol" arguments="{_atributo(u)}"/>'
                      for t, u in acciones if u)
    # Un "'@" al inicio de línea cerraría la here-string: se escapa la comilla simple y no hay saltos de línea
    xml = (f'<toast activationType="protocol" launch="{_atributo(lanzar)}">'
           f'<visual><binding template="ToastGeneric">'
           f'<text>{escape(str(titulo or ""))[:200]}</text><text>{escape(str(mensaje or ""))[:300]}</text>'
           f'</binding></visual>' + (f'<actions>{botones}</actions>' if botones else '') + '</toast>')
    return xml.replace("'", '&apos;').replace('\r', ' ').replace('\n', ' ')


SCRIPT = """[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml(@'
{xml}
'@)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app}').Show($toast)
"""


def mostrar(titulo, mensaje, archivo=None, carpeta=None, icono=None, textos=None):
    """Muestra el aviso en segundo plano; si algo falla, no molesta."""
    def tarea():
        _registrar(icono)
        script = SCRIPT.replace('{xml}', construir_xml(titulo, mensaje, archivo, carpeta, textos)).replace('{app}', APP_ID)
        ruta = None
        try:
            with tempfile.NamedTemporaryFile('w', suffix='.ps1', delete=False, encoding='utf-8-sig') as f:
                f.write(script)
                ruta = f.name
            subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                            '-File', ruta], creationflags=SIN_VENTANA, timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            pass
        finally:
            if ruta and os.path.exists(ruta):
                try:
                    os.unlink(ruta)
                except OSError:
                    pass
    threading.Thread(target=tarea, daemon=True).start()

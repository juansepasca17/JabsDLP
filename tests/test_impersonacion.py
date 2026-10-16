"""Pruebas del ajuste "impersonar" (suplantación de navegador con curl_cffi)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jabsdlp.ajustes import AJUSTES_POR_DEFECTO, Ajustes  # noqa: E402
from jabsdlp.impersonacion import (MOTIVO_SIN_CURL, aplicar_impersonacion, impersonation_disponible,  # noqa: E402
                                   objetivo_chrome)


def nuevos_ajustes(tmp_path, contenido=None):
    ruta = os.path.join(tmp_path, 'settings.json')
    if contenido is not None:
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(contenido, f)
    return Ajustes(ruta)


def opciones():
    return {'quiet': True}


# ---------- ajuste persistido ----------
def test_impersonar_por_defecto_false():
    assert AJUSTES_POR_DEFECTO['impersonar'] is False


def test_config_antigua_sin_la_clave_carga_con_el_default(tmp_path):
    a = nuevos_ajustes(tmp_path, {'gpu': 'nvenc', 'corte_exacto': True})
    assert a.get('impersonar') is False and a.get('gpu') == 'nvenc'


def test_impersonar_se_persiste_y_sanea(tmp_path):
    a = nuevos_ajustes(tmp_path)
    assert a.actualizar({'impersonar': True})['impersonar'] is True
    assert nuevos_ajustes(tmp_path).get('impersonar') is True   # se relée del disco
    a.actualizar({'impersonar': 'no-bool'})
    assert a.get('impersonar') is True                          # cualquier truthy → True


# ---------- disponibilidad ----------
def test_disponibilidad_devuelve_tupla_sin_lanzar():
    disponible, motivo = impersonation_disponible(forzar=True)
    assert isinstance(disponible, bool) and (motivo is None or isinstance(motivo, str))
    if disponible:
        assert motivo is None
    else:
        assert motivo  # hay un motivo que mostrar al usuario


def test_disponibilidad_sin_curl_cffi_da_motivo(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def sin_curl_cffi(nombre, *args, **kwargs):
        if nombre == 'curl_cffi' or nombre.startswith('curl_cffi.'):
            raise ModuleNotFoundError('No module named curl_cffi')
        return real_import(nombre, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', sin_curl_cffi)
    monkeypatch.setattr('jabsdlp.impersonacion._cache', None)
    disponible, motivo = impersonation_disponible(forzar=True)
    assert disponible is False and motivo == MOTIVO_SIN_CURL


# ---------- aplicación a las opciones de yt-dlp ----------
def test_switch_apagado_no_toca_nada():
    assert aplicar_impersonacion(opciones(), {'impersonar': False}) is None
    assert 'impersonate' not in opciones()


def test_switch_encendido_anade_el_objetivo_chrome(monkeypatch):
    monkeypatch.setattr('jabsdlp.impersonacion.impersonation_disponible', lambda forzar=False: (True, None))
    opts = opciones()
    assert aplicar_impersonacion(opts, {'impersonar': True}) is None
    assert str(opts['impersonate']) == 'chrome' == str(objetivo_chrome())


def test_switch_encendido_sin_disponibilidad_no_lanza_y_avisa(monkeypatch):
    monkeypatch.setattr('jabsdlp.impersonacion.impersonation_disponible', lambda forzar=False: (False, MOTIVO_SIN_CURL))
    opts = opciones()
    mensaje = aplicar_impersonacion(opts, {'impersonar': True})
    assert 'impersonate' not in opts and mensaje and MOTIVO_SIN_CURL in mensaje


def test_comando_personalizado_con_soporte_se_conserva(monkeypatch):
    monkeypatch.setattr('jabsdlp.impersonacion.impersonation_disponible', lambda forzar=False: (True, None))
    opts = {'impersonate': objetivo_chrome()}
    assert aplicar_impersonacion(opts, {'impersonar': True}) is None
    assert str(opts['impersonate']) == 'chrome'   # manda el comando personalizado


def test_comando_personalizado_sin_soporte_se_quita_y_avisa(monkeypatch):
    monkeypatch.setattr('jabsdlp.impersonacion.impersonation_disponible', lambda forzar=False: (False, MOTIVO_SIN_CURL))
    opts = {'impersonate': objetivo_chrome()}
    mensaje = aplicar_impersonacion(opts, {'impersonar': False})
    assert 'impersonate' not in opts and mensaje and MOTIVO_SIN_CURL in mensaje


# ---------- comando personalizado: --impersonate no está bloqueado ----------
def test_interpretar_acepta_impersonate():
    from yt_dlp.networking.impersonate import ImpersonateTarget

    from jabsdlp.argumentos import interpretar
    extra, pps = interpretar('--impersonate chrome')
    assert isinstance(extra['impersonate'], ImpersonateTarget)
    assert str(extra['impersonate']) == 'chrome' and not pps

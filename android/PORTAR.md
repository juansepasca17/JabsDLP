# JabsDLP para Android

La versión Android lleva el mismo número que la de PC: la 1.7.1 de Android tiene lo mismo que la 1.7.1 de PC,
salvo lo que solo tiene sentido en un PC. El APK se publica en la release de PC de esa versión (`v1.7.1`),
con su propia nota de versión al final.

## Cómo está hecha

| Parte | Dónde | Cómo |
|---|---|---|
| Interfaz | `ui/` (la del PC) | Dentro de un WebView. No se copia al repo: el build la toma de `../ui` en cada compilación. |
| Lógica | `jabsdlp/` (la del PC) | El mismo paquete de Python, ejecutado con Chaquopy (Python 3.13). También se toma de `../jabsdlp`. |
| Puente | `app/src/main/assets/android/bridge.js` | Crea `window.pywebview.api` con las mismas funciones que en PC, así `app.js` no cambia. Cada llamada va a Kotlin (`Puente.kt`) y de ahí a `Api` en Python (`jabsdlp_android/puente.py`). |
| Diferencias de plataforma | `app/src/main/python/jabsdlp_android/` | `arranque.py` prepara carpetas y sustituye, **antes de importar la Api**, lo que en Android funciona distinto (notificaciones, abrir archivos, portapapeles, papelera, diálogos, carpeta por defecto). `plataforma.py` hace esas cosas llamando a Kotlin (`Plataforma.kt`). **El código del PC no se toca.** |
| Pantalla del celular | `app/src/main/assets/android/android.css` y `android.js` | Barra de pestañas abajo, una columna, y se esconden los ajustes que solo existen en PC. |
| ffmpeg, QuickJS y aria2 | `scripts/compilar_nativos.sh` | ffmpeg 8.1 (x264, LAME, dav1d para AV1, mbedTLS), qjs y aria2 (con OpenSSL, para torrents; opcional: si no compila, el APK sale sin él) compilados con el NDK para arm64-v8a, guardados como `libffmpeg.so`, `libffprobe.so`, `libqjs.so` y `libaria2c.so` en `jniLibs`. Se ejecutan desde `nativeLibraryDir`, que es lo único que Android deja ejecutar; `arranque.py` los enlaza con su nombre normal en el PATH para que el código del PC los encuentre. |
| Descargas en segundo plano | `ServicioDescargas.kt` | Servicio en primer plano con notificación de progreso. Solo existe mientras hay descargas: cuando la cola termina (o está en pausa) se apaga solo. Botón **Detener**. Si quitas la app de recientes se detiene todo y la cola se guarda (ajuste «Seguir descargando al cerrar la app», apagado por defecto). |
| Compartir a la app | `MainActivity.kt`, `AndroidManifest.xml` | Dos opciones al compartir desde YouTube o el navegador: «Descargar con JabsDLP» manda el enlace a `recibirCaptura()` de la interfaz (reemplaza la captura rápida y el portapapeles del PC) y «Ver en JabsDLP» (el `activity-alias` `.VerEnJabsDLP`) a `verCompartido()` de la pestaña Ver. |
| Pantalla completa de Ver | `ui/ver.js` (`completaCss`) + `Puente.pantallaCompleta` | En Android el reproductor llena la pantalla con CSS (sin la API Fullscreen) y Kotlin esconde las barras y gira a horizontal. También al girar el teléfono. |
| Tarjeta SD y log | `Plataforma.kt`, `android.js` | En la SD solo se escribe en `Android/media/com.jabsdlp.app` (sin permisos). «Exportar log» comparte el logcat de la app (Python incluido) con los tokens ocultos. |
| Compilación | `.github/workflows/android.yml` | Al subir un tag `v<versión>-android` compila el APK, lo firma y lo sube a la release `v<versión>`. Gratis por ser repo público. |

Solo hay APK para **arm64-v8a**: Chaquopy con Python 3.12 o superior solo existe para 64 bits.

## Pasar una versión nueva de PC a Android

La idea es que casi todo pase solo: Android usa las mismas carpetas `ui/` y `jabsdlp/` que el PC.
Esto es lo que hay que revisar cuando sale una versión nueva de PC (por ejemplo 1.8.0) para sacar la 1.8.0 de Android.

1. **Ver qué cambió:**
   `git diff v<anterior> v<nueva> --stat -- ui jabsdlp requirements.txt`
2. **Por cada archivo cambiado**, revisar la tabla de abajo.
3. **Funciones nuevas en `jabsdlp/api.py`:** añadirlas a `android/funciones.txt` (la lista que expone el puente).
   El workflow falla si `api.py` tiene funciones públicas que no están en esa lista ni en `android/solo_pc.txt`.
   Puedes comprobarlo antes con `python android/scripts/revisar_api.py`.
4. **Si la función es solo de PC**, añadirla a `android/solo_pc.txt` con la respuesta que debe recibir la interfaz
   (por ejemplo `elegir_algo = null`), y esconder su botón en `android.css`. Si prefieres hacerlo desde la interfaz,
   `API.plataforma()` devuelve `'android'` en Android.
5. **Si cambió `requirements.txt`**, revisar que el paquete nuevo funcione en Chaquopy
   (Python puro: sí, añádelo a `scripts/requisitos.py`; con partes en C: hay que buscar o compilar una versión para Android).
6. **Subir `versionName` y `versionCode`** en `android/app/build.gradle.kts` (1.8.0 → `versionCode = 10800`).
   El workflow falla si `versionName` no coincide con la versión que se publica.
7. **Escribir la nota** en `android/notas/<versión>.md`.
8. **Crear el tag `v<nueva>-android`** y subirlo. Actions compila y añade el APK y la nota a la release `v<nueva>`.
   También se puede lanzar a mano desde *Actions → Android → Run workflow*.

### Qué revisar según el archivo que cambió

| Si cambió… | Revisar en Android |
|---|---|
| `jabsdlp/api.py` | Paso 3. Si la función nueva usa la ventana (`self._ventana`), diálogos o Windows, va en `solo_pc.txt` o se adapta en `jabsdlp_android/plataforma.py` (`adaptar_api`). |
| `jabsdlp/notificar.py`, `ventana.py` | En Android se reemplazan enteros (`arranque.py`). Si la Api empieza a usar una función nueva de ellos, añadirla al módulo falso de `arranque.py`. |
| `jabsdlp/utilidades.py` | Si cambian `abrir_en_explorador`, `leer_portapapeles`, `copiar_portapapeles` o `runtimes_js`, revisar sus sustitutos en `plataforma.py` / `arranque.py`. Si se añade otra función de Windows (ctypes, `os.startfile`…), sustituirla igual. |
| `jabsdlp/ajustes.py` | Rutas: en Android `%APPDATA%` y `%LOCALAPPDATA%` apuntan a la memoria de la app y la carpeta por defecto es `Descargas/JabsDLP`. Si hay ajustes nuevos solo de PC, esconder su fila en `android.css`. |
| `jabsdlp/ffmpeg_tools.py`, `trabajo.py`, `proxy.py` | Si se usa un códec o filtro nuevo de ffmpeg, comprobar que esté en la compilación de `compilar_nativos.sh`. Encoders de GPU no hay. |
| `jabsdlp/biblioteca.py` | `papelera()` y `miniatura()` se sustituyen en Android (la miniatura la saca `MediaMetadataRetriever`). |
| `jabsdlp/captura.py`, `bandeja.py`, `procesos.py`, `main.py` | No se usan en Android. |
| Módulo nuevo en `jabsdlp/` | Se incluye solo. Importarlo en Linux sin Windows debe funcionar (si usa `winreg`, `ctypes.windll`, etc. al importarse, hay que reemplazarlo en `arranque.py`). |
| `ui/index.html` | Botones o ajustes nuevos solo de PC: esconderlos en `android.css`. Probar cómo se ve en pantalla estrecha. |
| `ui/estilos.css` | Revisar que la vista de celular (`android.css`, bajo `@media (max-width: 999px)`) siga viéndose bien. |
| `ui/app.js` y demás | Nada, salvo que llamen a funciones nuevas de la Api (paso 3). |
| `requirements.txt` | Paso 5. |

### Probar sin celular
Con Python en el PC se puede comprobar la parte de Python, la lista de funciones y el aspecto en pantalla estrecha:
- `python android/scripts/revisar_api.py`
- Abrir `ui/index.html?mock=1` en el navegador, con el modo de dispositivo móvil, para ver el diseño.

## Firma del APK
El workflow firma con la clave guardada en los secretos del repo (*Settings → Secrets and variables → Actions*):
`JABSDLP_KEYSTORE_B64` (el archivo .jks en base64), `JABSDLP_KEYSTORE_PASS`, `JABSDLP_KEY_ALIAS` y `JABSDLP_KEY_PASS`.
Usa siempre la misma clave: si cambia, Android no deja instalar la versión nueva encima de la anterior.
Si faltan los secretos, el APK sale firmado con una clave de prueba y el workflow lo avisa.

## Compilar en el PC (opcional)
Necesitas Android Studio (o el SDK y el NDK), Gradle 8.14, Java 17 y Python 3.13 en el PATH.
```
bash android/scripts/compilar_nativos.sh <ruta del NDK>      # una vez (en Windows, desde WSL)
cd android && gradle assembleRelease
```

### Probar en el emulador (x86_64)
El emulador del PC es x86_64; el APK publicado es solo arm64-v8a. Para el emulador se compila un APK aparte:
1. ffmpeg y QuickJS para x86_64, una vez (desde WSL, con el NDK de Linux):
   `bash android/scripts/compilar_nativos.sh <NDK> android/nativos x86_64`
   (con `arm64-v8a,x86_64` compila los dos).
2. `JABSDLP_ABIS=x86_64 gradle assembleRelease` (o `arm64-v8a,x86_64` para un APK con las dos).
   Sin la variable sale el de siempre, solo arm64-v8a.
3. Emulador Android 14 x86_64 (Google APIs), y luego `adb install -r app/build/outputs/apk/release/*.apk`.
   - Capturas: `adb exec-out screencap -p > captura.png`.
   - Log: `adb logcat --pid=$(adb shell pidof com.jabsdlp.app)`.
   - La interfaz se puede inspeccionar con `chrome://inspect` si el APK es debug.

`android/nativos/` no se sube al repo (está en `.gitignore`).

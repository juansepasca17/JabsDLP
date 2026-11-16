package com.jabsdlp.app

import android.app.Activity
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.media.MediaScannerConnection
import android.net.Uri
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.webkit.MimeTypeMap
import android.widget.Toast
import androidx.core.app.NotificationCompat
import androidx.core.content.FileProvider
import java.io.File
import java.lang.ref.WeakReference
import java.util.concurrent.CompletableFuture
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/**
 * Lo que Python (jabsdlp_android/plataforma.py) necesita del sistema. Python llama a estos métodos
 * desde sus hilos; lo que toca la interfaz se pasa al hilo principal.
 */
object Plataforma {
    private lateinit var app: Context
    private var actividad: WeakReference<MainActivity>? = null
    private val principal = Handler(Looper.getMainLooper())
    private val idAviso = AtomicInteger(100)

    fun configurar(contexto: Context) {
        app = contexto.applicationContext
    }

    fun actividad(a: MainActivity?) {
        actividad = a?.let { WeakReference(it) }
    }

    private fun enPrincipal(bloque: () -> Unit) = principal.post { bloque() }

    private fun uriDe(archivo: File): Uri =
        FileProvider.getUriForFile(app, "${app.packageName}.archivos", archivo)

    private fun mimeDe(archivo: File): String =
        MimeTypeMap.getSingleton().getMimeTypeFromExtension(archivo.extension.lowercase()) ?: "*/*"

    // ---------- abrir ----------
    @JvmStatic
    fun abrir(ruta: String, carpeta: Boolean): Boolean {
        val f = File(ruta)
        val intento = if (carpeta || f.isDirectory) intentoCarpeta(if (f.isDirectory) f else f.parentFile ?: f)
        else Intent(Intent.ACTION_VIEW).setDataAndType(uriDe(f), mimeDe(f))
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        return lanzar(Intent.createChooser(intento, null))
    }

    /** Android no tiene un "explorador" común: se intenta abrir la carpeta en Archivos; si no, Descargas. */
    private fun intentoCarpeta(dir: File): Intent {
        val raiz = Environment.getExternalStorageDirectory().absolutePath
        val relativa = dir.absolutePath.removePrefix(raiz).trimStart('/')
        val uri = Uri.parse("content://com.android.externalstorage.documents/document/primary%3A" + Uri.encode(relativa))
        return Intent(Intent.ACTION_VIEW).setDataAndType(uri, "vnd.android.document/directory")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }

    private fun lanzar(intento: Intent): Boolean {
        val a = actividad?.get()
        return try {
            if (a != null) enPrincipal { iniciarSeguro(a, intento) }
            else app.startActivity(intento.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            true
        } catch (e: Exception) {
            false
        }
    }

    private fun iniciarSeguro(a: Activity, intento: Intent) {
        try {
            a.startActivity(intento)
        } catch (e: Exception) {
            try {   // sin app para la carpeta: se abre la lista de Descargas del sistema
                a.startActivity(Intent(android.app.DownloadManager.ACTION_VIEW_DOWNLOADS))
            } catch (_: Exception) {
                Toast.makeText(a, "No hay ninguna app para abrir esto.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    // ---------- notificaciones ----------
    @JvmStatic
    fun notificar(titulo: String, mensaje: String, archivo: String?) {
        val f = archivo?.let { File(it) }?.takeIf { it.isFile }
        val tocar = if (f != null) Intent(Intent.ACTION_VIEW).setDataAndType(uriDe(f), mimeDe(f))
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        else Intent(app, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        val pendiente = PendingIntent.getActivity(app, idAviso.get(), tocar,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val aviso = NotificationCompat.Builder(app, Canales.TERMINADAS)
            .setSmallIcon(R.drawable.ic_notificacion)
            .setContentTitle(titulo)
            .setContentText(mensaje)
            .setStyle(NotificationCompat.BigTextStyle().bigText(mensaje))
            .setContentIntent(pendiente)
            .setAutoCancel(true)
            .build()
        try {
            (app.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager)
                .notify(idAviso.incrementAndGet(), aviso)
        } catch (_: SecurityException) {   // sin permiso de notificaciones
        }
    }

    /** Miniatura de un video con los decodificadores de Android (AV1, VP9, HEVC…: el ffmpeg incluido no decodifica AV1).
     *  Guarda un JPEG de 320 px de ancho en `destino`. */
    @JvmStatic
    fun miniatura(ruta: String, destino: String): Boolean {
        val r = android.media.MediaMetadataRetriever()
        return try {
            r.setDataSource(ruta)
            val duracion = r.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
            val instante = if (duracion > 16_000) 8_000_000L else duracion * 500L   // microsegundos
            val opcion = android.media.MediaMetadataRetriever.OPTION_CLOSEST_SYNC
            val cuadro = (if (android.os.Build.VERSION.SDK_INT >= 27) r.getScaledFrameAtTime(instante, opcion, 320, 320)
                else r.getFrameAtTime(instante, opcion)) ?: return false
            val alto = (cuadro.height * 320f / cuadro.width).toInt().coerceAtLeast(1)
            val final = if (cuadro.width != 320) android.graphics.Bitmap.createScaledBitmap(cuadro, 320, alto, true) else cuadro
            File(destino).outputStream().use { final.compress(android.graphics.Bitmap.CompressFormat.JPEG, 78, it) }
            File(destino).length() > 0
        } catch (e: Exception) {
            false
        } finally {
            runCatching { r.release() }
        }
    }

    @JvmStatic
    fun escanear(ruta: String) {
        MediaScannerConnection.scanFile(app, arrayOf(ruta), null, null)
    }

    @JvmStatic
    fun aviso(texto: String) = enPrincipal { Toast.makeText(app, texto, Toast.LENGTH_LONG).show() }

    // ---------- portapapeles ----------
    private fun <T> enPrincipalYEsperar(defecto: T, bloque: () -> T): T {
        if (Looper.myLooper() == Looper.getMainLooper()) return bloque()
        val futuro = CompletableFuture<T>()
        principal.post { futuro.complete(runCatching(bloque).getOrDefault(defecto)) }
        return runCatching { futuro.get(5, TimeUnit.SECONDS) }.getOrDefault(defecto)
    }

    @JvmStatic
    fun leerPortapapeles(): String = enPrincipalYEsperar("") {
        val cm = app.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.primaryClip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(app)?.toString() ?: ""
    }

    @JvmStatic
    fun copiarPortapapeles(texto: String): Boolean = enPrincipalYEsperar(false) {
        val cm = app.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("JabsDLP", texto))
        true
    }

    // ---------- diálogos (bloquean el hilo de Python hasta que eliges algo) ----------
    @JvmStatic
    fun dialogo(tipo: String, mimes: String): String? {
        val a = actividad?.get() ?: return null
        val futuro = CompletableFuture<String?>()
        enPrincipal { a.pedirArchivo(tipo, mimes.split(',').map { it.trim() }.toTypedArray(), futuro) }
        return runCatching { futuro.get(15, TimeUnit.MINUTES) }.getOrNull()
    }

    // ---------- ventana ----------
    @JvmStatic
    fun colorBarras(claro: Boolean) = enPrincipal { actividad?.get()?.colorBarras(claro) }

    @JvmStatic
    fun pantallaCompleta(modo: Int) = enPrincipal { actividad?.get()?.pantallaCompleta(modo) }

    @JvmStatic
    fun reiniciar() = enPrincipal {
        // Como ProcessPhoenix: una actividad en otro proceso espera a que este muera y vuelve a abrir la app
        val intento = Intent(app, Reinicio::class.java)
            .putExtra(Reinicio.PID, android.os.Process.myPid())
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        app.startActivity(intento)
        actividad?.get()?.finishAndRemoveTask()
        Runtime.getRuntime().exit(0)
    }

    /** Carpeta por defecto: Descargas/JabsDLP (se ve en la app Archivos y en la Galería). */
    fun carpetaDescargas(): File =
        File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "JabsDLP")

    /** En la tarjeta SD Android solo deja escribir por ruta en la carpeta propia de la app
     *  (Android/media/com.jabsdlp.app): se ve en la Galería y no hace falta ningún permiso. */
    fun carpetaSd(): File? = app.externalMediaDirs.filterNotNull()
        .firstOrNull { Environment.isExternalStorageRemovable(it) && Environment.getExternalStorageState(it) == Environment.MEDIA_MOUNTED }
        ?.also { it.mkdirs() }

    @JvmStatic
    fun carpetaSdRuta(): String = carpetaSd()?.absolutePath ?: ""

    fun carpetaDisponible(ruta: String): Boolean {
        if (!ruta.startsWith("/storage/") || ruta.startsWith("/storage/emulated/") || ruta.startsWith("/storage/self/")) return true
        val volumen = File(ruta.split("/").take(3).joinToString("/"))   // /storage/XXXX-XXXX
        return volumen.isDirectory && volumen.canRead() && (File(ruta).isDirectory || File(ruta).parentFile?.canWrite() == true)
    }

}

package com.jabsdlp.app

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Build
import android.os.IBinder
import android.support.v4.media.MediaMetadataCompat
import android.support.v4.media.session.MediaSessionCompat
import android.support.v4.media.session.PlaybackStateCompat
import android.util.Base64
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import androidx.media.app.NotificationCompat.MediaStyle
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/**
 * Lo que suena en la pestaña Ver, en la notificación (y en la pantalla de bloqueo y el panel de controles
 * multimedia de Android): portada, título, anterior / pausa / siguiente y la barra de tiempo.
 * La interfaz avisa con JabsAndroid.musica(json) y los botones vuelven a la interfaz con controlMusica(…).
 * Mientras suena es un servicio en primer plano (así Android no corta la música con la app en segundo plano);
 * en pausa la notificación se puede quitar deslizándola.
 */
class ServicioMusica : Service() {
    private lateinit var sesion: MediaSessionCompat
    private val portadas = Executors.newSingleThreadExecutor()
    private var portadaClave = ""
    private var portada: Bitmap? = null
    private var enPrimerPlano = false
    private var cerrado = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        sesion = MediaSessionCompat(this, "JabsDLP").apply {
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlay() = MainActivity.controlMusica("play")
                override fun onPause() = MainActivity.controlMusica("pausa")
                override fun onSkipToNext() = MainActivity.controlMusica("siguiente")
                override fun onSkipToPrevious() = MainActivity.controlMusica("anterior")
                override fun onSeekTo(pos: Long) = MainActivity.controlMusica("ir", pos / 1000.0)
                override fun onStop() = MainActivity.controlMusica("pausa")
                override fun onCustomAction(action: String?, extras: android.os.Bundle?) { if (action == CERRAR) cerrar() }
            })
            isActive = true
        }
        servicio = this
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACCION -> intent.getStringExtra("orden")?.let { if (it == CERRAR) { cerrar(); return START_NOT_STICKY } else MainActivity.controlMusica(it) }
            QUITADA -> { terminar(); return START_NOT_STICKY }
        }
        val datos = ultimo
        if (datos == null) { terminar(); return START_NOT_STICKY }
        mostrar(datos)
        return START_NOT_STICKY
    }

    fun mostrar(d: JSONObject) {
        if (cerrado) return
        val sonando = d.optBoolean("sonando")
        val antes = Companion.sonando
        Companion.sonando = sonando
        mantener = sonando && d.optBoolean("mantener", true)
        if (antes && !mantener && !MainActivity.visible) MainActivity.ocultarPagina()   // en pausa ya no hace falta
        val titulo = texto(d, "titulo") ?: "JabsDLP"
        val artista = texto(d, "artista") ?: ""
        val clave = d.optString("portada")
        if (clave != portadaClave) {
            portadaClave = clave
            portada = null
            if (clave.isNotBlank()) portadas.execute {
                val b = cargarPortada(clave)
                if (clave == portadaClave && b != null) { portada = b; ultimo?.let { u -> android.os.Handler(mainLooper).post { mostrar(u) } } }
            }
        }
        val meta = MediaMetadataCompat.Builder()
            .putString(MediaMetadataCompat.METADATA_KEY_TITLE, titulo)
            .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, artista.ifBlank { "JabsDLP" })
            .putLong(MediaMetadataCompat.METADATA_KEY_DURATION, (d.optDouble("duracion", 0.0) * 1000).toLong().coerceAtLeast(0))
        portada?.let { meta.putBitmap(MediaMetadataCompat.METADATA_KEY_ALBUM_ART, it) }
        sesion.setMetadata(meta.build())
        var acciones = PlaybackStateCompat.ACTION_PLAY or PlaybackStateCompat.ACTION_PAUSE or
            PlaybackStateCompat.ACTION_PLAY_PAUSE or PlaybackStateCompat.ACTION_SEEK_TO or PlaybackStateCompat.ACTION_STOP
        if (d.optBoolean("anterior", true)) acciones = acciones or PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS
        if (d.optBoolean("siguiente")) acciones = acciones or PlaybackStateCompat.ACTION_SKIP_TO_NEXT
        sesion.setPlaybackState(PlaybackStateCompat.Builder()
            .setActions(acciones)
            .addCustomAction(PlaybackStateCompat.CustomAction.Builder(CERRAR, "Cerrar", android.R.drawable.ic_menu_close_clear_cancel).build())
            .setState(if (sonando) PlaybackStateCompat.STATE_PLAYING else PlaybackStateCompat.STATE_PAUSED,
                (d.optDouble("posicion", 0.0) * 1000).toLong(), if (sonando) d.optDouble("velocidad", 1.0).toFloat() else 0f)
            .build())

        val aviso = construir(titulo, artista, sonando, d.optBoolean("siguiente"))
        if (sonando) {
            val tipo = if (Build.VERSION.SDK_INT >= 29) ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK else 0
            try {
                ServiceCompat.startForeground(this, ID, aviso, tipo)
                enPrimerPlano = true
            } catch (e: Exception) {   // Android no deja pasar a primer plano desde segundo plano: solo la notificación
                runCatching { NotificationManagerCompat.from(this).notify(ID, aviso) }
            }
        } else {
            if (enPrimerPlano) {
                ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_DETACH)
                enPrimerPlano = false
            }
            runCatching { NotificationManagerCompat.from(this).notify(ID, aviso) }
        }
    }

    /** optString devuelve "null" (texto) si el valor es null en JSON: se trata como vacío. */
    private fun texto(d: JSONObject, clave: String): String? =
        if (d.isNull(clave)) null else d.optString(clave).takeUnless { it.isBlank() || it == "null" }

    private fun accion(orden: String, codigo: Int) = PendingIntent.getService(this, codigo,
        Intent(this, ServicioMusica::class.java).setAction(ACCION).putExtra("orden", orden),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)

    private fun construir(titulo: String, artista: String, sonando: Boolean, haySiguiente: Boolean): Notification {
        val abrir = PendingIntent.getActivity(this, 20,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val quitada = PendingIntent.getService(this, 21, Intent(this, ServicioMusica::class.java).setAction(QUITADA),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val b = NotificationCompat.Builder(this, Canales.MUSICA)
            .setSmallIcon(R.drawable.ic_notificacion)
            .setContentTitle(titulo)
            .setContentText(artista.ifBlank { null })
            .setLargeIcon(portada)
            .setContentIntent(abrir)
            .setDeleteIntent(quitada)
            .setOngoing(sonando)
            .setOnlyAlertOnce(true)
            .setSilent(true)
            .setShowWhen(false)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .addAction(android.R.drawable.ic_media_previous, "Anterior", accion("anterior", 22))
            .addAction(if (sonando) android.R.drawable.ic_media_pause else android.R.drawable.ic_media_play,
                if (sonando) "Pausa" else "Reproducir", accion(if (sonando) "pausa" else "play", 23))
        if (haySiguiente) b.addAction(android.R.drawable.ic_media_next, "Siguiente", accion("siguiente", 24))
        b.addAction(android.R.drawable.ic_menu_close_clear_cancel, "Cerrar", accion(CERRAR, 25))
        b.setStyle(MediaStyle().setMediaSession(sesion.sessionToken)
            .setShowActionsInCompactView(*if (haySiguiente) intArrayOf(0, 1, 2) else intArrayOf(0, 1)))
        return b.build()
    }

    /** La portada llega como data:image/…;base64 (archivos locales) o como https:// (miniatura del video). */
    private fun cargarPortada(fuente: String): Bitmap? = runCatching {
        val bytes = if (fuente.startsWith("data:")) Base64.decode(fuente.substringAfter(","), Base64.DEFAULT)
        else if (fuente.startsWith("https://")) {
            val c = URL(fuente).openConnection() as HttpURLConnection
            c.connectTimeout = 5000; c.readTimeout = 8000
            c.inputStream.use { it.readBytes().also { r -> if (r.size > 4_000_000) return null } }
        } else return null
        val b = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return null
        val lado = 512f / maxOf(b.width, b.height)
        if (lado < 1f) Bitmap.createScaledBitmap(b, (b.width * lado).toInt().coerceAtLeast(1), (b.height * lado).toInt().coerceAtLeast(1), true) else b
    }.getOrNull()

    /** La X: se pausa lo que suena y se quita la notificación. No vuelve a salir hasta que vuelvas a darle play. */
    private fun cerrar() {
        MainActivity.controlMusica("pausa")
        terminar()
    }

    private fun terminar() {
        cerrado = true
        if (servicio === this) servicio = null
        ultimo = null
        mantener = false
        if (sonando) { sonando = false; if (!MainActivity.visible) MainActivity.ocultarPagina() }
        enPrimerPlano = false
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        runCatching { NotificationManagerCompat.from(this).cancel(ID) }
        stopSelf()
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        terminar()
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        if (servicio === this) servicio = null
        sesion.isActive = false
        sesion.release()
        portadas.shutdownNow()
        super.onDestroy()
    }

    companion object {
        private const val ID = 7
        private const val ACCION = "com.jabsdlp.app.MUSICA"
        private const val QUITADA = "com.jabsdlp.app.MUSICA_QUITADA"
        @Volatile private var ultimo: JSONObject? = null
        @Volatile private var servicio: ServicioMusica? = null
        /** Algo suena en Ver con la notificación activa (la página sigue «visible» en segundo plano). */
        @Volatile var sonando = false
        /** Mientras suena, la página sigue «visible» con la app en segundo plano (los videos no se pausan). */
        @Volatile var mantener = false
        private const val CERRAR = "cerrar"

        /** Desde la interfaz: lo que suena ahora (o null para quitar la notificación). */
        fun actualizar(c: Context, json: String?) {
            val d = json?.let { runCatching { JSONObject(it) }.getOrNull() }
            ultimo = d
            val s = servicio
            if (d == null) {
                s?.let { android.os.Handler(it.mainLooper).post { it.terminar() } }
                return
            }
            if (s != null) {
                android.os.Handler(s.mainLooper).post { s.mostrar(d) }
                return
            }
            if (!d.optBoolean("sonando") || !MainActivity.visible) return   // se crea cuando empieza a sonar con la app delante
            runCatching {
                val i = Intent(c, ServicioMusica::class.java)
                if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i) else c.startService(i)
            }
        }
    }
}

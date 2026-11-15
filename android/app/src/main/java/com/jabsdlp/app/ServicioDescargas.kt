package com.jabsdlp.app

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import org.json.JSONObject

/**
 * Servicio en primer plano: mantiene viva la app mientras hay descargas, con su notificación de progreso.
 * Solo existe mientras hay algo descargándose: cuando la cola termina (o está en pausa) se apaga solo.
 */
class ServicioDescargas : Service() {
    private lateinit var hilo: HandlerThread
    private lateinit var tareas: Handler
    private var ultimoTexto = ""

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        hilo = HandlerThread("servicio-descargas").apply { start() }
        tareas = Handler(hilo.looper)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == DETENER) {
            tareas.post { runCatching { App.puente().callAttr("detener") } }
        }
        val tipo = if (Build.VERSION.SDK_INT >= 29) ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC else 0
        ServiceCompat.startForeground(this, ID, construir("Preparando descargas…", null, 0, true), tipo)
        if (!activo) {
            activo = true
            tareas.post(revisar)
        }
        return START_NOT_STICKY
    }

    private val revisar: Runnable = object : Runnable {
        override fun run() {
            val estado = runCatching { JSONObject(App.puente().callAttr("estado").toString()) }.getOrNull()
            if (estado != null && estado.optBoolean("listo")) {
                estado.optJSONArray("nuevos")?.let { nuevos ->
                    for (i in 0 until nuevos.length()) Plataforma.escanear(nuevos.getString(i))
                }
                val r = estado.getJSONObject("resumen")
                val activos = r.optInt("activos")
                val enCola = r.optInt("en_cola")
                if (activos == 0 && (enCola == 0 || r.optBoolean("pausado"))) {
                    terminar()
                    return
                }
                actualizar(estado, activos, enCola)
            }
            tareas.postDelayed(this, 1000)
        }
    }

    private fun actualizar(estado: JSONObject, activos: Int, enCola: Int) {
        val lista = estado.optJSONArray("activos")
        val primero = lista?.optJSONObject(0)
        var suma = 0.0
        for (i in 0 until (lista?.length() ?: 0)) {
            val t = lista!!.getJSONObject(i)
            suma += if (t.optString("estado") == "convirtiendo") t.optDouble("conversion", 0.0) else t.optDouble("progreso", 0.0)
        }
        val progreso = if (activos > 0) (suma / activos * 100).toInt().coerceIn(0, 100) else 0
        val titulo = if (activos == 1 && primero != null) primero.optString("titulo", "Descargando")
        else "$activos descargas en curso"
        val detalle = buildString {
            if (activos == 1 && primero != null) {
                append("$progreso %")
                velocidad(primero.opt("velocidad"))?.let { append(" · $it") }
                if (primero.optString("estado") == "convirtiendo") append(" · convirtiendo")
            } else append("$progreso % en total")
            if (enCola > 0) append(" · $enCola en cola")
        }
        val texto = "$titulo|$detalle"
        if (texto == ultimoTexto) return
        ultimoTexto = texto
        runCatching {
            NotificationManagerCompat.from(this).notify(ID, construir(titulo, detalle, progreso, progreso == 0))
        }
    }

    private fun velocidad(v: Any?): String? {
        val bytes = (v as? Number)?.toDouble() ?: return null
        if (bytes <= 0) return null
        return if (bytes >= 1_048_576) String.format("%.1f MB/s", bytes / 1_048_576) else String.format("%.0f KB/s", bytes / 1024)
    }

    private fun construir(titulo: String, detalle: String?, progreso: Int, indeterminado: Boolean): Notification {
        val abrir = PendingIntent.getActivity(this, 0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val detener = PendingIntent.getService(this, 1,
            Intent(this, ServicioDescargas::class.java).setAction(DETENER),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, Canales.PROGRESO)
            .setSmallIcon(R.drawable.ic_notificacion)
            .setContentTitle(titulo)
            .setContentText(detalle)
            .setProgress(100, progreso, indeterminado)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setSilent(true)
            .setContentIntent(abrir)
            .addAction(0, "Detener", detener)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    private fun terminar() {
        activo = false
        tareas.removeCallbacksAndMessages(null)
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    /** Quitaste la app de recientes. Con el ajuste apagado (por defecto) se detiene todo y la cola se guarda. */
    override fun onTaskRemoved(rootIntent: Intent?) {
        if (!Preferencias.seguirAlCerrar(this)) {
            runCatching { App.puente().callAttr("cerrar") }
            terminar()
            Runtime.getRuntime().exit(0)
        }
        super.onTaskRemoved(rootIntent)
    }

    /** Android 15 limita el tiempo de este tipo de servicio: al agotarse, se apaga sin cerrar la app. */
    override fun onTimeout(startId: Int, fgsType: Int) {
        terminar()
    }

    override fun onDestroy() {
        activo = false
        hilo.quitSafely()
        super.onDestroy()
    }

    companion object {
        private const val ID = 1
        private const val DETENER = "com.jabsdlp.app.DETENER"
        @Volatile var activo = false

        fun iniciar(c: Context) {
            if (activo) return
            runCatching {
                if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(Intent(c, ServicioDescargas::class.java))
                else c.startService(Intent(c, ServicioDescargas::class.java))
            }
        }
    }
}

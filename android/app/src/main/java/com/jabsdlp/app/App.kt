package com.jabsdlp.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

object Canales {
    const val PROGRESO = "progreso"
    const val TERMINADAS = "terminadas"
    const val MUSICA = "musica"
}

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        if (esProcesoDeReinicio()) return
        Plataforma.configurar(this)
        crearCanales()
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        val funciones = assets.open("android/funciones.txt").bufferedReader().use { it.readText() }
        puente().callAttr("iniciar", filesDir.absolutePath, cacheDir.absolutePath,
            Plataforma.carpetaDescargas().absolutePath, applicationInfo.nativeLibraryDir, funciones)
    }

    private fun esProcesoDeReinicio(): Boolean =
        Build.VERSION.SDK_INT >= 28 && getProcessName().endsWith(":reinicio")

    private fun crearCanales() {
        if (Build.VERSION.SDK_INT < 26) return
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(Canales.PROGRESO, "Descargas en curso",
            NotificationManager.IMPORTANCE_LOW).apply { setShowBadge(false) })
        nm.createNotificationChannel(NotificationChannel(Canales.TERMINADAS, "Descargas terminadas",
            NotificationManager.IMPORTANCE_DEFAULT))
        nm.createNotificationChannel(NotificationChannel(Canales.MUSICA, "Reproducción",
            NotificationManager.IMPORTANCE_LOW).apply { setShowBadge(false) })
    }

    companion object {
        /** Módulo jabsdlp_android.puente (Python). */
        fun puente(): PyObject = Python.getInstance().getModule("jabsdlp_android.puente")
    }
}

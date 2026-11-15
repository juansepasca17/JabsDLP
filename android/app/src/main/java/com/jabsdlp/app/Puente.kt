package com.jabsdlp.app

import android.content.Context
import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * Lo que ve bridge.js como `JabsAndroid`. Cada llamada de la interfaz se ejecuta en un hilo aparte
 * (como en pywebview, varias a la vez) y la respuesta vuelve con window.__jabsResolver(id, json).
 */
class Puente(private val contexto: Context, private val web: WebView) {
    private val hilos = Executors.newCachedThreadPool()

    @JavascriptInterface
    fun funciones(): String = leerAsset("android/funciones.txt")

    @JavascriptInterface
    fun soloPc(): String = leerAsset("android/solo_pc.txt")

    @JavascriptInterface
    fun llamar(id: Int, nombre: String, argumentos: String) {
        hilos.execute {
            val respuesta = try {
                App.puente().callAttr("llamar", nombre, argumentos).toString()
            } catch (e: Throwable) {
                JSONObject().put("e", e.message ?: e.toString()).toString()
            }
            web.post { web.evaluateJavascript("window.__jabsResolver($id, ${JSONObject.quote(respuesta)})", null) }
        }
    }

    @JavascriptInterface
    fun seguirAlCerrar(): Boolean = Preferencias.seguirAlCerrar(contexto)

    @JavascriptInterface
    fun cambiarSeguirAlCerrar(valor: Boolean) = Preferencias.cambiarSeguirAlCerrar(contexto, valor)

    @JavascriptInterface
    fun versionApp(): String = contexto.packageManager.getPackageInfo(contexto.packageName, 0).versionName ?: ""

    private fun leerAsset(ruta: String) = contexto.assets.open(ruta).bufferedReader().use { it.readText() }
}

object Preferencias {
    private const val ARCHIVO = "android"
    private const val SEGUIR = "seguir_al_cerrar"

    fun seguirAlCerrar(c: Context) = c.getSharedPreferences(ARCHIVO, Context.MODE_PRIVATE).getBoolean(SEGUIR, false)

    fun cambiarSeguirAlCerrar(c: Context, valor: Boolean) =
        c.getSharedPreferences(ARCHIVO, Context.MODE_PRIVATE).edit().putBoolean(SEGUIR, valor).apply()
}

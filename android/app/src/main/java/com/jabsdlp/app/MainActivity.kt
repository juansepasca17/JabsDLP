package com.jabsdlp.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.app.PendingIntent
import android.content.pm.ActivityInfo
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.DocumentsContract
import android.provider.OpenableColumns
import android.view.View
import android.view.ViewGroup
import android.webkit.ConsoleMessage
import android.webkit.RenderProcessGoneDetail
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.CompletableFuture
import java.util.concurrent.Executors

class MainActivity : ComponentActivity() {
    private lateinit var raiz: FrameLayout
    private lateinit var web: WebView
    private var vistaVideo: View? = null
    private var cerrarVideo: WebChromeClient.CustomViewCallback? = null
    private val principal = Handler(Looper.getMainLooper())
    private val fondo = Executors.newSingleThreadExecutor()
    private var futuroArchivo: CompletableFuture<String?>? = null
    private var pantallaCompletaAplicada = false
    private var completa = false
    private var videoCompleto = false

    // ---------- selector de archivos y carpetas (los diálogos del PC) ----------
    private val abrirDocumento = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        val futuro = futuroArchivo.also { futuroArchivo = null } ?: return@registerForActivityResult
        if (uri == null) futuro.complete(null) else fondo.execute { futuro.complete(rutaLegible(uri)) }
    }

    private val abrirCarpeta = registerForActivityResult(ActivityResultContracts.OpenDocumentTree()) { uri ->
        val futuro = futuroArchivo.also { futuroArchivo = null } ?: return@registerForActivityResult
        val ruta = uri?.let { rutaDeCarpeta(it) }
        if (uri != null && ruta == null) {
            Toast.makeText(this, "Elige una carpeta de la memoria interna (por ejemplo, dentro de Download o Movies).",
                Toast.LENGTH_LONG).show()
        }
        futuro.complete(ruta)
    }

    private val permisos = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        Plataforma.actividad(this)
        actual = java.lang.ref.WeakReference(this)

        if (0 != applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) WebView.setWebContentsDebuggingEnabled(true)
        raiz = FrameLayout(this).apply { setBackgroundColor(Color.parseColor("#09090b")) }
        web = WebViewJabs(this).apply { setBackgroundColor(Color.parseColor("#09090b")) }
        raiz.addView(web, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        setContentView(raiz)
        // Android 15 dibuja la app bajo las barras del sistema: se deja su espacio (y el del teclado)
        ViewCompat.setOnApplyWindowInsetsListener(raiz) { v, insets ->
            val b = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.ime()
                    or WindowInsetsCompat.Type.displayCutout())
            v.setPadding(b.left, b.top, b.right, b.bottom)
            WindowInsetsCompat.CONSUMED
        }

        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = true
            mediaPlaybackRequiresUserGesture = false
            setSupportZoom(false)
            textZoom = 100
        }
        web.addJavascriptInterface(Puente(this, web), "JabsAndroid")
        val guion = puenteJs()
        val alInicio = WebViewFeature.isFeatureSupported(WebViewFeature.DOCUMENT_START_SCRIPT)
        if (alInicio) WebViewCompat.addDocumentStartJavaScript(web, guion, setOf("*"))

        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val url = request.url
                if (url.scheme == "file" && url.path?.startsWith("/android_asset/") == true) return false
                // Los enlaces externos se abren en el navegador: la ventana de la app solo muestra su interfaz
                runCatching { startActivity(Intent(Intent.ACTION_VIEW, url)) }
                return true
            }

            override fun onPageFinished(view: WebView, url: String) {
                // También aquí: algunos WebView no inyectan el guion de inicio en páginas file://.
                // bridge.js y android.js no hacen nada si ya se ejecutaron.
                view.evaluateJavascript(guion, null)
            }

            override fun onRenderProcessGone(view: WebView, detail: RenderProcessGoneDetail): Boolean {
                recreate()
                return true
            }
        }
        web.webChromeClient = object : WebChromeClient() {
            override fun onShowCustomView(view: View, callback: CustomViewCallback) {
                vistaVideo?.let { cerrarVideo?.onCustomViewHidden() }
                vistaVideo = view
                cerrarVideo = callback
                raiz.addView(view, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
                barrasOcultas(true)
            }

            override fun onHideCustomView() = salirDeVideo()

            override fun onConsoleMessage(m: ConsoleMessage): Boolean {
                android.util.Log.d("JabsDLP-ui", "${m.message()} (${m.sourceId()}:${m.lineNumber()})")
                return true
            }
        }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (vistaVideo != null) salirDeVideo()
                else if (videoCompleto) web.evaluateJavascript("window.salirCompletaVer && salirCompletaVer()", null)
                else moveTaskToBack(true)   // atrás no cierra la app: las descargas siguen
            }
        })

        web.loadUrl("file:///android_asset/ui/index.html")
        pedirPermisos()
        recibirCompartido(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        recibirCompartido(intent)
    }

    override fun onResume() {
        super.onResume()
        visible = true
        web.dispatchWindowVisibilityChanged(View.VISIBLE)   // por si quedó «oculta» en segundo plano
        principal.post(vigilar)
    }

    override fun onPause() {
        visible = Build.VERSION.SDK_INT >= 24 && isInPictureInPictureMode   // en la ventanita sigue viéndose
        principal.removeCallbacks(vigilar)
        super.onPause()
    }

    override fun onDestroy() {
        if (actual?.get() === this) { actual = null; ServicioMusica.actualizar(this, null) }
        Plataforma.actividad(null)
        futuroArchivo?.complete(null)
        web.destroy()
        super.onDestroy()
    }

    private fun puenteJs(): String = listOf("android/bridge.js", "android/android.js").joinToString("\n") { ruta ->
        assets.open(ruta).bufferedReader().use { it.readText() }
    } + "\n;(function(){if(document.getElementById('jabs-android-css'))return;" +
        "var s=document.createElement('style');s.id='jabs-android-css';s.textContent=" +
        JSONObject.quote(assets.open("android/android.css").bufferedReader().use { it.readText() }) +
        ";function poner(){(document.head||document.documentElement).appendChild(s);}" +
        "if(document.documentElement)poner();else document.addEventListener('DOMContentLoaded',poner);})();"

    // ---------- servicio de descargas ----------
    /** Mientras la app está a la vista: si hay descargas, se arranca el servicio que las mantiene vivas. */
    private val vigilar: Runnable = object : Runnable {
        override fun run() {
            fondo.execute {
                val estado = runCatching { JSONObject(App.puente().callAttr("estado").toString()) }.getOrNull()
                if (estado != null && estado.optBoolean("listo")) {
                    if (!pantallaCompletaAplicada) {
                        pantallaCompletaAplicada = true
                        App.puente().callAttr("marcar_vistos")
                        val ajuste = App.puente().callAttr("ajuste", "pantalla_completa").toString()
                        if (ajuste == "true") principal.post { pantallaCompleta(1) }
                    }
                    val r = estado.getJSONObject("resumen")
                    if (r.optInt("activos") > 0 || (r.optInt("en_cola") > 0 && !r.optBoolean("pausado"))) {
                        principal.post { ServicioDescargas.iniciar(this@MainActivity) }
                    }
                }
            }
            principal.postDelayed(this, 2000)
        }
    }

    // ---------- compartir → JabsDLP ----------
    private fun recibirCompartido(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        val texto = listOfNotNull(intent.getStringExtra(Intent.EXTRA_TEXT), intent.getStringExtra(Intent.EXTRA_SUBJECT))
            .joinToString(" ")
        val urls = Regex("""https?://[^\s"'<>]+""").findAll(texto).map { it.value.trimEnd('.', ',', ')', ']') }
            .distinct().toList()
        if (urls.isEmpty()) {
            Toast.makeText(this, "No se encontró ningún enlace en lo compartido.", Toast.LENGTH_SHORT).show()
            return
        }
        val lista = JSONArray(urls).toString()
        // «Ver en JabsDLP» (el alias) abre el enlace en la pestaña Ver; «Descargar con JabsDLP», en Descargar
        val ver = intent.component?.className?.endsWith(".VerEnJabsDLP") == true
        val accion = if (ver) "if (window.verCompartido) { verCompartido(lista[0]); return; }" else "recibirCaptura(lista, 'auto'); return;"
        // Espera a que la interfaz haya cargado los ajustes antes de entregar el enlace
        web.evaluateJavascript("""
            (function entregar(n){
              var lista = $lista;
              try { if (window.recibirCaptura && S && S.ajustes && S.ajustes.tema !== undefined) { $accion } } catch (e) {}
              if (n < 200) setTimeout(function(){ entregar(n + 1); }, 150);
            })(0);
        """.trimIndent(), null)
        intent.action = null
    }

    // ---------- permisos ----------
    private fun pedirPermisos() {
        val lista = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= 33) {
            lista += Manifest.permission.POST_NOTIFICATIONS
            // Para ver en la Biblioteca los videos que ya estaban (p. ej. tras reinstalar la app)
            lista += Manifest.permission.READ_MEDIA_VIDEO
            lista += Manifest.permission.READ_MEDIA_AUDIO
        } else if (Build.VERSION.SDK_INT <= 29) {
            lista += Manifest.permission.WRITE_EXTERNAL_STORAGE
            lista += Manifest.permission.READ_EXTERNAL_STORAGE
        } else {
            lista += Manifest.permission.READ_EXTERNAL_STORAGE
        }
        val faltan = lista.filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }
        if (faltan.isNotEmpty()) permisos.launch(faltan.toTypedArray())
    }

    // ---------- diálogos ----------
    fun pedirArchivo(tipo: String, mimes: Array<String>, futuro: CompletableFuture<String?>) {
        futuroArchivo?.complete(null)
        futuroArchivo = futuro
        try {
            if (tipo == "FOLDER") abrirCarpeta.launch(null) else abrirDocumento.launch(mimes)
        } catch (e: Exception) {
            futuroArchivo = null
            futuro.complete(null)
        }
    }

    private val raizAlmacenamiento: String get() = Environment.getExternalStorageDirectory().absolutePath

    private fun rutaDeCarpeta(uri: Uri): String? {
        val id = runCatching { DocumentsContract.getTreeDocumentId(uri) }.getOrNull() ?: return null
        val partes = id.split(":", limit = 2)
        if (uri.authority != "com.android.externalstorage.documents") return null
        if (!partes[0].equals("primary", true)) {
            // Tarjeta SD (/storage/XXXX-XXXX/…): se devuelve la carpeta real. Leer (Biblioteca) se puede con el permiso
            // de videos y audio; si es la carpeta de descargas y no se puede escribir, Python usa la carpeta de la app
            val volumen = File("/storage", partes[0])
            if (!volumen.isDirectory) return null
            return File(volumen, partes.getOrElse(1) { "" }).absolutePath
        }
        return File(raizAlmacenamiento, partes.getOrElse(1) { "" }).absolutePath
    }

    /** Una ruta que Python pueda abrir: la real si se puede leer, si no una copia en la caché. */
    private fun rutaLegible(uri: Uri): String? {
        directa(uri)?.let { if (File(it).canRead()) return it }
        return runCatching {
            val nombre = contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) c.getString(0) else null
            } ?: "archivo"
            val destino = File(File(cacheDir, "importados").apply { mkdirs() }, File(nombre).name)
            contentResolver.openInputStream(uri)!!.use { entrada -> destino.outputStream().use { entrada.copyTo(it) } }
            destino.absolutePath
        }.getOrNull()
    }

    private fun directa(uri: Uri): String? {
        if (uri.scheme == "file") return uri.path
        if (!DocumentsContract.isDocumentUri(this, uri)) return null
        val id = DocumentsContract.getDocumentId(uri)
        return when (uri.authority) {
            "com.android.externalstorage.documents" -> {
                val partes = id.split(":", limit = 2)
                if (partes[0].equals("primary", true) && partes.size == 2) File(raizAlmacenamiento, partes[1]).absolutePath else null
            }
            "com.android.providers.downloads.documents" -> if (id.startsWith("raw:")) id.removePrefix("raw:") else null
            else -> null
        }
    }

    // ---------- ventana ----------
    fun colorBarras(claro: Boolean) {
        val color = Color.parseColor(if (claro) "#f4f4f7" else "#09090b")
        raiz.setBackgroundColor(color)
        web.setBackgroundColor(color)
        WindowCompat.getInsetsController(window, raiz).apply {
            isAppearanceLightStatusBars = claro
            isAppearanceLightNavigationBars = claro
        }
    }

    /** modo: 1 = entrar, 0 = salir, -1 = alternar. */
    fun pantallaCompleta(modo: Int) {
        completa = when (modo) { 1 -> true; 0 -> false; else -> !completa }
        barrasOcultas(completa)
    }

    private fun barrasOcultas(ocultas: Boolean) {
        WindowCompat.getInsetsController(window, raiz).apply {
            if (ocultas) {
                systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                hide(WindowInsetsCompat.Type.systemBars())
            } else show(WindowInsetsCompat.Type.systemBars())
        }
    }

    /** Pantalla completa del reproductor de Ver (la hace la interfaz con CSS): barras del sistema y giro. */
    fun modoVideo(activa: Boolean, horizontal: Boolean) {
        videoCompleto = activa
        barrasOcultas(activa || completa)
        requestedOrientation = if (activa && horizontal) ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        else ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
    }

    /** Log de la app (logcat de este proceso: Python, la interfaz y Android) a un archivo y «Compartir». */
    /** Texto del log: solo lo de la app (Python, la interfaz, avisos y errores), sin el ruido del sistema
     *  (GPU, pantalla, sensores…), con los tokens de las URLs ocultos. */
    private fun textoLog(): String {
        val filtros = arrayOf("python.stdout:V", "python.stderr:V", "JabsDLP-ui:V", "JabsDLP:V", "AndroidRuntime:V",
            "System.err:V", "libtorrent4j:V", "chromium:W", "cr_media:S", "*:S")
        val texto = Runtime.getRuntime().exec(arrayOf("logcat", "-d", "-v", "time", "--pid=${android.os.Process.myPid()}", *filtros))
            .inputStream.bufferedReader().use { it.readText() }
        val version = runCatching { packageManager.getPackageInfo(packageName, 0).versionName }.getOrNull() ?: "?"
        // El log propio de la app (jabsdlp/registro_app.py): LOCALAPPDATA/JabsDLP/logs
        val carpetaLog = File(filesDir, "local/JabsDLP/logs")
        val propio = listOf("jabsdlp-anterior.log" to "Sesión anterior", "jabsdlp.log.1" to "Sesión actual",
            "jabsdlp.log" to "Sesión actual").mapNotNull { (nombre, titulo) ->
            runCatching { File(carpetaLog, nombre).takeIf { it.isFile }?.readText()?.trim() }.getOrNull()
                ?.takeIf { it.isNotEmpty() }?.let { "===== $titulo =====\n$it" }
        }.joinToString("\n\n")
        return "JabsDLP $version · Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT}) · ${Build.MODEL}\n\n" +
            "########## Log de la app ##########\n" +
            ocultarTokens(propio).ifBlank { "(vacío: no ha pasado nada todavía o «Guardar log de la app» está apagado)" } +
            "\n\n########## Log del sistema (solo JabsDLP) ##########\n" +
            ocultarTokens(texto.takeLast(1_000_000)).ifBlank { "(sin mensajes)" }
    }

    /** Guarda el log en Descargas/JabsDLP para poder mandarlo por WhatsApp, correo, etc. Devuelve la ruta o "". */
    fun guardarLog(): String = try {
        val carpeta = Plataforma.carpetaDescargas().apply { mkdirs() }
        val fecha = java.text.SimpleDateFormat("yyyy-MM-dd_HH-mm", java.util.Locale.ROOT).format(java.util.Date())
        val archivo = File(carpeta, "jabsdlp-log-$fecha.txt")
        archivo.writeText(textoLog())
        Plataforma.escanear(archivo.absolutePath)   // que aparezca en Archivos y en «Adjuntar» de otras apps
        archivo.absolutePath
    } catch (e: Exception) {
        ""
    }

    fun compartirLog(): Boolean = try {
        val carpeta = File(cacheDir, "log").apply { mkdirs() }
        val archivo = File(carpeta, "jabsdlp-log.txt")
        archivo.writeText(textoLog())
        val uri = androidx.core.content.FileProvider.getUriForFile(this, "$packageName.archivos", archivo)
        val enviar = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_STREAM, uri)
            .putExtra(Intent.EXTRA_SUBJECT, "Log de JabsDLP").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        runOnUiThread { runCatching { startActivity(Intent.createChooser(enviar, "Compartir el log")) } }
        true
    } catch (e: Exception) {
        false
    }

    /** Como ocultar_tokens del PC: los parámetros de las URLs que suelen ser tokens o firmas no salen en el log. */
    private fun ocultarTokens(texto: String): String =
        Regex("""([?&](?:token|sig|signature|key|auth|access_token|policy|expires|hdnts|hmac|session)[^=&\s]*=)[^&\s"']+""",
            RegexOption.IGNORE_CASE).replace(texto) { it.groupValues[1] + "***" }

    private fun salirDeVideo() {
        vistaVideo?.let { raiz.removeView(it) }
        vistaVideo = null
        cerrarVideo?.onCustomViewHidden()
        cerrarVideo = null
        barrasOcultas(completa || videoCompleto)
    }

    // ---------- ventanita (picture in picture) ----------
    private var pipSonando = false
    private var pipSiguiente = false
    private var pipAuto = false
    private var pipProporcion = android.util.Rational(16, 9)
    private var receptorPip: android.content.BroadcastReceiver? = null

    private fun proporcion(ancho: Int, alto: Int): android.util.Rational {
        val r = ancho.coerceAtLeast(1).toDouble() / alto.coerceAtLeast(1)
        // Android solo admite entre 1:2,39 y 2,39:1
        return when {
            r > 2.39 -> android.util.Rational(239, 100)
            r < 1 / 2.39 -> android.util.Rational(100, 239)
            else -> android.util.Rational(ancho.coerceAtLeast(1), alto.coerceAtLeast(1))
        }
    }

    private fun accionPip(orden: String, icono: Int, titulo: String, codigo: Int): android.app.RemoteAction {
        val i = PendingIntent.getBroadcast(this, codigo, Intent(ACCION_PIP).setPackage(packageName).putExtra("orden", orden),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return android.app.RemoteAction(android.graphics.drawable.Icon.createWithResource(this, icono), titulo, titulo, i)
    }

    private fun parametrosPip(): android.app.PictureInPictureParams {
        val acciones = mutableListOf(accionPip("anterior", android.R.drawable.ic_media_previous, "Anterior", 40),
            if (pipSonando) accionPip("pausa", android.R.drawable.ic_media_pause, "Pausa", 41)
            else accionPip("play", android.R.drawable.ic_media_play, "Reproducir", 41))
        if (pipSiguiente) acciones.add(accionPip("siguiente", android.R.drawable.ic_media_next, "Siguiente", 42))
        val b = android.app.PictureInPictureParams.Builder().setAspectRatio(pipProporcion).setActions(acciones)
        if (Build.VERSION.SDK_INT >= 31) b.setAutoEnterEnabled(pipAuto).setSeamlessResizeEnabled(true)
        return b.build()
    }

    fun entrarPip(ancho: Int, alto: Int) {
        if (Build.VERSION.SDK_INT < 26) return
        pipProporcion = proporcion(ancho, alto)
        runCatching { enterPictureInPictureMode(parametrosPip()) }
    }

    fun estadoPip(json: String) {
        val d = runCatching { JSONObject(json) }.getOrNull() ?: return
        pipSonando = d.optBoolean("sonando")
        pipSiguiente = d.optBoolean("siguiente")
        pipAuto = d.optBoolean("auto")
        pipProporcion = proporcion(d.optInt("ancho", 16), d.optInt("alto", 9))
        if (Build.VERSION.SDK_INT >= 26) runCatching { setPictureInPictureParams(parametrosPip()) }
    }

    /** Android 8–11: entrar en la ventanita al salir de la app (en 12+ lo hace el sistema con setAutoEnterEnabled). */
    override fun onUserLeaveHint() {
        super.onUserLeaveHint()
        if (pipAuto && Build.VERSION.SDK_INT in 26..30) runCatching { enterPictureInPictureMode(parametrosPip()) }
    }

    override fun onPictureInPictureModeChanged(enPip: Boolean, nuevaConfig: android.content.res.Configuration) {
        super.onPictureInPictureModeChanged(enPip, nuevaConfig)
        if (enPip) { visible = true; web.dispatchWindowVisibilityChanged(View.VISIBLE) }
        if (enPip && receptorPip == null) {
            receptorPip = object : android.content.BroadcastReceiver() {
                override fun onReceive(c: Context?, i: Intent?) { i?.getStringExtra("orden")?.let { controlMusica(it) } }
            }
            androidx.core.content.ContextCompat.registerReceiver(this, receptorPip, android.content.IntentFilter(ACCION_PIP),
                androidx.core.content.ContextCompat.RECEIVER_NOT_EXPORTED)
        } else if (!enPip) {
            receptorPip?.let { runCatching { unregisterReceiver(it) } }
            receptorPip = null
        }
        web.evaluateJavascript("window.modoPip && modoPip($enPip)", null)
    }

    companion object {
        private const val ACCION_PIP = "com.jabsdlp.app.PIP"
        @Volatile private var actual: java.lang.ref.WeakReference<MainActivity>? = null
        /** La app está delante: solo entonces Android deja crear un servicio en primer plano. */
        @Volatile var visible = false

        /** La app está en segundo plano y ya no suena nada: la página pasa a oculta, como siempre. */
        fun ocultarPagina() {
            val a = actual?.get() ?: return
            a.runOnUiThread {
                if (!visible && !(Build.VERSION.SDK_INT >= 24 && a.isInPictureInPictureMode)) a.web.dispatchWindowVisibilityChanged(View.INVISIBLE)
            }
        }

        /** Botones de la notificación de música (y de los auriculares): se los pasa a la pestaña Ver. */
        fun controlMusica(orden: String, valor: Double? = null) {
            val a = actual?.get() ?: return
            a.runOnUiThread {
                // con la app en segundo plano, que la página siga «visible» para que Android deje sonar el video
                if (!visible && orden != "pausa") a.web.dispatchWindowVisibilityChanged(View.VISIBLE)
                a.web.evaluateJavascript("window.controlMusica && controlMusica(${JSONObject.quote(orden)}, ${valor ?: "null"})", null)
            }
        }
    }
}

/**
 * Android pausa los videos de una página que no se ve (app en segundo plano). Mientras suena algo con la
 * notificación de música, la página sigue creyéndose visible: el video sigue sonando (y pasa al siguiente)
 * con la pantalla apagada o en otra app. En pausa, o sin la notificación, se comporta como siempre.
 */
class WebViewJabs(contexto: android.content.Context) : WebView(contexto) {
    override fun onWindowVisibilityChanged(visibility: Int) {
        super.onWindowVisibilityChanged(if (ServicioMusica.mantener) View.VISIBLE else visibility)
    }
}


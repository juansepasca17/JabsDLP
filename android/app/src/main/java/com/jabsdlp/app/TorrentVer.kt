package com.jabsdlp.app

import org.json.JSONArray
import org.json.JSONObject
import org.libtorrent4j.Priority
import org.libtorrent4j.SessionHandle
import org.libtorrent4j.SessionManager
import org.libtorrent4j.SessionParams
import org.libtorrent4j.SettingsPack
import org.libtorrent4j.TorrentHandle
import org.libtorrent4j.TorrentInfo
import org.libtorrent4j.swig.settings_pack
import java.io.File
import java.util.concurrent.ConcurrentHashMap

/**
 * Torrents en la pestaña Ver (Android), con libtorrent4j: lo mismo que jabsdlp/ver_torrent.py hace en el PC con
 * libtorrent de Python. Lo usa jabsdlp_android/torrents.py; aquí solo están las operaciones de bajo nivel
 * (abrir, prioridad de piezas, ¿está la pieza?, estado y cerrar sin seguir compartiendo).
 */
object TorrentVer {
    private var sesion: SessionManager? = null
    private val activos = ConcurrentHashMap<String, TorrentHandle>()
    private val archivos = ConcurrentHashMap<String, Int>()

    private fun ajustes(subidaKb: Int): SettingsPack = SettingsPack()
        .uploadRateLimit(maxOf(1, subidaKb) * 1024)
        .listenInterfaces("0.0.0.0:0,[::]:0")
        .setBoolean(settings_pack.bool_types.enable_dht.swigValue(), true)
        .setBoolean(settings_pack.bool_types.enable_lsd.swigValue(), false)
        .setBoolean(settings_pack.bool_types.enable_upnp.swigValue(), false)
        .setBoolean(settings_pack.bool_types.enable_natpmp.swigValue(), false)
        // el límite es para el video que compartes, no para el protocolo (si no, la descarga se estrangula)
        .setBoolean(settings_pack.bool_types.rate_limit_ip_overhead.swigValue(), false)
        .setString(settings_pack.string_types.user_agent.swigValue(), "JabsDLP")

    @JvmStatic
    @Synchronized
    fun iniciar(subidaKb: Int) {
        val s = sesion
        if (s != null && s.isRunning) {
            s.applySettings(ajustes(subidaKb))
            return
        }
        sesion = SessionManager(false).also { it.start(SessionParams(ajustes(subidaKb))) }
    }

    @JvmStatic
    fun limiteSubida(kb: Int) {
        sesion?.applySettings(ajustes(kb))
    }

    /**
     * Abre un magnet o un archivo .torrent (ruta local) y prioriza solo `elegido` (lo decide Python con la lista
     * de archivos). Devuelve un JSON con la lista de archivos para que Python elija: ver [elegir].
     */
    @JvmStatic
    fun metadatos(origen: String, carpeta: String, esperaSeg: Int): String {
        val s = sesion ?: return JSONObject().put("error", "sesión no iniciada").toString()
        File(carpeta).mkdirs()
        val datos: ByteArray? = if (origen.startsWith("magnet:", true)) s.fetchMagnet(origen, esperaSeg, File(carpeta))
            else File(origen).readBytes()
        if (datos == null) return JSONObject().put("error", "sin_metadatos").toString()
        val ti = TorrentInfo(datos)
        val fs = ti.files()
        val lista = JSONArray()
        for (i in 0 until fs.numFiles()) {
            lista.put(JSONObject().put("ruta", fs.filePath(i)).put("tamano", fs.fileSize(i)).put("inicio", fs.fileOffset(i)))
        }
        // se guarda el .torrent para no volver a pedir la información al elegir el archivo
        File(carpeta, ".torrent").writeBytes(datos)
        return JSONObject().put("archivos", lista).put("pieza", ti.pieceLength()).put("piezas", ti.numPieces())
            .put("nombre", ti.name()).toString()
    }

    /** Empieza a descargar solo los archivos `prioritarios` (índices) en `carpeta`. Devuelve la clave o "". */
    @JvmStatic
    fun descargar(clave: String, carpeta: String, prioritarios: IntArray, elegido: Int): String {
        val s = sesion ?: return ""
        val ti = TorrentInfo(File(carpeta, ".torrent"))
        val prioridades = Array(ti.files().numFiles()) { Priority.IGNORE }
        prioritarios.forEach { if (it in prioridades.indices) prioridades[it] = Priority.TOP_PRIORITY }
        s.download(ti, File(carpeta), null, prioridades, null, org.libtorrent4j.swig.torrent_flags_t())
        val h = s.find(ti.infoHash()) ?: return ""
        h.resume()
        activos[clave] = h
        archivos[clave] = elegido
        return clave
    }

    @JvmStatic
    fun prioridad(clave: String, pieza: Int, plazoMs: Int) {
        activos[clave]?.setPieceDeadline(pieza, plazoMs)
    }

    @JvmStatic
    fun olvidarPrioridades(clave: String) {
        activos[clave]?.clearPieceDeadlines()
    }

    @JvmStatic
    fun tienePieza(clave: String, pieza: Int): Boolean = activos[clave]?.havePiece(pieza) ?: false

    @JvmStatic
    fun estado(clave: String): String {
        val h = activos[clave] ?: return ""
        val st = h.status()
        val progreso = runCatching { h.fileProgress()[archivos[clave] ?: 0] }.getOrDefault(0L)
        return JSONObject().put("pares", st.numPeers()).put("semillas", st.numSeeds())
            .put("bajada", st.downloadPayloadRate()).put("subida", st.uploadPayloadRate())
            .put("descargado", progreso).toString()
    }

    /** Quita el torrent sin seguir compartiendo y borra lo descargado. */
    @JvmStatic
    fun cerrar(clave: String) {
        val h = activos.remove(clave) ?: return
        archivos.remove(clave)
        runCatching { sesion?.remove(h, SessionHandle.DELETE_FILES) }
    }

    @JvmStatic
    fun cerrarTodo() {
        activos.keys.toList().forEach { cerrar(it) }
    }
}

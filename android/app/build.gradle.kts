import java.io.File

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

// ---------------------------------------------------------------------------------------------
// La interfaz (ui/) y la lógica (jabsdlp/) son las del PC: no se copian al repo, se toman de la raíz
// en cada compilación. Así una versión nueva de PC pasa a Android sin tocar esta carpeta.
// ---------------------------------------------------------------------------------------------
val raizPc: File = rootDir.parentFile
val generado: File = layout.buildDirectory.dir("generated/pc").get().asFile

fun espejo(origen: File, destino: File) {
    require(origen.isDirectory) { "No se encuentra ${origen.path}: compila desde el repo completo de JabsDLP." }
    destino.deleteRecursively()
    origen.copyRecursively(destino, overwrite = true)
    destino.walkBottomUp().filter { it.name == "__pycache__" || it.extension == "pyc" }.forEach { it.deleteRecursively() }
}

espejo(File(raizPc, "jabsdlp"), File(generado, "python/jabsdlp"))
espejo(File(raizPc, "ui"), File(generado, "assets/ui"))
File(generado, "assets/android").apply {
    mkdirs()
    listOf("funciones.txt", "solo_pc.txt").forEach { File(rootDir, it).copyTo(File(this, it), overwrite = true) }
}

// ffmpeg, ffprobe y qjs compilados para Android (android/scripts/compilar_nativos.sh)
val nativos: File = File(System.getenv("JABSDLP_NATIVOS") ?: File(rootDir, "nativos").path)

android {
    namespace = "com.jabsdlp.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.jabsdlp.app"
        minSdk = 24
        targetSdk = 35
        // Mismo número que la versión de PC. versionCode: 1.7.6 -> 10706
        versionName = "1.7.6"
        versionCode = 10706
        // Python 3.12+ en Android solo existe para 64 bits. El APK publicado es arm64-v8a;
        // JABSDLP_ABIS=x86_64 compila uno para el emulador del PC (ver PORTAR.md).
        ndk { abiFilters += (System.getenv("JABSDLP_ABIS") ?: "arm64-v8a").split(",").map { it.trim() } }
    }

    signingConfigs {
        create("jabsdlp") {
            val almacen = System.getenv("JABSDLP_KEYSTORE")
            if (almacen != null && File(almacen).isFile) {
                storeFile = File(almacen)
                storePassword = System.getenv("JABSDLP_KEYSTORE_PASS")
                keyAlias = System.getenv("JABSDLP_KEY_ALIAS")
                keyPassword = System.getenv("JABSDLP_KEY_PASS") ?: System.getenv("JABSDLP_KEYSTORE_PASS")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            val firma = signingConfigs.getByName("jabsdlp")
            signingConfig = if (firma.storeFile != null) firma else signingConfigs.getByName("debug")
        }
    }

    sourceSets {
        getByName("main") {
            assets.srcDir(File(generado, "assets"))
            jniLibs.srcDir(nativos)
        }
    }

    packaging {
        // Los binarios tienen que quedar como archivos en nativeLibraryDir para poder ejecutarlos
        jniLibs { useLegacyPackaging = true }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    lint {
        checkReleaseBuilds = false
        abortOnError = false
    }
}

chaquopy {
    defaultConfig {
        version = "3.13"
        System.getenv("JABSDLP_BUILD_PYTHON")?.let { buildPython(it) }
        pip { install("-r", "../requirements-android.txt") }
    }
    sourceSets {
        getByName("main") { srcDir(File(generado, "python")) }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.webkit:webkit:1.12.1")
    // Ver torrents en la pestaña Ver (libtorrent con bindings para Java; las .so se filtran por abiFilters)
    implementation("org.libtorrent4j:libtorrent4j:2.1.0-39")
    implementation("org.libtorrent4j:libtorrent4j-android-arm64:2.1.0-39")
    implementation("org.libtorrent4j:libtorrent4j-android-x86_64:2.1.0-39")
}

#!/usr/bin/env bash
# Compila para Android (arm64-v8a) los programas que JabsDLP ejecuta:
#   ffmpeg y ffprobe  (con x264, LAME y mbedTLS para https)  -> libffmpeg.so, libffprobe.so
#   qjs (QuickJS-ng), el motor de JavaScript que resuelve los retos de YouTube -> libqjs.so
#   aria2c (con OpenSSL), para descargar torrents -> libaria2c.so (opcional: si no compila, se sigue sin él)
# Se guardan con nombre lib*.so en android/nativos/<abi>/ para que el APK los ponga en nativeLibraryDir,
# la única carpeta desde la que Android deja ejecutar programas.
#
# Uso: android/scripts/compilar_nativos.sh <ruta del NDK> [carpeta de salida] [ABI]
#   ABI: arm64-v8a (por defecto, la del APK publicado) o x86_64 (solo para probar en el emulador del PC).
#   Varias separadas por comas: arm64-v8a,x86_64
# En GitHub Actions el resultado se guarda en caché: solo se recompila si cambia este archivo.
set -euo pipefail

NDK="${1:?Uso: compilar_nativos.sh <ruta del NDK> [salida] [ABI]}"
SALIDA="$(realpath -m "${2:-$(dirname "$0")/../nativos}")"
ABIS="${3:-arm64-v8a}"
if [[ "$ABIS" == *,* ]]; then
  for una in ${ABIS//,/ }; do bash "$0" "$NDK" "$SALIDA" "$una"; done
  exit 0
fi
API=24
ABI="$ABIS"
case "$ABI" in
  arm64-v8a) TRIPLE=aarch64-linux-android; FF_ARCH=(--arch=aarch64 --cpu=armv8-a); SIN_ASM=() ;;
  # x86_64 solo se usa en el emulador: sin ensamblador (evita reubicaciones de texto; la velocidad da igual)
  x86_64) TRIPLE=x86_64-linux-android; FF_ARCH=(--arch=x86_64); SIN_ASM=(--disable-asm) ;;
  *) echo "ABI no soportada: $ABI (usa arm64-v8a o x86_64)"; exit 1 ;;
esac

FFMPEG_VER=8.1.2
MBEDTLS_VER=3.6.6
LAME_VER=3.100
QJS_VER=0.17.0
X264_RAMA=stable

TC="$NDK/toolchains/llvm/prebuilt/linux-x86_64"
CC="$TC/bin/${TRIPLE}${API}-clang"
CXX="$TC/bin/${TRIPLE}${API}-clang++"
AR="$TC/bin/llvm-ar"
RANLIB="$TC/bin/llvm-ranlib"
STRIP="$TC/bin/llvm-strip"
NM="$TC/bin/llvm-nm"
TOOLCHAIN_CMAKE="$NDK/build/cmake/android.toolchain.cmake"
NUCLEOS="$(nproc)"
# Páginas de 16 KB (Android 15+): binarios alineados para que funcionen en cualquier teléfono nuevo
LDFLAGS_16K="-Wl,-z,max-page-size=16384"

TRABAJO="$(mktemp -d)"
DEPS="$TRABAJO/deps"
mkdir -p "$DEPS" "$SALIDA/$ABI"
trap 'rm -rf "$TRABAJO"' EXIT
cd "$TRABAJO"

bajar() {  # bajar <url> <archivo>
  curl -fsSL --retry 4 --retry-delay 5 -o "$2" "$1"
}

echo "::group::mbedTLS $MBEDTLS_VER"
bajar "https://github.com/Mbed-TLS/mbedtls/releases/download/mbedtls-$MBEDTLS_VER/mbedtls-$MBEDTLS_VER.tar.bz2" mbedtls.tar.bz2
tar xf mbedtls.tar.bz2
cmake -S "mbedtls-$MBEDTLS_VER" -B mbedtls-build \
  -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN_CMAKE" -DANDROID_ABI=$ABI -DANDROID_PLATFORM=android-$API \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$DEPS" -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DENABLE_TESTING=OFF -DENABLE_PROGRAMS=OFF -DUSE_SHARED_MBEDTLS_LIBRARY=OFF -DUSE_STATIC_MBEDTLS_LIBRARY=ON \
  -DMBEDTLS_FATAL_WARNINGS=OFF
cmake --build mbedtls-build -j"$NUCLEOS"
cmake --install mbedtls-build
echo "::endgroup::"

echo "::group::LAME $LAME_VER"
bajar "https://downloads.sourceforge.net/project/lame/lame/$LAME_VER/lame-$LAME_VER.tar.gz" lame.tar.gz
tar xf lame.tar.gz
(
  cd "lame-$LAME_VER"
  # config.sub de 2017: se usa el de automake del sistema si existe (reconoce *-linux-android)
  for f in config.sub config.guess; do
    [ -f "/usr/share/misc/$f" ] && cp "/usr/share/misc/$f" "$f" || true
  done
  CC="$CC" AR="$AR" RANLIB="$RANLIB" CFLAGS="-O2 -fPIC" \
    ./configure --host=$TRIPLE --prefix="$DEPS" --enable-static --disable-shared \
      --disable-frontend --disable-decoder --disable-gtktest --disable-analyzer-hooks
  make -j"$NUCLEOS"
  make install
)
echo "::endgroup::"

echo "::group::x264 ($X264_RAMA)"
git clone --depth 1 --branch "$X264_RAMA" https://code.videolan.org/videolan/x264.git x264
(
  cd x264
  configurar() {
    CC="$CC" ./configure --host=$TRIPLE --cross-prefix="$TC/bin/llvm-" --sysroot="$TC/sysroot" \
      --prefix="$DEPS" --enable-static --enable-pic --disable-cli --disable-opencl "$@"
  }
  # Con ensamblador es mucho más rápido; si el NDK no lo acepta, se compila sin él
  if [ ${#SIN_ASM[@]} -gt 0 ]; then configurar --disable-asm
  else configurar || { echo "x264: se reintenta sin ensamblador"; make distclean >/dev/null 2>&1 || true; configurar --disable-asm; }; fi
  make -j"$NUCLEOS"
  make install-lib-static
)
echo "::endgroup::"

# dav1d: decodificador AV1 por software (YouTube da casi todo en AV1 y el decodificador propio de FFmpeg
# solo funciona con aceleración por hardware). Opcional: sin él, ffmpeg sale igual pero sin AV1.
DAV1D_VER=1.5.1
EXTRA_FF=()
compilar_dav1d() {
  command -v meson >/dev/null && command -v ninja >/dev/null || { echo "dav1d: faltan meson y ninja"; return 1; }
  bajar "https://downloads.videolan.org/pub/videolan/dav1d/$DAV1D_VER/dav1d-$DAV1D_VER.tar.xz" dav1d.tar.xz
  tar xf dav1d.tar.xz
  case "$ABI" in arm64-v8a) familia=aarch64 ;; x86_64) familia=x86_64 ;; esac
  cat > dav1d-cross.txt <<FIN
[binaries]
c = '$CC'
ar = '$AR'
strip = '$STRIP'
[host_machine]
system = 'android'
cpu_family = '$familia'
cpu = '$familia'
endian = 'little'
FIN
  asm=true; [ ${#SIN_ASM[@]} -gt 0 ] && asm=false
  meson setup dav1d-build "dav1d-$DAV1D_VER" --cross-file dav1d-cross.txt --buildtype=release \
    --default-library=static --prefix="$DEPS" --libdir=lib -Denable_tools=false -Denable_tests=false -Denable_asm=$asm
  ninja -C dav1d-build
  ninja -C dav1d-build install
}
echo "::group::dav1d $DAV1D_VER"
if compilar_dav1d; then EXTRA_FF=(--enable-libdav1d); else echo "::warning::dav1d no se pudo compilar: ffmpeg sin AV1."; fi
echo "::endgroup::"

echo "::group::FFmpeg $FFMPEG_VER"
bajar "https://ffmpeg.org/releases/ffmpeg-$FFMPEG_VER.tar.xz" ffmpeg.tar.xz
tar xf ffmpeg.tar.xz
(
  cd "ffmpeg-$FFMPEG_VER"
  export PKG_CONFIG_LIBDIR="$DEPS/lib/pkgconfig"
  export PKG_CONFIG_PATH="$DEPS/lib/pkgconfig"
  ./configure \
    --prefix="$TRABAJO/ffmpeg-out" \
    --target-os=android "${FF_ARCH[@]}" ${SIN_ASM[@]+"${SIN_ASM[@]}"} --enable-cross-compile \
    --cc="$CC" --cxx="$CXX" --ar="$AR" --ranlib="$RANLIB" --nm="$NM" --strip="$STRIP" \
    --sysroot="$TC/sysroot" --pkg-config=pkg-config --pkg-config-flags=--static \
    --extra-cflags="-I$DEPS/include -O2 -fPIC" \
    --extra-ldflags="-L$DEPS/lib $LDFLAGS_16K" \
    --extra-libs="-lm" \
    --enable-gpl --enable-version3 \
    --enable-static --disable-shared --enable-pic \
    --disable-autodetect --enable-zlib \
    --enable-libx264 --enable-libmp3lame --enable-mbedtls ${EXTRA_FF[@]+"${EXTRA_FF[@]}"} \
    --enable-ffmpeg --enable-ffprobe --disable-ffplay \
    --disable-doc --disable-debug --disable-indevs --disable-outdevs \
    || { tail -n 80 ffbuild/config.log; exit 1; }
  make -j"$NUCLEOS"
  make install
)
cp "$TRABAJO/ffmpeg-out/bin/ffmpeg" "$SALIDA/$ABI/libffmpeg.so"
cp "$TRABAJO/ffmpeg-out/bin/ffprobe" "$SALIDA/$ABI/libffprobe.so"
echo "::endgroup::"

echo "::group::QuickJS-ng $QJS_VER"
bajar "https://github.com/quickjs-ng/quickjs/archive/refs/tags/v$QJS_VER.tar.gz" qjs.tar.gz
tar xf qjs.tar.gz
cmake -S "quickjs-$QJS_VER" -B qjs-build \
  -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN_CMAKE" -DANDROID_ABI=$ABI -DANDROID_PLATFORM=android-$API \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DQJS_BUILD_EXAMPLES=OFF \
  -DCMAKE_EXE_LINKER_FLAGS="$LDFLAGS_16K"
cmake --build qjs-build --target qjs_exe -j"$NUCLEOS"
QJS="$(find qjs-build -maxdepth 2 -type f -name qjs | head -n1)"
[ -n "$QJS" ] || { echo "No se encontró el binario qjs"; exit 1; }
cp "$QJS" "$SALIDA/$ABI/libqjs.so"
echo "::endgroup::"

# aria2 (descargar torrents) con OpenSSL. Opcional: si no compila, el APK sale igual y los torrents
# muestran un mensaje claro en lugar de fallar.
compilar_aria2() {
  echo "::group::OpenSSL $OPENSSL_VER + aria2 $ARIA2_VER"
  bajar "https://github.com/openssl/openssl/releases/download/openssl-$OPENSSL_VER/openssl-$OPENSSL_VER.tar.gz" openssl.tar.gz
  tar xf openssl.tar.gz
  (
    cd "openssl-$OPENSSL_VER"
    export ANDROID_NDK_ROOT="$NDK" PATH="$TC/bin:$PATH"
    case "$ABI" in arm64-v8a) objetivo=android-arm64 ;; x86_64) objetivo=android-x86_64 ;; esac
    ./Configure "$objetivo" -D__ANDROID_API__=$API no-shared no-tests no-docs no-apps no-engine no-dso --prefix="$DEPS" --libdir=lib
    make -j"$NUCLEOS" build_libs
    make install_dev
  )
  bajar "https://github.com/aria2/aria2/releases/download/release-$ARIA2_VER/aria2-$ARIA2_VER.tar.xz" aria2.tar.xz
  tar xf aria2.tar.xz
  (
    cd "aria2-$ARIA2_VER"
    PKG_CONFIG_LIBDIR="$DEPS/lib/pkgconfig" PKG_CONFIG_PATH="$DEPS/lib/pkgconfig" \
    CC="$CC" CXX="$CXX" AR="$AR" RANLIB="$RANLIB" \
    CPPFLAGS="-I$DEPS/include" CXXFLAGS="-O2 -fPIC" CFLAGS="-O2 -fPIC" \
    LDFLAGS="-L$DEPS/lib -static-libstdc++ $LDFLAGS_16K" LIBS="-ldl" \
      ./configure --host=$TRIPLE --prefix="$TRABAJO/aria2-out" --disable-nls --disable-shared \
        --with-openssl --without-gnutls --without-libnettle --without-libgmp --without-libgcrypt \
        --without-libxml2 --without-libexpat --without-sqlite3 --without-libssh2 --without-libcares --without-libz
    # (los certificados para https los toma de SSL_CERT_FILE, que arranque.py apunta al cacert.pem de certifi)
    make -j"$NUCLEOS"
  )
  cp "aria2-$ARIA2_VER/src/aria2c" "$SALIDA/$ABI/libaria2c.so"
  echo "::endgroup::"
}
OPENSSL_VER=3.5.4
ARIA2_VER=1.37.0
compilar_aria2 || { echo "::warning::aria2 no se pudo compilar para $ABI: el APK sale sin torrents."; rm -f "$SALIDA/$ABI/libaria2c.so"; }

"$STRIP" "$SALIDA/$ABI/"*.so
chmod 755 "$SALIDA/$ABI/"*.so
echo "Listo: ffmpeg $FFMPEG_VER (GPL v3 con x264, LAME $LAME_VER, mbedTLS $MBEDTLS_VER), quickjs-ng $QJS_VER y aria2 $ARIA2_VER (OpenSSL $OPENSSL_VER) para $ABI"
ls -la "$SALIDA/$ABI"
file "$SALIDA/$ABI/"*.so || true

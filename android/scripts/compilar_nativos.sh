#!/usr/bin/env bash
# Compila para Android (arm64-v8a) los programas que JabsDLP ejecuta:
#   ffmpeg y ffprobe  (con x264, LAME y mbedTLS para https)  -> libffmpeg.so, libffprobe.so
#   qjs (QuickJS-ng), el motor de JavaScript que resuelve los retos de YouTube -> libqjs.so
# Se guardan con nombre lib*.so en android/nativos/<abi>/ para que el APK los ponga en nativeLibraryDir,
# la única carpeta desde la que Android deja ejecutar programas.
#
# Uso: android/scripts/compilar_nativos.sh <ruta del NDK> [carpeta de salida]
# En GitHub Actions el resultado se guarda en caché: solo se recompila si cambia este archivo.
set -euo pipefail

NDK="${1:?Uso: compilar_nativos.sh <ruta del NDK> [salida]}"
SALIDA="$(realpath -m "${2:-$(dirname "$0")/../nativos}")"
API=24
ABI=arm64-v8a
TRIPLE=aarch64-linux-android

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
  configurar || { echo "x264: se reintenta sin ensamblador"; make distclean >/dev/null 2>&1 || true; configurar --disable-asm; }
  make -j"$NUCLEOS"
  make install-lib-static
)
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
    --target-os=android --arch=aarch64 --cpu=armv8-a --enable-cross-compile \
    --cc="$CC" --cxx="$CXX" --ar="$AR" --ranlib="$RANLIB" --nm="$NM" --strip="$STRIP" \
    --sysroot="$TC/sysroot" --pkg-config=pkg-config --pkg-config-flags=--static \
    --extra-cflags="-I$DEPS/include -O2 -fPIC" \
    --extra-ldflags="-L$DEPS/lib $LDFLAGS_16K" \
    --extra-libs="-lm" \
    --enable-gpl --enable-version3 \
    --enable-static --disable-shared --enable-pic \
    --disable-autodetect --enable-zlib \
    --enable-libx264 --enable-libmp3lame --enable-mbedtls \
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

"$STRIP" "$SALIDA/$ABI/"*.so
chmod 755 "$SALIDA/$ABI/"*.so
echo "Listo: ffmpeg $FFMPEG_VER (GPL v3 con x264, LAME $LAME_VER, mbedTLS $MBEDTLS_VER) y quickjs-ng $QJS_VER para $ABI"
ls -la "$SALIDA/$ABI"
file "$SALIDA/$ABI/"*.so || true

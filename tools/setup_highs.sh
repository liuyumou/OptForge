#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
native_root="$(pwd)/target/native/highs-1.11.0"
archive="$native_root/source.tar.gz"
source_dir="$native_root/HiGHS-1.11.0"
expected=2b44b074cf41439325ce4d0bbdac2d51379f56faf17ba15320a410d3c1f07275
mkdir -p "$native_root"
exec 9>"$native_root/build.lock"
flock --exclusive 9
if [[ ! -f "$archive" ]]; then
    curl --fail --location --retry 2 --connect-timeout 20 --max-time 180 \
        https://codeload.github.com/ERGO-Code/HiGHS/tar.gz/refs/tags/v1.11.0 \
        --output "$archive.partial"
    mv "$archive.partial" "$archive"
fi
printf '%s  %s\n' "$expected" "$archive" | sha256sum --check --status
if [[ ! -f "$source_dir/CMakeLists.txt" ]]; then
    tar -xzf "$archive" -C "$native_root"
fi
cmake -S "$source_dir" -B "$native_root/build" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$native_root/install" \
    -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -DBUILD_EXAMPLES=OFF \
    -DBUILD_CXX_EXE=ON -DHIGHSINT64=OFF -DZLIB=OFF \
    -DCUPDLP_GPU=OFF -DCUPDLP_FIND_CUDA=OFF
cmake --build "$native_root/build" --parallel 4
cmake --install "$native_root/build"

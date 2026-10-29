#!/usr/bin/env bash
# Builds one SDK's dump program and runs the conformance suite against it.
#
#   conformance/run.sh <typescript|python|ruby|java|csharp|rust|php|go>
#
# Expects that language's toolchain on PATH, and the SDK's own dependencies
# installable (npm, Maven, NuGet, Cargo, Go modules, Composer).
set -euo pipefail

lang="${1:?usage: run.sh <lang>}"
here="$(cd "$(dirname "$0")" && pwd)"
root="$(dirname "$here")"
cd "$here"

case "$lang" in
  typescript)
    (cd "$root/ts" && npm ci --no-audit --no-fund && npm run build)
    cmd=(node dumps/typescript/dump.mjs)
    ;;
  python)
    cmd=(env "PYTHONPATH=$root/python/src" python3 dumps/python/dump.py)
    ;;
  ruby)
    cmd=(ruby -w -I "$root/ruby/lib" dumps/ruby/dump.rb)
    ;;
  java)
    mvn -q -B -f "$root/java/pom.xml" package
    mvn -q -B -f "$root/java/pom.xml" dependency:build-classpath -Dmdep.outputFile="$here/dumps/java/deps.cp"
    jar=("$root"/java/target/bulk-instances-*[0-9].jar)
    cp="${jar[0]}:$(cat dumps/java/deps.cp)"
    javac -Xlint:all -Werror -d dumps/java/classes -cp "$cp" dumps/java/Dump.java
    cmd=(java -cp "dumps/java/classes:$cp" Dump)
    ;;
  csharp)
    # DOTNET_TFM picks which of the library's targets the dump runs against.
    tfm="${DOTNET_TFM:-net10.0}"
    dotnet build dumps/csharp -c Release -nologo -v q -p:DumpTfm="$tfm"
    cmd=(dotnet "dumps/csharp/bin/Release/$tfm/Dump.dll")
    ;;
  rust)
    cargo build --quiet --manifest-path dumps/rust/Cargo.toml
    cmd=(dumps/rust/target/debug/dump)
    ;;
  php)
    "${COMPOSER_BIN:-composer}" install --quiet --no-interaction --working-dir=dumps/php
    cmd=(php dumps/php/dump.php)
    ;;
  go)
    (cd dumps/go && go build -o dump .)
    cmd=(dumps/go/dump)
    ;;
  *)
    echo "unknown language: $lang" >&2
    exit 2
    ;;
esac

exec python3 suite.py "$lang" -- "${cmd[@]}"

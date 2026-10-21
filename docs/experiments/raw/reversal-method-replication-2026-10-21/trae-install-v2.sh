#!/bin/sh
# Generated from ide/trae-x ec6d339163f00b31339568beb79cd449c1cdd0b2; edit scripts/distribution-install instead.

set -eu

DEFAULT_CHANNEL='public'
DEFAULT_BASE_URL='https://lf-cdn.trae.com.cn/obj/trae-com-cn/trae-cli'
LEGACY_BASE_URL=''
# Normalize historical internal inputs once, before the shared install flow.
if [ "$DEFAULT_CHANNEL" = internal ]; then
    TRAECLI_CHANNEL="${TRAECLI_CHANNEL:-internal}"
    TRAECLI_RELEASE_CHANNEL="${TRAECLI_RELEASE_CHANNEL:-${TRAEX_INSTALL_CHANNEL:-stable}}"
    TRAECLI_VERSION="${TRAECLI_VERSION:-${TRAEX_VERSION:-latest}}"
    TRAECLI_INSTALL_DIR="${TRAECLI_INSTALL_DIR:-${TRAEX_INSTALL_DIR:-$HOME/.local/bin}}"
    TRAECLI_STATE_DIR="${TRAECLI_STATE_DIR:-${TRAEX_STATE_DIR:-$HOME/.local/share/traex}}"
    TRAECLI_DOWNLOAD_BASE_URL="${TRAECLI_DOWNLOAD_BASE_URL:-${TRAEX_TOS_BASE_URL:-${TRAEX_UPDATE_BASE_URL:-${TRAEX_RESOURCE_URL:-$DEFAULT_BASE_URL}}}}"
    LEGACY_BASE_URL="${TRAEX_LEGACY_TOS_BASE_URL:-$LEGACY_BASE_URL}"
fi

OFFLINE_DIR="${TRAECLI_OFFLINE_BUNDLE_DIR:-}"
if [ -z "$OFFLINE_DIR" ] && [ -f "$0" ]; then
    SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
    if [ -f "$SCRIPT_DIR/offline-manifest.json" ]; then
        OFFLINE_DIR=$SCRIPT_DIR
    fi
fi
if [ -n "$OFFLINE_DIR" ]; then
    OFFLINE_DIR=$(CDPATH= cd -- "$OFFLINE_DIR" && pwd)
    [ -f "$OFFLINE_DIR/offline-manifest.json" ] || {
        printf '%s\n' "[ERROR] offline-manifest.json is missing from $OFFLINE_DIR" >&2
        exit 1
    }
fi
BASE_URL="${TRAECLI_DOWNLOAD_BASE_URL:-$DEFAULT_BASE_URL}"
BASE_URL="${BASE_URL%/}"
if [ -n "$OFFLINE_DIR" ]; then
    if command -v python3 >/dev/null 2>&1; then
        offline_channel=$(OFFLINE_MANIFEST="$OFFLINE_DIR/offline-manifest.json" python3 - <<'PY' 2>/dev/null
import json
import os

channel = json.load(open(os.environ["OFFLINE_MANIFEST"], encoding="utf-8")).get("channel")
if isinstance(channel, str):
    print(channel)
PY
        ) || {
            printf '%s\n' "[ERROR] failed to read bundled release metadata" >&2
            exit 1
        }
    else
        offline_channel=$(sed -n 's/.*"channel"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$OFFLINE_DIR/offline-manifest.json" | head -n 1)
    fi
    CHANNEL="${TRAECLI_CHANNEL:-$offline_channel}"
    case "$CHANNEL" in
        private|private-alpha|tob-private|tob-private-alpha) ;;
        *)
            printf '%s\n' "[ERROR] offline bundles require TRAECLI_CHANNEL=tob-private or tob-private-alpha" >&2
            exit 1
            ;;
    esac
else
    CHANNEL="${TRAECLI_CHANNEL:-$DEFAULT_CHANNEL}"
fi
VERSION="${TRAECLI_VERSION:-latest}"
INSTALL_DIR="${TRAECLI_INSTALL_DIR:-${XDG_BIN_HOME:-$HOME/.local/bin}}"
STATE_DIR="${TRAECLI_STATE_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/traecli}"
RELEASES_DIR="${TRAEX_RELEASES_DIR:-$STATE_DIR/releases}"
CURRENT_LINK="$STATE_DIR/current"
INSTALL_LOCK_DIR="$STATE_DIR/install.lock"
ASSUME_YES="${TRAECLI_INSTALL_ASSUME_YES:-${TRAEX_INSTALL_ASSUME_YES:-${ASSUME_YES:-}}}"
MIGRATE_BREW="${TRAECLI_INSTALL_MIGRATE_BREW:-${TRAEX_INSTALL_MIGRATE_BREW:-1}}"
REMOVE_BREW="${TRAECLI_INSTALL_REMOVE_BREW:-${TRAEX_INSTALL_REMOVE_BREW:-}}"
REMOVE_COCO="${TRAECLI_INSTALL_REMOVE_COCO:-${TRAEX_INSTALL_REMOVE_COCO:-auto}}"
INSTALL_RG="${TRAECLI_INSTALL_RG:-${TRAEX_INSTALL_RG:-auto}}"
REQUIRE_RG="${TRAECLI_REQUIRE_RG:-${TRAEX_REQUIRE_RG:-}}"
INSTALL_BWRAP="${TRAECLI_INSTALL_BWRAP:-${TRAEX_INSTALL_BWRAP:-auto}}"
REQUIRE_BWRAP="${TRAECLI_REQUIRE_BWRAP:-${TRAEX_REQUIRE_BWRAP:-}}"
BINARY_NAME="traex"
CODE_MODE_HOST_NAME="traex-code-mode-host"
RELEASE_LEASE_PROBE_ARG="--trae-probe-release-lease"
RELEASE_CLEANUP_ARG="--trae-cleanup-managed-releases"
COMPAT_NAMES="traecli trae-cli trae-agent ta"
COCO_BINARY_NAMES="coco trae-cli"
COCO_ALIAS_NAMES="traecli trae-agent ta"
LEGACY_FORMULA_NAMES="traex"

info() { printf '%s\n' "[INFO] $*"; }
warn() { printf '%s\n' "[WARN] $*" >&2; }
die() { printf '%s\n' "[ERROR] $*" >&2; exit 1; }

is_yes() {
    case "${1:-}" in
        [Yy]|[Yy][Ee][Ss]|1|true|TRUE) return 0 ;;
        *) return 1 ;;
    esac
}

is_no() {
    case "${1:-}" in
        [Nn]|[Nn][Oo]|0|false|FALSE) return 0 ;;
        *) return 1 ;;
    esac
}

prompt_yes_no() {
    prompt=$1
    default=${2:-N}
    if is_yes "$ASSUME_YES"; then
        return 0
    fi
    if ! ( : < /dev/tty ) >/dev/null 2>&1; then
        [ "$default" = Y ]
        return $?
    fi
    if [ "$default" = Y ]; then
        printf '%s [Y/n] ' "$prompt" > /dev/tty
    else
        printf '%s [y/N] ' "$prompt" > /dev/tty
    fi
    read -r reply < /dev/tty || reply=""
    if [ -z "$reply" ]; then
        [ "$default" = Y ]
        return $?
    fi
    case "$reply" in
        [Yy]|[Yy][Ee][Ss]) return 0 ;;
        *) return 1 ;;
    esac
}

if [ -z "$OFFLINE_DIR" ]; then
    case "$BASE_URL" in
        https://*) ;;
        *) die "TRAECLI_DOWNLOAD_BASE_URL must use https" ;;
    esac
    base_url_host=$(printf '%s\n' "$BASE_URL" \
        | sed -n 's#^https://\([^/:]*\).*#\1#p' \
        | tr '[:upper:]' '[:lower:]')
    if [ "$CHANNEL" != internal ]; then
    case "$base_url_host" in
        code.byted.org|byted.org|*.byted.org|bytedance.net|*.bytedance.net|bytedance.com|*.bytedance.com|byteintl.net|*.byteintl.net|tosv-myabc*|*trae-common-2-asiasebd*)
            die "TRAECLI_DOWNLOAD_BASE_URL must not use an internal endpoint"
            ;;
    esac
    fi
    command -v curl >/dev/null 2>&1 || die "curl is required"
fi
command -v gzip >/dev/null 2>&1 || command -v gunzip >/dev/null 2>&1 || die "gzip or gunzip is required"

# Legacy selectors are accepted only at the installer boundary.
offline_track=
if [ -n "$OFFLINE_DIR" ]; then
    offline_track=$(sed -n 's/.*"release_channel"[[:space:]]*:[[:space:]]*"\([^" ]*\)".*/\1/p' "$OFFLINE_DIR/offline-manifest.json" | head -n 1)
fi
RELEASE_CHANNEL="${TRAECLI_RELEASE_CHANNEL:-${offline_track:-stable}}"
case "$CHANNEL" in
    public-alpha|private-alpha|tob-alpha|tob-private-alpha) RELEASE_CHANNEL=alpha ;;
esac
case "$RELEASE_CHANNEL" in stable|alpha) ;; *) die "invalid release channel" ;; esac
case "$CHANNEL" in
    internal)
        [ "$DEFAULT_CHANNEL" = internal ] || die "this entrypoint does not configure an internal source"
        [ -z "$OFFLINE_DIR" ] || die "internal does not accept private offline bundles"
        DELIVERY_CHANNEL=internal
        MANIFEST_CHANNEL=internal
        metadata_prefix=
        ;;
    public|public-alpha)
        DELIVERY_CHANNEL=public
        MANIFEST_CHANNEL=public
        metadata_prefix="v2/public/$RELEASE_CHANNEL"
        ;;
    private|private-alpha)
        [ -n "$OFFLINE_DIR" ] || die "private requires an offline bundle"
        DELIVERY_CHANNEL=private
        MANIFEST_CHANNEL=private
        metadata_prefix=
        ;;
    tob|tob-alpha)
        DELIVERY_CHANNEL=public
        MANIFEST_CHANNEL=$CHANNEL
        metadata_prefix=v2
        [ "$CHANNEL" != tob-alpha ] || metadata_prefix=v2/tob-alpha
        ;;
    tob-private|tob-private-alpha)
        [ -n "$OFFLINE_DIR" ] || die "private requires an offline bundle"
        DELIVERY_CHANNEL=private
        MANIFEST_CHANNEL=$CHANNEL
        metadata_prefix=
        ;;
    *) die "TRAECLI_CHANNEL must select public or an offline private bundle" ;;
esac
VERSION_BASE='(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'
case "$MANIFEST_CHANNEL" in
    tob) INSTALLABLE_VERSION_PATTERN="^$VERSION_BASE-tob(\.[1-9][0-9]*)?$" ;;
    tob-alpha) INSTALLABLE_VERSION_PATTERN="^$VERSION_BASE-tob-alpha\.[1-9][0-9]*$" ;;
    tob-private) INSTALLABLE_VERSION_PATTERN="^$VERSION_BASE-tob-private$" ;;
    tob-private-alpha) INSTALLABLE_VERSION_PATTERN="^$VERSION_BASE-tob-private-alpha\.[1-9][0-9]*$" ;;
    *)
        INSTALLABLE_VERSION_PATTERN="^$VERSION_BASE$"
        [ "$RELEASE_CHANNEL" != alpha ] || INSTALLABLE_VERSION_PATTERN="^$VERSION_BASE-alpha\.[1-9][0-9]*$"
        ;;
esac

detect_os() {
    case "$(uname -s)" in
        Darwin) printf '%s\n' macos ;;
        Linux) printf '%s\n' linux ;;
        *) die "unsupported operating system: $(uname -s)" ;;
    esac
}

detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64) printf '%s\n' x86_64 ;;
        arm64|aarch64) printf '%s\n' aarch64 ;;
        *) die "unsupported architecture: $(uname -m)" ;;
    esac
}

pick_shell_profile() {
    detected_os=$1
    case "${SHELL:-}" in
        */zsh) printf '%s\n' "$HOME/.zshrc"; return 0 ;;
        */bash)
            if [ "$detected_os" = macos ]; then
                for profile in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile"; do
                    if [ -f "$profile" ]; then
                        printf '%s\n' "$profile"
                        return 0
                    fi
                done
                printf '%s\n' "$HOME/.bash_profile"
            else
                printf '%s\n' "$HOME/.bashrc"
            fi
            return 0
            ;;
    esac
    if [ -f "$HOME/.zshrc" ]; then
        printf '%s\n' "$HOME/.zshrc"
    elif [ "$detected_os" = macos ]; then
        printf '%s\n' "$HOME/.bash_profile"
    else
        printf '%s\n' "$HOME/.bashrc"
    fi
}

real_path() {
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
    elif command -v perl >/dev/null 2>&1; then
        perl -MCwd=realpath -e 'print realpath($ARGV[0])' "$1"
    else
        printf '%s\n' "$1"
    fi
}

relative_symlink_target() {
    target_path=$1
    link_dir=$(dirname "$2")
    # Keep logical paths intact so a symlinked home can move as one tree.
    # Resolving either side physically here would bake in the old mount path.
    case "$target_path" in
        /*) ;;
        *) target_path="${PWD%/}/$target_path" ;;
    esac
    case "$link_dir" in
        /*) ;;
        *) link_dir="${PWD%/}/$link_dir" ;;
    esac

    link_target=$(TRAECLI_RELATIVE_TARGET_PATH="$target_path" TRAECLI_RELATIVE_LINK_DIR="$link_dir" awk '
        function components(path, output, parts, count, depth, i) {
            count = split(path, parts, "/")
            depth = 0
            for (i = 1; i <= count; i++) {
                if (parts[i] == "" || parts[i] == ".") {
                    continue
                }
                if (parts[i] == "..") {
                    if (depth > 0) {
                        depth--
                    }
                    continue
                }
                output[++depth] = parts[i]
            }
            return depth
        }
        BEGIN {
            target_count = components(ENVIRON["TRAECLI_RELATIVE_TARGET_PATH"], target)
            base_count = components(ENVIRON["TRAECLI_RELATIVE_LINK_DIR"], base)
            common = 1
            while (common <= target_count && common <= base_count &&
                   target[common] == base[common]) {
                common++
            }

            result = ""
            for (i = common; i <= base_count; i++) {
                result = result "../"
            }
            for (i = common; i <= target_count; i++) {
                if (result != "" && substr(result, length(result), 1) != "/") {
                    result = result "/"
                }
                result = result target[i]
            }

            sub(/\/$/, "", result)
            print (result == "" ? "." : result)
        }
    ')

    if [ ! -d "$link_dir" ] || [ ! -d "$(dirname "$target_path")" ]; then
        printf '%s\n' "$link_target"
        return 0
    fi
    # A relative link is interpreted from the physical link directory. Keep the
    # movable logical form only when it still resolves to the intended target.
    target_parent=$(CDPATH= cd -P "$(dirname "$target_path")" 2>/dev/null && pwd -P) || {
        printf '%s\n' "$target_path"
        return 0
    }
    link_target_parent=$(
        CDPATH= cd -P "$(dirname "$link_dir/$link_target")" 2>/dev/null && pwd -P
    ) || {
        printf '%s\n' "$target_path"
        return 0
    }
    resolved_link_target="$link_target_parent/$(basename "$link_target")"
    resolved_target="$target_parent/$(basename "$target_path")"
    if [ "$resolved_link_target" != "$resolved_target" ]; then
        printf '%s\n' "$target_path"
        return 0
    fi

    printf '%s\n' "$link_target"
}

current_binary_path() {
    command -v "$BINARY_NAME" 2>/dev/null || true
}

check_existing_installation() {
    [ -x "$CURRENT_LINK/$BINARY_NAME" ] ||
        [ -x "$INSTALL_DIR/$BINARY_NAME" ] ||
        [ -n "$(current_binary_path)" ]
}

ask_upgrade() {
    info "Trae CLI is already installed; continuing with upgrade/reinstall confirmation."
    if is_yes "$ASSUME_YES"; then
        info "Assume-yes is set; upgrading/reinstalling without prompting."
        return 0
    fi
    prompt_yes_no "Do you want to upgrade/reinstall?" N
}

brew_formula_installed() {
    command -v brew >/dev/null 2>&1 || return 1
    for formula in $LEGACY_FORMULA_NAMES; do
        if brew list "$formula" >/dev/null 2>&1; then
            printf '%s\n' "$formula"
            return 0
        fi
    done
    return 1
}

detect_brew_install() {
    formula=$(brew_formula_installed || true)
    if [ -n "$formula" ]; then
        printf '%s\n' "$formula"
        return 0
    fi
    current_path=$(current_binary_path)
    [ -n "$current_path" ] || return 1
    resolved=$(real_path "$current_path")
    case "$current_path:$resolved" in
        */opt/homebrew/*|*/usr/local/Cellar/*|*/Homebrew/Cellar/*|*/opt/homebrew/Cellar/*|*/usr/local/Homebrew/*)
            printf '%s\n' "path:$current_path"
            return 0
            ;;
    esac
    return 1
}

fetch_text() {
    curl -fsSL --proto '=https' --proto-redir '=https' --retry 3 --connect-timeout 15 "$@"
}

download_file() {
    curl -fL --proto '=https' --proto-redir '=https' --retry 3 --connect-timeout 15 --progress-bar "$1" -o "$2"
}

internal_url() {
    key=$1
    if [ "${TRAEX_PUBLIC_KEY_STYLE:-flat}" = flat ]; then
        key=$(printf '%s' "$key" | sed 's#/#__#g; s#-#_#g')
    fi
    printf '%s/%s\n' "$BASE_URL" "$key"
}

fetch_internal_manifest() {
    internal_key=$1
    fetch_text "$(internal_url "$internal_key")" 2>/dev/null || {
        [ -n "$LEGACY_BASE_URL" ] && fetch_text "$LEGACY_BASE_URL/$internal_key" 2>/dev/null
    }
}

source_url_allowed() {
    case "$1" in "$BASE_URL"/*) return 0 ;; esac
    if [ "$DELIVERY_CHANNEL" = internal ] && [ -n "$LEGACY_BASE_URL" ]; then
        case "$1" in "$LEGACY_BASE_URL"/*) return 0 ;; esac
    fi
    return 1
}

resolve_internal_release() {
    internal_requested=$VERSION
    LEGACY_ARTIFACT=0
    if [ "$VERSION" = latest ]; then
        if ! INTERNAL_MANIFEST=$(fetch_internal_manifest "traex_latest/$RELEASE_CHANNEL.json"); then
            [ "$RELEASE_CHANNEL" = stable ] || die "failed to resolve internal alpha release"
            warn "Failed to resolve latest version; falling back to bundled default 0.200.9."
            VERSION=0.200.9
        fi
    fi
    if [ "$VERSION" != latest ]; then
        VERSION=${VERSION#rust-v}; VERSION=${VERSION#v}
        printf '%s\n' "$VERSION" | grep -Eq "$INSTALLABLE_VERSION_PATTERN" || die "invalid release version: $VERSION"
        if ! INTERNAL_MANIFEST=$(fetch_internal_manifest "traex_manifest/$VERSION.json"); then
            # Historical releases predate manifests and the Code Mode host.
            LEGACY_ARTIFACT=1
            filename="traex-$platform.gz"
            artifact_url="$(internal_url "traex/$VERSION/$filename")"
            expected_sha="${TRAEX_INSTALL_SHA256:-}"
            expected_size="${TRAEX_INSTALL_SIZE:-}"
            host_filename=
            return
        fi
    fi
    expected_version=
    [ "$internal_requested" = latest ] || expected_version=$VERSION
    resolve_manifest internal "$expected_version" || die "$MANIFEST_ERROR"
}

json_field() {
    json=$1
    field=$2
    if command -v python3 >/dev/null 2>&1; then
        JSON_PAYLOAD="$json" JSON_FIELD="$field" python3 - <<'PY'
import json
import os

value = json.loads(os.environ["JSON_PAYLOAD"]).get(os.environ["JSON_FIELD"])
if value is not None:
    print(value)
PY
        return
    fi
    printf '%s' "$json" | tr '\n' ' ' | sed -n "s/.*\"$field\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" | head -n 1
}

json_artifact_field() {
    json=$1
    platform=$2
    field=$3
    if command -v python3 >/dev/null 2>&1; then
        JSON_PAYLOAD="$json" JSON_PLATFORM="$platform" JSON_FIELD="$field" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["JSON_PAYLOAD"])
for artifact in payload.get("artifacts", []):
    if artifact.get("platform") == os.environ["JSON_PLATFORM"]:
        value = artifact.get(os.environ["JSON_FIELD"])
        if value is not None:
            print(value)
        break
PY
        return
    fi

    record=$(printf '%s' "$json" \
        | tr '\n' ' ' \
        | sed 's/"sidecars"[[:space:]]*:[[:space:]]*\[[^]]*\]/"sidecars":[]/g' \
        | sed 's/}[[:space:]]*,[[:space:]]*{/}\
{/g' \
        | sed -n "/\"platform\"[[:space:]]*:[[:space:]]*\"$platform\"/p" \
        | head -n 1)
    case "$field" in
        size)
            printf '%s' "$record" | sed -n 's/.*"size"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p'
            ;;
        *)
            printf '%s' "$record" | sed -n "s/.*\"$field\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p"
            ;;
    esac
}

json_dependency_artifact_field() {
    json_artifact_field "$@"
}

json_sidecar_field() {
    json=$1
    platform=$2
    field=$3
    if command -v python3 >/dev/null 2>&1; then
        JSON_PAYLOAD="$json" JSON_PLATFORM="$platform" JSON_FIELD="$field" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["JSON_PAYLOAD"])
for artifact in payload.get("artifacts", []):
    if artifact.get("platform") != os.environ["JSON_PLATFORM"]:
        continue
    if os.environ["JSON_FIELD"] == "__present":
        print("yes" if "sidecars" in artifact else "no")
        break
    matches = [item for item in artifact.get("sidecars", [])
               if item.get("name") == "code_mode_host"]
    if len(matches) == 1:
        value = matches[0].get(os.environ["JSON_FIELD"])
        if value is not None:
            print(value)
    break
PY
        return
    fi

    record=$(printf '%s' "$json" \
        | tr '\n' ' ' \
        | sed 's/}[[:space:]]*,[[:space:]]*{/}\
{/g' \
        | sed -n "/\"platform\"[[:space:]]*:[[:space:]]*\"$platform\"/p" \
        | head -n 1)
    case "$record" in
        *'"sidecars"'*) ;;
        *) [ "$field" = __present ] && printf '%s\n' no; return ;;
    esac
    if [ "$field" = __present ]; then
        printf '%s\n' yes
        return
    fi
    sidecar=${record#*"sidecars"}
    sidecar=${sidecar#*[}
    sidecar=${sidecar%%]*}
    case "$field" in
        size)
            printf '%s' "$sidecar" | sed -n 's/.*"size"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p'
            ;;
        *)
            printf '%s' "$sidecar" | sed -n "s/.*\"$field\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p"
            ;;
    esac
}

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        die "sha256sum or shasum is required"
    fi
}

verify_file() {
    file=$1
    expected_sha=$2
    expected_size=$3
    actual_size=$(wc -c < "$file" | tr -d ' ')
    [ "$actual_size" = "$expected_size" ] || return 1
    actual_sha=$(sha256_file "$file")
    [ "$actual_sha" = "$expected_sha" ]
}

dependency_install_failed() {
    required=$1
    message=$2
    if is_yes "$required"; then
        die "$message"
    fi
    warn "$message"
}

install_managed_dependency() {
    name=$1
    command_name=$2
    install_mode=$3
    required=$4
    platform=$5

    case "$install_mode" in
        auto|never|force) ;;
        *)
            dependency_install_failed "$required" "invalid install mode for ${name}: $install_mode (expected auto, never or force)"
            return 0
            ;;
    esac
    if [ "$install_mode" = never ]; then
        info "Skipping ${name} dependency installation because install mode is never."
        return 0
    fi
    if [ "$install_mode" = auto ] && command -v "$command_name" >/dev/null 2>&1; then
        info "Found existing ${name}: $(command -v "$command_name")"
        return 0
    fi

    info "Resolving ${name} dependency"
    if [ -n "$OFFLINE_DIR" ]; then
        dependency_manifest_path="$OFFLINE_DIR/dependencies/$name/manifest.json"
        dependency_manifest=$(sed -n '1,$p' "$dependency_manifest_path" 2>/dev/null) || {
            dependency_install_failed "$required" "bundled ${name} dependency manifest is missing"
            return 0
        }
    else
        dependency_manifest_url="${BASE_URL}/v2/deps/${name}/latest.json"
        if [ "$DELIVERY_CHANNEL" = internal ]; then
            case "$name" in
                ripgrep) dep_version="${TRAEX_RG_VERSION:-latest}"; dep_base="${TRAEX_RG_BASE_URL:-}" ;;
                bubblewrap) dep_version="${TRAEX_BWRAP_VERSION:-latest}"; dep_base="${TRAEX_BWRAP_BASE_URL:-}" ;;
            esac
            dep_suffix="$dep_version/manifest.json"
            [ "$dep_version" != latest ] || dep_suffix=latest.json
            if [ -n "$dep_base" ]; then
                dependency_manifest=$(fetch_text "${dep_base%/}/$dep_suffix" 2>/dev/null) || dependency_manifest=
            else
                dependency_manifest=$(fetch_internal_manifest "traex_deps/$name/$dep_suffix") || dependency_manifest=
            fi
        else
            dependency_manifest=$(fetch_text "$dependency_manifest_url" 2>/dev/null) || dependency_manifest=
        fi
        [ -n "$dependency_manifest" ] || {
            dependency_install_failed "$required" "failed to resolve ${name} dependency for $platform"
            return 0
        }
    fi
    dependency_version=$(json_field "$dependency_manifest" version 2>/dev/null | head -n 1) || true
    dependency_url=$(json_dependency_artifact_field "$dependency_manifest" "$platform" url 2>/dev/null | head -n 1) || true
    dependency_filename=$(json_dependency_artifact_field "$dependency_manifest" "$platform" filename 2>/dev/null | head -n 1) || true
    dependency_archive_path=$(json_dependency_artifact_field "$dependency_manifest" "$platform" archive_path 2>/dev/null | head -n 1) || true
    dependency_sha=$(json_dependency_artifact_field "$dependency_manifest" "$platform" sha256 2>/dev/null | head -n 1) || true
    dependency_size=$(json_dependency_artifact_field "$dependency_manifest" "$platform" size 2>/dev/null | head -n 1) || true
    dependency_compression=$(json_dependency_artifact_field "$dependency_manifest" "$platform" compression 2>/dev/null | head -n 1) || true
    if [ -n "$OFFLINE_DIR" ]; then
        if [ "$dependency_url" != "dependencies/$name/$dependency_filename" ]; then
            dependency_install_failed "$required" "${name} dependency path is outside the offline bundle"
            return 0
        fi
    else
        case "$DELIVERY_CHANNEL:$dependency_url" in
            internal:*)
                source_url_allowed "$dependency_url" || {
                    [ -n "${dep_base:-}" ] && case "$dependency_url" in "$dep_base"/*) true ;; *) false ;; esac
                } || { dependency_install_failed "$required" "dependency URL is outside the configured source"; return 0; }
                ;;
            public:"${BASE_URL}"/v2/deps/*) ;;
            *)
                dependency_install_failed "$required" "${name} dependency URL is outside the public release prefix"
                return 0
                ;;
        esac
    fi
    if [ -z "$dependency_version" ] || [ -z "$dependency_filename" ] ||
        [ -z "$dependency_archive_path" ] || [ "$dependency_compression" != tar.gz ] ||
        [ "${#dependency_sha}" -ne 64 ]; then
        dependency_install_failed "$required" "invalid ${name} dependency metadata for $platform"
        return 0
    fi
    case "$dependency_filename:$dependency_archive_path:$dependency_size" in
        *..*|*%*|*[!0-9A-Za-z._/:-]*|*:)
            dependency_install_failed "$required" "unsafe ${name} dependency metadata for $platform"
            return 0
            ;;
    esac
    case "$dependency_size" in
        ''|*[!0-9]*)
            dependency_install_failed "$required" "invalid ${name} dependency size for $platform"
            return 0
            ;;
    esac

    dependency_tmp=$(mktemp -d "${TMPDIR:-/tmp}/traecli-dependency.XXXXXX")
    dependency_archive="$dependency_tmp/$dependency_filename"
    dependency_extract="$dependency_tmp/extract"
    mkdir -p "$dependency_extract"
    if [ -n "$OFFLINE_DIR" ]; then
        info "Loading bundled ${name} ${dependency_version} for ${platform}"
        if ! cp "$OFFLINE_DIR/$dependency_url" "$dependency_archive"; then
            rm -rf "$dependency_tmp"
            dependency_install_failed "$required" "failed to read bundled ${name} artifact"
            return 0
        fi
    else
        info "Downloading ${name} ${dependency_version} for ${platform}"
        if ! download_file "$dependency_url" "$dependency_archive"; then
            rm -rf "$dependency_tmp"
            dependency_install_failed "$required" "failed to download ${name}"
            return 0
        fi
    fi
    if ! verify_file "$dependency_archive" "$dependency_sha" "$dependency_size"; then
        rm -rf "$dependency_tmp"
        dependency_install_failed "$required" "${name} artifact verification failed"
        return 0
    fi
    if ! tar -xzf "$dependency_archive" -C "$dependency_extract"; then
        rm -rf "$dependency_tmp"
        dependency_install_failed "$required" "failed to extract ${name} artifact"
        return 0
    fi
    extracted_binary="$dependency_extract/$dependency_archive_path"
    if [ ! -f "$extracted_binary" ]; then
        rm -rf "$dependency_tmp"
        dependency_install_failed "$required" "${name} artifact did not contain $dependency_archive_path"
        return 0
    fi

    dependency_target="$INSTALL_DIR/$command_name"
    if { [ -e "$dependency_target" ] || [ -L "$dependency_target" ]; } && [ "$install_mode" != force ]; then
        warn "Leaving existing ${name} at $dependency_target. Use force mode to replace it."
        rm -rf "$dependency_tmp"
        return 0
    fi
    dependency_staged="$INSTALL_DIR/.${command_name}.tmp.$$"
    cp "$extracted_binary" "$dependency_staged"
    chmod 0755 "$dependency_staged"
    mv -f "$dependency_staged" "$dependency_target"
    rm -rf "$dependency_tmp"
    if "$dependency_target" --version >/dev/null 2>&1; then
        info "${name} installed successfully at $dependency_target"
    else
        dependency_install_failed "$required" "${name} was installed but failed to run"
    fi
}

install_dependencies() {
    os=$1
    platform=$2
    install_managed_dependency ripgrep rg "$INSTALL_RG" "$REQUIRE_RG" "$platform"
    if [ "$os" = linux ]; then
        install_managed_dependency bubblewrap bwrap "$INSTALL_BWRAP" "$REQUIRE_BWRAP" "$platform"
    fi
    if [ "$os" = linux ]; then
        bwrap_path=$(command -v bwrap 2>/dev/null || true)
        if [ -n "$bwrap_path" ] &&
            ! "$bwrap_path" --unshare-user --unshare-net --ro-bind / / /bin/true >/dev/null 2>&1; then
            warn "bubblewrap is installed at $bwrap_path, but the user-namespace sandbox probe failed."
        fi
    fi
}

check_node_dependency() {
    node_path=$(command -v node 2>/dev/null || true)
    npx_path=$(command -v npx 2>/dev/null || true)
    if [ -n "$node_path" ] && [ -n "$npx_path" ]; then
        info "Found Node.js: $node_path"
        info "Found npx: $npx_path"
        return 0
    fi
    warn "Node.js and npx are required for some Trae CLI plugin and tool workflows, but they were not both found on PATH."
    [ -n "$node_path" ] || warn "Missing command: node"
    [ -n "$npx_path" ] || warn "Missing command: npx"
    info "Install Node.js from https://nodejs.org/ or your system package manager."
}

coco_installation_paths() {
    bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
    data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
    data_binaries=""

    for name in $COCO_BINARY_NAMES; do
        data_binary="$data_home/$name/$name"
        if [ -e "$data_binary" ]; then
            printf '%s\n' "$data_binary"
            data_binaries="${data_binaries}$(real_path "$data_binary")
"
        fi
        old_home_binary="$HOME/bin/$name"
        if [ -e "$old_home_binary" ] || [ -L "$old_home_binary" ]; then
            printf '%s\n' "$old_home_binary"
        fi
        bin_entry="$bin_dir/$name"
        if { [ -e "$bin_entry" ] || [ -L "$bin_entry" ]; } &&
            [ "$(real_path "$bin_entry")" = "$(real_path "$data_binary")" ]; then
            printf '%s\n' "$bin_entry"
        fi
    done

    [ -n "$data_binaries" ] || return 0
    for name in $COCO_ALIAS_NAMES; do
        bin_entry="$bin_dir/$name"
        [ -e "$bin_entry" ] || [ -L "$bin_entry" ] || continue
        resolved=$(real_path "$bin_entry")
        printf '%s\n' "$data_binaries" | grep -Fx "$resolved" >/dev/null 2>&1 || continue
        printf '%s\n' "$bin_entry"
    done
}

maybe_remove_coco_installation() {
    paths=$(coco_installation_paths)
    [ -n "$paths" ] || return 0
    if is_no "$REMOVE_COCO"; then
        return 0
    fi
    if [ "$REMOVE_COCO" != auto ] && ! is_yes "$REMOVE_COCO"; then
        warn "Ignoring unsupported TRAECLI_INSTALL_REMOVE_COCO value: $REMOVE_COCO"
        return 0
    fi
    if [ "$REMOVE_COCO" = auto ] && is_yes "$ASSUME_YES"; then
        return 0
    fi

    warn "Detected existing TRAE CLI 1.0 legacy command files:"
    printf '%s\n' "$paths" | while IFS= read -r path; do
        [ -n "$path" ] && printf '  %s\n' "$path"
    done
    info "Only command binaries and symlinks will be removed. User data and cache/config directories will be kept."
    if ! is_yes "$ASSUME_YES" &&
        ! prompt_yes_no "Do you want to remove these TRAE CLI 1.0 legacy command files before installing Trae CLI 2.0?" N; then
        warn "Leaving TRAE CLI 1.0 legacy command files in place. They may shadow compatibility commands such as traecli."
        return 0
    fi
    printf '%s\n' "$paths" | while IFS= read -r path; do
        [ -n "$path" ] || continue
        if [ -e "$path" ] || [ -L "$path" ]; then
            info "Removing $path"
            rm -f "$path" || warn "Failed to remove $path"
        fi
    done
}

maybe_remove_brew() {
    brew_marker=$1
    [ -n "$brew_marker" ] || return 0
    warn "Detected previous Homebrew installation ($brew_marker)."
    info "This installer has migrated Trae CLI to the standalone installation."
    command -v brew >/dev/null 2>&1 || return 0

    remove=false
    if is_yes "$REMOVE_BREW"; then
        remove=true
    elif is_no "$REMOVE_BREW" || is_yes "$ASSUME_YES"; then
        warn "Leaving the Homebrew package installed. It may shadow the traecli command."
        return 0
    elif prompt_yes_no "Do you want to uninstall the old Homebrew package now?" N; then
        remove=true
    fi
    [ "$remove" = true ] || return 0
    for formula in $LEGACY_FORMULA_NAMES; do
        if brew list "$formula" >/dev/null 2>&1; then
            info "Removing old Homebrew formula: $formula"
            brew uninstall "$formula" || warn "Failed to uninstall $formula; remove it manually if needed."
        fi
    done
}

ensure_path() {
    case ":$PATH:" in
        *":$INSTALL_DIR:"*) return 0 ;;
    esac
    warn "$INSTALL_DIR is not on PATH."
    info "Add: export PATH=\"$INSTALL_DIR:\$PATH\""
    shell_profile=$(pick_shell_profile "$os")
    if [ -n "$shell_profile" ] && [ -r /dev/tty ] &&
        prompt_yes_no "Do you want to add it to $shell_profile automatically?" Y; then
        if ! grep -F "export PATH=\"$INSTALL_DIR:\$PATH\"" "$shell_profile" >/dev/null 2>&1; then
            {
                printf '\n'
                printf '%s\n' '# Added by Trae CLI installer'
                printf 'export PATH="%s:$PATH"\n' "$INSTALL_DIR"
            } >> "$shell_profile"
            info "Added PATH to $shell_profile"
        fi
    fi
}

check_path_priority() {
    target="$INSTALL_DIR/traecli"
    current_path=$(command -v traecli 2>/dev/null || true)
    if [ -z "$current_path" ]; then
        warn "Trae CLI is installed, but the current shell cannot find the traecli command yet."
        return 0
    fi
    resolved_current=$(real_path "$current_path")
    resolved_target=$(real_path "$target")
    if [ "$current_path" != "$target" ] && [ "$resolved_current" != "$resolved_target" ]; then
        warn "The current traecli command resolves to: $current_path"
        warn "Move $INSTALL_DIR earlier in PATH or remove the old command."
    fi
}

acquire_install_lock() {
    mkdir -p "$STATE_DIR"
    attempts=0
    while ! mkdir "$INSTALL_LOCK_DIR" 2>/dev/null; do
        attempts=$((attempts + 1))
        lock_pid=$(cat "$INSTALL_LOCK_DIR/pid" 2>/dev/null || true)
        if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
            rm -rf "$INSTALL_LOCK_DIR"
            continue
        fi
        if [ "$attempts" -ge 120 ]; then
            die "timed out waiting for another Trae CLI installation to finish"
        fi
        sleep 1
    done
    printf '%s\n' "$$" > "$INSTALL_LOCK_DIR/pid"
}

release_install_lock() {
    if [ -f "$INSTALL_LOCK_DIR/pid" ] &&
        [ "$(cat "$INSTALL_LOCK_DIR/pid" 2>/dev/null || true)" = "$$" ]; then
        rm -rf "$INSTALL_LOCK_DIR"
    fi
}

cleanup_stale_install_artifacts() {
    for stale_dir in "$RELEASES_DIR"/.staging.*; do
        [ -d "$stale_dir" ] || continue
        [ ! -L "$stale_dir" ] || continue
        rm -rf "$stale_dir"
    done
}

assert_current_link_is_managed() {
    [ -L "$CURRENT_LINK" ] || return 0
    releases_root=$(CDPATH= cd -P "$RELEASES_DIR" 2>/dev/null && pwd -P) ||
        die "failed to resolve the managed releases directory"
    if current_release=$(CDPATH= cd -P "$CURRENT_LINK" 2>/dev/null && pwd -P); then
        case "$current_release" in
            "$releases_root"/*) return 0 ;;
            *) die "refusing to replace a current release link not managed by this installer" ;;
        esac
    fi

    # A previous release may have been removed while current still points to it.
    # Allow that broken link to self-heal only when its direct parent is the
    # installer-managed releases directory. Resolving the parent keeps this
    # check safe across relative links, .. components, and symlinked homes.
    current_target=$(readlink "$CURRENT_LINK" 2>/dev/null) ||
        die "refusing to use an invalid current release link at $CURRENT_LINK"
    case "$current_target" in
        /*) missing_release=$current_target ;;
        *) missing_release="$(dirname "$CURRENT_LINK")/$current_target" ;;
    esac
    missing_release_parent=$(
        CDPATH= cd -P "$(dirname "$missing_release")" 2>/dev/null && pwd -P
    ) || die "refusing to use an invalid current release link at $CURRENT_LINK"
    [ "$missing_release_parent" = "$releases_root" ] ||
        die "refusing to replace a current release link not managed by this installer"
}

request_managed_release_cleanup() {
    current_binary="$CURRENT_LINK/$BINARY_NAME"
    if [ ! -x "$current_binary" ]; then
        return 0
    fi
    if ! "$current_binary" "$RELEASE_LEASE_PROBE_ARG" >/dev/null 2>&1; then
        warn "Skipping release cleanup because this Trae CLI version does not support release leases."
        return 0
    fi
    if ! "$current_binary" "$RELEASE_CLEANUP_ARG" >/dev/null 2>&1; then
        warn "Trae CLI release cleanup did not complete; existing releases were kept."
    fi
}

replace_current_symlink() {
    new_link=$1
    if mv --help 2>/dev/null | grep -q -- '-T'; then
        mv -fT "$new_link" "$CURRENT_LINK"
    elif mv -h "$new_link" "$CURRENT_LINK" 2>/dev/null; then
        :
    else
        rm -f "$CURRENT_LINK"
        mv "$new_link" "$CURRENT_LINK"
    fi
}

print_usage_guidance() {
    compat="$INSTALL_DIR/traecli"
    target="$INSTALL_DIR/$BINARY_NAME"
    current_compat=$(command -v traecli 2>/dev/null || true)
    managed_compat=false
    if { [ -e "$compat" ] || [ -L "$compat" ]; } &&
        [ "$(real_path "$compat")" = "$(real_path "$target")" ]; then
        managed_compat=true
    fi
    if [ "$managed_compat" = true ] &&
        [ -n "$current_compat" ] &&
        [ "$(real_path "$current_compat")" = "$(real_path "$target")" ]; then
        info "Run: traecli --version"
        return 0
    fi
    if [ "$managed_compat" = true ]; then
        info "Run: \"$compat\" --version"
        return 0
    fi

    warn "An existing traecli command was kept and may still run TRAE CLI 1.0."
    info "Run: \"$target\" --version"
}

resolve_manifest() {
    candidate_url=$1
    expected_version=$2
    MANIFEST_ERROR=""
    MANIFEST_NOT_FOUND=no

    if [ "$DELIVERY_CHANNEL" = internal ]; then
        candidate_manifest=$INTERNAL_MANIFEST
    elif [ -n "$OFFLINE_DIR" ]; then
        info "Reading bundled release metadata"
        candidate_manifest=$(sed -n '1,$p' "$candidate_url" 2>/dev/null) || {
            MANIFEST_ERROR="failed to read bundled release metadata"
            return 1
        }
    else
        info "Fetching release metadata"
        if candidate_response=$(fetch_text "$candidate_url" --write-out '\n%{http_code}' 2>/dev/null); then
            candidate_manifest=$(printf '%s\n' "$candidate_response" | sed '$d')
        else
            fetch_status=$?
            http_status=$(printf '%s\n' "$candidate_response" | tail -n 1)
            # A received HTTP 404 can coexist with a curl transport error (for example 56).
            if [ "$http_status" = 404 ]; then
                MANIFEST_NOT_FOUND=yes
            fi
            MANIFEST_ERROR="failed to download release metadata (curl ${fetch_status}, HTTP ${http_status:-unknown})"
            return 1
        fi
    fi
    if [ -z "$candidate_manifest" ]; then
        MANIFEST_ERROR="release metadata is empty"
        return 1
    fi

    if [ "$DELIVERY_CHANNEL" = internal ]; then
        candidate_channel=$(json_field "$candidate_manifest" channel | head -n 1)
        [ "$candidate_channel" = "$RELEASE_CHANNEL" ] || {
            MANIFEST_ERROR="release metadata is on a different release channel"; return 1;
        }
    else
    candidate_build_channel=$(json_field "$candidate_manifest" build_channel 2>/dev/null | head -n 1) || true
    if [ "$candidate_build_channel" != internal ] && [ "$candidate_build_channel" != tob ]; then
        MANIFEST_ERROR="release metadata has an unsupported build channel"
        return 1
    fi
    candidate_distribution=$(json_field "$candidate_manifest" distribution 2>/dev/null | head -n 1) || true
    case "$MANIFEST_CHANNEL" in
        public|private) expected_distribution=$DELIVERY_CHANNEL ;;
        tob-private) expected_distribution=tob-private ;;
        tob-private-alpha) expected_distribution=tob-private-alpha ;;
        *) expected_distribution=tob ;;
    esac
    if [ "$candidate_distribution" != "$expected_distribution" ]; then
        MANIFEST_ERROR="release metadata is not a ToB distribution"
        return 1
    fi
    candidate_channel=$(json_field "$candidate_manifest" channel 2>/dev/null | head -n 1) || true
    if [ "$candidate_channel" != "$MANIFEST_CHANNEL" ]; then
        MANIFEST_ERROR="release metadata is not on the ToB channel"
        return 1
    fi

    case "$MANIFEST_CHANNEL" in
        public|private)
            candidate_track=$(json_field "$candidate_manifest" release_channel 2>/dev/null | head -n 1) || true
            if [ "$candidate_track" != "$RELEASE_CHANNEL" ]; then
                MANIFEST_ERROR="release metadata is on a different release channel"
                return 1
            fi
            ;;
    esac
    fi
    candidate_version=$(json_field "$candidate_manifest" version 2>/dev/null | head -n 1) || true
    if [ -z "$candidate_version" ]; then
        MANIFEST_ERROR="release metadata has no version"
        return 1
    fi
    if ! printf '%s\n' "$candidate_version" \
        | grep -Eq "$INSTALLABLE_VERSION_PATTERN"; then
        MANIFEST_ERROR="invalid ToB release version: $candidate_version"
        return 1
    fi
    if [ -n "$expected_version" ] && [ "$candidate_version" != "$expected_version" ]; then
        MANIFEST_ERROR="release version mismatch: got $candidate_version, expected $expected_version"
        return 1
    fi

    candidate_filename=$(json_artifact_field "$candidate_manifest" "$platform" filename 2>/dev/null | head -n 1) || true
    candidate_artifact_url=$(json_artifact_field "$candidate_manifest" "$platform" url 2>/dev/null | head -n 1) || true
    candidate_expected_sha=$(json_artifact_field "$candidate_manifest" "$platform" sha256 2>/dev/null | head -n 1) || true
    candidate_expected_size=$(json_artifact_field "$candidate_manifest" "$platform" size 2>/dev/null | head -n 1) || true
    candidate_compression=$(json_artifact_field "$candidate_manifest" "$platform" compression 2>/dev/null | head -n 1) || true
    candidate_host_filename=$(json_sidecar_field "$candidate_manifest" "$platform" filename 2>/dev/null | head -n 1) || true
    candidate_host_url=$(json_sidecar_field "$candidate_manifest" "$platform" url 2>/dev/null | head -n 1) || true
    candidate_host_sha=$(json_sidecar_field "$candidate_manifest" "$platform" sha256 2>/dev/null | head -n 1) || true
    candidate_host_size=$(json_sidecar_field "$candidate_manifest" "$platform" size 2>/dev/null | head -n 1) || true
    candidate_host_compression=$(json_sidecar_field "$candidate_manifest" "$platform" compression 2>/dev/null | head -n 1) || true
    candidate_has_sidecars=$(json_sidecar_field "$candidate_manifest" "$platform" __present 2>/dev/null | head -n 1) || true

    if [ -z "$candidate_filename" ]; then
        MANIFEST_ERROR="release metadata has no artifact for $platform"
        return 1
    fi
    case "$candidate_filename" in
        */*|*..*|*%*|*[!0-9A-Za-z._-]*)
            MANIFEST_ERROR="unsafe artifact filename: $candidate_filename"
            return 1
            ;;
    esac
    if [ -n "$OFFLINE_DIR" ]; then
        if [ "$candidate_artifact_url" != "artifacts/$candidate_filename" ]; then
            MANIFEST_ERROR="artifact path is outside the offline bundle"
            return 1
        fi
    else
        if ! source_url_allowed "$candidate_artifact_url"; then
                MANIFEST_ERROR="artifact URL is outside the public release prefix"
                return 1
        fi
    fi
    if [ "$candidate_compression" != gzip ]; then
        MANIFEST_ERROR="unsupported artifact compression: $candidate_compression"
        return 1
    fi
    if [ "${#candidate_expected_sha}" -ne 64 ]; then
        MANIFEST_ERROR="invalid artifact sha256"
        return 1
    fi
    case "$candidate_expected_sha" in
        *[!0-9A-Fa-f]*)
            MANIFEST_ERROR="invalid artifact sha256"
            return 1
            ;;
    esac
    case "$candidate_expected_size" in
        ''|*[!0-9]*)
            MANIFEST_ERROR="invalid artifact size"
            return 1
            ;;
    esac
    case "$platform" in
        windows-*) expected_host_filename="traex-code-mode-host-${platform}.exe.gz" ;;
        *) expected_host_filename="traex-code-mode-host-${platform}.gz" ;;
    esac
    if [ "$candidate_has_sidecars" = no ] && [ -z "$candidate_host_filename$candidate_host_url$candidate_host_sha$candidate_host_size$candidate_host_compression" ]; then
        if [ -n "$OFFLINE_DIR" ]; then
            MANIFEST_ERROR="release metadata has no code mode host sidecar for $platform"
            return 1
        fi
        expected_host_filename=""
    elif [ "$candidate_host_filename" != "$expected_host_filename" ]; then
        MANIFEST_ERROR="invalid code mode host filename: $candidate_host_filename"; return 1;
    elif [ -n "$OFFLINE_DIR" ]; then
        [ "$candidate_host_url" = "artifacts/$candidate_host_filename" ] || {
            MANIFEST_ERROR="code mode host path is outside the offline bundle"; return 1;
        }
    else
        source_url_allowed "$candidate_host_url" || {
            MANIFEST_ERROR="code mode host URL is outside the public release prefix"; return 1;
        }
    fi
    if [ -n "$candidate_host_filename" ]; then
        [ "$candidate_host_compression" = gzip ] || { MANIFEST_ERROR="unsupported code mode host compression"; return 1; }
        case "$candidate_host_sha" in
            ????????????????????????????????????????????????????????????????) ;;
            *) MANIFEST_ERROR="invalid code mode host sha256"; return 1 ;;
        esac
        case "$candidate_host_sha" in *[!0-9A-Fa-f]*) MANIFEST_ERROR="invalid code mode host sha256"; return 1 ;; esac
        case "$candidate_host_size" in ''|*[!0-9]*) MANIFEST_ERROR="invalid code mode host size"; return 1 ;; esac
    fi

    manifest=$candidate_manifest
    VERSION=$candidate_version
    filename=$candidate_filename
    artifact_url=$candidate_artifact_url
    expected_sha=$candidate_expected_sha
    expected_size=$candidate_expected_size
    compression=$candidate_compression
    host_filename=$candidate_host_filename
    host_url=$candidate_host_url
    host_expected_sha=$candidate_host_sha
    host_expected_size=$candidate_host_size
    return 0
}

resolve_latest_manifests() {
    CHANNEL_METADATA_MISSING=no
    latest_manifest_url="${BASE_URL}/${metadata_prefix}/latest.json"
    fallback_manifest_url="${BASE_URL}/${metadata_prefix}/fallback.json"
    if ! resolve_manifest "$latest_manifest_url" ""; then
        latest_error=$MANIFEST_ERROR
        latest_not_found=$MANIFEST_NOT_FOUND
        warn "Latest release metadata is unavailable or invalid (${latest_error}); trying the last-known-good release"
        if ! resolve_manifest "$fallback_manifest_url" ""; then
            if [ "$latest_not_found" = yes ] && [ "$MANIFEST_NOT_FOUND" = yes ]; then
                CHANNEL_METADATA_MISSING=yes
            fi
            MANIFEST_ERROR="latest release metadata failed validation (${latest_error}); last-known-good metadata is unavailable (${MANIFEST_ERROR})"
            return 1
        fi
        warn "Installing last-known-good Trae CLI ${VERSION}"
    fi
}

os=$(detect_os)
arch=$(detect_arch)
platform="${os}-${arch}"
brew_marker=""
LEGACY_ARTIFACT=0

if [ "$DELIVERY_CHANNEL" = internal ]; then
    resolve_internal_release
elif [ -n "$OFFLINE_DIR" ]; then
    requested_version=$VERSION
    expected_version=""
    if [ "$requested_version" != latest ]; then
        if ! printf '%s\n' "$requested_version" \
            | grep -Eq "$INSTALLABLE_VERSION_PATTERN"; then
            die "invalid ToB release version: $requested_version"
        fi
        expected_version=$requested_version
    fi
    if ! resolve_manifest "$OFFLINE_DIR/offline-manifest.json" "$expected_version"; then
        die "$MANIFEST_ERROR"
    fi
elif [ "$VERSION" = latest ]; then
    if ! resolve_latest_manifests; then
        # A shared installer can be published by alpha before public stable exists.
        # Only the implicit default may use the legacy stable entry points.
        if [ "$CHANNEL_METADATA_MISSING" = yes ] &&
            [ -z "${TRAECLI_CHANNEL:-}" ] && [ -z "${TRAECLI_RELEASE_CHANNEL:-}" ]; then
            warn "Public stable metadata is not published (HTTP 404); trying the legacy ToB stable release"
            CHANNEL=tob
            MANIFEST_CHANNEL=tob
            metadata_prefix=v2
            INSTALLABLE_VERSION_PATTERN="^$VERSION_BASE-tob(\.[1-9][0-9]*)?$"
            resolve_latest_manifests || die "$MANIFEST_ERROR"
        else
            die "$MANIFEST_ERROR"
        fi
    fi
else
    requested_version=$VERSION
    if ! printf '%s\n' "$requested_version" \
        | grep -Eq "$INSTALLABLE_VERSION_PATTERN"; then
        die "invalid ToB release version: $requested_version"
    fi
    manifest_url="${BASE_URL}/v2/releases/${requested_version}/manifest.json"
    if ! resolve_manifest "$manifest_url" "$requested_version"; then
        die "$MANIFEST_ERROR"
    fi
fi

if is_yes "$MIGRATE_BREW"; then
    brew_marker=$(detect_brew_install || true)
fi
maybe_remove_coco_installation

if check_existing_installation; then
    if ! ask_upgrade; then
        info "Installation cancelled."
        exit 0
    fi
fi

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/traecli-install.XXXXXX")
trap 'rm -rf "$tmp_dir"; release_install_lock' EXIT HUP INT TERM
archive="$tmp_dir/$filename"
binary="$tmp_dir/$BINARY_NAME"
host_binary="$tmp_dir/$CODE_MODE_HOST_NAME"
if [ -n "$host_filename" ]; then
    host_archive="$tmp_dir/$host_filename"
fi

if [ -n "$OFFLINE_DIR" ]; then
    info "Loading bundled Trae CLI ${VERSION} for ${platform}"
    cp "$OFFLINE_DIR/$artifact_url" "$archive" || die "failed to read bundled artifact $artifact_url"
    if [ -n "$host_filename" ]; then
        cp "$OFFLINE_DIR/$host_url" "$host_archive" || die "failed to read bundled code mode host $host_url"
    fi
else
    info "Downloading Trae CLI ${VERSION} for ${platform}"
    download_file "$artifact_url" "$archive" || die "failed to download $artifact_url"
    if [ -n "$host_filename" ]; then
        download_file "$host_url" "$host_archive" || die "failed to download $host_url"
    fi
fi

actual_size=$(wc -c < "$archive" | tr -d ' ')
[ -z "$expected_size" ] && [ "$LEGACY_ARTIFACT" = 1 ] || [ "$actual_size" = "$expected_size" ] || die "artifact size mismatch: got $actual_size, expected $expected_size"
actual_sha=$(sha256_file "$archive")
[ -z "$expected_sha" ] && [ "$LEGACY_ARTIFACT" = 1 ] || [ "$actual_sha" = "$expected_sha" ] || die "artifact sha256 mismatch: got $actual_sha, expected $expected_sha"
if [ -n "$host_filename" ]; then
    host_actual_size=$(wc -c < "$host_archive" | tr -d ' ')
    [ "$host_actual_size" = "$host_expected_size" ] || die "code mode host size mismatch: got $host_actual_size, expected $host_expected_size"
    host_actual_sha=$(sha256_file "$host_archive")
    [ "$host_actual_sha" = "$host_expected_sha" ] || die "code mode host sha256 mismatch: got $host_actual_sha, expected $host_expected_sha"
fi

info "Decompressing verified artifact"
if command -v gzip >/dev/null 2>&1; then
    gzip -dc "$archive" > "$binary"
    if [ -n "$host_filename" ]; then gzip -dc "$host_archive" > "$host_binary"; fi
else
    gunzip -c "$archive" > "$binary"
    if [ -n "$host_filename" ]; then gunzip -c "$host_archive" > "$host_binary"; fi
fi
[ -s "$binary" ] || die "decompressed binary is empty"
if [ -n "$host_filename" ]; then
    [ -s "$host_binary" ] || die "decompressed code mode host is empty"
    chmod 0755 "$host_binary"
fi
chmod 0755 "$binary"

prepare_executable() {
    executable=$1
    if [ "$os" = macos ] && command -v xattr >/dev/null 2>&1; then
        xattr -cr "$executable" >/dev/null 2>&1 || true
    fi
    if [ "$os" = macos ] && command -v codesign >/dev/null 2>&1; then
        if ! codesign --verify "$executable" >/dev/null 2>&1; then
            warn "artifact is not signed; applying an ad-hoc signature"
            codesign --force --sign - "$executable" >/dev/null 2>&1 || die "failed to sign the macOS binary"
        fi
    fi
}
prepare_executable "$binary"
"$binary" --version >/dev/null 2>&1 || die "downloaded binary failed the --version smoke test"
if [ -n "$host_filename" ]; then
    prepare_executable "$host_binary"
    "$host_binary" </dev/null >/dev/null 2>&1 || die "downloaded code mode host failed the startup smoke test"
fi

acquire_install_lock
mkdir -p "$INSTALL_DIR" "$STATE_DIR" "$RELEASES_DIR"
cleanup_stale_install_artifacts
if [ -e "$CURRENT_LINK" ] && [ ! -L "$CURRENT_LINK" ]; then
    die "refusing to replace non-symlink path at $CURRENT_LINK"
fi
assert_current_link_is_managed
staging_dir=$(mktemp -d "$RELEASES_DIR/.staging.${VERSION}-${platform}.XXXXXX")
release_name=$(basename "$staging_dir" | sed 's/^\.staging\.//')
release_dir="$RELEASES_DIR/$release_name"
cp "$binary" "$staging_dir/$BINARY_NAME"
case "$DELIVERY_CHANNEL" in
    private) installation_auto_update=false ;;
    *) installation_auto_update=true ;;
esac
printf '{"channel":"%s","release_channel":"%s","auto_update":%s}\n' \
    "$DELIVERY_CHANNEL" "$RELEASE_CHANNEL" "$installation_auto_update" \
    > "$staging_dir/trae-installation.json"
if [ -n "$host_filename" ]; then cp "$host_binary" "$staging_dir/$CODE_MODE_HOST_NAME"; fi
chmod 0755 "$staging_dir/$BINARY_NAME"
if [ -n "$host_filename" ]; then chmod 0755 "$staging_dir/$CODE_MODE_HOST_NAME"; fi
"$staging_dir/$BINARY_NAME" --version >/dev/null 2>&1 ||
    die "staged binary failed the --version smoke test"
mv "$staging_dir" "$release_dir"

request_managed_release_cleanup
new_current="$STATE_DIR/.current.$$"
rm -f "$new_current"
ln -s "$(relative_symlink_target "$release_dir" "$new_current")" "$new_current"
replace_current_symlink "$new_current"

target="$INSTALL_DIR/$BINARY_NAME"
staged_target="$INSTALL_DIR/.${BINARY_NAME}.tmp.$$"
rm -f "$staged_target"
ln -s "$(relative_symlink_target "$CURRENT_LINK/$BINARY_NAME" "$staged_target")" "$staged_target"
"$staged_target" --version >/dev/null 2>&1 ||
    die "installed command link failed the --version smoke test"
mv -f "$staged_target" "$target" ||
    die "failed to activate the visible Trae CLI command"
if [ -f "${target}.bak" ] || [ -L "${target}.bak" ]; then
    rm -f "${target}.bak"
    info "Removed the legacy fixed-path backup."
fi
"$target" --version >/dev/null 2>&1 ||
    die "installed binary failed the --version smoke test"
request_managed_release_cleanup
if [ "$DELIVERY_CHANNEL" = internal ]; then
    printf '%s\n' "$VERSION" > "$STATE_DIR/.current_version.$$"
    mv -f "$STATE_DIR/.current_version.$$" "$STATE_DIR/current_version"
fi

for name in $COMPAT_NAMES; do
    compat="$INSTALL_DIR/$name"
    compat_target="$(relative_symlink_target "$target" "$compat")"
    if [ ! -e "$compat" ] && [ ! -L "$compat" ]; then
        ln -s "$compat_target" "$compat"
        info "Created compatibility command: $compat"
    elif [ -L "$compat" ]; then
        existing_compat_target="$(readlink "$compat" 2>/dev/null || true)"
        if [ "$existing_compat_target" = "$compat_target" ]; then
            continue
        fi
        if [ "$existing_compat_target" = "$target" ] ||
            [ "$(real_path "$compat")" = "$(real_path "$target")" ]; then
            staged_compat="$INSTALL_DIR/.${name}.tmp.$$"
            rm -f "$staged_compat"
            ln -s "$compat_target" "$staged_compat"
            mv -f "$staged_compat" "$compat"
        else
            warn "Leaving existing command unchanged: $compat"
        fi
    elif [ "$compat" != "$target" ]; then
        warn "Leaving existing command unchanged: $compat"
    fi
done

version_tmp="$STATE_DIR/.current_version.$$"
printf '%s\n' "$VERSION" > "$version_tmp"
mv -f "$version_tmp" "$STATE_DIR/current_version"
release_install_lock

install_dependencies "$os" "$platform"
check_node_dependency
ensure_path
maybe_remove_brew "$brew_marker"
check_path_priority

info "Trae CLI ${VERSION} installed successfully"
print_usage_guidance

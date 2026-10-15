#!/bin/zsh

emulate -LR zsh
setopt errexit nounset pipefail
unsetopt xtrace verbose

for secret_name in ONEAPI_TOKEN OPENAI_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY \
  AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN \
  HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy; do
  unset "$secret_name" 2>/dev/null || true
done
unset secret_name
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"

readonly SCRIPT_PATH="${0:A}"
readonly SKILL_ROOT="${SCRIPT_PATH:h:h}"
readonly GALLERY="$SKILL_ROOT/scripts/theme-gallery.mjs"
readonly VERIFICATION_SUMMARY="$SKILL_ROOT/scripts/verification-summary.mjs"
readonly OWNER_MARKER="$SKILL_ROOT/.codex-wallpaper-managed"
readonly COMPANION_VERSION_FILE="$SKILL_ROOT/VERSION"
readonly EXPECTED_COMPANION_VERSION='0.2.0'
readonly USER_HOME="${HOME:?无法确定用户目录}"
readonly ENGINE_ROOT="$USER_HOME/.codex/codex-dream-skin-studio"
readonly ENGINE_SCRIPTS="$ENGINE_ROOT/scripts"
readonly ENGINE_VERSION_FILE="$ENGINE_ROOT/VERSION"
readonly EXPECTED_ENGINE_VERSION='1.5.20'
readonly COMMON_MACOS="$ENGINE_SCRIPTS/common-macos.sh"
readonly STATE_ROOT="$USER_HOME/Library/Application Support/CodexDreamSkinStudio"
readonly THEMES_ROOT="$STATE_ROOT/themes"
readonly ACTIVE_THEME="$STATE_ROOT/theme"
readonly INJECTOR="$ENGINE_SCRIPTS/injector.mjs"
readonly SWITCH_THEME="$ENGINE_SCRIPTS/switch-theme-macos.sh"
readonly LOAD_IMAGE="$ENGINE_SCRIPTS/load-image-theme-macos.sh"
readonly DIMENSION_CHECKER="$ENGINE_SCRIPTS/check-image-dimensions.mjs"
readonly COMPANION_STATE="$USER_HOME/Library/Application Support/CodexWallpaper"
readonly NONCE_ROOT="$COMPANION_STATE/nonces"
readonly RESTART_STATE="$COMPANION_STATE/restart-status"
readonly RESTART_LOG="$COMPANION_STATE/restart.log"
readonly RESTART_LOCK="$COMPANION_STATE/restart-apply.lock"
readonly RESTART_LOCK_OWNER="$RESTART_LOCK/owner"
readonly RESTART_LOCK_STALE_AFTER=120
readonly PORT=9341

typeset -ga THEME_IDS=()
typeset -ga THEME_NAMES=()
typeset -g APPLY_RESULT_NOTE=''
typeset -g VERIFICATION_NOTE=''
typeset -g NODE=''
typeset -g CODEX_BIN=''
typeset -g CODEX_APP=''
typeset -g RESTART_WORKER_ID=''
typeset -g RESTART_LOCK_TOKEN=''
typeset -g RESTART_OPERATION_ID=''
typeset -g RESTART_OWNER_TUPLE=''
typeset -g RESTART_NONCE_PATH=''
typeset -g RESTART_SCHEDULER_ACKED=0

die() {
  print -u2 -- "错误：$*"
  return 1
}

usage() {
  print -- '用法：'
  print -- '  codex-wallpaper.zsh list'
  print -- '  codex-wallpaper.zsh status'
  print -- '  codex-wallpaper.zsh gallery'
  print -- '  codex-wallpaper.zsh apply <名称或ID>'
  print -- '  codex-wallpaper.zsh restart-apply <名称或ID> --yes'
  print -- '  codex-wallpaper.zsh import <图片路径> <主题名称>'
}

read_engine_version() {
  [[ -f "$ENGINE_VERSION_FILE" && ! -L "$ENGINE_VERSION_FILE" ]] || return 1
  local value="$(/bin/cat "$ENGINE_VERSION_FILE" 2>/dev/null || true)"
  value="${value//$'\r'/}"
  value="${value//$'\n'/}"
  [[ -n "$value" ]] || return 1
  print -r -- "$value"
}

engine_support_label() {
  local actual="$(read_engine_version 2>/dev/null || true)"
  if [[ -z "$actual" ]]; then
    print -- '缺失（只读可用；变更已禁用）'
  elif [[ "$actual" != "$EXPECTED_ENGINE_VERSION" ]]; then
    print -- "不受支持：$actual（要求 $EXPECTED_ENGINE_VERSION；只读可用）"
  else
    print -- "受支持：$actual"
  fi
}

discover_upstream_runtime() {
  [[ -f "$COMMON_MACOS" && ! -L "$COMMON_MACOS" ]] || die 'Dream Skin 缺少 common-macos.sh。'
  local output
  output="$(/bin/bash -c '
    source "$1"
    discover_codex_app
    require_macos_runtime quick
    printf "%s\n%s\n%s\n" "$CODEX_BUNDLE" "$CODEX_EXE" "$NODE"
  ' _ "$COMMON_MACOS" 2>/dev/null)" || die '无法通过 Dream Skin 验证 Codex.app/ChatGPT.app 与内置 Node。'
  local -a fields=("${(@f)output}")
  (( ${#fields} == 3 )) || die 'Dream Skin 返回了无效的运行时信息。'
  CODEX_APP="$fields[1]"
  CODEX_BIN="$fields[2]"
  NODE="$fields[3]"
  [[ -d "$CODEX_APP" && -x "$CODEX_BIN" && -x "$NODE" ]] || die '验证后的 Codex 运行时不完整。'
}

require_mutation_runtime() {
  [[ -f "$COMPANION_VERSION_FILE" && ! -L "$COMPANION_VERSION_FILE" \
    && "$(/bin/cat "$COMPANION_VERSION_FILE")" == "$EXPECTED_COMPANION_VERSION" ]] \
    || die "companion 版本必须精确为 $EXPECTED_COMPANION_VERSION。"
  [[ -f "$OWNER_MARKER" && ! -L "$OWNER_MARKER" \
    && "$(/bin/cat "$OWNER_MARKER")" == 'managed-by-codex-wallpaper' ]] \
    || die '缺少有效的 managed-owner 标记。'
  local actual="$(read_engine_version 2>/dev/null || true)"
  [[ "$actual" == "$EXPECTED_ENGINE_VERSION" ]] \
    || die "变更要求 Dream Skin $EXPECTED_ENGINE_VERSION；当前为 ${actual:-缺失}。"
  discover_upstream_runtime
  [[ -f "$INJECTOR" ]] || die '找不到 Dream Skin 注入器。'
  [[ -f "$GALLERY" && ! -L "$GALLERY" ]] || die '找不到安全的壁纸缩略图选择器。'
  [[ -f "$VERIFICATION_SUMMARY" && ! -L "$VERIFICATION_SUMMARY" ]] || die '找不到安全的验证摘要程序。'
  [[ -x "$SWITCH_THEME" || -f "$SWITCH_THEME" ]] || die '找不到 Dream Skin 主题切换脚本。'
  [[ -x "$LOAD_IMAGE" || -f "$LOAD_IMAGE" ]] || die '找不到 Dream Skin 图片导入脚本。'
  [[ -d "$THEMES_ROOT" ]] || die '尚未找到 Dream Skin 主题库。'
}

read_theme_name() {
  local theme_json="$1"
  local value="$(/usr/bin/plutil -extract name raw -o - "$theme_json" 2>/dev/null || true)"
  value="${value//$'\r'/ }"
  value="${value//$'\n'/ }"
  [[ -n "$value" ]] || return 1
  print -rn -- "$value"
}

collect_themes() {
  THEME_IDS=()
  THEME_NAMES=()
  [[ -d "$THEMES_ROOT" && ! -L "$THEMES_ROOT" ]] || return 0
  local dir id name
  for dir in "$THEMES_ROOT"/*(N/); do
    [[ ! -L "$dir" && -f "$dir/theme.json" && ! -L "$dir/theme.json" ]] || continue
    id="${dir:t}"
    name="$(read_theme_name "$dir/theme.json" 2>/dev/null || true)"
    [[ -n "$name" ]] || name="$id"
    THEME_IDS+=("$id")
    THEME_NAMES+=("$name")
  done
}

validate_theme_id() {
  local id="$1"
  [[ "$id" == [A-Za-z0-9]* && "$id" != *[^A-Za-z0-9._-]* && ${#id} -le 80 ]] \
    || die '主题 ID 格式不安全。'
}

resolve_theme() {
  local query="$1"
  [[ -n "$query" ]] || die '主题名称或 ID 不能为空。'
  collect_themes
  local -a matches=()
  local index
  for (( index = 1; index <= ${#THEME_IDS}; index++ )); do
    if [[ "${THEME_IDS[index]}" == "$query" ]]; then
      print -r -- "${THEME_IDS[index]}"
      return 0
    fi
    [[ "${THEME_NAMES[index]}" == "$query" ]] && matches+=("${THEME_IDS[index]}")
  done
  (( ${#matches} > 0 )) || die "找不到主题：$query"
  if (( ${#matches} > 1 )); then
    print -u2 -- "错误：主题名称重复，请改用 ID：${(j:, :)matches}"
    return 1
  fi
  print -r -- "$matches[1]"
}

archive_dir() {
  local id="$1"
  validate_theme_id "$id"
  local dir="$THEMES_ROOT/$id"
  [[ -d "$dir" && ! -L "$dir" ]] || die "主题目录无效：$id"
  local root_real="${THEMES_ROOT:A}"
  local dir_real="${dir:A}"
  [[ "$dir_real" == "$root_real/"* ]] || die '主题目录越出了主题库。'
  print -r -- "$dir_real"
}

validate_payload() {
  local dir="$1"
  [[ -f "$dir/theme.json" && ! -L "$dir/theme.json" ]] || die '主题缺少有效的 theme.json。'
  "$NODE" "$INJECTOR" --check-payload --theme-dir "$dir" >/dev/null 2>&1 \
    || die "主题内容校验失败：${dir:t}"
}

upstream_owns_port() {
  [[ -n "$CODEX_BIN" ]] || return 1
  /bin/bash -c '
    source "$1"
    CODEX_EXE="$2"
    port_belongs_to_codex "$3"
  ' _ "$COMMON_MACOS" "$CODEX_BIN" "$PORT" >/dev/null 2>&1
}

# 返回 0=安全可用，10=未监听，20=存在不安全或无关监听者。
validate_cdp_listener() {
  local records
  records="$(/usr/sbin/lsof -nP -a -iTCP:$PORT -sTCP:LISTEN -Fpn 2>/dev/null || true)"
  [[ -n "$records" ]] || return 10

  local -a listener_pids=()
  local current_pid='' line address
  while IFS= read -r line; do
    case "$line" in
      p*)
        current_pid="${line#p}"
        [[ "$current_pid" == <-> ]] || return 20
        (( ${listener_pids[(Ie)$current_pid]} )) || listener_pids+=("$current_pid")
        ;;
      n*)
        address="${line#n}"
        case "$address" in
          127.0.0.1:$PORT|'[::1]':$PORT) ;;
          *) return 20 ;;
        esac
        ;;
    esac
  done <<< "$records"
  (( ${#listener_pids} > 0 )) || return 20

  upstream_owns_port || return 20

  local targets
  targets="$(/usr/bin/curl --noproxy '*' --fail --silent --show-error --max-time 2 \
    "http://127.0.0.1:$PORT/json/list" 2>/dev/null || true)"
  [[ -n "$targets" ]] || return 20
  "$NODE" -e '
const items = JSON.parse(process.argv[1]);
if (!Array.isArray(items) || !items.some((item) => {
  if (item?.type !== "page" || typeof item.url !== "string" || !item.url.startsWith("app://")) return false;
  try {
    const url = new URL(item.webSocketDebuggerUrl);
    return url.protocol === "ws:" && ["127.0.0.1", "localhost", "::1"].includes(url.hostname)
      && url.port === "9341" && /^\/devtools\/page\/[A-Za-z0-9._-]+$/.test(url.pathname);
  } catch { return false; }
})) process.exit(1);
' "$targets" >/dev/null 2>&1 || return 20
  return 0
}

listener_state() {
  local code=0
  validate_cdp_listener || code=$?
  if (( code == 0 )); then
    print -- '安全可用'
  elif (( code == 10 )); then
    print -- '未开启'
  else
    print -- '不安全（已拒绝）'
  fi
  return "$code"
}

switch_without_apply() {
  local id="$1"
  /bin/bash "$SWITCH_THEME" --id "$id" --no-apply >/dev/null \
    || die "保存主题选择失败：$id"
  validate_payload "$ACTIVE_THEME"
}

summarize_verification() {
  local verify_code="$1" verify_output="$2" mode="$3"
  local saved_id="$(/usr/bin/plutil -extract id raw -o - "$ACTIVE_THEME/theme.json" 2>/dev/null || true)"
  VERIFICATION_NOTE=''
  [[ -f "$VERIFICATION_SUMMARY" && ! -L "$VERIFICATION_SUMMARY" ]] \
    || { VERIFICATION_NOTE='验证结果：[invalid-report] 缺少验证摘要程序。'; return 1; }
  local code=0
  VERIFICATION_NOTE="$(print -rn -- "$verify_output" | "$NODE" "$VERIFICATION_SUMMARY" \
    "$verify_code" "$mode" "$EXPECTED_ENGINE_VERSION" "$saved_id" 2>/dev/null)" || code=$?
  [[ -n "$VERIFICATION_NOTE" ]] || VERIFICATION_NOTE='验证结果：[invalid-report] 无法解析验证结果。'
  return "$code"
}

verify_active() {
  local verify_output verify_code=0
  verify_output="$("$NODE" "$INJECTOR" --verify --port "$PORT" \
    --theme-dir "$ACTIVE_THEME" --timeout-ms 10000 2>/dev/null)" || verify_code=$?
  summarize_verification "$verify_code" "$verify_output" verify
}

inject_active_once() {
  APPLY_RESULT_NOTE=''
  local inject_output inject_code=0 summary_code=0
  inject_output="$("$NODE" "$INJECTOR" --once --port "$PORT" --theme-dir "$ACTIVE_THEME" \
    --timeout-ms 8000 2>/dev/null)" || inject_code=$?
  summarize_verification "$inject_code" "$inject_output" once || summary_code=$?
  if (( summary_code != 0 && summary_code != 3 )); then
    print -u2 -r -- "$VERIFICATION_NOTE"
    die '壁纸注入未通过校验。'
    return 1
  fi
  summary_code=0
  verify_active || summary_code=$?
  if (( summary_code == 0 )); then
    return 0
  elif (( summary_code == 3 )); then
    APPLY_RESULT_NOTE='主题身份与结构匹配；DOM 报告 hidden，尚未确认可见效果，请切回窗口检查。'
    return 0
  fi
  print -u2 -r -- "$VERIFICATION_NOTE"
  die '壁纸已注入，但界面校验未通过。'
}

list_themes() {
  collect_themes
  print -- "Dream Skin 引擎：$(engine_support_label)"
  print -- "已保存主题：${#THEME_IDS} 个"
  local index
  for (( index = 1; index <= ${#THEME_IDS}; index++ )); do
    print -r -- "- ${THEME_NAMES[index]}  [${THEME_IDS[index]}]"
  done
}

ensure_companion_state() {
  umask 077
  [[ ! -L "$COMPANION_STATE" && ! -L "$NONCE_ROOT" ]] || die 'companion 状态目录不能是符号链接。'
  /bin/mkdir -p "$NONCE_ROOT"
  /bin/chmod 700 "$COMPANION_STATE" "$NONCE_ROOT"
  [[ ! -L "$RESTART_STATE" && ! -L "$RESTART_LOG" ]] || die 'companion 状态文件不能是符号链接。'
}

process_birth() {
  local pid="$1"
  /bin/ps -p "$pid" -o lstart= 2>/dev/null \
    | /usr/bin/awk '{$1=$1; print}'
}

make_owner_tuple() {
  print -r -- "$1"$'\n'"$2"$'\n'"$3"$'\n'"$4"$'\n'"$5"$'\n'"$6"
}

valid_owner_tuple() {
  local tuple="$1"
  local -a fields=("${(@f)tuple}")
  (( ${#fields} == 6 )) || return 1
  [[ ${#fields[1]} == 32 && "$fields[1]" != *[^0-9a-f]* \
    && -n "$fields[2]" && "$fields[2]" != *$'\n'* \
    && ${#fields[3]} == 32 && "$fields[3]" != *[^0-9a-f]* \
    && "$fields[4]" == (scheduler|worker) \
    && "$fields[5]" == <-> && -n "$fields[6]" ]]
}

read_owner_tuple() {
  [[ -f "$RESTART_LOCK_OWNER" && ! -L "$RESTART_LOCK_OWNER" ]] || return 1
  /bin/cat "$RESTART_LOCK_OWNER" 2>/dev/null
}

owner_matches() {
  local expected="$1"
  local current="$(read_owner_tuple 2>/dev/null || true)"
  [[ -n "$current" && "$current" == "$expected" ]]
}

tuple_owned_by_current_process() {
  local tuple="$1"
  valid_owner_tuple "$tuple" || return 1
  local -a fields=("${(@f)tuple}")
  [[ "$fields[5]" == "$$" && "$fields[6]" == "$(process_birth "$$")" ]]
}

publish_owner_tuple() {
  local tuple="$1"
  valid_owner_tuple "$tuple" || return 1
  [[ -d "$RESTART_LOCK" && ! -L "$RESTART_LOCK" ]] || return 1
  [[ "${CODEX_WALLPAPER_PROTOCOL_TEST:-}" != 1 \
    || "${CODEX_WALLPAPER_FAILPOINT:-}" != owner-publication ]] || return 1
  local temporary="$RESTART_LOCK/.owner.$$"
  print -rn -- "$tuple" >| "$temporary" || return 1
  /bin/chmod 600 "$temporary" || { /bin/rm -f "$temporary"; return 1; }
  /bin/mv -f "$temporary" "$RESTART_LOCK_OWNER"
}

recover_dead_restart_lock() {
  [[ -d "$RESTART_LOCK" && ! -L "$RESTART_LOCK" \
    && -f "$RESTART_LOCK_OWNER" && ! -L "$RESTART_LOCK_OWNER" ]] || return 1
  local tuple="$(read_owner_tuple 2>/dev/null || true)"
  valid_owner_tuple "$tuple" || return 1
  local -a owner=("${(@f)tuple}")
  local pid="$owner[5]" birth="$owner[6]" token="$owner[3]"
  local created="$(/usr/bin/stat -f '%m' "$RESTART_LOCK" 2>/dev/null || true)"
  [[ "$created" == <-> ]] || return 1
  local now="$(/bin/date +%s)"
  (( now >= created && now - created >= RESTART_LOCK_STALE_AFTER )) || return 1
  local current_birth="$(process_birth "$pid")"
  [[ -z "$current_birth" || "$current_birth" != "$birth" ]] || return 1

  local stale="$COMPANION_STATE/.restart-apply.stale.$$.$token"
  [[ ! -e "$stale" && ! -L "$stale" ]] || return 1
  /bin/mv "$RESTART_LOCK" "$stale" 2>/dev/null || return 1
  local moved="$(/bin/cat "$stale/owner" 2>/dev/null || true)"
  if [[ "$moved" != "$tuple" ]]; then
    [[ ! -e "$RESTART_LOCK" && ! -L "$RESTART_LOCK" ]] && /bin/mv "$stale" "$RESTART_LOCK" 2>/dev/null
    return 1
  fi
  /bin/rm -rf "$stale"
}

acquire_restart_lock() {
  local theme_id="$1"
  ensure_companion_state
  [[ ! -L "$RESTART_LOCK" ]] || { die '重启锁不能是符号链接。'; return 1; }
  local token="$(/usr/bin/openssl rand -hex 16 2>/dev/null || true)"
  [[ ${#token} == 32 && "$token" != *[^0-9a-f]* ]] || { die '无法生成重启锁凭据。'; return 1; }
  local operation_id="$(/usr/bin/openssl rand -hex 16 2>/dev/null || true)"
  [[ ${#operation_id} == 32 && "$operation_id" != *[^0-9a-f]* ]] \
    || { die '无法生成重启操作 ID。'; return 1; }
  local attempt
  for attempt in 1 2; do
    if /bin/mkdir "$RESTART_LOCK" 2>/dev/null; then
      local birth="$(process_birth "$$")"
      local tuple=''
      if [[ "${CODEX_WALLPAPER_PROTOCOL_TEST:-}" == 1 \
        && "${CODEX_WALLPAPER_FAILPOINT:-}" == lock-after-mkdir ]]; then
        /bin/rm -rf "$RESTART_LOCK"
        die '测试注入：锁初始化失败。'
        return 1
      fi
      if ! /bin/chmod 700 "$RESTART_LOCK" || [[ -z "$birth" ]]; then
        /bin/rm -rf "$RESTART_LOCK"
        die '无法初始化重启锁。'
        return 1
      fi
      tuple="$(make_owner_tuple "$operation_id" "$theme_id" "$token" scheduler "$$" "$birth")"
      if ! publish_owner_tuple "$tuple"; then
        /bin/rm -rf "$RESTART_LOCK"
        die '无法发布重启锁所有者。'
        return 1
      fi
      RESTART_LOCK_TOKEN="$token"
      RESTART_OPERATION_ID="$operation_id"
      RESTART_OWNER_TUPLE="$tuple"
      return 0
    fi
    (( attempt == 1 )) && recover_dead_restart_lock && continue
    die '已有 restart-apply 正在运行；已拒绝重复重启。'
    return 1
  done
}

claim_restart_lock() {
  local scheduled_tuple="$1"
  local nonce_path="$2"
  [[ -d "$RESTART_LOCK" && ! -L "$RESTART_LOCK" \
    && -f "$RESTART_LOCK_OWNER" && ! -L "$RESTART_LOCK_OWNER" ]] \
    || { die '重启锁已丢失。'; return 1; }
  valid_owner_tuple "$scheduled_tuple" && owner_matches "$scheduled_tuple" \
    || { die '重启锁所有权无效。'; return 1; }
  [[ "$(/bin/cat "$nonce_path" 2>/dev/null || true)" == "$scheduled_tuple" ]] \
    || { die '一次性重启凭据与锁不匹配。'; return 1; }
  /bin/mkdir "$RESTART_LOCK/claim" 2>/dev/null \
    || { die '重启锁已被其他 worker 认领。'; return 1; }
  [[ ! -e "$RESTART_LOCK/decision" && ! -L "$RESTART_LOCK/decision" ]] \
    || { die '重启操作已取消。'; return 1; }
  owner_matches "$scheduled_tuple" || { die '重启锁在认领期间发生变化。'; return 1; }
  local -a scheduled=("${(@f)scheduled_tuple}")
  local birth="$(process_birth "$$")"
  [[ -n "$birth" ]] || { die '无法验证 worker 进程。'; return 1; }
  local worker_tuple="$(make_owner_tuple "$scheduled[1]" "$scheduled[2]" "$scheduled[3]" worker "$$" "$birth")"
  print -rn -- "$worker_tuple" >| "$RESTART_LOCK/claim/owner"
  /bin/chmod 600 "$RESTART_LOCK/claim/owner"
  [[ ! -e "$RESTART_LOCK/decision" ]] || { die '重启操作已取消。'; return 1; }
  publish_owner_tuple "$worker_tuple" || { die '无法转移重启锁所有权。'; return 1; }
  RESTART_LOCK_TOKEN="$scheduled[3]"
  RESTART_OPERATION_ID="$scheduled[1]"
  RESTART_OWNER_TUPLE="$worker_tuple"
  consume_restart_nonce "$nonce_path" "$scheduled_tuple"
  if [[ "${CODEX_WALLPAPER_PROTOCOL_TEST:-}" == 1 \
    && "${CODEX_WALLPAPER_CLAIM_ACK_DELAY:-0}" != 0 ]]; then
    /bin/sleep "$CODEX_WALLPAPER_CLAIM_ACK_DELAY"
  fi
  [[ ! -f "$RESTART_LOCK/decision/cancel" ]] \
    || { die 'scheduler 已取消 worker 认领。'; return 1; }
  print -rn -- "$worker_tuple" >| "$RESTART_LOCK/ack"
  /bin/chmod 600 "$RESTART_LOCK/ack"
}

release_restart_lock() {
  local expected="${1:-}"
  [[ -n "$expected" && -d "$RESTART_LOCK" && ! -L "$RESTART_LOCK" \
    && -f "$RESTART_LOCK_OWNER" && ! -L "$RESTART_LOCK_OWNER" ]] || return 0
  owner_matches "$expected" && tuple_owned_by_current_process "$expected" || return 1
  local -a owner=("${(@f)expected}")
  local released="$COMPANION_STATE/.restart-apply.released.$$.$owner[3]"
  [[ ! -e "$released" && ! -L "$released" ]] || return 1
  /bin/mv "$RESTART_LOCK" "$released" 2>/dev/null || return 1
  local moved="$(/bin/cat "$released/owner" 2>/dev/null || true)"
  if [[ "$moved" != "$expected" ]]; then
    [[ ! -e "$RESTART_LOCK" && ! -L "$RESTART_LOCK" ]] && /bin/mv "$released" "$RESTART_LOCK" 2>/dev/null
    return 1
  fi
  /bin/rm -rf "$released"
  RESTART_LOCK_TOKEN=''
  RESTART_OPERATION_ID=''
  RESTART_OWNER_TUPLE=''
}

write_restart_state() {
  local owner_tuple="$1" state="$2" id="$3" message="$4"
  owner_matches "$owner_tuple" && tuple_owned_by_current_process "$owner_tuple" \
    || { die '非当前所有者不能写入重启状态。'; return 1; }
  ensure_companion_state
  local timestamp="$(/bin/date -u '+%Y-%m-%dT%H:%M:%SZ')"
  local temporary="$COMPANION_STATE/.restart-status.$$"
  print -r -- "$state\t$timestamp\t$id\t$message" >| "$temporary"
  /bin/chmod 600 "$temporary"
  /bin/mv -f "$temporary" "$RESTART_STATE"
  print -r -- "$state\t$timestamp\t$id\t$message" >> "$RESTART_LOG"
  /bin/chmod 600 "$RESTART_LOG"
}

ack_matches_scheduled() {
  local ack="$1"
  local scheduled="$2"
  valid_owner_tuple "$ack" && valid_owner_tuple "$scheduled" || return 1
  local -a ack_fields=("${(@f)ack}")
  local -a scheduled_fields=("${(@f)scheduled}")
  [[ "$ack_fields[1]" == "$scheduled_fields[1]" \
    && "$ack_fields[2]" == "$scheduled_fields[2]" \
    && "$ack_fields[3]" == "$scheduled_fields[3]" \
    && "$ack_fields[4]" == worker ]]
}

scheduler_wait_for_ack() {
  local scheduled_tuple="$1"
  local loops="${2:-50}"
  local index ack=''
  for (( index = 1; index <= loops; index++ )); do
    ack="$(/bin/cat "$RESTART_LOCK/ack" 2>/dev/null || true)"
    if ack_matches_scheduled "$ack" "$scheduled_tuple" && owner_matches "$ack"; then
      /bin/mkdir "$RESTART_LOCK/decision" 2>/dev/null || return 1
      print -rn -- "$ack" >| "$RESTART_LOCK/decision/go"
      /bin/chmod 600 "$RESTART_LOCK/decision/go"
      REPLY="$ack"
      return 0
    fi
    /bin/sleep 0.1
  done
  /bin/mkdir "$RESTART_LOCK/decision" 2>/dev/null || return 1
  print -rn -- "$scheduled_tuple" >| "$RESTART_LOCK/decision/cancel"
  /bin/chmod 600 "$RESTART_LOCK/decision/cancel"
  owner_matches "$scheduled_tuple" && release_restart_lock "$scheduled_tuple" >/dev/null 2>&1
  return 1
}

restart_scheduler_cleanup() {
  if (( RESTART_SCHEDULER_ACKED == 0 )) && [[ -n "$RESTART_NONCE_PATH" \
    && "$RESTART_NONCE_PATH" == "$NONCE_ROOT/restart."* \
    && -f "$RESTART_NONCE_PATH" && ! -L "$RESTART_NONCE_PATH" ]]; then
    /bin/rm -f "$RESTART_NONCE_PATH" 2>/dev/null || true
  fi
  release_restart_lock "${RESTART_OWNER_TUPLE:-}" >/dev/null 2>&1 || true
}

worker_wait_for_go() {
  local worker_tuple="$1"
  local loops="${2:-100}"
  local index
  for (( index = 1; index <= loops; index++ )); do
    [[ -f "$RESTART_LOCK/decision/cancel" ]] && return 1
    if [[ "$(/bin/cat "$RESTART_LOCK/decision/go" 2>/dev/null || true)" == "$worker_tuple" ]] \
      && owner_matches "$worker_tuple"; then
      return 0
    fi
    /bin/sleep 0.1
  done
  return 1
}

show_restart_status() {
  if [[ -f "$RESTART_STATE" && ! -L "$RESTART_STATE" ]]; then
    local line="$(/usr/bin/tail -n 1 "$RESTART_STATE" 2>/dev/null || true)"
    [[ -n "$line" ]] && print -r -- "最近一次重启任务：$line" || print -- '最近一次重启任务：无'
  else
    print -- '最近一次重启任务：无'
  fi
}

show_status() {
  collect_themes
  local active='无'
  if [[ -f "$ACTIVE_THEME/theme.json" ]]; then
    active="$(read_theme_name "$ACTIVE_THEME/theme.json" 2>/dev/null || true)"
    [[ -n "$active" ]] || active='未知'
  fi
  local cdp='无法验证' code=0 actual="$(read_engine_version 2>/dev/null || true)"
  if [[ "$actual" == "$EXPECTED_ENGINE_VERSION" ]] && discover_upstream_runtime 2>/dev/null; then
    cdp="$(listener_state)" || code=$?
  fi
  print -- "Dream Skin 引擎：$(engine_support_label)"
  print -- "主题库：${#THEME_IDS} 个"
  print -- "当前保存主题：$active"
  print -- "热切换端口 $PORT：$cdp"
  show_restart_status
  if [[ "$actual" == "$EXPECTED_ENGINE_VERSION" && "$cdp" == '安全可用' ]]; then
    local verification_code=0
    verify_active || verification_code=$?
    print -r -- "$VERIFICATION_NOTE"
    (( verification_code == 0 || verification_code == 3 )) || return 1
  else
    print -- '实时主题：未验证（需要受支持的引擎、有效运行时和安全 CDP 端口）。'
  fi
  (( code != 20 )) || return 1
}

hot_apply() {
  local query="$1"
  require_mutation_runtime
  local id dir
  id="$(resolve_theme "$query")"
  dir="$(archive_dir "$id")"
  validate_payload "$dir"
  if validate_cdp_listener; then
    :
  else
    local code=$?
    (( code == 10 )) && die "Codex 未开启安全热切换端口；请使用 restart-apply '$id' --yes。"
    die "端口 $PORT 存在不安全或无关监听者，已拒绝操作。"
  fi
  switch_without_apply "$id"
  inject_active_once
  local name="$(read_theme_name "$dir/theme.json" 2>/dev/null || print -r -- "$id")"
  if [[ -n "$APPLY_RESULT_NOTE" ]]; then
    print -- "已应用：$name [$id]；$APPLY_RESULT_NOTE"
  else
    print -- "已应用并验证：$name [$id]"
  fi
}

find_chatgpt_main() {
  local -a pids
  pids=("${(@f)$(/bin/ps -axo pid=,command= 2>/dev/null | /usr/bin/awk -v bin="$CODEX_BIN" '$2 == bin { print $1 }' || true)}")
  pids=("${(@)pids:#}")
  (( ${#pids} == 1 )) || die "需要且只能有一个 Codex 主进程，当前找到 ${#pids} 个。"
  print -r -- "$pids[1]"
}

consume_restart_nonce() {
  local nonce_path="$1"
  local expected_tuple="$2"
  [[ "$nonce_path" == "$NONCE_ROOT/restart."* && -f "$nonce_path" && ! -L "$nonce_path" ]] \
    || die '一次性重启凭据无效。'
  [[ "${nonce_path:h:A}" == "${NONCE_ROOT:A}" ]] || die '一次性重启凭据越出了私有目录。'
  [[ "$(/usr/bin/stat -f '%Lp' "$nonce_path" 2>/dev/null || true)" == 600 \
    && "$(/usr/bin/stat -f '%u' "$nonce_path" 2>/dev/null || true)" == "$(/usr/bin/id -u)" ]] \
    || die '一次性重启凭据权限无效。'
  local consumed="$NONCE_ROOT/.consumed.$$"
  /bin/mv "$nonce_path" "$consumed" || die '一次性重启凭据已被消费。'
  local nonce="$(/bin/cat "$consumed" 2>/dev/null || true)"
  /bin/rm -f "$consumed"
  [[ "$nonce" == "$expected_tuple" ]] || die '一次性重启凭据 tuple 无效。'
}

restart_worker() {
  local id="$1"
  local nonce_path="$2"
  local operation_id="$3"
  local lock_token="$4"
  local dir main_pid index code
  RESTART_WORKER_ID="$id"
  RESTART_LOCK_TOKEN="$lock_token"
  RESTART_OPERATION_ID="$operation_id"
  trap 'restart_worker_exit $?' EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  local scheduled_tuple="$(/bin/cat "$nonce_path" 2>/dev/null || true)"
  local -a scheduled=("${(@f)scheduled_tuple}")
  (( ${#scheduled} == 6 )) && [[ "$scheduled[1]" == "$operation_id" \
    && "$scheduled[2]" == "$id" && "$scheduled[3]" == "$lock_token" \
    && "$scheduled[4]" == scheduler ]] || die 'worker 参数与 nonce tuple 不匹配。'
  claim_restart_lock "$scheduled_tuple" "$nonce_path"
  local worker_tuple="$RESTART_OWNER_TUPLE"
  worker_wait_for_go "$worker_tuple" || die 'scheduler 未确认 worker；已取消重启。'
  write_restart_state "$worker_tuple" 'scheduled' "$id" '已安排一次性重启'
  require_mutation_runtime
  write_restart_state "$worker_tuple" 'running' "$id" '正在重启并应用'
  dir="$(archive_dir "$id")"
  validate_payload "$dir"
  main_pid="$(find_chatgpt_main)"

  /bin/kill -TERM "$main_pid" || die '无法终止 Codex 主进程。'
  for index in {1..60}; do
    /bin/kill -0 "$main_pid" 2>/dev/null || break
    /bin/sleep 0.25
  done
  /bin/kill -0 "$main_pid" 2>/dev/null && die 'Codex 在 15 秒内没有退出；未强制终止，也未重新打开。'

  [[ -z "$(/usr/sbin/lsof -nP -a -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null || true)" ]] \
    || die "端口 $PORT 仍被占用；已拒绝重新打开 Codex。"

  /usr/bin/open -na "$CODEX_APP" --args \
    --remote-debugging-address=127.0.0.1 --remote-debugging-port="$PORT" \
    || die '重新打开 Codex 失败。'

  code=10
  for index in {1..180}; do
    if validate_cdp_listener; then
      code=0
      break
    else
      code=$?
    fi
    (( code == 20 )) && break
    /bin/sleep 0.25
  done
  (( code == 0 )) || die 'Codex 已重新打开，但安全热切换端口未通过校验。'
  switch_without_apply "$id"
  inject_active_once
  local name="$(read_theme_name "$dir/theme.json" 2>/dev/null || print -r -- "$id")"
  local result_message
  if [[ -n "$APPLY_RESULT_NOTE" ]]; then
    result_message="已应用：$name；$APPLY_RESULT_NOTE"
  else
    result_message="已应用并验证：$name"
  fi
  write_restart_state "$worker_tuple" 'succeeded' "$id" "$result_message"
  release_restart_lock "$worker_tuple"
  trap - EXIT HUP INT TERM
  /usr/bin/osascript -e 'on run argv' \
    -e 'display notification (item 1 of argv) with title "Codex 壁纸"' \
    -e 'end run' "$result_message" >/dev/null 2>&1 || true
}

restart_worker_exit() {
  local code="${1:-1}"
  if (( code != 0 )); then
    write_restart_state "${RESTART_OWNER_TUPLE:-}" 'failed' "${RESTART_WORKER_ID:-未知}" \
      '重启或应用失败' 2>/dev/null || true
    /usr/bin/osascript -e 'display notification "重启或应用失败，请运行壁纸状态检查。" with title "Codex 壁纸"' \
      >/dev/null 2>&1 || true
  fi
  release_restart_lock "${RESTART_OWNER_TUPLE:-}" >/dev/null 2>&1 || true
}

schedule_restart_apply() {
  local query="$1"
  local confirmation="$2"
  [[ "$confirmation" == '--yes' ]] || die '重启操作必须显式提供 --yes。'
  require_mutation_runtime
  local id dir
  id="$(resolve_theme "$query")"
  dir="$(archive_dir "$id")"
  validate_payload "$dir"
  find_chatgpt_main >/dev/null
  ensure_companion_state
  acquire_restart_lock "$id"
  RESTART_NONCE_PATH=''
  RESTART_SCHEDULER_ACKED=0
  trap 'restart_scheduler_cleanup' EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  local lock_token="$RESTART_LOCK_TOKEN"
  local operation_id="$RESTART_OPERATION_ID"
  local scheduled_tuple="$RESTART_OWNER_TUPLE"
  local nonce_file
  nonce_file="$(/usr/bin/mktemp "$NONCE_ROOT/restart.XXXXXXXX")" || die '无法创建一次性重启凭据。'
  RESTART_NONCE_PATH="$nonce_file"
  /bin/chmod 600 "$nonce_file"
  print -rn -- "$scheduled_tuple" >| "$nonce_file" \
    || { /bin/rm -f "$nonce_file"; die '无法写入一次性重启凭据。'; }
  /bin/chmod 600 "$nonce_file"
  /usr/bin/nohup "$SCRIPT_PATH" __restart-worker "$id" "$nonce_file" "$operation_id" "$lock_token" \
    >>"$RESTART_LOG" 2>&1 &!
  if ! scheduler_wait_for_ack "$scheduled_tuple" 50; then
    die 'worker 未在 5 秒内确认；重启已取消。'
  fi
  RESTART_SCHEDULER_ACKED=1
  RESTART_LOCK_TOKEN=''
  RESTART_OPERATION_ID=''
  RESTART_OWNER_TUPLE=''
  RESTART_NONCE_PATH=''
  trap - EXIT HUP INT TERM
  print -- "已安排一次性重启并应用：$id。可运行 status 查看进度。"
}

choose_theme_gallery() {
  require_mutation_runtime
  collect_themes
  (( ${#THEME_IDS} > 0 )) || die '没有可选择的主题。'
  local selected id
  selected="$("$NODE" "$GALLERY" --serve --themes-root "$THEMES_ROOT" \
    --active-theme "$ACTIVE_THEME" --timeout-ms 600000)"
  [[ "$selected" != '__CANCEL__' ]] || { print -- '已取消。'; return 0; }
  [[ "$selected" != '__TIMEOUT__' ]] || { print -- '选择器已超时关闭。'; return 0; }
  id="$(resolve_theme "$selected")"

  if validate_cdp_listener; then
    hot_apply "$id"
    return 0
  else
    local code=$?
  fi
  (( code == 10 )) || die "端口 $PORT 存在不安全或无关监听者，已拒绝操作。"
  local decision
  decision="$(/usr/bin/osascript -e 'try' \
    -e 'display dialog "Codex 当前无法热切换。是否只重启一次并应用所选壁纸？" with title "Codex 壁纸" buttons {"取消", "重启并应用"} default button "重启并应用" cancel button "取消" with icon caution' \
    -e 'return button returned of result' \
    -e 'on error number -128' -e 'return "取消"' -e 'end try')"
  [[ "$decision" == '重启并应用' ]] || { print -- '已取消。'; return 0; }
  schedule_restart_apply "$id" --yes
}

import_image() {
  local image="$1"
  local name="$2"
  require_mutation_runtime
  [[ -n "$name" ]] || die '主题名称不能为空。'
  [[ "$image" == /* ]] || die '图片路径必须是绝对路径。'
  [[ -f "$image" && ! -L "$image" && -r "$image" ]] || die '图片不存在、不可读或是符号链接。'
  [[ -f "$DIMENSION_CHECKER" && ! -L "$DIMENSION_CHECKER" && -s "$DIMENSION_CHECKER" ]] \
    || die 'Dream Skin 安装不完整：缺少有效的 check-image-dimensions.mjs，已拒绝导入。'
  collect_themes
  local -A before=()
  local id
  for id in "${THEME_IDS[@]}"; do before[$id]=1; done

  /bin/bash "$LOAD_IMAGE" --file "$image" --name "$name" \
    --appearance dark --focus-x 0.72 --focus-y 0.45 \
    --safe-area left --task-mode ambient --no-apply >/dev/null \
    || die '图片导入失败。'

  collect_themes
  local -a added=()
  for id in "${THEME_IDS[@]}"; do
    [[ -n "${before[$id]:-}" ]] || added+=("$id")
  done
  (( ${#added} == 1 )) || die "导入完成，但无法唯一确定新增主题 ID（找到 ${#added} 个）。"
  local dir="$(archive_dir "$added[1]")"
  validate_payload "$dir"
  print -- "已导入但未应用：$name [${added[1]}]"
}

main() {
  local command="${1:-}"
  case "$command" in
    list)
      (( $# == 1 )) || die 'list 不接受其他参数。'
      list_themes
      ;;
    status)
      (( $# == 1 )) || die 'status 不接受其他参数。'
      show_status
      ;;
    gallery)
      (( $# == 1 )) || die 'gallery 不接受其他参数。'
      choose_theme_gallery
      ;;
    apply)
      (( $# == 2 )) || die 'apply 需要一个主题名称或 ID。'
      hot_apply "$2"
      ;;
    restart-apply)
      (( $# == 3 )) || die 'restart-apply 需要主题名称或 ID，以及 --yes。'
      schedule_restart_apply "$2" "$3"
      ;;
    import)
      (( $# == 3 )) || die 'import 需要图片绝对路径和主题名称。'
      import_image "$2" "$3"
      ;;
    __restart-worker)
      (( $# == 5 )) || die '内部命令不可直接使用。'
      restart_worker "$2" "$3" "$4" "$5"
      ;;
    -h|--help|help|'')
      usage
      ;;
    *)
      usage >&2
      die "未知命令：$command"
      ;;
  esac
}

if [[ "${CODEX_WALLPAPER_SOURCE_ONLY:-}" != 1 ]]; then
  main "$@"
fi

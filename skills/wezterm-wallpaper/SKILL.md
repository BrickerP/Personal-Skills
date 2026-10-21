---
name: wezterm-wallpaper
description: Pick, preview, and switch WezTerm background wallpapers on macOS through a local gallery, with auto brightness and a blur/subtle mode so wallpapers never fight the TUI text. Use when the user asks to change or choose the WezTerm background/wallpaper (换壁纸、换背景、选壁纸), or wants their terminal to match a desktop theme.
---

# WezTerm Wallpaper

Use `scripts/wezterm-bg.mjs`; do not hand-edit `~/.wezterm.lua` for wallpaper changes.

## Commands

```zsh
scripts/wezterm-bg.mjs list                    # 列出所有壁纸（* = 当前）
scripts/wezterm-bg.mjs current                 # 当前壁纸 / 亮度
scripts/wezterm-bg.mjs set '<name|id|子串>'     # 切换（自动亮度 + 柔和模式）
scripts/wezterm-bg.mjs subtle on|off           # 柔和模式：模糊 + 降对比/饱和
scripts/wezterm-bg.mjs brightness 0.05-1       # 手动调亮度
scripts/wezterm-bg.mjs off                     # 关闭壁纸，回纯色
scripts/wezterm-bg.mjs gallery                 # 打开可视化选择器
```

`set` 支持唯一子串匹配（如 `set 银河`）；重名时按 ID。

## How it works

- 壁纸来源自动扫描：`~/.config/wezterm/backgrounds/` 与 Dream Skin 主题库
  `~/Library/Application Support/CodexDreamSkinStudio/themes/*/background.*`（新导入主题自动出现）。
- 状态写入 `~/.config/wezterm/background.conf`（`file` / `display` / `brightness` / `subtle`）。
- `~/.wezterm.lua` 读取该文件并注册到 `wezterm.add_to_config_reload_watch_list`，改状态即热重载，无需重启 WezTerm。
- 柔和模式（默认开）：ffmpeg `gblur=sigma=30` + `eq=contrast=0.55:brightness=-0.08:saturation=0.75`，
  结果缓存在 `~/.cache/wezterm-bg/subtle/`；没有 ffmpeg 时退回 sips 缩/放模糊。
- 自动亮度：`sips` 缩到 1×1 BMP 取平均亮度，浅色图压得更狠
  （subtle: 目标 0.07/上限 0.45；普通: 目标 0.08/上限 0.60）。
- Gallery：临时 HTTP 服务，绑定 `127.0.0.1` 随机端口 + 随机 token，浏览器点选即应用；
  Ctrl+C 退出或闲置 15 分钟自动关闭。没有常驻进程。

## Requirements

- macOS + WezTerm（`~/.wezterm.lua` 必须已包含读取 `background.conf` 的那段配置；
  该配置由本 skill 的初始化步骤写入一次，见下）。
- `sips`（系统自带）；ffmpeg 可选但推荐（`/opt/homebrew/bin/ffmpeg`）。

## First-time setup (once per machine)

`~/.wezterm.lua` 需要有这段（备份后追加）：

```lua
local bg_state = os.getenv('HOME') .. '/.config/wezterm/background.conf'
local bg_file, bg_display, bg_brightness = nil, nil, 0.40
pcall(function()
  local fh = io.open(bg_state, 'r')
  if not fh then return end
  for line in fh:lines() do
    local k, v = line:match('^(%w+)=(.*)$')
    if k == 'file' and v ~= '' then bg_file = v end
    if k == 'display' and v ~= '' then bg_display = v end
    if k == 'brightness' then bg_brightness = tonumber(v) or bg_brightness end
  end
  fh:close()
end)
local bg_final = bg_display or bg_file
if bg_final then
  config.window_background_image = bg_final
  config.window_background_image_hsb = { brightness = bg_brightness, hue = 1.0, saturation = 1.0 }
end
pcall(function() wezterm.add_to_config_reload_watch_list(bg_state) end)
```

## Safety

- 只监听 `127.0.0.1`，不暴露到局域网。
- 不修改 WezTerm 程序或 `~/.wezterm.lua`（只读状态文件）。
- `off` 只清空状态条目，不删除任何图片。
- 不做后台常驻、不装 LaunchAgent、不写开机项。

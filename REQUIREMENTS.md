# MSI Mystic Light RGB Web Control Panel — 需求文档

> 项目路径：`/home/msi_rgb`  
> 服务端口：`17700`  
> 设计风格：苹果风（Apple Design Language）  
> 使用环境：内网（无密码保护）

---

## 1. 项目概述

为 MSI PRO B760M-A DDR4 II (MS-7D99) 主板构建一个常驻在 17700 端口的 Web 控制面板，通过浏览器远程控制主板 Mystic Light RGB 灯效系统。

**核心特性**：
- 网页操作调整后立即生效（实时写入硬件）
- 支持多区域独立控制
- 丰富的预设与动效
- 定时自动化调度
- 开机自启、崩溃自动重启

---

## 2. 硬件信息

| 项目 | 详情 |
|:---|:---|
| 主板 | MSI PRO B760M-A DDR4 II (MS-7D99) |
| RGB 控制器 | MSI Mystic Light (USB VID: 1462, PID: 7D99) |
| 可控区域 | JRGB1、JRAINBOW1、JRAINBOW2、ONBOARD |
| 通信协议 | HID Feature Report (185-byte, Report ID 0x52) |
| 设备节点 | `/dev/hidraw2` |

---

## 3. 设计风格：苹果风（Apple Design Language）

### 3.1 色彩系统

| Token | 值 | 用途 |
|:---|:---|:---|
| `--bg-primary` | `#000000` | 页面主背景（纯黑，非死黑带灰） |
| `--bg-secondary` | `#1C1C1E` | 卡片/面板底色（Apple 系统灰） |
| `--bg-tertiary` | `#2C2C2E` | 悬浮层、输入框底色 |
| `--border` | `rgba(255,255,255,0.08)` | 极淡分割线 |
| `--accent` | `#E3000F` | MSI 红，用于激活态、滑块、开关 |
| `--accent-glow` | `rgba(227,0,15,0.3)` | 红色发光（开关开启时的柔和光晕） |
| `--text-primary` | `#FFFFFF` | 主文字 |
| `--text-secondary` | `rgba(255,255,255,0.55)` | 次级文字（SF Pro Text 风格） |
| `--text-tertiary` | `rgba(255,255,255,0.3)` | 禁用态文字 |

### 3.2 字体

- **标题/界面文字**：`-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif`
- **技术数值（HEX/RGB）**：`"SF Mono", "JetBrains Mono", ui-monospace, monospace`
- **字号层级**：标题 28px (700) / 区域名 17px (600) / 正文 15px (400) / 数值 13px (500, monospace)

### 3.3 圆角与间距

- **大面板**：`20px` 圆角（Apple Card 风格）
- **按钮/色块**：`12px` 圆角
- **开关/滑块**：`9999px`（胶囊形）
- **间距体系**：`8px` 为基础单位，卡片内边距 `20px`，卡片间距 `16px`

### 3.4 动效规范

- **页面加载**：卡片 stagger 淡入上浮，`0.6s cubic-bezier(0.22, 1, 0.36, 1)`
- **颜色切换**：硬件写入后前端色块 `0.3s ease-out` 过渡
- **按钮按压**：`scale(0.96)`，`0.1s ease`
- **开关拨动**：滑块 `0.25s cubic-bezier(0.4, 0.0, 0.2, 1)`
- **滑块拖动**：实时跟随，松手时轨道有 subtle 光晕扩散

### 3.5 质感

- **毛玻璃（ backdrop-filter ）**：顶部状态栏、部分悬浮面板使用 `backdrop-filter: blur(20px) saturate(180%)`，底层 `rgba(28,28,30,0.72)`
- **无硬阴影**：不使用大面积 drop-shadow，靠微妙的边框和背景层级区分
- **发光效果**：开关开启时，MSI 红 accent 有柔和外发光，类似 iOS 开关的绿光

---

## 4. 布局结构

### 4.1 桌面端（> 900px）

```
┌─────────────────────────────────────────────────────────────┐
│  [毛玻璃顶栏]                                                │
│  MSI Mystic Light Control              [🔴 总闸开关 ON]      │
├──────────────────────────┬──────────────────────────────────┤
│                          │                                  │
│    区域控制面板           │      快捷预设 + 自动化            │
│    (左侧 55%)             │      (右侧 45%)                   │
│                          │                                  │
│  ┌────────────────────┐  │  ┌────────────────────────────┐  │
│  │ JRGB1              │  │  │  [纯色组] [氛围组] ...      │  │
│  │ ○ 颜色环            │  │  │                            │  │
│  │ 模式 ▾   亮度━━━    │  │  │  ◼ ◼ ◼ ◼ ◼ ◼ ◼ ◼          │  │
│  │ 速度━━━   [同步]     │  │  │  ◼ ◼ ◼ ◼ ◼ ◼ ◼ ◼          │  │
│  └────────────────────┘  │  │                            │  │
│  ┌────────────────────┐  │  └────────────────────────────┘  │
│  │ JRAINBOW1          │  │  ┌────────────────────────────┐  │
│  │ ...                │  │  │ ⏰ 自动灯光调度              │  │
│  └────────────────────┘  │  │ 06:00 ████  18:00 ████      │  │
│  ┌────────────────────┐  │  │ 22:00 ████  [开关]          │  │
│  │ JRAINBOW2          │  │  └────────────────────────────┘  │
│  │ ...                │  │                                  │
│  └────────────────────┘  │                                  │
│  ┌────────────────────┐  │                                  │
│  │ ONBOARD            │  │                                  │
│  │ ...                │  │                                  │
│  └────────────────────┘  │                                  │
│                          │                                  │
└──────────────────────────┴──────────────────────────────────┘
```

### 4.2 移动端（< 900px）

- 单列布局，顶部总闸
- 区域面板变成可折叠 Accordion（手风琴），默认只展开第一个
- 预设区横向滚动色条（类似 iOS 颜色选择器）
- 定时区折叠为底部面板

---

## 5. 功能模块详解

### 5.1 顶部总闸（Master Switch）

- **大号胶囊开关（iOS Toggle 风格）**：
  - OFF：轨道 `#39393D`，滑块白色，所有区域指示灯熄灭
  - ON：轨道 `#E3000F`（MSI 红），滑块白色，滑块右侧有 `12px` 柔和红色光晕
- **一键恢复**：关闭后再打开，恢复关闭前的颜色/模式（非全黑）
- **状态指示灯**：开关右侧有微小红点呼吸灯，表示控制器在线

### 5.2 区域控制面板（4 个区域）

每个区域是一个独立的 Card：

| 控件 | 说明 |
|:---|:---|
| **区域标题栏** | 左侧区域名 + 右侧「独立控制」开关（默认关闭 = 跟随全局） |
| **颜色选择器** | 圆形色环（自定义 `<input type="color">` 样式），实时显示当前 HEX |
| **模式选择** | Apple 风格下拉菜单：黑色背景 + 细白边 + 红色选中指示器，支持搜索过滤 |
| **亮度滑块** | 细轨道 `#39393D`，填充段 `#E3000F`，滑块白色圆形带阴影，拖动实时生效 |
| **速度滑块** | 同上，标签为「慢 / 中 / 快」 |
| **实时预览条** | 区域卡片底部有一条 `4px` 高的色带，实时显示当前颜色 |

**默认行为**：
- 刚打开页面时，4 个区域均为「同步模式」—— 操作右侧全局预设或顶部总闸，所有区域一起变
- 开启某区域的「独立控制」开关后，该区域脱离全局控制，可单独调色

### 5.3 快捷预设区

**分组标签栏（Segmented Control 风格）**：

```
[ 纯色组 ] [ 氛围组 ] [ MSI主题 ] [ 暗黑科技 ] [ 自然系 ] [ 再加10个 ]
```

- 选中态：白色文字 + 灰色背景胶囊
- 未选中态：半透明白文字

**色块矩阵**：
- 每组 6-8 个，网格布局 `gap: 12px`
- 每个色块：`56px × 56px`，圆角 `12px`，显示真实颜色
- **Hover**：`scale(1.08)` + 轻微阴影上浮，显示颜色名称 Tooltip
- **点击**：立即全局生效（所有未开启「独立控制」的区域同步变色）

**预设清单（32 个，6 组）**：

| 分组 | 颜色 |
|:---|:---|
| **纯色组** (8) | 纯白 `#FFFFFF`、正红 `#FF0000`、纯绿 `#00FF00`、纯蓝 `#0000FF`、正黄 `#FFFF00`、青色 `#00FFFF`、紫色 `#800080`、橙色 `#FFA500` |
| **氛围组** (8) | 暖白 `#FFF5E6`、冰蓝 `#00D5FF`、樱花粉 `#FFB7C5`、薰衣草 `#E6E6FA`、日落橙 `#FF8C00`、玫瑰金 `#B76E79`、薄荷绿 `#98FF98`、珊瑚红 `#FF7F50` |
| **MSI主题** (4) | MSI红 `#E3000F`、龙魂金 `#FFD700`、暗夜黑 `#1A1A1A`、电竞绿 `#00E676` |
| **暗黑科技** (6) | 霓虹粉 `#FF10F0`、电光紫 `#BF00FF`、赛博青 `#00F0FF`、毒液绿 `#00FF41`、矩阵绿 `#008F11`、暗紫 `#310062` |
| **自然系** (4) | 森林绿 `#228B22`、深海蓝 `#006994`、日落橙 `#FF4500`、薰衣草田 `#967BB6` |
| **再加10个** (4) | 熔岩红 `#FF2400`、极光绿 `#39FF14`、冰川白 `#F0F8FF`、钛金灰 `#87868C`、霓虹橙 `#FF6700`、荧光黄 `#CCFF00`、紫罗兰 `#8B00FF`、银白 `#C0C0C0`、樱花 `#FFB7C5`、苔藓 `#8FBC8F` |

### 5.4 动效模式列表（20+ 种）

下拉菜单中可选：

| 模式 | 说明 |
|:---|:---|
| Direct | 直连控制 |
| Static | 常亮 |
| Breathing | 呼吸灯 |
| Flashing | 快闪 |
| Double flashing | 双闪 |
| Lightning | 闪电 |
| Meteor | 流星 |
| Color ring | 色环旋转 |
| Planetary | 行星轨道 |
| Double meteor | 双流星 |
| Energy | 能量流动 |
| Blink | 慢闪 |
| Clock | 时钟扫描 |
| Color pulse | 颜色脉冲 |
| Color shift | 颜色渐变切换 |
| Color wave | 波浪扩散 |
| Marquee | 跑马灯 |
| Rainbow wave | 🌈 彩虹波浪 |
| Visor | Visor 扫描 |
| Rainbow flashing | 彩虹闪烁 |
| Color ring double flashing | 色环双闪 |
| Stack | 堆叠效果 |
| Fire | 🔥 火焰效果 |

### 5.5 定时/自动化调度

卡片标题：「自动灯光」带时钟图标

- **主开关**：iOS Toggle 风格
- **时间段配置（3 段）**：

| 时段 | 默认颜色 | 默认模式 |
|:---|:---|:---|
| 06:00 - 18:00 | 冷白 `#E8F4FF` | Static |
| 18:00 - 22:00 | 暖橙 `#FFCC80` | Breathing |
| 22:00 - 06:00 | 深红 `#4A0000` / 关闭 | Static / Off |

- **交互**：每段可点击展开，自定义时间和颜色
- **后端逻辑**：每分钟检查当前时间，落在哪个区间就自动切换

---

## 6. 后端 API 规范

### 6.1 端点

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | `/api/set` | 设置灯效 |
| POST | `/api/set_zone` | 设置指定区域 |
| POST | `/api/master` | 总闸开关 + 一键恢复 |
| GET | `/api/status` | 获取当前硬件状态 |
| GET | `/api/modes` | 获取可用模式列表 |
| POST | `/api/schedule` | 保存定时配置 |
| GET | `/api/schedule` | 获取定时配置 |

### 6.2 请求/响应示例

**POST /api/set**
```json
{
  "mode": "Rainbow wave",
  "color": "FF0000",
  "brightness": 100,
  "speed": "medium"
}
```

**POST /api/set_zone**
```json
{
  "zone": "JRAINBOW1",
  "mode": "Static",
  "color": "00FF00",
  "brightness": 100
}
```

**POST /api/master**
```json
{
  "state": "on"
}
```

### 6.3 实时性要求

- API 响应时间 `< 100ms`
- hidapi 写入后立即返回，不阻塞前端

---

## 7. 技术栈

| 层级 | 技术 | 说明 |
|:---|:---|:---|
| 后端框架 | Python Flask | 轻量，单文件可运行 |
| HID 通信 | `hidapi` Python 库 | 直接操作 `/dev/hidraw2` |
| 前端 | 纯 HTML5 + CSS3 + Vanilla JS | 无框架、无 CDN 依赖，断网可用 |
| 进程守护 | systemd | 开机自启，崩溃自动重启 |
| 日志 | 本地 rotating log | `/home/msi_rgb/logs/server.log` |

---

## 8. 文件结构

```
/home/msi_rgb/
├── REQUIREMENTS.md          # 本文档
├── AGENTS.md                # 项目背景与架构说明
├── server.py                # Flask 后端主程序
├── controller.py            # HID 控制器封装（读写硬件）
├── scheduler.py             # 定时任务线程
├── static/
│   ├── css/
│   │   └── style.css        # 前端样式（苹果风）
│   └── js/
│       └── app.js           # 前端逻辑
├── templates/
│   └── index.html           # 主页面
├── logs/                    # 运行日志目录
├── presets.json             # 预设颜色配置
└── msi-rgb.service          # systemd 服务文件
```

---

## 9. 部署方式

### 9.1 安装依赖

```bash
pip install flask hidapi
```

### 9.2 注册 systemd 服务

```bash
sudo cp /home/msi_rgb/msi-rgb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now msi-rgb
```

### 9.3 服务文件配置

- 工作目录：`/home/msi_rgb`
- 监听地址：`0.0.0.0:17700`
- 用户：`root`（需要访问 `/dev/hidraw2`）
- 重启策略：`always`

### 9.4 访问方式

内网任意设备浏览器访问：
```
http://<服务器IP>:17700
```

---

## 10. 硬件协议逆向与测试记录

> **警告**：本章记录的是经过实际测试验证的方法，后续开发人员必须严格遵循，禁止自行猜测或修改关键参数。

### 10.1 测试环境

- 主板：MSI PRO B760M-A DDR4 II (MS-7D99)
- BIOS 版本：1.A0 (03/21/2024)
- BIOS 中 RGB 设置：Enabled（已确认）
- OS：Ubuntu 22.04 LTS
- Python：`hidapi` 库直接访问 `/dev/hidraw2`

### 10.2 设备识别

```bash
lsusb | grep Mystic
# Bus 001 Device 003: ID 1462:7d99 Micro Star International MYSTIC LIGHT

cat /sys/class/hidraw/hidraw2/device/uevent
# HID_NAME=MSI MYSTIC LIGHT
# HID_ID=0003:00001462:00007D99
```

设备节点：`/dev/hidraw2`，VID=0x1462，PID=0x7D99。

### 10.3 OpenRGB 的局限性（经过实测验证）

| 工具 | 版本 | 结果 |
|:---|:---|:---|
| OpenRGB (PPA) | 0.81 | ❌ 不支持 MS-7D99，设备列表为空 |
| OpenRGB (源码编译) | 0.9+ git | ⚠️ 能识别设备，但灯不亮 |

**OpenRGB 灯不亮的根因**：OpenRGB 的 `MSIMysticLight185Controller::SetMode()` 中设置 `speedAndBrightnessFlags = (brightness << 2) | (speed & 0x03)`，但没有将**位 7 置 1**。导致控制器虽然接收了数据包，但硬件输出被禁用。

### 10.4 关键发现：`speedAndBrightnessFlags` 位 7 是区域使能开关

通过对比 **Windows 下 MSI Center 写入后的状态** 与 **Linux 下 OpenRGB 写入后的状态**，发现决定性差异：

| 区域 | Linux/OpenRGB 写入后 | Windows/MSI Center 写入后 | 差异 |
|:---|:---|:---|:---|
| JRGB1 | `spd=0x28` | `spd=0x28` | 相同（但 JRGB1 在 Windows 下为 Static 白色时确实亮了） |
| ONBOARD | `spd=0x28` | `spd=0xa8` | **位 7：0 → 1** |
| JRAINBOW1 | `spd=0x29` | `spd=0x28` | 接近 |

**0x28 = 0010 1000，0xa8 = 1010 1000。区别仅在 bit 7。**

**验证实验**：
1. 将 ONBOARD 的 `speedAndBrightnessFlags` 从 `0x28` 改为 `0xa8`（与 `0x80` OR）
2. 发送数据包
3. **灯立即亮起**（彩虹变化效果）
4. 改回 `0x28`，灯保持亮（因为已激活），但重启后会灭

**结论**：`speedAndBrightnessFlags |= 0x80` 是所有区域点亮的必要条件。

### 10.5 双包发送协议

MSI Mystic Light 控制器要求**连续发送两次 Feature Report**：

```python
# 第一次：save_data = 0（旧状态/占位）
buf[184] = 0
dev.send_feature_report(bytes(buf))
time.sleep(0.05)

# 第二次：save_data = 1（新状态，真正生效）
buf[184] = 1
dev.send_feature_report(bytes(buf))
```

两次发送之间必须有短暂延迟（≥ 50ms）。只发一次可能导致控制器忽略命令。

### 10.6 FeaturePacket_185 数据结构（185 字节）

Report ID：`0x52`

```
Offset 0:     report_id           = 0x52
Offset 1-10:  ZoneData            j_rgb_1
Offset 11-20: ZoneData            j_pipe_1
Offset 21-30: ZoneData            j_pipe_2
Offset 31-41: RainbowZoneData     j_rainbow_1
Offset 42-52: RainbowZoneData     j_rainbow_2
Offset 53-63: CorsairZoneData     j_corsair
Offset 64-73: ZoneData            j_corsair_outerll120
Offset 74-83: ZoneData            on_board_led
Offset 84-93: ZoneData            on_board_led_1
Offset 94-103: ZoneData           on_board_led_2
Offset 104-113: ZoneData          on_board_led_3
Offset 114-123: ZoneData          on_board_led_4
Offset 124-133: ZoneData          on_board_led_5
Offset 134-143: ZoneData          on_board_led_6
Offset 144-153: ZoneData          on_board_led_7
Offset 154-163: ZoneData          on_board_led_8
Offset 164-173: ZoneData          on_board_led_9
Offset 174-183: ZoneData          j_rgb_2
Offset 184:     save_data
```

**ZoneData 结构（10 字节）**：
```
+0: effect                    (1 byte)    — 模式 ID
+1: color.R                   (1 byte)
+2: color.G                   (1 byte)
+3: color.B                   (1 byte)
+4: speedAndBrightnessFlags   (1 byte)    — 必须与 0x80 OR
+5: color2.R                  (1 byte)
+6: color2.G                  (1 byte)
+7: color2.B                  (1 byte)
+8: colorFlags                (1 byte)    — bit 7 = 1 固定颜色, 0 = 随机/彩虹
+9: padding                   (1 byte)
```

**RainbowZoneData 结构（11 字节）**：继承 ZoneData + 1 byte
```
+10: cycle_or_led_num         (1 byte)    — 通常设为 100
```

**CorsairZoneData 结构（11 字节）**：
```
+0:  effect
+1-3: color
+4:  fan_flags
+5:  corsair_quantity
+6-9: padding[4]
+10: is_individual
```

### 10.7 各区域使能时的推荐参数（经 Windows 实测验证）

| 区域 | effect | speedAndBrightnessFlags | colorFlags | padding | cycle/led_num | 备注 |
|:---|:---|:---|:---|:---|:---|:---|
| JRGB1 | 用户选择 | `0x28 \| 0x80 = 0xa8` | `0x80` | `0` | — | 固定颜色时 colorFlags=0x80 |
| JPIPE1 | 用户选择 | `0xa8` | `0x80` | `0` | — | |
| JPIPE2 | 用户选择 | `0xa8` | `0x80` | `0` | — | |
| JRAINBOW1 | 用户选择 | `0xa8` | `0x00`（彩虹模式）或 `0x80`（固定） | `0` | `100` | RainbowZoneData 有额外字节 |
| JRAINBOW2 | 用户选择 | `0xa8` | `0x00` 或 `0x80` | `0` | `100` | |
| JCORSAIR | `0`（禁用） | `0x28` | `0x80` | `0` | `12` | Windows 下禁用 |
| JCOROUT | 用户选择 | `0xa8` | `0x80` | `0` | — | |
| ONBOARD | 用户选择 | `0xa8` | `0x01` | `4` | — | colorFlags 必须带 SYNC_SETTING_ONBOARD=0x01 |
| ONBRD1-9 | 用户选择 | `0xa8` | `0x80` | `0` | — | |
| JRGB2 | 用户选择 | `0xa8` | `0x80` | `0` | — | |

**特别说明**：
- ONBOARD 的 `padding` 在 Windows 下为 `4`，其他区域为 `0`
- ONBOARD 的 `colorFlags` 为 `0x01`（仅 SYNC_SETTING_ONBOARD），而非 `0x80`
- 对于彩虹/随机颜色模式（Rainbow wave 等），所有区域的 `colorFlags` 位 7 必须为 `0`

### 10.8 模式 ID 对照表

```python
MODES = {
    "Direct": 0x25,       # 特殊值，直接控制
    "Static": 1,
    "Breathing": 2,
    "Flashing": 3,
    "Double flashing": 4,
    "Lightning": 6,
    "Meteor": 8,
    "Color ring": 11,
    "Planetary": 12,
    "Double meteor": 13,
    "Energy": 14,
    "Blink": 16,
    "Clock": 17,
    "Color pulse": 18,
    "Color shift": 19,
    "Color wave": 20,
    "Marquee": 21,
    "Rainbow wave": 26,
    "Visor": 27,
    "Rainbow flashing": 29,
    "Color ring double flashing": 30,
    "Stack": 31,
    "Fire": 32,
}
```

### 10.9 USB 设备重置方法

当控制器处于异常状态（如被 Windows VM 占用、驱动崩溃）时，可通过以下方式重置：

```bash
# 从宿主机解绑
sudo sh -c 'echo 1-9 > /sys/bus/usb/drivers/usb/unbind'
sleep 2

# 重新绑定
sudo sh -c 'echo 1-9 > /sys/bus/usb/drivers/usb/bind'
sleep 2

# 重新赋权
sudo chmod 666 /dev/hidraw2
```

其中 `1-9` 是 Mystic Light 在 USB 总线上的地址（通过 `lsusb -t` 确认）。

### 10.10 Windows VM + MSI Center 的实测结果

- 将 Mystic Light USB 直通给 Windows 11 VM 后，设备在 VM 内可见
- **MSI Center 检测到虚拟机主板为非 MSI 主板，拒绝显示 Mystic Light 控制面板**
- 因此无法通过 Windows VM 里的 MSI Center 来"解锁"控制器
- 最终解决方案完全依赖 Linux 下的直接 HID 通信

### 10.11 测试成功的完整写入代码（Python + hidapi）

```python
import hid
import time

dev = hid.device()
dev.open(0x1462, 0x7D99)  # MSI Mystic Light

# 读取当前状态作为基础
buf = bytearray(dev.get_feature_report(0x52, 185))

# 设置所有区域为 Static 绿色，位 7 使能
zones = [
    (1, 10),    # JRGB1
    (11, 10),   # JPIPE1
    (21, 10),   # JPIPE2
    (31, 11),   # JRAINBOW1
    (42, 11),   # JRAINBOW2
    (64, 10),   # JCOROUT
    (74, 10),   # ONBOARD
    (84, 10),   # ONBRD1
    (94, 10),   # ONBRD2
    (104, 10),  # ONBRD3
    (114, 10),  # ONBRD4
    (134, 10),  # ONBRD6
    (144, 10),  # ONBRD7
    (154, 10),  # ONBRD8
    (164, 10),  # ONBRD9
    (174, 10),  # JRGB2
]

for off, size in zones:
    buf[off] = 1           # Static
    buf[off+1] = 0         # R
    buf[off+2] = 255       # G
    buf[off+3] = 0         # B
    buf[off+4] = 0xa8      # speed/brightness WITH BIT 7 ENABLED
    buf[off+5] = 0         # color2 R
    buf[off+6] = 255       # color2 G
    buf[off+7] = 0         # color2 B
    buf[off+8] = 0x80      # fixed color
    buf[off+9] = 0         # padding
    if size == 11:
        buf[off+10] = 100  # cycle/led_num

# 禁用不需要的区域（保持 Windows 风格）
# JCORSAIR: offset 53, disable
buf[53] = 0

# ONBRD5: offset 124, disable（Windows 下也是禁用）
buf[124] = 0

# ONBOARD 特殊处理
buf[74] = 1
buf[75] = 0; buf[76] = 255; buf[77] = 0
buf[78] = 0xa8
buf[79] = 0; buf[80] = 255; buf[81] = 0
buf[82] = 0x01       # SYNC_SETTING_ONBOARD
buf[83] = 4          # padding = 4（Windows 实测值）

# 双包发送协议
buf[184] = 0
dev.send_feature_report(bytes(buf))
time.sleep(0.05)
buf[184] = 1
dev.send_feature_report(bytes(buf))

dev.close()
```

### 10.12 开发注意事项

1. **位 7 必须使能**：任何写入 `speedAndBrightnessFlags` 的操作都必须执行 `value |= 0x80`，否则区域不亮
2. **双包发送**：先 `save_data=0`，再 `save_data=1`，间隔 ≥ 50ms
3. **ONBOARD 特殊处理**：`padding=4`，`colorFlags=0x01`（不是 0x80）
4. **彩虹/随机模式**：`colorFlags` 位 7 必须为 `0`（`0x00` 或带 sync 标志但清除了位 7）
5. **权限**：必须以 root 运行，或确保 `/dev/hidraw2` 对运行用户可读写
6. **USB 独占**：同一时间只有一个进程可以打开 hidraw2，确保没有其他程序（如 OpenRGB daemon）占用

---

## 11. 变更记录

| 日期 | 变更 | 说明 |
|:---|:---|:---|
| 2026-05-08 | 初稿 | 工业控制面板风格 |
| 2026-05-08 | 修订 | 改为苹果风（Apple Design Language） |
| 2026-05-08 | 补充 | 新增第 10 章「硬件协议逆向与测试记录」，详细记录测试成功的方法、数据结构、关键参数 |

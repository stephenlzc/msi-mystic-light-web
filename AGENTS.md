# AGENTS.md — MSI Mystic Light RGB Web Control Panel

## 项目概述

本项目目标是为 MSI PRO B760M-A DDR4 II (MS-7D99) 主板构建一个运行在 Linux 上的 Web 控制面板，通过浏览器远程控制主板 Mystic Light RGB 灯效系统。

**当前状态**：需求已确认，文档已完成，**等待编码实现**。

- **服务地址**：`http://<服务器IP>:17700`
- **设计风格**：苹果风（Apple Design Language）
- **使用环境**：内网（无密码保护）

## 硬件上下文

| 项目 | 详情 |
|:---|:---|
| 主板 | MSI PRO B760M-A DDR4 II (MS-7D99) |
| RGB 控制器 | MSI Mystic Light (USB HID, VID=1462, PID=7D99) |
| 设备节点 | `/dev/hidraw2` |
| 通信协议 | HID Feature Report，Report ID `0x52`，185 字节数据包 |
| 可控区域 | JRGB1、JRAINBOW1、JRAINBOW2、ONBOARD |

### 关键逆向发现（已验证）

1. **`speedAndBrightnessFlags` 位 7 必须置 1**（即 `value |= 0x80`），否则区域不亮
2. **双包发送**：先 `save_data=0`，再 `save_data=1`，间隔 ≥ 50ms
3. **ONBOARD 特殊参数**：`padding=4`，`colorFlags=0x01`（不是 0x80）
4. **彩虹模式**：`colorFlags` 位 7 必须为 `0`
5. **185 字节数据结构**：详见 `REQUIREMENTS.md` 第 10 章

## 待完成工作（TODO）

按优先级排序：

- [ ] `controller.py` — HID 控制器封装（硬件读写核心）
- [ ] `server.py` — Flask 后端（API 路由、CORS、异常处理）
- [ ] `scheduler.py` — 定时任务线程（时间自动变色）
- [ ] `templates/index.html` — 前端主页面（苹果风布局）
- [ ] `static/css/style.css` — 前端样式（深色主题、毛玻璃、动效）
- [ ] `static/js/app.js` — 前端逻辑（实时通信、区域控制、预设切换）
- [ ] `presets.json` — 32 个预设颜色配置
- [ ] `msi-rgb.service` — systemd 服务文件
- [ ] 创建 `logs/` 目录
- [ ] 安装依赖并启动测试
- [ ] 验证所有 API 端点
- [ ] 验证前端所有交互

## 当前文件结构

```
/home/msi_rgb/
├── AGENTS.md            # 本文档
├── REQUIREMENTS.md      # 产品需求 + 硬件协议逆向记录
└── (源码文件待创建)
```

## 技术架构

```
Browser (任何设备)
    ↓ HTTP (内网)
Flask Server (Python, 端口 17700)
    ↓ hidapi
/dev/hidraw2 → MSI Mystic Light 控制器
    ↓
JRGB1 / JRAINBOW1 / JRAINBOW2 / ONBOARD
```

### 技术栈

| 层级 | 技术 | 说明 |
|:---|:---|:---|
| 后端框架 | Python Flask | 轻量，单文件可运行 |
| HID 通信 | `hidapi` Python 库 | 直接操作 `/dev/hidraw2` |
| 前端 | 纯 HTML5 + CSS3 + Vanilla JS | 无框架、无 CDN 依赖，断网可用 |
| 进程守护 | systemd | 开机自启，崩溃自动重启 |
| 日志 | 本地 rotating log | `/home/msi_rgb/logs/server.log` |

## 编码规范

- **Python**：PEP 8，类型注解可选但推荐
- **前端**：纯 Vanilla JS，无框架，无外部 CDN（内网可能断网）
- **CSS**：CSS 变量（Custom Properties）管理主题色，BEM-like 命名
- **硬件访问**：必须通过 `controller.py` 统一封装，禁止在路由中直接调用 hidapi

## 构建与运行

```bash
# 安装依赖
pip install flask hidapi

# 开发运行
sudo python3 /home/msi_rgb/server.py

# 生产部署
sudo cp /home/msi_rgb/msi-rgb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now msi-rgb
```

## 安全注意事项

1. **权限**：服务必须以 root 运行（需要访问 `/dev/hidraw2`）
2. **USB 稳定性**：如果设备被其他进程占用（如之前实验中的 Python 脚本或 OpenRGB），需要先释放 `hidraw2`
3. **虚拟机干扰**：同一台机器上运行的 Windows VM 如果直通了这个 USB 设备，宿主机将无法访问
4. **无认证**：内网裸奔，不设密码

## 参考文档

- `REQUIREMENTS.md`：完整的产品需求文档，包含设计风格规范、API 定义、功能模块详解、预设色表、动效模式列表、硬件协议逆向记录等。

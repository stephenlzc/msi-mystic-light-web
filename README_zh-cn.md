# MSI Mystic Light RGB Web 控制面板

> 为 MSI PRO B760M-A DDR4 II (MS-7D99) 主板打造的 Linux 网页 RGB 灯效控制器。

![Platform](https://img.shields.io/badge/platform-Linux-blue)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

[English README](README.md)

---

## 目录

1. [项目简介](#1-项目简介)
2. [需求背景](#2-需求背景)
3. [踩坑记录](#3-踩坑记录)
4. [技术实现](#4-技术实现)
5. [功能特性](#5-功能特性)
6. [安装与使用](#6-安装与使用)
7. [文件结构](#7-文件结构)
8. [已知限制](#8-已知限制)
9. [致谢](#9-致谢)

---

## 1. 项目简介

本项目是为 MSI Mystic Light 主板打造的 **Linux 原生网页 RGB 灯效控制器**，监听端口 `17700`，**完全不依赖 Windows**。

在发现现有 Linux 工具都无法正确控制我的 MSI PRO B760M-A DDR4 II 主板灯效后，我逆向了 USB HID 协议，从零搭建了这个控制面板。它支持多区域独立控制、23 种动效模式、颜色预设、定时调度、总闸开关——任何内网浏览器都能访问。

## 2. 需求背景

**硬件：** MSI PRO B760M-A DDR4 II (MS-7D99) + Intel i7-12700K + NVIDIA RTX 4060 Ti  
**系统：** Ubuntu 22.04.5 LTS (Jammy)

我想在 Linux 下控制主板 RGB。官方 **MSI Center** 没有 Linux 版。我尝试了三种常见方案，全部失败：

1. **OpenRGB PPA (v0.81)** — 设备列表为空，不支持 MS-7D99。
2. **OpenRGB Git 版 (v0.9+)** — 能识别设备，但**灯不亮**。
3. **Windows VM + MSI Center** — USB 直通成功，但 MSI Center 检测到虚拟机的非 MSI DMI，**拒绝加载 Mystic Light 模块**。

唯一剩下的路：从 Linux 宿主机直接跟硬件对话。

## ⚠️ 使用声明

> **这不是一个即插即用的通用工具。**
>
> 本项目是针对**特定主板**（MSI PRO B760M-A DDR4 II，MS-7D99）在 **Ubuntu 22.04 LTS** 环境下逆向开发的。USB HID 协议、区域偏移表、数据包结构均来自该硬件的实测。
>
> **请勿直接 `git clone` 后在不同主板上运行。** 如果你的主板型号、USB ID 或 HID 数据包大小不同，代码不会直接工作。
>
> **推荐 workflow：**
> 1. 阅读本 README 和 `REQUIREMENTS.md` 中的协议文档。
> 2. 将本仓库作为**参考起点**。
> 3. 使用 AI 编程助手（如 [Kimi Code](https://github.com/MoonshotAI/kimi-cli)）根据自己的硬件调整协议参数（VID、PID、区域偏移、数据包大小等）。
> 4. 先在本地验证（`python3 server.py`），确认灯能正常响应后再配置常驻服务。

## 3. 踩坑记录

### 3.1 OpenRGB：能识别，灯不亮

OpenRGB 的 `MSIMysticLight185Controller::SetMode()` 计算 `speedAndBrightnessFlags = (brightness << 2) | (speed & 0x03)`，但**始终没有把 bit 7 置 1**。

通过对比 Windows MSI Center 写入的状态码，我发现了关键差异：

| 区域 | OpenRGB 写入 | MSI Center 写入 | 差异 |
|:---|:---|:---|:---|
| ONBOARD | `0x28` | `0xa8` | **位 7：0 → 1** |
| JRAINBOW1 | `0x29` | `0x28` | 接近 |

`0xa8 = 0x28 | 0x80`。这一位是**硬件使能标志**。没有它，控制器虽然收到了数据包，但物理输出被禁用，灯永远不会亮。

**验证：** 在 Python 脚本中手动翻转这一位后，灯立即亮起。

### 3.2 Windows VM 路线彻底走不通

把 USB 设备直通进 Windows 11 虚拟机在 USB 层面是成功的，但 MSI Center 会执行 DMI/主板厂商检测。它看到 QEMU/虚拟主板，判定"这不是 MSI 主板"，**直接隐藏 Mystic Light 控制面板**，没有任何绕过方法。

### 3.3 VM 会抢占 USB 设备

Windows VM 运行时会通过 `usbfs` 抢占 Mystic Light USB 设备，导致宿主机上 `/dev/hidraw2` 消失。回收方法：

```bash
echo '1-9' > /sys/bus/usb/drivers/usb/unbind
sleep 2
echo '1-9' > /sys/bus/usb/drivers/usb/bind
sleep 2
```

## 4. 技术实现

### 4.1 硬件协议逆向

- **设备：** USB HID，`VID=0x1462`，`PID=0x7D99`
- **节点：** `/dev/hidraw2`
- **数据包：** 185 字节 Feature Report，Report ID `0x52`

**区域偏移表：**

| 区域 | 偏移 | 大小 | 说明 |
|:---|:---|:---|:---|
| JRGB1 | 1 | 10 | |
| JPIPE1 | 11 | 10 | |
| JPIPE2 | 21 | 10 | |
| JRAINBOW1 | 31 | 11 | +10 有额外字节 |
| JRAINBOW2 | 42 | 11 | +10 有额外字节 |
| JCORSAIR | 53 | 11 | 默认禁用 |
| JCOROUT | 64 | 10 | |
| ONBOARD | 74 | 10 | 需特殊处理 |
| ONBRD1–9 | 84–164 | 10 each | |
| JRGB2 | 174 | 10 | |
| save_data | 184 | 1 | 0=预览，1=生效 |

**关键协议发现：**
1. **使能位：** `speedAndBrightnessFlags |= 0x80`（位 7 必须置 1，否则区域不亮）
2. **双包发送：** 先 `save_data=0`，再 `save_data=1`，间隔 ≥50ms
3. **ONBOARD 特殊：** `colorFlags = 0x01`（不是 `0x80`），`padding = 4`
4. **JRAINBOW 额外字节：** offset +10 = `100`（循环/LED 数量）

### 4.2 软件架构

| 层级 | 技术 |
|:---|:---|
| 后端 | Flask (Python 3)，系统 `python3-hid` |
| 前端 | 纯 HTML/CSS/JS，苹果风暗色主题 |
| 通信 | RESTful JSON over HTTP，端口 `17700` |
| 部署 | systemd 服务，开机自启，崩溃自动重启 |

### 4.3 核心逻辑

- **`controller.py`** — 线程安全 HID 封装，带超时重连。处理双包协议、设备句柄失效检测、状态缓存。
- **`server.py`** — Flask 路由，`/api/set`、`/api/set_zone`、`/api/master`、`/api/status`、`/api/schedule`。
- **`scheduler.py`** — 可选的定时自动切换（默认关闭）。

## 5. 功能特性

- **4 区域独立控制：** JRGB1、JRAINBOW1、JRAINBOW2、ONBOARD（主板灯带）
- **23 种动效模式**（中文本地化）：静态、呼吸、闪烁、双闪、闪电、流星、彩色环、行星、双流星、能量、眨眼、时钟、彩色脉冲、颜色变换、彩色波浪、跑马灯、彩虹波浪、面罩、彩虹闪烁、彩色环双闪、堆叠、火焰、直接控制
- **32 色快捷预设**，分 3 组（常用、暗黑科技、氛围）
- **总闸开关**，带状态保存/恢复
- **第二颜色支持** — 15 种双色模式自动展开第二颜色选择器
- **彩虹模式提示** — 4 种内置彩虹/预设模式标注"所选颜色不影响效果"
- **可选定时调度** — 按时间段自动变色

## 6. 安装与使用

### 依赖

```bash
sudo apt update
sudo apt install python3-flask python3-hid
```

### 安装 systemd 服务

```bash
sudo cp msi-rgb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable msi-rgb.service
sudo systemctl start msi-rgb.service
```

### 访问

浏览器打开 `http://<服务器IP>:17700`。

## 7. 文件结构

```
msi_rgb/
├── controller.py          # HID 硬件抽象层
├── server.py              # Flask Web 服务器 & API
├── scheduler.py           # 定时自动切换
├── presets.json           # 颜色预设定义
├── msi-rgb.service        # systemd 服务文件
├── templates/
│   └── index.html         # Web UI
├── static/
│   ├── css/style.css      # 苹果风暗色主题
│   └── js/app.js          # 前端逻辑
├── logs/                  # 运行时日志
├── REQUIREMENTS.md        # 完整协议逆向文档
└── AGENTS.md              # 面向 AI 代理的项目上下文
```

## 8. 已知限制

- **JRAINBOW2 / ONBOARD 全局同步：** 控制器固件将这两个区域视为"主控通道"，修改时可能会同步到其他区域。这是硬件行为，非软件缺陷。
- **亮度/速度滑块为 UI 占位：** 控制器的 `speedAndBrightnessFlags` 使用固定的验证值（`0xa8`）。滑块会发送数值，但不改变硬件标志。
- **需要 root：** 访问 `/dev/hidraw2` 需要 root 权限或自定义 udev 规则。

## 9. 致谢

- **[Kimi Code](https://github.com/MoonshotAI/kimi-cli)**（[Moonshot AI](https://github.com/MoonshotAI)）— 整个项目完全在 Kimi Code 中开发完成。AI 驱动的编程环境使本次逆向工程和完整实现的整个过程成为可能。
- **[OpenRGB](https://github.com/CalcProgrammer1/OpenRGB)** — 提供了 MSI Mystic Light 控制器结构的初始参考（虽然最终未在该主板上工作）。
- **MSI Center (Windows)** — 正确 USB 数据包值的来源。

## 许可证

MIT

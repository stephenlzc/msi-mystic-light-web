# README 大纲（中英双语，中文为主）

## 1. 项目简介 / Project Overview
- 一句话描述：为 MSI PRO B760M-A DDR4 II (MS-7D99) 主板构建的 Mystic Light RGB Web 控制面板
- 痛点：Linux 下没有官方工具，OpenRGB 不支持或灯不亮
- 成品效果：浏览器访问，多区域独立控制，23种动效，32色预设

## 2. 需求背景 / Motivation
- 硬件环境：MSI B760M + i7-12700K + RTX 4060 Ti
- 操作系统：Ubuntu 22.04
- 问题：MSI Center 没有 Linux 版，Windows VM 中因 DMI 检测失败无法加载 Mystic Light 模块
- 目标：在 Linux 宿主机上直接控制主板 RGB，无需依赖 Windows

## 3. 踩坑记录 / Problems Encountered
### 3.1 OpenRGB 无法识别
- PPA 版 0.81 不支持 MS-7D99，设备列表为空
- Git 版 0.9+ 能识别但灯不亮

### 3.2 灯不亮的根因（核心发现）
- 对比 Windows MSI Center 写入的状态码 vs OpenRGB 写入的状态码
- 关键差异：`speedAndBrightnessFlags` 的 bit 7 必须置 1（`|= 0x80`）
- OpenRGB 遗漏了这位置位，导致硬件输出被禁用
- 验证：手动修改后灯立即亮起

### 3.3 Windows VM 方案失败
- USB 直通成功，MSI Center 检测到非 MSI 主板（虚拟机 DMI）
- Mystic Light 模块拒绝加载

### 3.4 USB 设备抢占问题
- Windows VM 运行时会抢占 Mystic Light USB 设备
- 需要从 Linux 宿主机回收设备（unbind/bind）

## 4. 技术实现 / Implementation
### 4.1 硬件协议逆向
- USB HID 设备：VID=0x1462, PID=0x7D99
- 设备节点：`/dev/hidraw2`
- 数据包结构：185-byte Feature Report (Report ID 0x52)
- Zone 偏移表：JRGB1(1), JRAINBOW1(31), JRAINBOW2(42), ONBOARD(74) 等
- 关键协议：
  - 双包发送（save_data=0 然后 save_data=1）
  - ONBOARD 特殊处理：padding=4, colorFlags=0x01
  - JRAINBOW 区域有额外字节（11-byte ZoneData）

### 4.2 软件架构
- 后端：Flask + Python hidapi
- 前端：纯 HTML/CSS/JS，苹果风暗色主题
- 通信：RESTful API，端口 17700
- 部署：systemd 服务，开机自启，崩溃自动重启

### 4.3 核心代码逻辑
- `controller.py`：HID 封装层，线程安全，超时重连
- `server.py`：Flask 路由，API 设计
- `scheduler.py`：定时任务（可选）

## 5. 功能特性 / Features
- 4 区域独立控制（JRGB1 / JRAINBOW1 / JRAINBOW2 / ONBOARD）
- 23 种动效模式（中文名称）
- 32 色快捷预设（3 组）
- 总闸开关 + 状态保存/恢复
- 第二颜色支持（15 种双色模式自动展开）
- 彩虹模式提示（4 种内置效果标注"不受颜色控制"）
- 定时调度（可选）

## 6. 安装与使用 / Installation & Usage
- 依赖安装（python3-flask, python3-hid）
- systemd 服务配置
- 浏览器访问 http://ip:17700

## 7. 文件结构 / File Structure
- 列出各文件作用

## 8. 已知限制 / Known Limitations
- JRAINBOW2 / ONBOARD 调整时控制器固件会全局同步（硬件行为）
- 亮度/速度滑块当前为 UI 占位（控制器实际使用固定值 0xa8）
- 需 root 权限访问 hidraw 设备

## 9. 致谢 / Acknowledgments
- OpenRGB 项目（虽然未直接使用，但提供了参考）
- MSI Center（Windows 逆向数据来源）


# 局域网开发/访问指南 (LAN Deployment Guide)

要让同一局域网下的其他设备（手机、平板、其他电脑）访问本系统，请按照以下步骤操作。

## 1. 准备工作

确保你的电脑和手机连接的是**同一个 WiFi** 或局域网。
你需要知道你电脑的**局域网 IP 地址**。
- **Windows**: 打开 CMD 输入 `ipconfig`，查找 IPv4 地址 (例如 `192.168.1.5`)。

## 2. 启动后端 (Backend)

后端需要监听所有网络接口 (`0.0.0.0`)，而不仅仅是本地回环。

1. 打开一个终端窗口。
2. 进入 `backend` 目录。
3. 运行以下命令：
   ```bash
   flask run --host=0.0.0.0 --port=5000
   ```
   *(注意: 不要直接用 VSCode 的 Run 按钮，建议使用上述命令行)*

## 3. 启动前端 (Frontend)

前端也需要暴露给局域网。我已经在 `package.json` 中为你添加了专用脚本。

1. 打开一个新的终端窗口。
2. 进入 `frontend` 目录。
3. 运行以下命令：
   ```bash
   npm run dev:lan
   ```
   终端会显示类似如下的访问地址：
   ```
   Network: http://192.168.1.5:5173/
   ```

## 4. 访问测试

现在，拿起你的手机或其他电脑，打开浏览器，输入步骤 3 中显示的 Network 地址 (例如 `http://192.168.1.5:5173`)。

### 常见问题
- **PowerShell 报错 "禁止运行脚本"**:
  - 这是一个 Windows 安全限制。
  - **解决方法 A (推荐)**: 改用 **Command Prompt (CMD)** 运行命令，不要用 PowerShell。
  - **解决方法 B**: 在 PowerShell 中运行 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` 解除限制。

- **无法访问**: 请检查电脑的**防火墙**设置，确保允许 python.exe 和 node.exe 通过防火墙，或者暂时关闭防火墙。
- **API 报错**: 前端配置了代理，访问网页时，请求会发送给电脑上的 Vite 服务，Vite 服务会转发给本机的 Backend (localhost:5000)，所以通常不需要修改代码即可正常工作。

祝开发愉快！

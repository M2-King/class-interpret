# 听课搭子：免费本地课堂同传

介绍页：仓库 [`docs/index.html`](docs/index.html)（同目录已带 Mac / Windows 安装包）。

这是一个运行在自己电脑上的英语课堂同传。浏览器采集麦克风或网课声音，给出英文原文和中文译文。课后可点 **生成课后总结**。上课同传不需要付费语音 API。

新版同传会在本机使用低延迟流式通道持续显示英文草稿，停顿后保存定稿并生成中文；点击 **Floating subtitles** 可打开适合叠在课件上的独立字幕窗。流式通道不可用时会自动切回兼容录音模式，课堂不会因为新功能而无法继续。

## Windows 怎么用

1. 下载并双击 [ClassInterpreter-Setup-Windows.bat](https://raw.githubusercontent.com/M2-King/class-interpret/codex/ui2-cross-platform/ClassInterpreter-Setup-Windows.bat)。
2. 安装器会自动下载完整应用、解压、检测旧安装路径、修复并启动。
3. 以后如有损坏，双击主文件夹里的 **FIX-CLASS-INTERPRETER.bat**。
4. 浏览器打开 `http://127.0.0.1:8765/`，必须显示 **0.3.3**。点黄色按钮，模型选 **Small**。校园网失败请换手机热点。
5. 若提示「Windows 已保护你的电脑」：更多信息 → 仍要运行。
6. 如果已经删掉或损坏 `.venv`，安装器会自动隔离并重建。第一次会重新装包，要几分钟。
7. 解压后路径：`ClassInterpreter-0.3.3\Start.bat` · 环境 `.venv\` · 模型 `hf\` · 笔记 `data\`。

完整便携包仍可下载：[ClassInterpreter-windows-0.3.3.zip](https://raw.githubusercontent.com/M2-King/class-interpret/codex/ui2-cross-platform/ClassInterpreter-windows-0.3.3.zip)。

## Mac 怎么用

1. 下载 [ClassInterpreter-Setup-Mac.zip](https://raw.githubusercontent.com/M2-King/class-interpret/codex/ui2-cross-platform/ClassInterpreter-Setup-Mac.zip)。
2. 解压后双击 **ClassInterpreter-Setup-Mac.command**，它会自动下载并安装完整应用。
3. 以后如有损坏，双击应用旁的 **FIX-CLASS-INTERPRETER.command**。
4. 若无法打开：按住 Control 点 Open.command → 打开；或系统设置 → 隐私与安全性 → 仍要打开。
5. 左上角应为 **Class Interpreter · 0.3.3**。黄色条下载模型，建议 **Small** 或 **Medium**。校园网请换手机热点。
6. 完整便携包：[ClassInterpreter-mac-0.3.3.zip](https://raw.githubusercontent.com/M2-King/class-interpret/codex/ui2-cross-platform/ClassInterpreter-mac-0.3.3.zip)。依赖在 `~/Library/Application Support/ClassInterpret`，日志在 `~/Library/Logs/class-interpret.log`。
7. 下课后点 **退出听课搭子**。上课请让 Mac 保持清醒。

苹果芯片用 CPU，不是 NVIDIA。页面：`http://127.0.0.1:8765/`。

**iPhone / iPad：** 手机不能单独装同传。先在 Mac 打开听课搭子，再双击 `听课搭子手机.app`，把 `https://….trycloudflare.com` 用 Safari / Chrome 打开（不要用微信内置浏览器）。

## 已经能用的电脑（例如 R9000P）

运行独立安装器即可；它会检测旧路径、保留 `.venv`/模型/笔记，并备份被替换的应用文件。

修复包：[ClassInterpreter-recover-0.3.3.zip](https://raw.githubusercontent.com/M2-King/class-interpret/codex/ui2-cross-platform/ClassInterpreter-recover-0.3.3.zip)

**如果已经删掉 `.venv`：** 用手机热点，按上面的 Windows 步骤解压新包。第一次会重新装包，黑窗口要留着。装好后页面必须是 **0.3.3**，再点黄色按钮下载 Small。显卡加速会尽量重装 CUDA 库；失败时仍可用 CPU。

## 课后总结与 DeepSeek

**生成课后总结** 是独立功能，直接点击就能使用。未安装 DeepSeek 时，会给出忠于课堂记录的摘录，不会编造概念或截止时间。

若你们共用 DeepSeek 云接口：把 key 贴进 `secrets/deepseek.api`（一行，`sk-` 开头）。应用会加密写入 `deepseek_api.enc`。朋友用带这个加密文件的 zip 时，点 **生成课后总结** 即可，不用填 key。明文 key 不会进 git。仓库若是公开的，拿到 zip 的人仍可能还原 key，只适合小范围朋友。

也可以不用云接口：在页面点 **安装 DeepSeek**，应用会查找已有的 Ollama；没有则下载，并拉取 `deepseek-r1:1.5b`（约 1.1GB）。校园网请换手机热点。已经装过 `deepseek-r1:7b` / `8b` 时会自动用更大的型号。

## 选择识别精度

| 模式 | 适合情况 |
| --- | --- |
| Small | 普通笔记本、希望尽量跟上课堂 |
| Medium | 口音较重、电脑性能较好 |
| Large v3 | 有较强显卡或能容忍较长延迟、优先准确率 |

本应用直接使用开源 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 识别，支持 CTranslate2 的 CPU/GPU 推理；中文翻译优先使用已配置的 DeepSeek 云接口并验证输出，失败时安全回退到 [Argos Translate](https://github.com/argosopentech/argos-translate) 离线模型。流式模式按短间隔刷新英文草稿、按自然停顿定稿；兼容模式仍按自然停顿或最长约 8 秒切段。模型大小、麦克风距离、教室噪声、术语提示都会影响结果；**无法保证每句完全准确或严格零延迟**。课堂笔记可直接点击“修正识别 / 译文”。

本机若有 NVIDIA 显卡，可选装免费的 CUDA 推理库，以显著缩短等待时间；安装包较大（合计约 1.4 GB），应用也能自动回退 CPU：

```powershell
D:\class-interpret\.venv\Scripts\python.exe -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

## 数据与排查

- 课堂文字保存在 `data/`，仅在本机监听 `127.0.0.1`。音频只用于当前识别，不持久保存。
- 首次下载模型时可能等待较久。课程中若显示“待处理”过多，切换较小识别模型，或改善麦克风收音。
- 没有中文译文时，先联网重新打开应用，并在页面点「现在安装中文翻译模型」。校园网证书错误时请换手机热点。
- 只有英文口音的课堂已被预设为英语识别；若老师主要讲马来语，当前版本不适用。
- 课后总结只根据已识别的文字生成；作业、考试和日期请核对原文或课程平台。

## 手机使用（Cloudflare，无需 SSH）

**手机不需要终端，也不需要 SSH App。** 只要 Safari / Chrome 打开一个 `https://` 链接。终端只出现在 **Mac** 上（双击 `.command` 时系统会自动弹出「终端」窗口）。

第三方只负责把本机的 **页面 + API** 变成 HTTPS，识别仍在 Mac 上。Firebase / GitHub Pages 只能放静态前端，不能跑 Whisper。

**在 Mac 上做（一次或自动）：** 双击 `手机访问.command` 时会检测系统；没有 Homebrew / `cloudflared` 会自动装。也可以在 Mac 终端运行 `bash start-tunnel.sh`。

**每次上课，在 Mac 上：** 双击 `手机访问.command`（不会用双击时，在 Mac 的「终端」里执行 `bash start-tunnel.sh`）。Mac 的终端里会出现一行 `https://….trycloudflare.com`，把它发给手机（隔空投送、信息、备忘录均可）。下课后在 **Mac 终端** 按 `Ctrl+C` 关掉。隧道开着时，知道链接的人都能访问。

**在手机上做：** 用系统浏览器打开那条 `https://` 链接（不要用微信内置浏览器）→ 允许麦克风 → 开始同传。没有终端、没有命令可敲。

临时隧道每次启动地址可能不同；需要固定域名时再在 Cloudflare 做 Named Tunnel。

## 手机使用（SSH）

若不想用 Cloudflare：手机页面已适配窄屏，麦克风录音可由手机浏览器发起，识别与翻译仍在运行 `server.py` 的电脑或服务器完成。手机里的 `127.0.0.1` 是手机本身；不能直接打开电脑上显示的本机地址。浏览器麦克风需要 HTTPS 或本机回环地址，因此也可以通过 SSH 客户端的 **本地端口转发**，再在手机浏览器打开 `http://127.0.0.1:8765/`。

**若应用运行在你的 Linux SSH 服务器：** 在服务器克隆此仓库，运行 `bash start.sh`（建议在 `tmux` 内保持运行）；在手机 SSH 客户端连接该服务器，添加本地转发 `127.0.0.1:8765 → 服务器 127.0.0.1:8765`。服务器若没有 GPU，Medium 模型可能明显落后于课堂进度，可选 Small。

需要随服务器自动启动时，把项目放到 `/opt/class-interpret`，以 root 运行 `bash deploy/install.sh`。安装脚本会创建独立 Python 环境、下载免费离线模型，并注册 `class-interpret.service`。可用 `systemctl status class-interpret` 查看状态。

**若希望继续用这台电脑的显卡：** 保持本机应用和电脑开机，在电脑终端运行 `ssh -N -R 18765:127.0.0.1:8765 用户名@服务器地址`；手机 SSH 客户端连接同一服务器，添加本地转发 `127.0.0.1:8765 → 服务器 127.0.0.1:18765`。这样手机的麦克风音频经 SSH 送到电脑处理，不把应用端口直接暴露到公网。SSH 服务器需允许端口转发。

手机端适合**线下课堂麦克风收音和看字幕**。手机浏览器共享本机其他 App 的音频支持有限；锁屏或切到后台可能使录音/SSH 连接中断，尤其在 iPhone 上，听课时请保持页面在前台。

## 技术结构

`server.py` 是仅监听本机的 Python 服务；`index.html`、`style.css`、`app.js` 是浏览器界面；`setup_models.py` 安装离线翻译模型；`deepseek_api.py` 使用加密后的 DeepSeek API；`deepseek_hub.py` 可选用本机 Ollama。Mac 请双击 `Open.command`。Windows 请双击 `Start.bat`。

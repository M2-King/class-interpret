# 听课搭子：免费本地课堂同传

这是一个运行在自己电脑上的英语课堂同传应用。用浏览器采集麦克风或网课标签页的声音，约每 3–8 秒给出英文原文及中文译文；可选中文朗读、修正识别结果、自动保存、导出笔记，并有独立的 **“生成课后总结”** 按钮。

## 第一次使用（Windows）

1. 安装 [Python 3.10–3.12](https://www.python.org/downloads/)；安装时勾选 **Add Python to PATH**。推荐使用 Chrome 或 Edge。
2. 双击 `启动同传.bat`。第一次会安装免费依赖和英语→中文翻译模型，需要联网。安装结束会打开 `http://127.0.0.1:8765/`。
3. 输入课程名和常见英文术语，选择“麦克风”或“共享标签页/屏幕音频”，点击 **开始同传**，允许浏览器访问声音。网课共享时要勾选浏览器的 **共享音频**。
4. 首次识别还会下载所选的免费 Whisper 模型。等下载完成后，之后可离线识别和翻译。

如果双击无法启动，在 PowerShell 运行：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\class-interpret\start.ps1"
```

## 课后总结与 DeepSeek

**生成课后总结** 是独立功能，直接点击就能使用。未安装 DeepSeek 时，会给出忠于课堂记录的摘录，不会编造概念或截止时间。如果希望使用免费的本机 DeepSeek 归纳：

1. 安装 [Ollama](https://ollama.com/download/windows)。
2. 在终端运行 `ollama pull deepseek-r1:1.5b`（较轻，约 1.1 GB）或 `ollama pull deepseek-r1:7b`（质量更好，约 4.7 GB）。
3. 保持 Ollama 运行，刷新应用页面，再点击 **生成课后总结**。应用会自动选择已安装的 DeepSeek-R1；不需要 API Key，也不调用收费接口。

## 选择识别精度

| 模式 | 适合情况 |
| --- | --- |
| Small | 普通笔记本、希望尽量跟上课堂 |
| Medium（默认） | 口音较重、电脑性能较好 |
| Large v3 | 有较强显卡或能容忍较长延迟、优先准确率 |

本应用直接使用开源 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 识别，支持 CTranslate2 的 CPU/GPU 推理；中文翻译使用 [Argos Translate](https://github.com/argosopentech/argos-translate) 的免费离线模型。录音按自然停顿或最长约 8 秒切段，避免固定位置频繁切断单词。模型大小、麦克风距离、教室噪声、术语提示都会影响结果；**无法保证每句完全准确或严格零延迟**。课堂笔记可直接点击“修正识别 / 译文”。

本机若有 NVIDIA 显卡，可选装免费的 CUDA 推理库，以显著缩短等待时间；安装包较大（合计约 1.4 GB），应用也能自动回退 CPU：

```powershell
D:\class-interpret\.venv\Scripts\python.exe -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

## 数据与排查

- 课堂文字保存在 `data/`，仅在本机监听 `127.0.0.1`。音频只用于当前识别，不持久保存。
- 首次下载模型时可能等待较久。课程中若显示“待处理”过多，切换较小识别模型，或改善麦克风收音。
- 没有中文译文时，先联网重新运行 `启动同传.bat` 以安装 Argos 翻译模型。
- 只有英文口音的课堂已被预设为英语识别；若老师主要讲马来语，当前版本不适用。
- 课后总结只根据已识别的文字生成；作业、考试和日期请核对原文或课程平台。

## 技术结构

`server.py` 是仅监听本机的 Python 服务；`index.html`、`style.css`、`app.js` 是浏览器界面；`setup_models.py` 安装离线翻译模型；`start.ps1` / `启动同传.bat` 负责启动。Python 依赖见 `requirements.txt`。不需要数据库、云端账号或付费 API。

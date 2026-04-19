# NCM 转 MP3 网页版

这个项目同时包含两种用法：

- `ncm_to_mp3.py`：命令行批量转换
- `web_app.py`：浏览器上传并下载 MP3 的网页版

## 本地运行网页版

使用这个项目自己的 Python 环境启动：

```powershell
E:\格式转换脚本\.venv\Scripts\python.exe web_app.py
```

然后浏览器打开：

```text
http://127.0.0.1:8000
```

## 本地运行命令行版

```powershell
E:\格式转换脚本\.venv\Scripts\python.exe ncm_to_mp3.py
```

如果想把输出写到别的目录：

```powershell
E:\格式转换脚本\.venv\Scripts\python.exe ncm_to_mp3.py --output-dir output
```

## 让别人通过网址访问

要让别人直接通过公网网址使用，需要把项目部署到云平台。这个项目已经补好了：

- `Dockerfile`
- `render.yaml`
- `.gitignore`

最简单的路线是部署到 Render。

### Render 部署步骤

1. 把当前项目上传到一个 GitHub 仓库。
2. 登录 Render。
3. 选择 `New +`。
4. 选择 `Blueprint`。
5. 连接你刚才的 GitHub 仓库。
6. Render 会自动识别根目录下的 `render.yaml`。
7. 确认创建后开始部署。
8. 部署完成后，Render 会给你一个 `*.onrender.com` 的公网网址。

### 为什么用 Docker

项目里的 `Dockerfile` 已经自动安装了 `ffmpeg`。这很重要，因为有些 `.ncm` 文件解密后内部并不是 MP3，而是 `flac` 或其他格式，需要服务器继续转码成 MP3。

## 注意事项

- 网页版当前一次处理一个 `.ncm` 文件。
- 默认最大上传体积是 100 MB，可以通过环境变量 `MAX_UPLOAD_BYTES` 调整。
- 服务监听端口使用环境变量 `PORT`。
- `.gitignore` 已经忽略了 `.venv`、`.ncm`、`.mp3` 等本地文件，上传仓库时更干净。

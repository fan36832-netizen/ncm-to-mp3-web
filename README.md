---
title: NCM 转 MP3
emoji: 🎵
colorFrom: yellow
colorTo: blue
sdk: docker
app_port: 8000
short_description: 在线把 .ncm 文件转换成 MP3
---

# NCM 转 MP3 网页版

这个项目提供一个简单的网页：上传 `.ncm` 文件，服务端完成解密/转码后，直接下载 `.mp3` 文件。

## 当前能力

- 浏览器上传 `.ncm`
- 自动输出 `.mp3`
- 如果原始音频不是 MP3，会使用 `ffmpeg` 转码
- 默认单次处理 1 个文件

## 本地运行

```powershell
python web_app.py
```

然后浏览器打开：

```text
http://127.0.0.1:8000
```

## 命令行用法

```powershell
python ncm_to_mp3.py
```

如果想把输出写到别的目录：

```powershell
python ncm_to_mp3.py --output-dir output
```

## 推荐部署到 Hugging Face Spaces

这个仓库已经补好了 Docker 部署文件，并且加了 GitHub Actions 自动同步方案。

### 第一步：在 Hugging Face 创建一个 Space

1. 登录 Hugging Face。
2. 新建一个 `Space`。
3. SDK 选择 `Docker`。
4. Space 名称建议也叫 `ncm-to-mp3-web`。
5. 可见性可选 `Public`。

### 第二步：创建 Hugging Face Token

根据 Hugging Face 官方说明，可以创建 `write` 或更细粒度的 token 来同步仓库：
[User Access Tokens](https://huggingface.co/docs/hub/en/security-tokens)

### 第三步：把 Token 配到 GitHub 仓库

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions` 里添加：

- Secret 名称：`HF_TOKEN`
- Variable 名称：`HF_SPACE_REPO_ID`
- Variable 值：`你的 Hugging Face 用户名/ncm-to-mp3-web`

例如：

```text
fan36832-netizen/ncm-to-mp3-web
```

### 第四步：触发同步

仓库里已经带了 GitHub Actions 工作流。你可以：

- 推送一次新的提交
- 或者去 GitHub 的 `Actions` 页面手动运行 `Sync to Hugging Face Space`

Hugging Face 官方关于 GitHub Actions 同步的说明：
[Managing Spaces with GitHub Actions](https://huggingface.co/docs/hub/spaces-github-actions)

## Docker 说明

项目里的 `Dockerfile` 会自动安装 `ffmpeg`，因为部分 `.ncm` 文件内部实际是 `flac` 或其他格式，必须在服务端继续转码成 MP3。

## 注意事项

- 默认最大上传体积是 100 MB，可以通过环境变量 `MAX_UPLOAD_BYTES` 调整。
- 服务监听端口由环境变量 `PORT` 控制，默认是 `8000`。
- 网页版当前一次处理一个 `.ncm` 文件。
- `.gitignore` 已忽略 `.venv`、`.ncm`、`.mp3` 等本地文件。

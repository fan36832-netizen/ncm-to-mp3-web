const fileInput = document.getElementById("file-input");
const dropzone = document.getElementById("dropzone");
const selection = document.getElementById("selection");
const convertButton = document.getElementById("convert-button");
const statusNode = document.getElementById("status");

let selectedFile = null;
let isConverting = false;

function formatBytes(size) {
  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function setStatus(message, kind = "") {
  statusNode.textContent = message;
  statusNode.classList.remove("is-error", "is-success");
  if (kind) {
    statusNode.classList.add(kind);
  }
}

function setSelectedFile(file) {
  selectedFile = file;
  if (file) {
    selection.textContent = `${file.name} (${formatBytes(file.size)})`;
    convertButton.disabled = isConverting;
    setStatus("文件已准备好，正在开始转换...", "");
    return;
  }

  selection.textContent = "当前还没有选择文件。";
  convertButton.disabled = true;
  setStatus("上传、转换、下载一步完成，整个过程会尽量保持简单直接。", "");
}

function parseDownloadName(contentDisposition) {
  if (!contentDisposition) {
    return "converted.mp3";
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) {
    return decodeURIComponent(utf8Match[1]);
  }

  const plainMatch = contentDisposition.match(/filename="([^"]+)"/i);
  return plainMatch ? plainMatch[1] : "converted.mp3";
}

async function convertSelectedFile() {
  if (!selectedFile || isConverting) {
    return;
  }

  isConverting = true;
  convertButton.disabled = true;
  setStatus("正在上传并转换，请稍等片刻...", "");

  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
        "X-Filename": encodeURIComponent(selectedFile.name),
      },
      body: await selectedFile.arrayBuffer(),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({ error: "上传失败。" }));
      throw new Error(payload.error || "上传失败。");
    }

    const blob = await response.blob();
    const downloadName = parseDownloadName(response.headers.get("Content-Disposition"));
    const downloadUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = downloadUrl;
    anchor.download = downloadName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(downloadUrl);

    const rawMessage = response.headers.get("X-Conversion-Message");
    const message = rawMessage ? decodeURIComponent(rawMessage) : "转换成功。";
    setStatus(message, "is-success");
  } catch (error) {
    setStatus(error.message || "转换失败。", "is-error");
  } finally {
    isConverting = false;
    convertButton.disabled = selectedFile === null;
  }
}

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("is-dragging");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("is-dragging");
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("is-dragging");
  const [file] = event.dataTransfer.files;
  if (!file) {
    return;
  }

  if (!file.name.toLowerCase().endsWith(".ncm")) {
    setSelectedFile(null);
    setStatus("请选择扩展名为 .ncm 的文件。", "is-error");
    return;
  }

  fileInput.files = event.dataTransfer.files;
  setSelectedFile(file);
  convertSelectedFile();
});

fileInput.addEventListener("change", () => {
  const [file] = fileInput.files;
  if (!file) {
    setSelectedFile(null);
    return;
  }

  if (!file.name.toLowerCase().endsWith(".ncm")) {
    fileInput.value = "";
    setSelectedFile(null);
    setStatus("请选择扩展名为 .ncm 的文件。", "is-error");
    return;
  }

  setSelectedFile(file);
  convertSelectedFile();
});

convertButton.addEventListener("click", convertSelectedFile);

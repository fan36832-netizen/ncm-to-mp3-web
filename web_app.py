from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote, unquote
from wsgiref.simple_server import make_server

from ncm_converter import ConversionError, convert_ncm_bytes


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))
DEFAULT_HOST = os.environ.get("HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("PORT", "8000"))


def read_text_file(path: Path) -> bytes:
    return path.read_text(encoding="utf-8").encode("utf-8")


def json_response(start_response, status: str, payload: dict) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def file_response(start_response, status: str, body: bytes, content_type: str) -> list[bytes]:
    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def ascii_fallback_filename(filename: str) -> str:
    fallback = "".join(char if char.isascii() and char not in {'"', "\\"} else "_" for char in filename)
    return fallback or "download.mp3"


def app(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")

    if method == "GET" and path == "/":
        return file_response(start_response, "200 OK", read_text_file(STATIC_DIR / "index.html"), "text/html; charset=utf-8")

    if method == "GET" and path == "/style.css":
        return file_response(start_response, "200 OK", read_text_file(STATIC_DIR / "style.css"), "text/css; charset=utf-8")

    if method == "GET" and path == "/app.js":
        return file_response(
            start_response,
            "200 OK",
            read_text_file(STATIC_DIR / "app.js"),
            "application/javascript; charset=utf-8",
        )

    if method == "GET" and path == "/healthz":
        return json_response(start_response, "200 OK", {"ok": True})

    if method == "POST" and path == "/api/convert":
        try:
            content_length = int(environ.get("CONTENT_LENGTH") or "0")
        except ValueError:
            return json_response(start_response, "400 Bad Request", {"error": "上传内容长度无效。"})

        if content_length <= 0:
            return json_response(start_response, "400 Bad Request", {"error": "请上传一个 .ncm 文件。"})
        if content_length > MAX_UPLOAD_BYTES:
            return json_response(
                start_response,
                "413 Payload Too Large",
                {"error": f"文件太大了，当前最大支持 {MAX_UPLOAD_BYTES // (1024 * 1024)} MB。"},
            )

        filename = unquote(environ.get("HTTP_X_FILENAME") or "upload.ncm")
        if not filename.lower().endswith(".ncm"):
            return json_response(start_response, "400 Bad Request", {"error": "目前只支持上传 .ncm 文件。"})

        payload = environ["wsgi.input"].read(content_length)
        if len(payload) != content_length:
            return json_response(start_response, "400 Bad Request", {"error": "上传流提前结束，请重试。"})

        try:
            converted = convert_ncm_bytes(payload, filename, ffmpeg_path=os.environ.get("FFMPEG_PATH"))
        except ConversionError as exc:
            return json_response(start_response, "400 Bad Request", {"error": str(exc)})
        except Exception:
            return json_response(start_response, "500 Internal Server Error", {"error": "服务器发生了未知错误。"})

        download_name = quote(converted.filename)
        fallback_name = ascii_fallback_filename(converted.filename)
        headers = [
            ("Content-Type", converted.media_type),
            ("Content-Length", str(len(converted.data))),
            ("Content-Disposition", f"attachment; filename=\"{fallback_name}\"; filename*=UTF-8''{download_name}"),
            ("X-Conversion-Message", quote(converted.message)),
        ]
        start_response("200 OK", headers)
        return [converted.data]

    return json_response(start_response, "404 Not Found", {"error": "接口不存在。"})


def main() -> None:
    with make_server(DEFAULT_HOST, DEFAULT_PORT, app) as server:
        print(f"服务已启动：http://127.0.0.1:{DEFAULT_PORT}")
        server.serve_forever()


if __name__ == "__main__":
    main()

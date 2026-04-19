from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


CORE_KEY = bytes.fromhex("687A4852416D736F356B496E62617857")
META_KEY = bytes.fromhex("2331346C6A6B5F215C5D2630553C2728")
NCM_HEADER = b"CTENFDAM"
CHUNK_SIZE = 0x8000
AUDIO_MIME_TYPES = {
    "mp3": "audio/mpeg",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
}


class ConversionError(RuntimeError):
    """Raised when an NCM file cannot be converted into audio output."""


@dataclass(slots=True)
class ConvertedAudio:
    filename: str
    data: bytes
    output_format: str
    media_type: str
    message: str
    original_format: str


def aes_ecb_decrypt(data: bytes, key: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    decryptor = cipher.decryptor()
    return decryptor.update(data) + decryptor.finalize()


def pkcs7_unpad(data: bytes) -> bytes:
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(data) + unpadder.finalize()


def read_u32_le(handle) -> int:
    value = handle.read(4)
    if len(value) != 4:
        raise ConversionError("NCM 文件结构不完整。")
    return int.from_bytes(value, "little")


def build_key_box(key_data: bytes) -> list[int]:
    if not key_data:
        raise ConversionError("NCM key 数据为空。")

    box = list(range(256))
    last_byte = 0
    key_offset = 0

    for index in range(256):
        swap = box[index]
        cursor = (swap + last_byte + key_data[key_offset]) & 0xFF
        key_offset = (key_offset + 1) % len(key_data)
        box[index] = box[cursor]
        box[cursor] = swap
        last_byte = cursor

    return box


def decode_audio_chunk(chunk: bytes, key_box: list[int]) -> bytes:
    data = bytearray(chunk)
    for index in range(len(data)):
        j = (index + 1) & 0xFF
        data[index] ^= key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xFF]) & 0xFF]
    return bytes(data)


def sniff_audio_extension(header: bytes) -> str:
    if header.startswith(b"ID3") or header[:2] in {b"\xFF\xFB", b"\xFF\xF3", b"\xFF\xF2"}:
        return "mp3"
    if header.startswith(b"fLaC"):
        return "flac"
    if header.startswith(b"OggS"):
        return "ogg"
    if len(header) >= 8 and header[4:8] == b"ftyp":
        return "m4a"
    return "bin"


def parse_metadata(raw_meta: bytes) -> dict:
    if not raw_meta:
        return {}

    try:
        obfuscated = bytearray(raw_meta)
        for index in range(len(obfuscated)):
            obfuscated[index] ^= 0x63

        decoded = base64.b64decode(bytes(obfuscated[22:]))
        decrypted = pkcs7_unpad(aes_ecb_decrypt(decoded, META_KEY))
        json_text = decrypted[6:].decode("utf-8", errors="replace")
        payload = json.loads(json_text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def find_ffmpeg(user_supplied: str | None = None) -> str | None:
    if user_supplied:
        return user_supplied
    return shutil.which("ffmpeg")


def choose_output_stem(original_name: str, metadata: dict) -> str:
    music_name = metadata.get("musicName")
    if isinstance(music_name, str) and music_name.strip():
        candidate = music_name.strip()
    else:
        candidate = Path(original_name).stem.strip() or "converted"

    candidate = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", candidate)
    candidate = candidate.rstrip(". ").strip()
    return candidate or "converted"


def decode_ncm_bytes(ncm_bytes: bytes) -> tuple[bytes, dict, str]:
    source_file = BytesIO(ncm_bytes)
    header = source_file.read(8)
    if header != NCM_HEADER:
        raise ConversionError("这不是有效的 .ncm 文件。")

    source_file.read(2)

    key_length = read_u32_le(source_file)
    key_data = bytearray(source_file.read(key_length))
    if len(key_data) != key_length:
        raise ConversionError("NCM key 数据块不完整。")
    for index in range(len(key_data)):
        key_data[index] ^= 0x64

    decrypted_key = pkcs7_unpad(aes_ecb_decrypt(bytes(key_data), CORE_KEY))
    key_box = build_key_box(decrypted_key[17:])

    meta_length = read_u32_le(source_file)
    meta_data = source_file.read(meta_length)
    if len(meta_data) != meta_length:
        raise ConversionError("NCM 元数据块不完整。")
    metadata = parse_metadata(meta_data) if meta_length else {}

    source_file.read(4)
    source_file.read(5)

    image_size = read_u32_le(source_file)
    if image_size:
        source_file.read(image_size)

    encrypted_audio = source_file.read()
    if not encrypted_audio:
        raise ConversionError("NCM 文件中没有音频数据。")

    audio_data = bytearray()
    for start in range(0, len(encrypted_audio), CHUNK_SIZE):
        chunk = encrypted_audio[start : start + CHUNK_SIZE]
        audio_data.extend(decode_audio_chunk(chunk, key_box))

    metadata_format = str(metadata.get("format", "")).strip().lower()
    audio_extension = metadata_format or sniff_audio_extension(bytes(audio_data[:16]))
    return bytes(audio_data), metadata, audio_extension


def transcode_bytes_to_mp3(audio_data: bytes, source_extension: str, ffmpeg_path: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="ncm-web-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        source_path = temp_dir / f"input.{source_extension}"
        target_path = temp_dir / "output.mp3"

        source_path.write_bytes(audio_data)

        process = subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-i",
                str(source_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(target_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode != 0 or not target_path.exists():
            error_text = process.stderr.strip() or process.stdout.strip() or "ffmpeg 执行失败。"
            raise ConversionError(f"ffmpeg 无法转出 MP3 文件：{error_text}")

        return target_path.read_bytes()


def convert_ncm_bytes(ncm_bytes: bytes, original_name: str, ffmpeg_path: str | None = None) -> ConvertedAudio:
    audio_data, metadata, audio_extension = decode_ncm_bytes(ncm_bytes)
    output_stem = choose_output_stem(original_name, metadata)

    if audio_extension == "mp3":
        return ConvertedAudio(
            filename=f"{output_stem}.mp3",
            data=audio_data,
            output_format="mp3",
            media_type=AUDIO_MIME_TYPES["mp3"],
            message="转换成功，原始音频流本身就是 MP3。",
            original_format="mp3",
        )

    resolved_ffmpeg = find_ffmpeg(ffmpeg_path)
    if not resolved_ffmpeg:
        raise ConversionError(
            "该 NCM 文件解密后不是 MP3 音频流，需要在服务器上安装 ffmpeg 才能继续转成 MP3。"
        )

    mp3_data = transcode_bytes_to_mp3(audio_data, audio_extension, resolved_ffmpeg)
    return ConvertedAudio(
        filename=f"{output_stem}.mp3",
        data=mp3_data,
        output_format="mp3",
        media_type=AUDIO_MIME_TYPES["mp3"],
        message=f"转换成功，原始音频流是 {audio_extension}，已额外转成 MP3。",
        original_format=audio_extension,
    )


def convert_ncm_file(input_path: Path, output_dir: Path | None = None, ffmpeg_path: str | None = None) -> tuple[Path, str]:
    converted = convert_ncm_bytes(input_path.read_bytes(), input_path.name, ffmpeg_path=ffmpeg_path)
    destination_dir = output_dir or input_path.parent
    destination_dir.mkdir(parents=True, exist_ok=True)
    output_path = destination_dir / converted.filename
    output_path.write_bytes(converted.data)
    return output_path, converted.message


def collect_inputs(arguments: list[str]) -> list[Path]:
    if not arguments:
        return sorted(Path.cwd().glob("*.ncm"))

    files: list[Path] = []
    for item in arguments:
        path = Path(item).expanduser()
        if path.is_dir():
            files.extend(sorted(path.glob("*.ncm")))
        elif path.suffix.lower() == ".ncm":
            files.append(path)
    return files

from __future__ import annotations

import argparse
from pathlib import Path

from ncm_converter import collect_inputs, convert_ncm_file


def main() -> int:
    parser = argparse.ArgumentParser(description="把 .ncm 文件转换成 MP3。")
    parser.add_argument(
        "inputs",
        nargs="*",
        help="可选的 .ncm 文件或目录；不传时处理当前目录下全部 .ncm 文件。",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="输出目录，默认就是当前目录。",
    )
    parser.add_argument(
        "--ffmpeg",
        help="可选的 ffmpeg 路径；当解密后的音频流不是 MP3 时需要它。",
    )
    args = parser.parse_args()

    input_files = collect_inputs(args.inputs)
    if not input_files:
        print("当前没有找到可转换的 .ncm 文件。")
        return 1

    output_dir = Path(args.output_dir).expanduser()

    for input_file in input_files:
        try:
            output_file, message = convert_ncm_file(input_file, output_dir=output_dir, ffmpeg_path=args.ffmpeg)
            print(f"[成功] {input_file.name} -> {output_file.name}")
            print(f"       {message}")
        except Exception as exc:  # noqa: BLE001
            print(f"[失败] {input_file.name}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

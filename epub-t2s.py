import zipfile
import os
import shutil
import argparse
from opencc import OpenCC

# 初始化繁体转简体
cc = OpenCC("t2s")

# 需要转换的文件类型
TEXT_EXTS = [".html", ".xhtml", ".htm", ".opf", ".ncx", ".xml"]


def make_default_output_name(input_file: str) -> str:
    """
    如果用户没有提供输出文件名，则生成：
    input.epub → input-简体.epub
    """
    base, ext = os.path.splitext(input_file)
    return f"{base}-简体{ext}"


def convert_epub(input_epub, output_epub):
    workdir = "epub_temp"

    # 清理旧目录
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    os.makedirs(workdir)

    # 1. 解包 EPUB
    with zipfile.ZipFile(input_epub, "r") as zin:
        zin.extractall(workdir)

    # 2. 遍历文本文件并转换
    for root, dirs, files in os.walk(workdir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()

            if ext in TEXT_EXTS:
                path = os.path.join(root, file)

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()

                    converted = cc.convert(content)

                    with open(path, "w", encoding="utf-8") as f:
                        f.write(converted)

                    print(f"✔ Converted: {path}")

                except Exception as e:
                    print(f"⚠ Skipped: {path} ({e})")

    # 3. 重新打包 EPUB（符合规范）
    with zipfile.ZipFile(output_epub, "w") as zout:

        # mimetype 必须第一个且不压缩
        mimetype_path = os.path.join(workdir, "mimetype")
        zout.write(
            mimetype_path,
            "mimetype",
            compress_type=zipfile.ZIP_STORED
        )

        # 其他文件正常压缩写入
        for root, dirs, files in os.walk(workdir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, workdir)

                if rel_path == "mimetype":
                    continue

                zout.write(
                    full_path,
                    rel_path,
                    compress_type=zipfile.ZIP_DEFLATED
                )

    # 4. 清理临时目录
    shutil.rmtree(workdir)

    print("\n✅ Done!")
    print("输出文件:", output_epub)


def main():
    parser = argparse.ArgumentParser(
        description="将 EPUB 中的繁体中文转换为简体中文，并重新打包输出"
    )

    parser.add_argument(
        "input",
        help="输入 EPUB 文件路径，例如 book.epub"
    )

    parser.add_argument(
        "output",
        nargs="?",  # 输出参数可选
        help="输出 EPUB 文件路径（可选），例如 book-简体.epub"
    )

    args = parser.parse_args()

    # 如果用户没提供输出文件名，则自动生成
    output_file = args.output or make_default_output_name(args.input)

    convert_epub(args.input, output_file)


if __name__ == "__main__":
    main()

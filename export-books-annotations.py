#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import plistlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

HOME = Path.home()

SQLITE_PATH = HOME / "Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/AEAnnotation_v10312011_1727_local.sqlite"
PLIST_PATH = HOME / "Library/Containers/com.apple.BKAgentService/Data/Documents/iBooks/Books/Books.plist"
OUTPUT_DIR = HOME / "Desktop/iBookAnotations"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ========= Apple CoreData 时间转换 =========
# CoreData 时间是从 2001-01-01 起算

def convert_apple_timestamp(ts):
    if ts is None:
        return None
    apple_epoch = datetime(2001, 1, 1)
    return apple_epoch + timedelta(seconds=ts)


# ========= 读取书籍标题 =========

def load_books():
    book_map = {}

    if not PLIST_PATH.exists():
        print("Books.plist 未找到")
        return book_map

    with open(PLIST_PATH, "rb") as f:
        plist = plistlib.load(f)

    books = plist.get("Books", [])

    for item in books:
        book_id = item.get("BKGeneratedItemId")
        title = item.get("BKDisplayName") or item.get("itemName")

        if book_id and title:
            book_map[str(book_id)] = title

    print(f"Books.plist 中发现 {len(book_map)} 本书")
    return book_map

# ========= 读取标注 =========

def load_annotations():
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()

    query = """
    SELECT
        ZANNOTATIONASSETID,
        ZANNOTATIONSELECTEDTEXT,
        ZANNOTATIONNOTE,
        ZANNOTATIONCREATIONDATE,
        ZANNOTATIONDELETED
    FROM ZAEANNOTATION
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    conn.close()
    return rows


# ========= 导出 Markdown =========

def export_md(book_map, annotations):
    from datetime import datetime

    grouped = defaultdict(list)

    for book_id, text, note, date_val, deleted in annotations:

        if deleted == 1:
            continue

        if not text:
            continue

        grouped[str(book_id)].append(
            (
                text.strip(),
                note.strip() if note else None,
                convert_apple_timestamp(date_val)
            )
        )

    print(f"共发现 {len(grouped)} 本书有标注")

    for book_id, items in grouped.items():

        title = book_map.get(book_id, f"UnknownBook_{book_id}")
        safe_title = "".join(c for c in title if c not in r'\/:*?"<>|')

        file_path = OUTPUT_DIR / f"{safe_title}.md"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            sorted_items = sorted(items, key=lambda x: x[2] or datetime.min)

            for i, (text, note, dt) in enumerate(sorted_items, 1):

                f.write(f"## 标注 {i}\n\n")

                # 高亮 → quote callout
                f.write("> [!quote]\n")
                for line in text.splitlines():
                    f.write(f"> {line}\n")
                f.write("\n")

                # 批注 → note callout
                if note:
                    f.write("> [!note]\n")
                    for line in note.splitlines():
                        f.write(f"> {line}\n")
                    f.write("\n")

                # 时间
                if dt:
                    f.write(f"*{dt.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

                f.write("---\n\n")

        print("已生成:", file_path)


# ========= 主程序 =========

def main():
    print("读取书籍信息...")
    book_map = load_books()

    print("读取标注数据...")
    annotations = load_annotations()

    print(f"数据库共 {len(annotations)} 条记录")

    print("生成 Markdown 文件...")
    export_md(book_map, annotations)

    print("\n完成，输出目录：", OUTPUT_DIR)


if __name__ == "__main__":
    main()
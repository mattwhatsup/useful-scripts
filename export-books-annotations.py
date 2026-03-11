#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import plistlib
import sys
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

HOME = Path.home()

ANNOTATION_DB = HOME / "Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/AEAnnotation_v10312011_1727_local.sqlite"
BOOKS_PLIST = HOME / "Library/Containers/com.apple.BKAgentService/Data/Documents/iBooks/Books/Books.plist"

OUTPUT_DIR = HOME / "Desktop/ibooks_annotations"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===============================
# Apple 时间转换
# ===============================

def apple_time_to_datetime(ts):
    if ts is None:
        return None
    epoch = datetime(2001, 1, 1)
    return epoch + timedelta(seconds=ts)


# ===============================
# callout映射
# ===============================

CALLOUT_MAP = {
    0: "quote",        # yellow
    1: "固定表达",      # green
    2: "生词",         # blue
    3: "important",    # pink
    4: "info"          # purple
}

def get_callout(style):
    return CALLOUT_MAP.get(style, "quote")


# ===============================
# 读取 Books.plist
# ===============================

def load_books():

    book_map = {}

    if not BOOKS_PLIST.exists():
        print("未找到 Books.plist")
        return book_map

    with open(BOOKS_PLIST, "rb") as f:
        plist = plistlib.load(f)

    books = plist.get("Books", [])

    for item in books:

        book_id = item.get("BKGeneratedItemId")

        title = (
            item.get("BKDisplayName")
            or item.get("itemName")
            or "UnknownBook"
        )

        author = item.get("BKAuthor", "")

        if book_id:
            book_map[str(book_id)] = {
                "title": title,
                "author": author
            }

    print(f"Books.plist 读取到 {len(book_map)} 本书")

    return book_map


# ===============================
# 过滤书名
# ===============================

def filter_books(book_map, keyword):

    if not keyword:
        return book_map

    keyword = keyword.lower()

    filtered = {}

    for book_id, info in book_map.items():

        title = info["title"]

        if keyword in title.lower():
            filtered[book_id] = info

    return filtered


# ===============================
# 自动检测字段
# ===============================

def detect_columns(cursor):

    cursor.execute("PRAGMA table_info(ZAEANNOTATION)")
    cols = [row[1] for row in cursor.fetchall()]

    chapter_candidates = [
        "ZANNOTATIONCHAPTERTITLE",
        "ZANNOTATIONSECTION",
        "ZANNOTATIONCHAPTER"
    ]

    chapter_col = None

    for c in chapter_candidates:
        if c in cols:
            chapter_col = c
            break

    return cols, chapter_col


# ===============================
# 读取标注
# ===============================

def load_annotations():

    conn = sqlite3.connect(ANNOTATION_DB)
    cursor = conn.cursor()

    cols, chapter_col = detect_columns(cursor)

    fields = [
        "ZANNOTATIONASSETID",
        "ZANNOTATIONSELECTEDTEXT",
        "ZANNOTATIONNOTE",
        "ZANNOTATIONCREATIONDATE",
        "ZANNOTATIONSTYLE",
        "ZANNOTATIONLOCATION",
        "ZANNOTATIONDELETED"
    ]

    if chapter_col:
        fields.insert(5, chapter_col)

    query = f"SELECT {', '.join(fields)} FROM ZAEANNOTATION"

    cursor.execute(query)
    rows = cursor.fetchall()

    conn.close()

    print(f"数据库共有 {len(rows)} 条标注")

    return rows, chapter_col


# ===============================
# Markdown 导出
# ===============================

def export_markdown(book_map, annotations, chapter_col, with_chapter):

    grouped = defaultdict(list)

    for row in annotations:

        if chapter_col:
            book_id, text, note, ts, style, chapter, location, deleted = row
        else:
            book_id, text, note, ts, style, location, deleted = row
            chapter = None

        if deleted == 1:
            continue

        if not text:
            continue

        if str(book_id) not in book_map:
            continue

        dt = apple_time_to_datetime(ts)

        grouped[str(book_id)].append(
            (text, note, dt, style, chapter, location)
        )

    print(f"{len(grouped)} 本书包含标注")

    for book_id, items in grouped.items():

        info = book_map[book_id]

        title = info["title"]
        author = info["author"]

        safe_title = "".join(c for c in title if c not in r'\/:*?"<>|')

        file_path = OUTPUT_DIR / f"{safe_title}.md"

        with open(file_path, "w", encoding="utf-8") as f:

            f.write("---\n")
            f.write(f"title: {title}\n")

            if author:
                f.write(f"author: {author}\n")

            f.write("source: Apple Books\n")
            f.write(f"exported: {datetime.now().isoformat()}\n")
            f.write("---\n\n")

            f.write(f"# {title}\n\n")

            items.sort(key=lambda x: x[2] or datetime.min)

            for i, (text, note, dt, style, chapter, location) in enumerate(items, 1):

                callout = get_callout(style)

                f.write(f"## 标注 {i}\n\n")

                if with_chapter and chapter:
                    f.write(f"章节：{chapter}\n\n")

                else:
                    if with_chapter and location:
                        f.write(f"位置：{location}\n\n")

                f.write(f"> [!{callout}]\n")

                for line in text.splitlines():
                    f.write(f"> {line}\n")

                f.write("\n")

                if note:

                    f.write("> [!note]\n")

                    for line in note.splitlines():
                        f.write(f"> {line}\n")

                    f.write("\n")

                if dt:
                    f.write(f"*{dt.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

                f.write("---\n\n")

        print("已导出:", file_path)


# ===============================
# Anki 导出
# ===============================

def export_anki(book_map, annotations, chapter_col):

    cards = []

    for row in annotations:

        if chapter_col:
            book_id, text, note, ts, style, chapter, location, deleted = row
        else:
            book_id, text, note, ts, style, location, deleted = row

        if deleted == 1:
            continue

        if not text or not note:
            continue

        if str(book_id) not in book_map:
            continue

        if style == 2:   # 生词
            cards.append([text.strip(), note.strip()])

        if style == 1:   # 固定表达
            cards.append([text.strip(), note.strip()])

    path = OUTPUT_DIR / "anki_cards.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(cards)

    print(f"导出 {len(cards)} 张 Anki 卡片 → {path}")


# ===============================
# 主程序
# ===============================

def main():

    keyword = None
    with_chapter = False
    output_anki = False

    for arg in sys.argv[1:]:

        if arg == "--with-chapter":
            with_chapter = True

        elif arg == "--output-anki":
            output_anki = True

        else:
            keyword = arg

    print("读取书籍信息...")
    books = load_books()

    if keyword:
        print(f"书名过滤关键字: {keyword}")
        books = filter_books(books, keyword)

        if not books:
            print("没有匹配到任何书名")
            return

        print(f"匹配到 {len(books)} 本书")

    print("读取标注...")
    annotations, chapter_col = load_annotations()

    if output_anki:
        export_anki(books, annotations, chapter_col)
    else:
        print("生成 Markdown...")
        export_markdown(books, annotations, chapter_col, with_chapter)

    print("完成！输出目录：", OUTPUT_DIR)


if __name__ == "__main__":
    main()

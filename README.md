

## export-books-annotations.py

用于导出 ibook 里epub的高亮和注释内容，适用于macos 26.2

颜色分类：

- yellow：quote
- green：固定用法
- blue：生词
- pink：important
- purple：info

命令：

```
# 导出所有书籍annotation
python3 export-books-annotations.py

# 导出匹配书名的书籍annotion，不区分大小写，部分匹配
python3 export-books-annotations.py "they were"
```

### 开关
--with-chapter 导出章节或位置信息
--output-anki 导出anki卡片数据库（csv）

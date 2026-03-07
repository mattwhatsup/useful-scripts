#!/bin/bash
set -euo pipefail
shopt -s nullglob

INPUT_DIR="$1"

# ================== 可调参数 ==================
MAX_DIMENSION=1200        # 最大边长；0 表示不缩放
MIN_FILESIZE_KB=300       # 小于该体积的 JPEG 跳过（避免二次压缩）
JPEGOPTIM_QUALITY=75      # jpegoptim 最大质量（推荐 70–80）
# ============================================

if [[ -z "${INPUT_DIR:-}" || ! -d "$INPUT_DIR" ]]; then
  echo "用法：$0 <图片文件夹路径>"
  exit 1
fi

for img in "$INPUT_DIR"/*.{jpg,JPG,jpeg,JPEG}; do
  [ -f "$img" ] || continue

  filesize_kb=$(($(stat -f%z "$img") / 1024))
  if [[ "$filesize_kb" -lt "$MIN_FILESIZE_KB" ]]; then
    echo "⏭ 跳过（体积已很小）：$(basename "$img")"
    continue
  fi

  echo "▶ 处理：$(basename "$img") (${filesize_kb}KB)"

  # 1. 尺寸规范（只做一次）
  if [[ "$MAX_DIMENSION" -gt 0 ]]; then
    sips -Z "$MAX_DIMENSION" "$img" >/dev/null
  fi

  # 2. JPEG 编码优化（无 EXIF 破坏）
  jpegoptim \
    --strip-all \
    --max="$JPEGOPTIM_QUALITY" \
    --preserve \
    "$img" >/dev/null

  new_size_kb=$(($(stat -f%z "$img") / 1024))
  echo "✅ 完成：${filesize_kb}KB → ${new_size_kb}KB"
done

echo
echo "🎉 JPEG 生产级压缩完成"

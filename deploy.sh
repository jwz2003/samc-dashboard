#!/bin/bash
# SAMC Explorer 一键部署：同步数据 → 构建 → 推送到 GitHub Pages 公网
# 用法：bash ~/dashboard/deploy.sh
set -e
cd "$(dirname "$0")"

echo "① 同步最新行情数据到 React 构建目录…"
cp data.js react/public/data.js
rm -rf react/public/data && cp -r data react/public/data

echo "② 构建 React 应用…"
cd react && npm run build
cd ..

echo "③ 部署产物到仓库根…"
cp react/dist/index.html ./index.html
rm -rf assets && cp -r react/dist/assets ./assets
cp react/dist/data.js ./data.js
rm -rf data && cp -r react/dist/data ./data

echo "④ 提交并推送（GitHub Pages 约 1-2 分钟生效）…"
git add -A
git commit -m "daily update $(date +%F_%H%M)"
git push origin main

echo "✅ 已部署: https://jwz2003.github.io/samc-dashboard/"

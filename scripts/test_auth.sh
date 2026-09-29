#!/bin/bash
# 登录态管理功能测试脚本

API_BASE="http://127.0.0.1:8000"
PROFILE="test"
LOGIN_URL="https://www.baidu.com"

echo "=========================================="
echo "登录态管理功能测试"
echo "=========================================="
echo ""

echo "1. 查看当前登录态状态"
curl -s "${API_BASE}/auth/status" | python -m json.tool
echo ""
echo ""

echo "2. 启动登录会话（浏览器会自动打开）"
curl -s -X POST "${API_BASE}/auth/start?profile=${PROFILE}&login_url=${LOGIN_URL}" | python -m json.tool
echo ""
echo ""

echo "请在打开的浏览器中完成登录操作..."
echo "按任意键继续保存登录态..."
read -n 1 -s
echo ""

echo "3. 保存登录态"
curl -s -X POST "${API_BASE}/auth/save?profile=${PROFILE}" | python -m json.tool
echo ""
echo ""

echo "4. 验证登录态文件"
if [ -f "auth_files/auth_${PROFILE}.json" ]; then
    echo "✅ 登录态文件已生成: auth_files/auth_${PROFILE}.json"
    ls -lh "auth_files/auth_${PROFILE}.json"
else
    echo "❌ 登录态文件未找到"
fi
echo ""

echo "5. 查看更新后的状态"
curl -s "${API_BASE}/auth/status" | python -m json.tool
echo ""
echo ""

echo "=========================================="
echo "测试完成！"
echo "=========================================="

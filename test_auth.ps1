# 登录态管理功能测试脚本 (Windows)

$API_BASE = "http://127.0.0.1:8000"
$PROFILE = "test"
$LOGIN_URL = "https://www.baidu.com"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "登录态管理功能测试" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. 查看当前登录态状态" -ForegroundColor Yellow
$response = Invoke-RestMethod -Uri "$API_BASE/auth/status" -Method Get
$response | ConvertTo-Json -Depth 10
Write-Host ""

Write-Host "2. 启动登录会话（浏览器会自动打开）" -ForegroundColor Yellow
$response = Invoke-RestMethod -Uri "$API_BASE/auth/start?profile=$PROFILE&login_url=$LOGIN_URL" -Method Post
$response | ConvertTo-Json -Depth 10
Write-Host ""

Write-Host "请在打开的浏览器中完成登录操作..." -ForegroundColor Green
Write-Host "按任意键继续保存登录态..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Write-Host ""

Write-Host "3. 保存登录态" -ForegroundColor Yellow
$response = Invoke-RestMethod -Uri "$API_BASE/auth/save?profile=$PROFILE" -Method Post
$response | ConvertTo-Json -Depth 10
Write-Host ""

Write-Host "4. 验证登录态文件" -ForegroundColor Yellow
$authFile = "auth_files\auth_$PROFILE.json"
if (Test-Path $authFile) {
    Write-Host "✅ 登录态文件已生成: $authFile" -ForegroundColor Green
    Get-Item $authFile | Format-Table Name, Length, LastWriteTime
} else {
    Write-Host "❌ 登录态文件未找到" -ForegroundColor Red
}
Write-Host ""

Write-Host "5. 查看更新后的状态" -ForegroundColor Yellow
$response = Invoke-RestMethod -Uri "$API_BASE/auth/status" -Method Get
$response | ConvertTo-Json -Depth 10
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "测试完成！" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

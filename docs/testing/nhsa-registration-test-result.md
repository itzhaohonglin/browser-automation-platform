# NHSA 注册证号查询测试结果

**测试日期**: 2026-09-30
**配置 ID**: 45
**任务 ID**: 40

## 测试参数
- registration_no: 滇械注准20192140008

## 执行结果
- 状态: FAILED
- 执行时间: 约41秒
- 错误信息: 元素 input[name='zczbh'] 等待超时

## 问题分析

### 根本原因
选择器无法找到输入框，原因是该输入框位于iframe内部，需要先进入iframe才能访问。

### 技术细节
1. Playwright成功启动（Windows事件循环策略问题已解决）
2. 页面可以加载
3. 但是选择器 `input[name='zczbh']` 无法直接访问
4. 根据配置，应该存在两层iframe嵌套：
   - 第一层: `iframe#dataInfo`
   - 第二层: `iframe.els-iframe.active`

## 选择器验证状态
- [ ] input[name='zczbh'] - **失败**: 等待超时，需要进入iframe
- [ ] iframe1_selector: iframe#dataInfo - 需要验证
- [ ] iframe2_selector: iframe.els-iframe.active - 需要验证
- [ ] submit_selector: button:has-text('查询') - 待测试
- [ ] wait_selector: .ui-jqgrid-btable - 待测试
- [ ] list_selector: tbody tr.jqgrow - 待测试
- [ ] detail_button_selector: a:has-text('详情') - 待测试
- [ ] detail_iframe_selector: iframe[src*='detail'] - 待测试

## Windows平台问题解决

### 问题描述
在Windows上使用uvicorn的--reload模式时，Playwright启动失败并抛出`NotImplementedError`。

### 解决方案
不使用`--reload`模式启动服务：
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info
```

而不是：
```bash
uvicorn app.main:app --reload --log-level info  # 在Windows上会失败
```

### 技术原因
- main.py已经设置了`asyncio.WindowsProactorEventLoopPolicy()`
- 但uvicorn的reload模式会启动子进程，子进程中事件循环策略未正确传递
- 不使用reload模式可以避免这个问题

## 下一步行动

### 立即行动（Task 3）
1. 使用调试脚本验证iframe选择器
2. 确认input元素在哪一层iframe中
3. 调整配置中的iframe选择器（如果需要）
4. 重新测试任务执行

### 验证项目
- [ ] 确认iframe1和iframe2选择器正确
- [ ] 确认input元素可以在正确的iframe层级被找到
- [ ] 确认表单可以提交
- [ ] 确认结果列表可以提取
- [ ] 确认详情按钮可以点击
- [ ] 确认详情iframe可以进入
- [ ] 确认详情数据可以提取

## Task 3 调试结果

### iframe验证结果
- [x] iframe#dataInfo: **验证通过** - 找到第1层iframe
- [x] iframe.els-iframe.active: **验证通过** - 找到第2层iframe
- [x] input[name='zczbh']: **验证失败** - 不存在此选择器
- [x] input[name='regcardNm']: **正确选择器** - 实际的注册证号输入框

### 配置调整

**问题**: 输入框选择器错误
- 原配置: `input[name='zczbh']`
- 正确配置: `input[name='regcardNm']`

**修复脚本**: `/d/dev/PyCharmProjects/browser-automation-platform/scripts/fix_nhsa_input_selector.py`

**修复内容**:
```json
{
  "selector": "input[name='regcardNm']",
  "param_name": "registration_no",
  "label": "注册证号",
  "required": true
}
```

### 重测结果

**新任务 ID**: 42

**执行结果**:
- 状态: SUCCESS
- 页面抓取: 1页
- 列表数据: 1条
- 详情数据: 0条 (详情采集失败，需要在Task 4修复)

**列表数据提取成功**:
```json
{
  "序号": "1",
  "医用耗材代码": "C1402020000000001522",
  "一级分类": "基础卫生材料",
  "二级分类": "常规医疗用品",
  "三级分类": "其他常规医疗用品",
  "注册证号": "-",
  "医疗器械名称": "纱布",
  "生产企业": "山东贝泰医疗科技股份有限公司"
}
```

**详情采集失败原因**:
- 错误: 点击详情链接超时
- 原因: 点击详情链接时，出现了遮挡元素 (artDialog-iframe弹窗)
- 状态: 需要在Task 4中修复详情iframe选择器

### 自我审查
- [x] iframe验证脚本已运行
- [x] 选择器问题已识别 (input[name='zczbh'] -> input[name='regcardNm'])
- [x] 配置已调整
- [x] 重新测试已执行
- [x] 测试文档已更新

### 下一步建议
- 进入Task 4: 修复详情采集逻辑，正确处理详情弹窗iframe

## 服务启动命令（已验证）

```bash
# Windows平台正确启动方式
cd D:/dev/PyCharmProjects/browser-automation-platform
uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info

# 健康检查
curl http://127.0.0.1:8000/health

# 执行任务
curl -X POST 'http://127.0.0.1:8000/task/run?config_id=45&limit=1'
```

## 测试环境
- OS: Windows 11 Pro 10.0.26200
- Python: 3.10+
- Playwright: 1.47.0
- FastAPI: 0.115.0
- 浏览器: Chromium (headless模式)

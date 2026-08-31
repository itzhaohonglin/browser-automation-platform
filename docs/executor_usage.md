# Playwright 执行器使用指南

## 快速开始

### 1. 准备测试数据

插入配置：
```sql
INSERT INTO crawler_configs (
    config_name, target_url, need_login,
    input_configs, submit_selector, wait_selector, fields_mapping,
    max_pages, is_active
) VALUES (
    '示例配置',
    'https://example.com',
    0,
    '[{"selector":"#search","value":"{keyword}","type":"fill"}]',
    '#submit',
    '.results',
    '{"title":".item-title text","link":".item-link @href"}',
    2,
    1
);
```

插入任务：
```sql
INSERT INTO job_queue (config_id, query_params, status)
VALUES (1, '{"keyword":"测试"}', 'pending');
```

### 2. 执行任务

通过 API 接口：
```bash
curl -X POST "http://localhost:8000/task/run?config_id=1&limit=1"
```

或访问 Swagger UI：`http://localhost:8000/docs`

### 3. 查看结果

检查任务状态：
```sql
SELECT * FROM job_queue WHERE id = 1;
```

查看提取的数据：
```sql
SELECT extracted_data FROM crawler_results WHERE job_id = 1;
```

## 配置说明

### input_configs 格式

支持三种输入类型：

1. **填充文本** (fill)：
   ```json
   {"selector":"#search","value":"{keyword}","type":"fill"}
   ```

2. **下拉选择** (select)：
   ```json
   {"selector":"#category","value":"{category}","type":"select"}
   ```

3. **复选框** (check)：
   ```json
   {"selector":"#agree","value":"true","type":"check"}
   ```

### fields_mapping 格式

1. **提取文本**：
   ```json
   {"title": ".item-title text"}
   ```

2. **提取属性**：
   ```json
   {"link": ".item-link @href", "image": "img @src"}
   ```

### 占位符替换

在 `input_configs` 的 `value` 中使用 `{参数名}` 格式，会自动从 `query_params` 中替换：

- `query_params`: `{"keyword": "Python", "date": "2026-08-31"}`
- `value`: `"{keyword}"`
- 实际值: `"Python"`

## 翻页配置

设置 `pagination_selector` 和 `max_pages` 实现自动翻页：

```json
{
  "pagination_selector": ".next-page",
  "max_pages": 5
}
```

系统会自动：
1. 点击下一页按钮
2. 等待新页面加载
3. 提取数据
4. 重复直到无下一页或达到 max_pages

## 登录态配置

如果网站需要登录：

1. 设置 `need_login = 1`
2. 设置 `auth_profile`（如 "taobao"）
3. 通过 `/auth/start` 接口更新登录态
4. 登录态文件保存在 `auth_files/auth_{profile}.json`

## 错误处理

常见错误及解决方案：

1. **元素等待超时**
   - 检查选择器是否正确
   - 增加 wait_selector 等待时间（代码中配置）

2. **登录态文件不存在**
   - 先调用 `/auth/start` 更新登录态

3. **占位符替换失败**
   - 检查 query_params 是否包含所需参数

4. **数据提取为 null**
   - 检查 fields_mapping 选择器是否正确
   - 查看日志确认具体原因

## 日志查看

启动服务时查看详细日志：

```bash
uvicorn app.main:app --reload --log-level=info
```

## API 响应示例

成功：
```json
{
  "status": "completed",
  "config_id": 1,
  "total_jobs": 1,
  "success_count": 1,
  "failed_count": 0,
  "results": [{
    "job_id": 1,
    "status": "success",
    "result_id": 1,
    "extracted_count": 10,
    "pages_crawled": 2,
    "execution_time": 15.5
  }]
}
```

失败：
```json
{
  "status": "completed",
  "config_id": 1,
  "total_jobs": 1,
  "success_count": 0,
  "failed_count": 1,
  "results": [{
    "job_id": 1,
    "status": "failed",
    "error": "元素等待超时: ...",
    "execution_time": 5.2
  }]
}
```

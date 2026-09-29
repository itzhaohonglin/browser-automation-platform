// static/config_manager.js

// 全局状态
const state = {
    configId: null,
    listFields: [],
    detailFields: []
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 从 URL 获取配置 ID
    const urlParams = new URLSearchParams(window.location.search);
    state.configId = urlParams.get('id');

    if (!state.configId) {
        alert('缺少配置 ID 参数');
        window.location.href = '/static/index.html';
        return;
    }

    document.getElementById('config-id-display').textContent = state.configId;

    // 初始化事件监听
    initEventListeners();

    // 加载配置数据
    loadConfig();
});

/**
 * 初始化事件监听器
 */
function initEventListeners() {
    // 列表字段：添加字段按钮
    document.getElementById('add-list-field').addEventListener('click', function() {
        addListField();
    });

    // 详情字段：添加字段按钮
    document.getElementById('add-detail-field').addEventListener('click', function() {
        addDetailField();
    });

    // 启用详情采集复选框
    document.getElementById('enable-detail').addEventListener('change', function(e) {
        const panel = document.getElementById('detail-config-panel');
        panel.style.display = e.target.checked ? 'block' : 'none';
    });

    // 关闭方式单选框
    const closeMethodRadios = document.querySelectorAll('input[name="close-method"]');
    closeMethodRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            updateCloseSelectorVisibility();
        });
    });

    // 测试配置按钮
    document.getElementById('test-config').addEventListener('click', function() {
        testConfig();
    });

    // 保存配置按钮
    document.getElementById('save-config').addEventListener('click', function() {
        saveConfig();
    });
}

/**
 * 添加列表字段行
 */
function addListField(name = '', selector = '', attr = 'text') {
    const container = document.getElementById('list-fields-container');
    const row = createFieldRow(name, selector, attr, 'list');
    container.appendChild(row);
    state.listFields.push({ name, selector, attr });
}

/**
 * 添加详情字段行
 */
function addDetailField(name = '', selector = '', attr = 'text') {
    const container = document.getElementById('detail-fields-container');
    const row = createFieldRow(name, selector, attr, 'detail');
    container.appendChild(row);
    state.detailFields.push({ name, selector, attr });
}

/**
 * 创建字段行 DOM 元素
 */
function createFieldRow(name, selector, attr, type) {
    const row = document.createElement('div');
    row.className = 'field-row';

    row.innerHTML = `
        <input type="text"
               class="field-name"
               placeholder="字段名称"
               value="${name}"
               data-type="${type}">
        <input type="text"
               class="field-selector"
               placeholder="CSS 选择器"
               value="${selector}"
               data-type="${type}">
        <select class="field-attr" data-type="${type}">
            <option value="text" ${attr === 'text' ? 'selected' : ''}>text</option>
            <option value="href" ${attr === 'href' ? 'selected' : ''}>href</option>
            <option value="src" ${attr === 'src' ? 'selected' : ''}>src</option>
        </select>
        <button type="button" class="btn-remove" onclick="removeFieldRow(this, '${type}')">删除</button>
    `;

    return row;
}

/**
 * 删除字段行
 */
function removeFieldRow(button, type) {
    const row = button.parentElement;
    const index = Array.from(row.parentElement.children).indexOf(row);

    row.remove();

    if (type === 'list') {
        state.listFields.splice(index, 1);
    } else {
        state.detailFields.splice(index, 1);
    }
}

/**
 * 更新关闭选择器输入框的可见性
 */
function updateCloseSelectorVisibility() {
    const closeMethod = document.querySelector('input[name="close-method"]:checked').value;
    const closeSelectorGroup = document.getElementById('close-selector-group');

    // 只有选择 "click" 或 "auto" 时才显示关闭选择器输入框
    closeSelectorGroup.style.display = (closeMethod === 'click' || closeMethod === 'auto') ? 'block' : 'none';
}

/**
 * 加载配置数据
 */
async function loadConfig() {
    try {
        const response = await fetch(`/api/configs/${state.configId}`);

        if (!response.ok) {
            throw new Error(`加载配置失败: ${response.statusText}`);
        }

        const result = await response.json();
        const config = result.data;

        // 填充列表容器选择器
        document.getElementById('list-selector').value = config.fields_mapping?.list_selector || '';

        // 填充列表字段
        const listFields = config.fields_mapping?.fields || [];
        listFields.forEach(field => {
            addListField(field.name, field.selector, field.attr);
        });

        // 如果没有字段，添加一个空行
        if (listFields.length === 0) {
            addListField();
        }

        // 填充详情配置
        const detailConfig = config.fields_mapping?.detail_config;
        if (detailConfig && detailConfig.enabled) {
            document.getElementById('enable-detail').checked = true;
            document.getElementById('detail-config-panel').style.display = 'block';

            document.getElementById('detail-button-selector').value = detailConfig.detail_button_selector || '';
            document.getElementById('detail-wait-selector').value = detailConfig.wait_selector || '';
            document.getElementById('detail-iframe-selector').value = detailConfig.detail_iframe_selector || '';

            // 填充详情字段
            const detailFields = detailConfig.fields || [];
            detailFields.forEach(field => {
                addDetailField(field.name, field.selector, field.attr);
            });

            if (detailFields.length === 0) {
                addDetailField();
            }

            // 填充高级配置
            const closeMethod = detailConfig.close_method || 'auto';
            document.querySelector(`input[name="close-method"][value="${closeMethod}"]`).checked = true;
            document.getElementById('close-selector').value = detailConfig.close_selector || '';

            if (detailConfig.retry) {
                document.getElementById('max-attempts').value = detailConfig.retry.max_attempts || 3;
                document.getElementById('retry-delay').value = detailConfig.retry.delay_seconds || 2;
            }

            updateCloseSelectorVisibility();
        } else {
            // 默认添加一个空字段行
            addDetailField();
        }

    } catch (error) {
        console.error('加载配置失败:', error);
        alert(`加载配置失败: ${error.message}`);
    }
}

/**
 * 收集表单数据
 */
function collectFormData() {
    // 收集列表字段
    const listFields = [];
    const listFieldRows = document.querySelectorAll('#list-fields-container .field-row');

    listFieldRows.forEach(row => {
        const name = row.querySelector('.field-name').value.trim();
        const selector = row.querySelector('.field-selector').value.trim();
        const attr = row.querySelector('.field-attr').value;

        if (name && selector) {
            listFields.push({ name, selector, attr });
        }
    });

    // 收集详情字段
    const detailFields = [];
    const detailFieldRows = document.querySelectorAll('#detail-fields-container .field-row');

    detailFieldRows.forEach(row => {
        const name = row.querySelector('.field-name').value.trim();
        const selector = row.querySelector('.field-selector').value.trim();
        const attr = row.querySelector('.field-attr').value;

        if (name && selector) {
            detailFields.push({ name, selector, attr });
        }
    });

    // 构建配置对象
    const listSelector = document.getElementById('list-selector').value.trim();
    const enableDetail = document.getElementById('enable-detail').checked;

    const fieldsMapping = {
        list_selector: listSelector,
        fields: listFields
    };

    if (enableDetail) {
        const closeMethod = document.querySelector('input[name="close-method"]:checked').value;

        fieldsMapping.detail_config = {
            enabled: true,
            detail_button_selector: document.getElementById('detail-button-selector').value.trim(),
            wait_selector: document.getElementById('detail-wait-selector').value.trim(),
            detail_iframe_selector: document.getElementById('detail-iframe-selector').value.trim() || null,
            fields: detailFields,
            close_method: closeMethod,
            close_selector: document.getElementById('close-selector').value.trim() || null,
            timeout: {
                click: 10000,
                wait_selector: 5000,
                iframe_load: 10000,
                close: 5000
            },
            retry: {
                max_attempts: parseInt(document.getElementById('max-attempts').value) || 3,
                delay_seconds: parseInt(document.getElementById('retry-delay').value) || 2
            }
        };
    } else {
        fieldsMapping.detail_config = {
            enabled: false
        };
    }

    return fieldsMapping;
}

/**
 * 验证表单数据
 */
function validateFormData(fieldsMapping) {
    const errors = [];

    // 验证列表容器选择器
    if (!fieldsMapping.list_selector) {
        errors.push('列表容器选择器不能为空');
        showFieldError('list-selector', '请输入列表容器选择器');
    }

    // 验证列表字段
    if (fieldsMapping.fields.length === 0) {
        errors.push('至少需要配置一个列表字段');
    }

    // 验证详情配置
    if (fieldsMapping.detail_config && fieldsMapping.detail_config.enabled) {
        if (!fieldsMapping.detail_config.detail_button_selector) {
            errors.push('详情按钮选择器不能为空');
            showFieldError('detail-button-selector', '请输入详情按钮选择器');
        }

        if (!fieldsMapping.detail_config.wait_selector) {
            errors.push('详情等待选择器不能为空');
            showFieldError('detail-wait-selector', '请输入详情等待选择器');
        }

        if (fieldsMapping.detail_config.fields.length === 0) {
            errors.push('至少需要配置一个详情字段');
        }
    }

    return errors;
}

/**
 * 显示字段错误
 */
function showFieldError(fieldId, message) {
    const field = document.getElementById(fieldId);
    const errorElement = document.getElementById(`${fieldId}-error`);

    if (field) {
        field.classList.add('error');
    }

    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }
}

/**
 * 清除所有字段错误
 */
function clearFieldErrors() {
    document.querySelectorAll('.form-control.error').forEach(el => {
        el.classList.remove('error');
    });

    document.querySelectorAll('.error-message.show').forEach(el => {
        el.classList.remove('show');
        el.textContent = '';
    });
}

/**
 * 测试配置
 */
async function testConfig() {
    // 清除之前的错误
    clearFieldErrors();

    // 收集表单数据
    const fieldsMapping = collectFormData();

    // 验证表单数据
    const errors = validateFormData(fieldsMapping);
    if (errors.length > 0) {
        alert('表单验证失败:\n' + errors.join('\n'));
        return;
    }

    // 获取查询参数（从配置中获取第一个输入框的值）
    const queryParams = {};
    try {
        const configResponse = await fetch(`/api/configs/${state.configId}`);
        const configResult = await configResponse.json();
        const inputConfigs = configResult.data.input_configs?.inputs || [];

        if (inputConfigs.length > 0) {
            const firstInput = inputConfigs[0];
            const paramKey = firstInput.param_key || 'keyword';
            queryParams[paramKey] = prompt(`请输入测试用的 ${paramKey}:`, '滇械注准20192140008') || '';
        }
    } catch (error) {
        console.error('获取查询参数失败:', error);
    }

    // 禁用测试按钮
    const testButton = document.getElementById('test-config');
    testButton.disabled = true;
    testButton.innerHTML = '<span class="loading"></span> 测试中...';

    // 显示测试结果面板
    const resultPanel = document.getElementById('test-result-panel');
    const resultContent = document.getElementById('test-result-content');
    resultPanel.style.display = 'block';
    resultContent.innerHTML = '<p>正在执行测试采集，请稍候...</p>';

    try {
        const response = await fetch(`/api/configs/${state.configId}/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fields_mapping: fieldsMapping,
                query_params: queryParams
            })
        });

        const result = await response.json();

        if (result.success) {
            displayTestSuccess(result.data);
        } else {
            displayTestError(result.error, result.error_type);
        }

    } catch (error) {
        displayTestError(error.message, 'network_error');
    } finally {
        // 恢复测试按钮
        testButton.disabled = false;
        testButton.textContent = '测试配置';
    }
}

/**
 * 显示测试成功结果
 */
function displayTestSuccess(data) {
    const resultContent = document.getElementById('test-result-content');

    let html = `
        <div class="test-status success">
            ✓ 成功提取 ${data.total_tested} 条数据
            （详情成功 ${data.success_count} 条，失败 ${data.failed_count} 条，跳过 ${data.skipped_count} 条）
        </div>
    `;

    if (data.sample_items && data.sample_items.length > 0) {
        html += '<div class="sample-data">';

        data.sample_items.forEach((item, index) => {
            html += `
                <div class="sample-item">
                    <h4>样本数据（第 ${index + 1} 条）</h4>

                    <div class="data-section">
                        <strong>列表数据：</strong>
                        ${renderDataFields(item.list_data)}
                    </div>

                    <div class="data-section">
                        <strong>详情数据：</strong>
                        ${renderDataFields(item.detail_data)}
                        <div class="data-field">
                            <span class="data-field-label">详情状态:</span>
                            <span class="data-field-value">${item.detail_status}</span>
                        </div>
                        ${item.detail_error ? `
                            <div class="data-field">
                                <span class="data-field-label">错误信息:</span>
                                <span class="data-field-value" style="color: #f44336;">${item.detail_error}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });

        html += '</div>';
    }

    resultContent.innerHTML = html;
}

/**
 * 渲染数据字段
 */
function renderDataFields(data) {
    if (!data || Object.keys(data).length === 0) {
        return '<p style="color: #999;">无数据</p>';
    }

    let html = '';
    for (const [key, value] of Object.entries(data)) {
        html += `
            <div class="data-field">
                <span class="data-field-label">${key}:</span>
                <span class="data-field-value">${value}</span>
            </div>
        `;
    }
    return html;
}

/**
 * 显示测试错误
 */
function displayTestError(error, errorType) {
    const resultContent = document.getElementById('test-result-content');

    let errorMessage = error;
    let suggestion = '';

    switch (errorType) {
        case 'selector_not_found':
            suggestion = '建议：检查选择器是否正确，或使用浏览器开发者工具验证';
            break;
        case 'load_timeout':
            suggestion = '建议：增加等待时间，或检查网络连接';
            break;
        case 'execution_error':
            suggestion = '建议：检查配置是否完整，或查看服务器日志';
            break;
        default:
            suggestion = '建议：检查配置并重试';
    }

    resultContent.innerHTML = `
        <div class="test-status error">
            ✗ 测试失败
        </div>
        <p><strong>错误信息：</strong>${errorMessage}</p>
        <p><strong>${suggestion}</strong></p>
    `;
}

/**
 * 保存配置
 */
async function saveConfig() {
    // 清除之前的错误
    clearFieldErrors();

    // 收集表单数据
    const fieldsMapping = collectFormData();

    // 验证表单数据
    const errors = validateFormData(fieldsMapping);
    if (errors.length > 0) {
        alert('表单验证失败:\n' + errors.join('\n'));
        return;
    }

    // 确认保存
    if (!confirm('确定要保存配置吗？')) {
        return;
    }

    // 禁用保存按钮
    const saveButton = document.getElementById('save-config');
    saveButton.disabled = true;
    saveButton.textContent = '保存中...';

    try {
        const response = await fetch(`/api/configs/${state.configId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fields_mapping: fieldsMapping
            })
        });

        if (!response.ok) {
            throw new Error(`保存失败: ${response.statusText}`);
        }

        alert('配置保存成功！');

        // 可选：返回配置列表页
        // window.location.href = '/static/index.html';

    } catch (error) {
        alert(`保存配置失败: ${error.message}`);
    } finally {
        // 恢复保存按钮
        saveButton.disabled = false;
        saveButton.textContent = '保存配置';
    }
}

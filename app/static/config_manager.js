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

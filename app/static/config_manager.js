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

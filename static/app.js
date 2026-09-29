// WebSocket 连接管理
class DashboardApp {
    constructor() {
        this.ws = null;
        this.reconnectTimeout = null;
        this.reconnectDelay = 3000;
        this.maxLogs = 100;
        this.logs = [];
        this.currentJobId = null;

        // 结果查看器状态
        this.currentPage = 0;
        this.pageSize = 20;
        this.filters = {
            job_id: null,
            config_id: null
        };

        // 配置管理状态
        this.configCurrentPage = 1;
        this.configPageSize = 10;
        this.editingConfigId = null;

        // DOM 元素
        this.wsStatus = document.getElementById('ws-status');
        this.statTotal = document.getElementById('stat-total');
        this.statSuccess = document.getElementById('stat-success');
        this.statFailed = document.getElementById('stat-failed');
        this.statRate = document.getElementById('stat-rate');
        this.progressContent = document.getElementById('progress-content');
        this.authList = document.getElementById('auth-list');
        this.logContainer = document.getElementById('log-container');

        // 结果模态框元素
        this.resultsModal = document.getElementById('results-modal');
        this.resultsContainer = document.getElementById('results-container');
        this.viewResultsBtn = document.getElementById('view-results-btn');
        this.closeModalBtn = document.getElementById('close-modal-btn');
        this.filterJobId = document.getElementById('filter-job-id');
        this.filterConfigId = document.getElementById('filter-config-id');
        this.applyFilterBtn = document.getElementById('apply-filter-btn');
        this.clearFilterBtn = document.getElementById('clear-filter-btn');
        this.prevPageBtn = document.getElementById('prev-page-btn');
        this.nextPageBtn = document.getElementById('next-page-btn');
        this.pageInfo = document.getElementById('page-info');

        // 配置管理模态框元素
        this.configModal = document.getElementById('config-modal');
        this.configEditModal = document.getElementById('config-edit-modal');
        this.manageConfigsBtn = document.getElementById('manage-configs-btn');
        this.closeConfigModalBtn = document.getElementById('close-config-modal-btn');
        this.closeConfigEditModalBtn = document.getElementById('close-config-edit-modal-btn');
        this.addConfigBtn = document.getElementById('add-config-btn');
        this.configListContainer = document.getElementById('config-list-container');
        this.configPrevPageBtn = document.getElementById('config-prev-page-btn');
        this.configNextPageBtn = document.getElementById('config-next-page-btn');
        this.configPageInfo = document.getElementById('config-page-info');
        this.configForm = document.getElementById('config-form');
        this.configEditTitle = document.getElementById('config-edit-title');
        this.cancelConfigBtn = document.getElementById('cancel-config-btn');
        this.needLoginCheckbox = document.getElementById('need_login');
    }

    init() {
        this.connectWebSocket();
        this.startHeartbeat();
        this.initResultsViewer();
        this.initConfigManager();
    }

    initResultsViewer() {
        // 打开模态框
        this.viewResultsBtn.addEventListener('click', () => {
            this.openResultsModal();
        });

        // 关闭模态框
        this.closeModalBtn.addEventListener('click', () => {
            this.closeResultsModal();
        });

        // 点击模态框外部关闭
        this.resultsModal.addEventListener('click', (e) => {
            if (e.target === this.resultsModal) {
                this.closeResultsModal();
            }
        });

        // ESC 键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.resultsModal.classList.contains('hidden')) {
                this.closeResultsModal();
            }
        });

        // 应用筛选
        this.applyFilterBtn.addEventListener('click', () => {
            this.applyFilters();
        });

        // 清除筛选
        this.clearFilterBtn.addEventListener('click', () => {
            this.clearFilters();
        });

        // 分页按钮
        this.prevPageBtn.addEventListener('click', () => {
            if (this.currentPage > 0) {
                this.currentPage--;
                this.loadResults();
            }
        });

        this.nextPageBtn.addEventListener('click', () => {
            this.currentPage++;
            this.loadResults();
        });

        // 回车键应用筛选
        [this.filterJobId, this.filterConfigId].forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.applyFilters();
                }
            });
        });
    }

    openResultsModal() {
        this.resultsModal.classList.remove('hidden');
        this.currentPage = 0;
        this.loadResults();
    }

    closeResultsModal() {
        this.resultsModal.classList.add('hidden');
    }

    applyFilters() {
        this.filters.job_id = this.filterJobId.value ? parseInt(this.filterJobId.value) : null;
        this.filters.config_id = this.filterConfigId.value ? parseInt(this.filterConfigId.value) : null;
        this.currentPage = 0;
        this.loadResults();
    }

    clearFilters() {
        this.filterJobId.value = '';
        this.filterConfigId.value = '';
        this.filters.job_id = null;
        this.filters.config_id = null;
        this.currentPage = 0;
        this.loadResults();
    }

    async loadResults() {
        this.resultsContainer.innerHTML = '<div class="loading-spinner">加载中...</div>';

        try {
            // 构建查询参数
            const params = new URLSearchParams({
                limit: this.pageSize,
                offset: this.currentPage * this.pageSize
            });

            if (this.filters.job_id) {
                params.append('job_id', this.filters.job_id);
            }

            if (this.filters.config_id) {
                params.append('config_id', this.filters.config_id);
            }

            const response = await fetch(`/results?${params.toString()}`);

            if (!response.ok) {
                throw new Error('获取数据失败');
            }

            const data = await response.json();
            this.renderResults(data);
            this.updatePagination(data);

        } catch (error) {
            console.error('加载结果失败:', error);
            this.resultsContainer.innerHTML = `
                <div class="empty-results">
                    <div class="empty-results-icon">❌</div>
                    <div class="empty-results-text">加载失败: ${error.message}</div>
                </div>
            `;
        }
    }

    renderResults(data) {
        if (!data.items || data.items.length === 0) {
            this.resultsContainer.innerHTML = `
                <div class="empty-results">
                    <div class="empty-results-icon">📭</div>
                    <div class="empty-results-text">暂无采集结果</div>
                </div>
            `;
            return;
        }

        const resultsHtml = data.items.map(item => `
            <div class="result-card">
                <div class="result-header">
                    <div class="result-meta">
                        <div class="result-meta-item">
                            <span class="result-meta-label">结果ID</span>
                            <span class="result-meta-value">#${item.id}</span>
                        </div>
                        <div class="result-meta-item">
                            <span class="result-meta-label">任务ID</span>
                            <span class="result-meta-value">#${item.job_id}</span>
                        </div>
                        <div class="result-meta-item">
                            <span class="result-meta-label">配置ID</span>
                            <span class="result-meta-value">#${item.config_id}</span>
                        </div>
                        <div class="result-meta-item">
                            <span class="result-meta-label">抓取页数</span>
                            <span class="result-meta-value">${item.page_count} 页</span>
                        </div>
                    </div>
                    <div class="result-time">
                        ${this.formatDateTime(item.created_at)}
                    </div>
                </div>
                <div class="result-body">
                    ${item.query_params && Object.keys(item.query_params).length > 0 ? `
                        <div class="result-section">
                            <div class="result-section-title">🔍 查询参数</div>
                            <div class="result-data">${this.formatJSON(item.query_params)}</div>
                        </div>
                    ` : ''}
                    <div class="result-section">
                        <div class="result-section-title">📦 提取数据</div>
                        <div class="result-data">${this.formatJSON(item.extracted_data)}</div>
                    </div>
                </div>
            </div>
        `).join('');

        this.resultsContainer.innerHTML = resultsHtml;
    }

    updatePagination(data) {
        const totalPages = Math.ceil(data.total / this.pageSize);
        const currentPage = this.currentPage + 1;

        this.pageInfo.textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页 (总计 ${data.total} 条)`;

        // 更新按钮状态
        this.prevPageBtn.disabled = this.currentPage === 0;
        this.nextPageBtn.disabled = this.currentPage >= totalPages - 1 || data.items.length < this.pageSize;
    }

    formatJSON(obj) {
        return JSON.stringify(obj, null, 2);
    }

    formatDateTime(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.addLog('info', `正在连接 WebSocket: ${wsUrl}`);

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => this.onOpen();
            this.ws.onmessage = (event) => this.onMessage(event);
            this.ws.onerror = (error) => this.onError(error);
            this.ws.onclose = () => this.onClose();
        } catch (error) {
            this.addLog('error', `WebSocket 连接失败: ${error.message}`);
            this.scheduleReconnect();
        }
    }

    onOpen() {
        this.updateConnectionStatus(true);
        this.addLog('info', 'WebSocket 连接成功');

        // 清除重连定时器
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }

        // 请求初始统计数据
        this.fetchInitialStats();
    }

    onMessage(event) {
        try {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        } catch (error) {
            console.error('解析 WebSocket 消息失败:', error);
        }
    }

    onError(error) {
        console.error('WebSocket 错误:', error);
    }

    onClose() {
        this.updateConnectionStatus(false);
        this.addLog('warning', 'WebSocket 连接已断开，将在 3 秒后重连...');
        this.scheduleReconnect();
    }

    scheduleReconnect() {
        if (this.reconnectTimeout) {
            return;
        }

        this.reconnectTimeout = setTimeout(() => {
            this.reconnectTimeout = null;
            this.connectWebSocket();
        }, this.reconnectDelay);
    }

    startHeartbeat() {
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send('ping');
            }
        }, 30000);
    }

    updateConnectionStatus(connected) {
        if (connected) {
            this.wsStatus.textContent = '已连接';
            this.wsStatus.className = 'status-badge connected';
        } else {
            this.wsStatus.textContent = '已断开';
            this.wsStatus.className = 'status-badge disconnected';
        }
    }

    handleMessage(message) {
        switch (message.type) {
            case 'progress':
                this.handleProgress(message);
                break;
            case 'log':
                this.handleLog(message);
                break;
            case 'stats':
                this.handleStats(message);
                break;
            case 'auth_status':
                this.handleAuthStatus(message);
                break;
            default:
                console.warn('未知的消息类型:', message.type);
        }
    }

    handleProgress(message) {
        this.currentJobId = message.job_id;
        const progress = message.progress;

        let progressHtml = `
            <div class="task-info">
                <div class="task-id">任务 #${message.job_id}</div>
                <div class="task-message">${message.message}</div>
            </div>
        `;

        if (progress && progress.current !== undefined && progress.total !== undefined) {
            const percentage = Math.round((progress.current / progress.total) * 100);
            progressHtml += `
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${percentage}%">
                        ${percentage}%
                    </div>
                </div>
            `;
        }

        this.progressContent.innerHTML = progressHtml;
    }

    handleLog(message) {
        this.addLog(message.level, message.message);
    }

    handleStats(message) {
        const data = message.data;
        this.statTotal.textContent = data.total || 0;
        this.statSuccess.textContent = data.success || 0;
        this.statFailed.textContent = data.failed || 0;
        this.statRate.textContent = `${data.success_rate?.toFixed(1) || 0}%`;
    }

    handleAuthStatus(message) {
        // 这里简化处理，实际应维护一个状态列表
        this.addLog('info', `登录态更新: ${message.profile} - ${message.status}`);
    }

    addLog(level, message) {
        const now = new Date();
        const time = now.toTimeString().split(' ')[0];

        const logEntry = {
            time,
            level,
            message,
            timestamp: now.getTime()
        };

        this.logs.push(logEntry);

        // 限制日志数量
        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }

        this.renderLogs();
    }

    renderLogs() {
        const logsHtml = this.logs.map(log => `
            <div class="log-entry log-${log.level}">
                <span class="log-time">[${log.time}]</span>
                <span class="log-level">[${log.level.toUpperCase()}]</span>
                <span class="log-message">${this.escapeHtml(log.message)}</span>
            </div>
        `).join('');

        this.logContainer.innerHTML = logsHtml;

        // 自动滚动到底部
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async fetchInitialStats() {
        try {
            const response = await fetch('/api/stats');
            if (response.ok) {
                const data = await response.json();
                this.handleStats({ type: 'stats', data });
            }
        } catch (error) {
            console.error('获取初始统计数据失败:', error);
        }
    }

    // ============ 配置管理相关方法 ============

    initConfigManager() {
        // 打开配置管理模态框
        this.manageConfigsBtn.addEventListener('click', () => {
            this.openConfigModal();
        });

        // 关闭配置列表模态框
        this.closeConfigModalBtn.addEventListener('click', () => {
            this.closeConfigModal();
        });

        // 关闭配置编辑模态框
        this.closeConfigEditModalBtn.addEventListener('click', () => {
            this.closeConfigEditModal();
        });

        // 点击模态框外部关闭
        this.configModal.addEventListener('click', (e) => {
            if (e.target === this.configModal) {
                this.closeConfigModal();
            }
        });

        this.configEditModal.addEventListener('click', (e) => {
            if (e.target === this.configEditModal) {
                this.closeConfigEditModal();
            }
        });

        // ESC 键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (!this.configEditModal.classList.contains('hidden')) {
                    this.closeConfigEditModal();
                } else if (!this.configModal.classList.contains('hidden')) {
                    this.closeConfigModal();
                }
            }
        });

        // 新建配置按钮
        this.addConfigBtn.addEventListener('click', () => {
            this.openConfigEditModal();
        });

        // 取消按钮
        this.cancelConfigBtn.addEventListener('click', () => {
            this.closeConfigEditModal();
        });

        // 配置分页按钮
        this.configPrevPageBtn.addEventListener('click', () => {
            if (this.configCurrentPage > 1) {
                this.configCurrentPage--;
                this.loadConfigs();
            }
        });

        this.configNextPageBtn.addEventListener('click', () => {
            this.configCurrentPage++;
            this.loadConfigs();
        });

        // 需要登录复选框变化
        this.needLoginCheckbox.addEventListener('change', (e) => {
            const authProfileGroup = document.getElementById('auth_profile_group');
            const loginUrlGroup = document.getElementById('login_url_group');
            const authProfileInput = document.getElementById('auth_profile');

            if (e.target.checked) {
                authProfileGroup.style.display = 'block';
                loginUrlGroup.style.display = 'block';
                authProfileInput.required = true;
            } else {
                authProfileGroup.style.display = 'none';
                loginUrlGroup.style.display = 'none';
                authProfileInput.required = false;
            }
        });

        // 表单提交
        this.configForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveConfig();
        });
    }

    openConfigModal() {
        this.configModal.classList.remove('hidden');
        this.configCurrentPage = 1;
        this.loadConfigs();
    }

    closeConfigModal() {
        this.configModal.classList.add('hidden');
    }

    openConfigEditModal(config = null) {
        this.editingConfigId = config ? config.id : null;
        this.configEditTitle.textContent = config ? '✏️ 编辑配置' : '➕ 新建配置';

        // 重置表单
        this.configForm.reset();

        if (config) {
            // 填充表单数据
            document.getElementById('config_name').value = config.config_name;
            document.getElementById('target_url').value = config.target_url;
            document.getElementById('need_login').checked = config.need_login;
            document.getElementById('is_active').checked = config.is_active;
            document.getElementById('auth_profile').value = config.auth_profile || '';
            document.getElementById('login_url').value = config.login_url || '';
            document.getElementById('input_configs').value = JSON.stringify(config.input_configs, null, 2);
            document.getElementById('submit_selector').value = config.submit_selector;
            document.getElementById('wait_selector').value = config.wait_selector;
            document.getElementById('fields_mapping').value = JSON.stringify(config.fields_mapping, null, 2);
            document.getElementById('pagination_selector').value = config.pagination_selector || '';
            document.getElementById('max_pages').value = config.max_pages;

            // 显示/隐藏登录相关字段
            const authProfileGroup = document.getElementById('auth_profile_group');
            const loginUrlGroup = document.getElementById('login_url_group');
            if (config.need_login) {
                authProfileGroup.style.display = 'block';
                loginUrlGroup.style.display = 'block';
            }
        } else {
            // 新建时设置默认值
            document.getElementById('is_active').checked = true;
            document.getElementById('max_pages').value = 1;
        }

        this.configEditModal.classList.remove('hidden');
    }

    closeConfigEditModal() {
        this.configEditModal.classList.add('hidden');
        this.editingConfigId = null;
    }

    async loadConfigs() {
        this.configListContainer.innerHTML = '<div class="loading-spinner">加载中...</div>';

        try {
            const params = new URLSearchParams({
                page: this.configCurrentPage,
                page_size: this.configPageSize
            });

            const response = await fetch(`/api/configs?${params.toString()}`);

            if (!response.ok) {
                throw new Error('获取配置列表失败');
            }

            const data = await response.json();
            this.renderConfigs(data);
            this.updateConfigPagination(data);

        } catch (error) {
            console.error('加载配置失败:', error);
            this.configListContainer.innerHTML = `
                <div class="empty-results">
                    <div class="empty-results-icon">❌</div>
                    <div class="empty-results-text">加载失败: ${error.message}</div>
                </div>
            `;
        }
    }

    renderConfigs(data) {
        if (!data.items || data.items.length === 0) {
            this.configListContainer.innerHTML = `
                <div class="empty-results">
                    <div class="empty-results-icon">📭</div>
                    <div class="empty-results-text">暂无配置</div>
                </div>
            `;
            return;
        }

        const configsHtml = data.items.map(config => `
            <div class="config-card">
                <div class="config-header">
                    <div class="config-title">
                        <span class="config-name">${this.escapeHtml(config.config_name)}</span>
                        <span class="config-badge ${config.is_active ? 'badge-active' : 'badge-inactive'}">
                            ${config.is_active ? '启用' : '禁用'}
                        </span>
                        ${config.need_login ? '<span class="config-badge badge-login">需登录</span>' : ''}
                    </div>
                    <div class="config-actions">
                        <button class="btn-icon" onclick="app.editConfig(${config.id})" title="编辑">✏️</button>
                        <button class="btn-icon" onclick="app.deleteConfig(${config.id}, '${this.escapeHtml(config.config_name)}')" title="删除">🗑️</button>
                    </div>
                </div>
                <div class="config-body">
                    <div class="config-info">
                        <div class="config-info-item">
                            <span class="config-info-label">ID:</span>
                            <span class="config-info-value">#${config.id}</span>
                        </div>
                        <div class="config-info-item">
                            <span class="config-info-label">目标URL:</span>
                            <span class="config-info-value">${this.escapeHtml(config.target_url)}</span>
                        </div>
                        ${config.auth_profile ? `
                        <div class="config-info-item">
                            <span class="config-info-label">登录态:</span>
                            <span class="config-info-value">${this.escapeHtml(config.auth_profile)}</span>
                        </div>
                        ` : ''}
                        <div class="config-info-item">
                            <span class="config-info-label">最大翻页:</span>
                            <span class="config-info-value">${config.max_pages} 页</span>
                        </div>
                        <div class="config-info-item">
                            <span class="config-info-label">创建时间:</span>
                            <span class="config-info-value">${this.formatDateTime(config.created_at)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        this.configListContainer.innerHTML = configsHtml;
    }

    updateConfigPagination(data) {
        const totalPages = Math.ceil(data.total / data.page_size);

        this.configPageInfo.textContent = `第 ${data.page} 页 / 共 ${totalPages} 页 (总计 ${data.total} 条)`;

        this.configPrevPageBtn.disabled = data.page === 1;
        this.configNextPageBtn.disabled = data.page >= totalPages || data.items.length < data.page_size;
    }

    async editConfig(configId) {
        try {
            const response = await fetch(`/api/configs/${configId}`);

            if (!response.ok) {
                throw new Error('获取配置详情失败');
            }

            const config = await response.json();
            this.openConfigEditModal(config);

        } catch (error) {
            console.error('加载配置详情失败:', error);
            showToast('加载失败', error.message, 'error');
        }
    }

    async deleteConfig(configId, configName) {
        const confirmed = await showConfirm(
            '确认删除配置',
            `确定要删除配置"${configName}"吗？\n\n删除后可以从数据库中恢复。`,
            {
                confirmText: '删除',
                cancelText: '取消',
                icon: '🗑️',
                danger: true
            }
        );

        if (!confirmed) {
            return;
        }

        try {
            const response = await fetch(`/api/configs/${configId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '删除失败');
            }

            showToast('删除成功', '配置已成功删除', 'success');
            this.loadConfigs();

        } catch (error) {
            console.error('删除配置失败:', error);
            showToast('删除失败', error.message, 'error');
        }
    }

    async saveConfig() {
        try {
            // 收集表单数据
            const formData = new FormData(this.configForm);

            // 解析 JSON 字段
            let inputConfigs, fieldsMapping;
            try {
                inputConfigs = JSON.parse(formData.get('input_configs'));
                fieldsMapping = JSON.parse(formData.get('fields_mapping'));
            } catch (e) {
                showToast('格式错误', 'JSON 格式错误，请检查输入框配置和字段映射规则', 'error');
                return;
            }

            // 构建请求数据
            const configData = {
                config_name: formData.get('config_name'),
                target_url: formData.get('target_url'),
                need_login: formData.get('need_login') === 'on',
                is_active: formData.get('is_active') === 'on',
                input_configs: inputConfigs,
                submit_selector: formData.get('submit_selector'),
                wait_selector: formData.get('wait_selector'),
                fields_mapping: fieldsMapping,
                max_pages: parseInt(formData.get('max_pages'))
            };

            // 可选字段
            if (configData.need_login) {
                configData.auth_profile = formData.get('auth_profile');
            }

            const loginUrl = formData.get('login_url');
            if (loginUrl) {
                configData.login_url = loginUrl;
            }

            const paginationSelector = formData.get('pagination_selector');
            if (paginationSelector) {
                configData.pagination_selector = paginationSelector;
            }

            // 发送请求
            const url = this.editingConfigId
                ? `/api/configs/${this.editingConfigId}`
                : '/api/configs';

            const method = this.editingConfigId ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(configData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '保存失败');
            }

            showToast('保存成功', this.editingConfigId ? '配置已成功更新' : '配置已成功创建', 'success');
            this.closeConfigEditModal();
            this.loadConfigs();

        } catch (error) {
            console.error('保存配置失败:', error);
            showToast('保存失败', error.message, 'error');
        }
    }
}

// ===== 自定义对话框和 Toast 功能 =====

/**
 * 显示确认对话框
 * @param {string} title - 对话框标题
 * @param {string} message - 对话框消息
 * @param {object} options - 配置选项
 * @returns {Promise<boolean>} - 用户是否确认
 */
function showConfirm(title, message, options = {}) {
    return new Promise((resolve) => {
        const {
            confirmText = '确定',
            cancelText = '取消',
            icon = '⚠️',
            danger = false
        } = options;

        // 创建对话框 HTML
        const dialogHTML = `
            <div class="custom-dialog-overlay" id="custom-dialog-overlay">
                <div class="custom-dialog">
                    <div class="dialog-header">
                        <span class="dialog-icon">${icon}</span>
                        <h3 class="dialog-title">${title}</h3>
                    </div>
                    <div class="dialog-body">${message}</div>
                    <div class="dialog-footer">
                        <button class="dialog-btn dialog-btn-cancel" id="dialog-cancel">${cancelText}</button>
                        <button class="dialog-btn ${danger ? 'dialog-btn-danger' : 'dialog-btn-confirm'}" id="dialog-confirm">${confirmText}</button>
                    </div>
                </div>
            </div>
        `;

        // 插入到页面
        document.body.insertAdjacentHTML('beforeend', dialogHTML);

        const overlay = document.getElementById('custom-dialog-overlay');
        const confirmBtn = document.getElementById('dialog-confirm');
        const cancelBtn = document.getElementById('dialog-cancel');

        // 确认按钮事件
        confirmBtn.addEventListener('click', () => {
            overlay.remove();
            resolve(true);
        });

        // 取消按钮事件
        cancelBtn.addEventListener('click', () => {
            overlay.remove();
            resolve(false);
        });

        // 点击背景关闭
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
                resolve(false);
            }
        });

        // ESC 键关闭
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                overlay.remove();
                resolve(false);
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
    });
}

/**
 * 显示 Toast 提示
 * @param {string} title - 提示标题
 * @param {string} message - 提示消息
 * @param {string} type - 提示类型: success, error, warning, info
 * @param {number} duration - 显示时长（毫秒），默认 3000
 */
function showToast(title, message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    // 图标映射
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

    const icon = icons[type] || icons.info;

    // 创建 Toast HTML
    const toastId = `toast-${Date.now()}`;
    const toastHTML = `
        <div class="toast toast-${type}" id="${toastId}">
            <span class="toast-icon">${icon}</span>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="closeToast('${toastId}')">×</button>
        </div>
    `;

    // 插入到容器
    container.insertAdjacentHTML('beforeend', toastHTML);

    // 自动关闭
    setTimeout(() => {
        closeToast(toastId);
    }, duration);
}

/**
 * 关闭指定的 Toast
 * @param {string} toastId - Toast ID
 */
function closeToast(toastId) {
    const toast = document.getElementById(toastId);
    if (toast) {
        toast.classList.add('toast-hide');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }
}

// 将函数暴露到全局作用域
window.showConfirm = showConfirm;
window.showToast = showToast;
window.closeToast = closeToast;

// 初始化应用
const app = new DashboardApp();
app.init();

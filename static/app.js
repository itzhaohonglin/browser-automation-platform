// WebSocket 连接管理
class DashboardApp {
    constructor() {
        this.ws = null;
        this.reconnectTimeout = null;
        this.reconnectDelay = 3000;
        this.maxLogs = 100;
        this.logs = [];
        this.currentJobId = null;

        // DOM 元素
        this.wsStatus = document.getElementById('ws-status');
        this.statTotal = document.getElementById('stat-total');
        this.statSuccess = document.getElementById('stat-success');
        this.statFailed = document.getElementById('stat-failed');
        this.statRate = document.getElementById('stat-rate');
        this.progressContent = document.getElementById('progress-content');
        this.authList = document.getElementById('auth-list');
        this.logContainer = document.getElementById('log-container');
    }

    init() {
        this.connectWebSocket();
        this.startHeartbeat();
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
}

// 初始化应用
const app = new DashboardApp();
app.init();

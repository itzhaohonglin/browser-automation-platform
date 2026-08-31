"""
WebSocket connection manager for real-time task monitoring
"""
import logging
from typing import Set
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    WebSocket 连接管理器（全局单例）

    负责管理活跃的 WebSocket 连接，并提供消息广播功能。
    """

    def __init__(self):
        """初始化连接管理器"""
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """
        添加新的 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """
        移除 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
        """
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """
        向所有活跃连接广播消息

        Args:
            message: 要广播的消息字典

        自动处理断开的连接：
        - 捕获 WebSocketDisconnect 异常
        - 捕获其他发送异常
        - 自动清理失败的连接
        """
        if not self.active_connections:
            return

        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                logger.warning("WebSocket disconnected during broadcast")
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(connection)

        # 清理断开的连接
        for connection in disconnected:
            self.active_connections.discard(connection)

        if disconnected:
            logger.info(f"Cleaned up {len(disconnected)} disconnected websockets")

    async def websocket_endpoint(self, websocket: WebSocket):
        """
        WebSocket 端点处理函数

        Args:
            websocket: WebSocket 连接对象

        处理流程：
        1. 接受连接并添加到活跃连接集合
        2. 保持连接，等待客户端消息（支持 ping/pong 心跳）
        3. 连接断开时自动清理
        """
        await self.connect(websocket)
        try:
            while True:
                # 等待客户端消息（用于心跳检测）
                data = await websocket.receive_text()

                # 支持简单的 ping/pong 心跳
                if data == "ping":
                    await websocket.send_text("pong")
                else:
                    logger.debug(f"Received message from client: {data}")

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await self.disconnect(websocket)


# 全局单例实例
websocket_manager = WebSocketManager()

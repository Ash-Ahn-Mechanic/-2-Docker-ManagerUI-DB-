from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import threading
import time

from manager_ui.backend.api import admin, client, recommendations
from manager_ui.backend.db.connection import check_connection
from manager_ui.backend.services.ws_manager import ws_manager


# ── ROS2 Admin 커맨드 퍼블리셔 노드 ──────────────────────────────
_admin_node = None

def _init_ros():
    global _admin_node
    try:
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
        import json

        class AdminCmdNode(Node):
            def __init__(self):
                super().__init__('manager_ui_admin')
                self.pub = self.create_publisher(String, '/admin_command', 10)

            def publish(self, command: str):
                msg = String()
                msg.data = json.dumps({'command': command})
                self.pub.publish(msg)

        rclpy.init()
        _admin_node = AdminCmdNode()
        threading.Thread(target=rclpy.spin, args=(_admin_node,), daemon=True).start()
        print('✅ ROS2 admin node 초기화 성공')
    except Exception as e:
        print(f'⚠️ ROS2 admin node 초기화 실패 (ROS2 없이 실행): {e}')


@asynccontextmanager
async def lifespan(app: FastAPI):
    if check_connection():
        print('✅ DB 연결 성공')
    else:
        print('❌ DB 연결 실패 — .env 확인 필요')
    _init_ros()
    yield


app = FastAPI(title='Robot Admin API', version='1.0.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(admin.router)
app.include_router(client.router)
app.include_router(recommendations.router)

# Manager UI 정적 파일
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.isdir(FRONTEND_DIR):
    from fastapi.responses import RedirectResponse

    @app.get('/')
    def root():
        return RedirectResponse(url='/manager')

    app.mount('/manager', StaticFiles(directory=FRONTEND_DIR, html=True), name='manager')


@app.websocket('/ws/client')
async def ws_client(websocket: WebSocket):
    await ws_manager.connect_client(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.websocket('/ws/admin/logs')
async def ws_admin(websocket: WebSocket):
    await ws_manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.post('/internal/notify')
async def internal_notify(payload: dict):
    """db_logger 프로세스에서 이벤트 발생 시 호출 → WebSocket으로 admin에 push"""
    await ws_manager.broadcast_admin(payload)
    return {'ok': True}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('manager_ui.backend.main:app', host='0.0.0.0', port=8000, reload=True)


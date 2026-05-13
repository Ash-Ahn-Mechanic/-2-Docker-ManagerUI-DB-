import json
import uuid
from datetime import datetime
import urllib.request

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from manager_ui.backend.db.connection import SessionLocal
from manager_ui.backend.db.models import CommandLog, ErrorLog
from manager_ui.backend.db import mongo

_NOTIFY_URL = 'http://localhost:8000/internal/notify'


def _notify(scope: str):
    try:
        body = json.dumps({'type': 'data_update', 'scope': scope}).encode()
        req = urllib.request.Request(_NOTIFY_URL, data=body,
                                     headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass


class DbLoggerNode(Node):
    def __init__(self):
        super().__init__('db_logger_node')

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(String, '/ui_bridge/state', self._on_ui_bridge_state, qos)

        self._current_command_id: str  = ''
        self._pending_raw_text: str    = ''
        self._current_action: str      = ''
        self._current_target: str      = ''
        self._execution_started: bool  = False

        self._prev_stt:           str  = ''
        self._prev_voice_command: str  = ''
        self._prev_status_str:    str  = ''
        self._prev_detection:     str  = ''
        self._prev_rosout:        str  = ''
        self._new_command_pending: bool = False

        self.get_logger().info('DbLoggerNode 시작 — /ui_bridge/state 구독 중')

    def _on_ui_bridge_state(self, msg: String):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            return

        stt_result    = data.get('stt_result', '')
        voice_command = data.get('voice_command', '')
        status_str    = data.get('status', '')
        detection_str = data.get('detection', '')
        rosout_str    = data.get('rosout', '')

        if stt_result and stt_result != self._prev_stt:
            self._prev_stt = stt_result
            self._pending_raw_text = stt_result
            self._new_command_pending = True

        if voice_command and self._new_command_pending:
            self._new_command_pending = False
            self._prev_voice_command = voice_command
            self._process_command(voice_command)

        if status_str and status_str != self._prev_status_str:
            self._prev_status_str = status_str
            self._process_status(status_str)

        if detection_str and detection_str != self._prev_detection:
            self._prev_detection = detection_str
            self._process_detection(detection_str)

        if rosout_str and rosout_str != self._prev_rosout:
            self._prev_rosout = rosout_str
            self._process_rosout(rosout_str)

    # ── /voice_command ──────────────────────────────
    def _process_command(self, voice_command: str):
        try:
            sequence = json.loads(voice_command)
        except json.JSONDecodeError:
            self.get_logger().error(f'voice_command JSON 파싱 실패: {voice_command}')
            return

        if not isinstance(sequence, list):
            self.get_logger().error('voice_command 형식 오류: JSON 배열이 아님')
            return

        command_id = str(uuid.uuid4())
        self._current_command_id = command_id
        self._current_action     = ''
        self._current_target     = ''
        self._execution_started  = False
        raw_text = self._pending_raw_text

        with SessionLocal() as db:
            db.add(CommandLog(
                command_id=command_id,
                raw_text=raw_text,
                status='received',
                action_count=len(sequence),
            ))
            db.commit()

        mongo_doc_id = ''
        try:
            mongo_doc_id = mongo.create_command(command_id, sequence)
        except Exception as e:
            self.get_logger().error(f'MongoDB command 저장 실패: {e}')

        if mongo_doc_id:
            with SessionLocal() as db:
                cmd = db.query(CommandLog).filter_by(command_id=command_id).first()
                if cmd:
                    cmd.mongo_doc_id = mongo_doc_id
                    db.commit()

        self.get_logger().info(
            f'command 저장 — id={command_id[:8]}… raw="{raw_text[:20]}" actions={len(sequence)}'
        )
        _notify('command')

    # ── /status ─────────────────────────────────────
    def _process_status(self, status_str: str):
        try:
            data = json.loads(status_str)
        except json.JSONDecodeError:
            self.get_logger().error(f'status JSON 파싱 실패: {status_str}')
            return

        state      = data.get('state', '')
        action     = data.get('action', '')
        target     = data.get('target', '')
        command_id = self._current_command_id

        with SessionLocal() as db:
            if command_id:
                cmd = db.query(CommandLog).filter_by(command_id=command_id).first()
                if cmd:
                    if state == 'RUNNING':
                        cmd.status         = 'executing'
                        cmd.current_action = action

                        if not self._execution_started:
                            cmd.started_at          = datetime.now()
                            self._execution_started = True

                        if action and action != self._current_action:
                            if self._current_action:
                                mongo.append_execution_log(command_id, {
                                    'type':   'action_done',
                                    'action': self._current_action,
                                    'target': self._current_target,
                                })
                            mongo.append_execution_log(command_id, {
                                'type':   'action_start',
                                'action': action,
                                'target': target,
                            })
                            self._current_action = action
                            self._current_target = target

                    elif state in ('SUCCESS', 'IDLE') and cmd.status == 'executing':
                        cmd.status         = 'done'
                        cmd.finished_at    = datetime.now()
                        cmd.current_action = None
                        if self._current_action:
                            mongo.append_execution_log(command_id, {
                                'type':   'action_done',
                                'action': self._current_action,
                                'target': self._current_target,
                            })

                    elif state == 'FAILURE':
                        if action == 'none':
                            # 큐 소진으로 인한 BT 종료 — 정상 완료
                            cmd.status         = 'done'
                            cmd.finished_at    = datetime.now()
                            cmd.current_action = None
                            if self._current_action:
                                mongo.append_execution_log(command_id, {
                                    'type':   'action_done',
                                    'action': self._current_action,
                                    'target': self._current_target,
                                })
                        else:
                            cmd.status         = 'failed'
                            cmd.finished_at    = datetime.now()
                            cmd.current_action = None
                            cmd.error_count    = (cmd.error_count or 0) + 1
                            if self._current_action:
                                mongo.append_execution_log(command_id, {
                                    'type':   'action_failed',
                                    'action': self._current_action,
                                    'target': self._current_target,
                                })

            db.commit()

        if command_id:
            try:
                mongo.append_execution_log(command_id, {
                    'type':   'state_change',
                    'state':  state,
                    'action': action,
                    'target': target,
                })
            except Exception as e:
                self.get_logger().warn(f'MongoDB execution_logs append 실패: {e}')

        self.get_logger().info(f'state 저장 — state={state} action={action} target={target}')
        _notify('status')

    # ── /detection ──────────────────────────────────
    def _process_detection(self, detection_str: str):
        try:
            data = json.loads(detection_str)
        except json.JSONDecodeError:
            self.get_logger().error(f'detection JSON 파싱 실패: {detection_str}')
            return

        command_id  = self._current_command_id or None
        object_name = data.get('object_name', '')
        confidence  = float(data.get('confidence', 0.0))
        detected    = bool(data.get('detected', False))

        if command_id:
            try:
                mongo.add_detection_result(command_id, {
                    'object_name': object_name,
                    'confidence':  confidence,
                    'detected':    detected,
                    'bbox':        data.get('bbox'),
                    'position':    data.get('position'),
                })
                mongo.append_execution_log(command_id, {
                    'type':        'detection',
                    'object_name': object_name,
                    'confidence':  confidence,
                    'detected':    detected,
                })
            except Exception as e:
                self.get_logger().warn(f'MongoDB detection 저장 실패: {e}')

        self.get_logger().info(
            f'detection — object={object_name} conf={confidence:.2f} detected={detected}'
        )
        _notify('detection')

    # ── /rosout (WARN 이상만 저장) ───────────────────
    def _process_rosout(self, rosout_str: str):
        try:
            data = json.loads(rosout_str)
        except json.JSONDecodeError:
            return

        level = data.get('level', 'INFO')
        if level not in ('ERROR', 'FATAL'):
            return

        command_id = self._current_command_id or None

        with SessionLocal() as db:
            db.add(ErrorLog(
                command_id=command_id,
                level=level,
                node_name=data.get('node', ''),
                message=data.get('msg', ''),
            ))
            if command_id and level in ('ERROR', 'FATAL'):
                cmd = db.query(CommandLog).filter_by(command_id=command_id).first()
                if cmd:
                    cmd.error_count = (cmd.error_count or 0) + 1
            db.commit()
        _notify('error')


def main():
    rclpy.init()
    node = DbLoggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

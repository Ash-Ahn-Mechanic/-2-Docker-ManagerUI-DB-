"""
MongoDB 연결 모듈 — command_documents 컬렉션 전용

도큐먼트 구조:
    {
        "command_id":       "uuid",
        "parsed_result":    [{"action": "pick", "params": {"target": "사과"}}, ...],
        "recipe_sequence":  ["pick", "shake"],          # 액션명 순서 목록
        "action_params":    [{"seq": 0, "action": "pick", "params": {...}, "status": "pending"}, ...],
        "detection_result": [],                         # ObjectDetectionNode 결과
        "execution_logs":   [{"timestamp": ..., "type": "state_change", ...}, ...]
    }

    ※ raw_text / created_at / finished_at 은 MySQL command_logs에만 저장 (중복 제거)

사용 방법:
    from manager_ui.backend.db import mongo

    # 명령 생성 → MongoDB _id(str) 반환
    doc_id = mongo.create_command(command_id, parsed_result)

    # 실행 로그 추가 (상태 전환, 액션 갱신 등)
    mongo.append_execution_log(command_id, {
        'type': 'state_change', 'state': 'EXECUTING', 'detail': {...}
    })

    # 액션 상태 갱신
    mongo.update_action_status(command_id, seq=0, status='done')

    # 탐지 결과 추가
    mongo.add_detection_result(command_id, {
        'object_name': '사과', 'confidence': 0.95,
        'position': {'x': 0.3, 'y': 0.1, 'z': 0.5}, 'detected': True
    })

    # command_id로 전체 도큐먼트 조회
    doc = mongo.get_command(command_id)

환경변수 (manager_ui/.env):
    MONGO_URI=mongodb://localhost:27017
    MONGO_DB_NAME=robot_admin
    MONGO_COMMAND_COLLECTION=command_documents
"""

from datetime import datetime
from pymongo import MongoClient
from manager_ui.backend.config import settings

_client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
_db = _client[settings.mongo_db_name]
commands = _db[settings.mongo_command_collection]


def create_command(command_id: str, parsed_result: list) -> str:
    """command_documents에 새 도큐먼트를 삽입하고 MongoDB _id(str)를 반환.

    raw_text / created_at / finished_at 은 MySQL command_logs에만 저장.
    """
    action_params = [
        {
            'seq':    i,
            'action': step.get('action', ''),
            'params': step.get('params', {}),
            'status': 'pending',
        }
        for i, step in enumerate(parsed_result)
    ]
    doc = {
        'command_id':       command_id,
        'parsed_result':    parsed_result,
        'recipe_sequence':  [step.get('action', '') for step in parsed_result],
        'action_params':    action_params,
        'detection_result': [],
        'execution_logs':   [],
    }
    result = commands.insert_one(doc)
    return str(result.inserted_id)


def append_execution_log(command_id: str, entry: dict):
    """execution_logs 배열에 로그 항목을 추가. timestamp는 자동 삽입."""
    entry.setdefault('timestamp', datetime.now())
    commands.update_one(
        {'command_id': command_id},
        {'$push': {'execution_logs': entry}},
    )


def update_action_status(command_id: str, seq: int, status: str):
    """action_params 배열에서 seq에 해당하는 항목의 status를 갱신."""
    commands.update_one(
        {'command_id': command_id, 'action_params.seq': seq},
        {'$set': {'action_params.$.status': status}},
    )


def add_detection_result(command_id: str, result: dict):
    """detection_result 배열에 탐지 결과를 추가."""
    result.setdefault('timestamp', datetime.now())
    commands.update_one(
        {'command_id': command_id},
        {'$push': {'detection_result': result}},
    )


def get_command(command_id: str) -> dict | None:
    """command_id로 도큐먼트를 조회. 없으면 None 반환. _id 필드 제외."""
    return commands.find_one({'command_id': command_id}, {'_id': 0})


def get_all_detections(limit: int = 50) -> list:
    """모든 도큐먼트의 detection_result를 집계해 최신순으로 반환."""
    pipeline = [
        {'$unwind': '$detection_result'},
        {'$sort': {'detection_result.timestamp': -1}},
        {'$limit': limit},
        {'$project': {
            '_id':         0,
            'command_id':  1,
            'object_name': '$detection_result.object_name',
            'confidence':  '$detection_result.confidence',
            'position':    '$detection_result.position',
            'detected':    '$detection_result.detected',
            'timestamp':   '$detection_result.timestamp',
        }},
    ]
    return list(commands.aggregate(pipeline))

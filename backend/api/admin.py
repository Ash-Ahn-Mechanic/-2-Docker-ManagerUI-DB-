from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from manager_ui.backend.db.connection import get_db
from manager_ui.backend.db.models import CommandLog, ErrorLog
from manager_ui.backend.db import mongo

router = APIRouter(prefix='/admin', tags=['admin'])


@router.get('/commands')
def get_commands(limit: int = Query(50, le=200), db: Session = Depends(get_db)):
    rows = db.query(CommandLog).order_by(desc(CommandLog.created_at)).limit(limit).all()
    return [
        {
            'command_id':    r.command_id,
            'mongo_doc_id':  r.mongo_doc_id,
            'raw_text':      r.raw_text,
            'status':        r.status,
            'action_count':  r.action_count,
            'current_action': r.current_action,
            'error_count':   r.error_count,
            'created_at':    r.created_at,
            'started_at':    r.started_at,
            'finished_at':   r.finished_at,
        }
        for r in rows
    ]


@router.get('/commands/{command_id}')
def get_command_detail(command_id: str):
    """MongoDB에서 명령 상세 문서 전체 반환"""
    doc = mongo.get_command(command_id)
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail='command not found')
    return doc


@router.get('/actions')
def get_actions(command_id: str = Query(...), db: Session = Depends(get_db)):
    """command_id의 MongoDB action_params 반환"""
    doc = mongo.get_command(command_id)
    if not doc:
        return []
    return doc.get('action_params', [])


@router.get('/errors')
def get_errors(limit: int = Query(100, le=500), db: Session = Depends(get_db)):
    rows = db.query(ErrorLog).order_by(desc(ErrorLog.created_at)).limit(limit).all()
    return [
        {
            'id':         r.id,
            'command_id': r.command_id,
            'level':      r.level,
            'node_name':  r.node_name,
            'message':    r.message,
            'created_at': r.created_at,
        }
        for r in rows
    ]


@router.get('/detections')
def get_detections(limit: int = Query(50, le=200)):
    """MongoDB detection_result 집계 반환"""
    return mongo.get_all_detections(limit=limit)


@router.post('/emergency-stop')
def emergency_stop():
    from manager_ui.backend.main import _admin_node
    if not _admin_node:
        return {'ok': False, 'message': 'ROS2 node not ready'}
    _admin_node.publish('ESTOP')
    return {'ok': True}


@router.post('/admin-unlock')
def admin_unlock():
    from manager_ui.backend.main import _admin_node
    if not _admin_node:
        return {'ok': False, 'message': 'ROS2 node not ready'}
    _admin_node.publish('UNLOCK')
    return {'ok': True}

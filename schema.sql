-- ============================================================
-- robot_admin — MySQL + MongoDB 혼합 구조 (v4)
-- MySQL  : command_logs / error_logs (인덱스 전용)
-- MongoDB: command_documents (계층적 상세 데이터 전용)
-- command_id 가 MySQL ↔ MongoDB 연결 키
-- ============================================================

CREATE DATABASE IF NOT EXISTS robot_admin
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE robot_admin;

-- ── 명령 요약 ────────────────────────────────────────────────
-- 집계·필터 전용. 상세 JSON(parsed_text, full execution logs)은 MongoDB로
CREATE TABLE IF NOT EXISTS command_logs (
    command_id     VARCHAR(100) PRIMARY KEY,
    mongo_doc_id   VARCHAR(24),               -- MongoDB ObjectId (hex)
    raw_text       TEXT,                       -- STT 원문
    status         VARCHAR(50),               -- received / executing / done / failed
    action_count   INT          DEFAULT 0,    -- 전체 액션 수
    current_action VARCHAR(100),              -- 현재 실행 중인 액션명
    error_count    INT          DEFAULT 0,    -- 누적 에러 수
    created_at     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    started_at     DATETIME,                  -- 첫 EXECUTING 진입 시각
    finished_at    DATETIME,                  -- 완료·실패 시각
    INDEX idx_created_at (created_at)
);

-- ── 에러 로그 ────────────────────────────────────────────────
-- recommendations 규칙 매칭에 사용하므로 MySQL 유지
CREATE TABLE IF NOT EXISTS error_logs (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    command_id VARCHAR(100),
    level      VARCHAR(10),                  -- WARN / ERROR / FATAL
    node_name  VARCHAR(100),
    message    TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

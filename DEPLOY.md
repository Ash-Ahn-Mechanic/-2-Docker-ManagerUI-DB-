# Robot Stack 배포 가이드 (ver5)

Manager UI (FastAPI) + db_logger (ROS2) + MySQL + MongoDB 를 3개 컨테이너로 실행합니다.  
이미지는 Docker Hub에서 자동으로 pull 되며, DB 데이터는 로컬 디렉토리에 유지됩니다.

---

## 컨테이너 구성

| 컨테이너 | 이미지 | 역할 |
|---|---|---|
| mysql | mysql:8.0 | command_logs, error_logs 저장 |
| mongodb | mongo:7 | command_documents (상세 실행 로그) 저장 |
| robot | ash20000529/robot-stack:ver5 | Manager UI (FastAPI :8000) + db_logger_node (ROS2) |

> `network_mode: host` — 세 컨테이너 모두 호스트 네트워크 공유.  
> robot 컨테이너가 ROS2 DDS 토픽을 메인 PC 호스트 노드들과 직접 주고받습니다.

---

## 사전 요구사항

- Docker 및 Docker Compose 설치
- 인터넷 연결 (Docker Hub pull)

```bash
docker --version
docker compose version
```

---

## 1. 파일 준비

아래 3개 파일을 같은 폴더에 준비합니다.

```
deploy/
├── docker-compose.deploy.yml
├── schema.sql
└── .env
```

---

## 2. .env 설정

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=robot_admin
DB_USER=robot
DB_PASSWORD=변경필요
MYSQL_ROOT_PASSWORD=변경필요

MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=robot_admin
MONGO_COMMAND_COLLECTION=command_documents

ROS_DOMAIN_ID=0
```

> `DB_PASSWORD`, `MYSQL_ROOT_PASSWORD` 는 반드시 변경합니다.  
> `ROS_DOMAIN_ID` 는 메인 PC 호스트와 동일한 값으로 설정합니다.  
> 호스트 확인: `echo $ROS_DOMAIN_ID`

---

## 3. 실행

```bash
docker compose -f docker-compose.deploy.yml up -d
```

최초 실행 시 MySQL이 `schema.sql` 을 자동으로 읽어 DB · 테이블을 초기화합니다.

---

## 4. 확인

```bash
# 컨테이너 상태
docker compose -f docker-compose.deploy.yml ps

# 전체 로그
docker compose -f docker-compose.deploy.yml logs -f

# robot 컨테이너 내부 로그만
docker compose -f docker-compose.deploy.yml logs -f robot
```

브라우저에서 `http://localhost:8000/manager` 접속 후 **CONNECTED** 표시되면 정상입니다.

---

## 5. 데이터 저장 위치

DB 데이터는 `docker-compose.deploy.yml` 이 있는 디렉토리 기준 **bind mount** 로 저장됩니다.

```
deploy/
├── db_data/
│   ├── mysql/    ← MySQL 데이터 (자동 생성)
│   └── mongo/    ← MongoDB 데이터 (자동 생성)
```

컨테이너를 삭제하거나 `docker compose down -v` 를 실행해도 `db_data/` 는 로컬에 유지됩니다.

---

## 6. 통신 구조

```
메인 PC 호스트 ROS2 노드
────────────────────────────────────────────────────────
state_manager  ──→  /voice_command_via, /stt_result_via, /status
object_det     ──→  /detection
dsr_bringup    ──→  /rosout
                        │  (DDS, network_mode: host)
                        ▼
              robot 컨테이너 (db_logger_node)
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
       localhost:3306        localhost:27017
          MySQL                 MongoDB

브라우저 ──→ localhost:8000 ──→ Manager UI (robot 컨테이너)
```

---

## 7. 중지 / 재시작 / 초기화

```bash
# 중지 (데이터 유지)
docker compose -f docker-compose.deploy.yml down

# 재시작
docker compose -f docker-compose.deploy.yml up -d

# DB 초기화 (시연 리셋) — db_data/ 폴더 직접 삭제
docker compose -f docker-compose.deploy.yml down
rm -rf db_data/
docker compose -f docker-compose.deploy.yml up -d
```

> 컴퓨터 재부팅 후 Docker 데몬이 시작되면 `restart: unless-stopped` 설정으로 컨테이너가 자동으로 올라옵니다.

---

## 8. 이미지 업데이트

```bash
docker compose -f docker-compose.deploy.yml pull robot
docker compose -f docker-compose.deploy.yml up -d robot
```

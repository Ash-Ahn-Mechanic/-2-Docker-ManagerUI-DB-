# 호스트 DB 설치 가이드 (초심자용)

MySQL과 MongoDB를 호스트(Ubuntu)에 직접 설치합니다.  
컨테이너는 `network_mode: host` 로 실행되므로 호스트의 DB에 `localhost` 로 바로 접근합니다.

---

## 1. MySQL 설치

```bash
sudo apt update
sudo apt install -y mysql-server
```

설치 후 자동으로 실행됩니다. 상태 확인:

```bash
sudo systemctl status mysql
```

`active (running)` 이면 정상입니다.

---

## 2. MySQL 초기 설정

### root 접속

```bash
sudo mysql
```

### DB / 유저 / 테이블 생성

아래 SQL을 순서대로 붙여넣기 합니다.

**① DB 생성**
```sql
CREATE DATABASE IF NOT EXISTS robot_admin
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
```

**② 유저 생성** (비밀번호는 .env의 DB_PASSWORD와 동일하게)
```sql
CREATE USER IF NOT EXISTS 'robot'@'localhost'
    IDENTIFIED WITH mysql_native_password BY '여기에비밀번호';

CREATE USER IF NOT EXISTS 'robot'@'%'
    IDENTIFIED WITH mysql_native_password BY '여기에비밀번호';
```

**③ 권한 부여**
```sql
GRANT ALL PRIVILEGES ON robot_admin.* TO 'robot'@'localhost';
GRANT ALL PRIVILEGES ON robot_admin.* TO 'robot'@'%';
FLUSH PRIVILEGES;
exit;
```

**④ 스키마 적용**

`schema.sql` 파일로 DB·테이블을 한 번에 생성합니다.

```bash
sudo mysql < schema.sql
```

**⑤ 확인**
```bash
sudo mysql -e "USE robot_admin; SHOW TABLES;"
```

`command_logs`, `error_logs` 두 테이블이 보이면 완료입니다.

---

## 3. MongoDB 설치

```bash
# GPG 키 등록
curl -fsSL https://pgp.mongodb.com/server-7.0.asc \
    | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

# 저장소 등록
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" \
    | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# 설치
sudo apt update
sudo apt install -y mongodb-org
```

MongoDB 시작 및 자동 시작 등록:

```bash
sudo systemctl start mongod
sudo systemctl enable mongod
```

상태 확인:

```bash
sudo systemctl status mongod
```

`active (running)` 이면 정상입니다.

---

## 4. 재부팅 후 자동 시작 확인

재부팅해도 자동으로 시작되도록 설정:

```bash
sudo systemctl enable mysql
sudo systemctl enable mongod
```

---

## 5. DB 초기화 (시연 리셋)

데이터를 전부 지우고 싶을 때:

```bash
sudo mysql -e "DROP DATABASE IF EXISTS robot_admin;"
sudo mysql < schema.sql
mongosh --eval "db.getSiblingDB('robot_admin').command_documents.drop()"
```

---

## 6. 연결 확인

DB가 준비됐으면 컨테이너 실행:

```bash
docker compose up -d
```

브라우저에서 `http://localhost:8000/manager` 접속 후 **CONNECTED** 뜨면 완료입니다.

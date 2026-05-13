# HOMIE — Helping Out! Making It Easy!
> **조 이름:** B-2조  
> **팀원:** 박기범(시스템 총괄) · 안상헌(Docker/DB/UI) · 이지민(Voice/LLM) · 김재흥(Motion) · 김재훈(Vision)

두산 M0609 협동 로봇 기반 가정용 도우미 로봇 시스템.  
음성 명령 → LLM 파싱 → BehaviorTree 제어 → 객체 탐지 → 로봇 동작의 end-to-end 파이프라인을 구현한다.

---

## 1. 🎨 시스템 설계 및 플로우 차트

### 1-1. 시스템 설계도 (System Architecture)
<p align="center">
  <img src="./images/system_architecture.png" alt="시스템 설계도" width="700">
</p>

* *음성·비전·로봇 제어가 ROS2 단일 그래프로 연결되며, ui_bridge 노드가 10Hz JSON으로 외부 Docker UI / DB에 데이터를 통합 전달한다.*

### 1-2. 플로우 차트 (Flow Chart)
<p align="center">
  <img src="./images/flow_chart.png" alt="플로우 차트" width="500">
</p>

* *Wakeup → STT → LLM 파싱 → BT tick → 객체 탐지 → 로봇 동작 → DB 로깅의 전체 흐름을 나타낸다.*

---

## 2. 🖥️ 운영체제 환경 (OS Environment)

| 항목 | 내용 |
|:---|:---|
| **OS** | Ubuntu 22.04 LTS |
| **ROS Version** | ROS2 Humble |
| **Language** | Python 3.10 / C++17 |
| **Container** | Docker (Compose) |
| **IDE** | VS Code |
| **ROS_DOMAIN_ID** | 86 |

---

## 3. 🛠️ 사용 장비 목록 (Hardware List)

| 장비명 (Model) | 수량 | 비고 |
|:---:|:---:|:---|
| Doosan M0609 | 1 | 6축 협동 로봇 (TCP 12345) |
| OnRobot RG | 1 | 그리퍼 (Force 8–25 N) |
| Intel RealSense D-series | 1 | RGB-D 카메라 (USB-C) |
| USB 마이크 | 1 | 48 kHz mono int16 |

---

## 4. 📦 의존성 (Dependencies)

### 4-1. 로봇 제어 (`cobot_ws`)
* ROS2 Humble (rclpy / rclcpp)
* BehaviorTree.CPP v3
* CycloneDDS
* DSR_ROBOT2 (Doosan SDK)
* Ultralytics YOLO 11
* pyrealsense2 / cv_bridge / OpenCV
* openwakeword · onnxruntime
* openai (Whisper STT · GPT-4o)
* langchain==0.3.27 · langchain-openai==0.3.28
* pymodbus==2.5.3
* pyaudio · scipy · numpy

### 4-2. Manager UI / Docker (`manager_ui`)
```
fastapi==0.115.12
uvicorn[standard]==0.34.0
pymysql==1.1.1
cryptography==44.0.3
sqlalchemy==2.0.40
pymongo==4.12.1
pydantic-settings==2.9.1
```

### 4-3. Client Web UI (`web/cobot2`)
```
fastapi==0.136.1
uvicorn==0.46.0
websockets==16.0
pyaudio==0.2.14
numpy==1.24.4
scipy==1.15.3
openwakeword==0.6.0
onnxruntime==1.23.2
openai==1.98.0
```

---

## 5. ▶️ 실행 순서 (Usage Guide)

> **사전 준비 파일** (동일 폴더에 위치):  
> `docker-compose.deploy.yml` · `schema.sql` · `.env.example`

### Step 1. Docker 설치 (최초 1회)
```bash
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER   # 재로그인 필요
```

### Step 2. .env 설정 (최초 1회)
제공된 `.env.example` 을 복사해 비밀번호와 ROS_DOMAIN_ID를 설정한다.
```bash
cp .env.example .env
nano .env
```
```env
DB_PASSWORD=your_password
MYSQL_ROOT_PASSWORD=your_root_password
ROS_DOMAIN_ID=86        # 호스트 ROS 환경과 동일한 값
```

### Step 3. Manager UI (Docker) 실행
MySQL · MongoDB · Manager UI 가 컨테이너로 한 번에 기동된다.  
최초 실행 시 `schema.sql` 이 자동으로 적용되어 DB · 테이블이 생성된다.
```bash
docker compose -f docker-compose.deploy.yml up -d

# 상태 확인
docker compose -f docker-compose.deploy.yml ps
```
> 브라우저에서 `http://localhost:8000` 접속

### Step 4. bt_manager 의존성 설치 (최초 1회)
bt_manager 빌드에 필요한 라이브러리를 설치한다.
```bash
sudo apt install -y ros-humble-behaviortree-cpp-v3 nlohmann-json3-dev
```

### Step 5. cobot_ws 빌드 및 소스
```bash
cd ~/cobot_ws
colcon build --packages-select bt_manager cobot_core object_detection voice_processing cobot_bringup command od_msg
source install/setup.bash
```

### Step 6. 두산 로봇 드라이버 실행
로봇 전원을 켜고 PC와 이더넷으로 연결한 뒤 DSR 드라이버를 기동한다.
```bash
ros2 launch dsr_bringup2 dsr_bringup2_rviz.launch.py \
  mode:=real host:=192.168.1.100 port:=12345 model:=m0609
```

### Step 7. 전체 시스템 런치
음성, 비전, 로봇 제어, BT Manager 노드를 한 번에 실행한다.  
BT Manager는 다른 노드 준비 후 4초 지연 실행된다.
```bash
ros2 launch cobot_bringup system.launch.py
```

### Step 8. Client Web UI 실행
사용자용 클라이언트 UI 백엔드를 실행한다.
```bash
cd web/cobot2
pip install -r requirements.txt
python backend/main.py
```
> 브라우저에서 `http://localhost:8001` 접속  
> 외부 접속: `https://cobot2.thatshoon.com` (Cloudflare Tunnel)



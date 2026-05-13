FROM ros:humble-ros-base

ENV DEBIAN_FRONTEND=noninteractive

# Supervisor + colcon + CycloneDDS
RUN apt-get update && apt-get install -y \
    supervisor \
    python3-pip \
    python3-colcon-common-extensions \
    ros-humble-rmw-cyclonedds-cpp \
    && rm -rf /var/lib/apt/lists/*

ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Python 의존성
COPY manager_ui/requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Manager UI 앱
COPY manager_ui/__init__.py  /app/manager_ui/__init__.py
COPY manager_ui/backend/     /app/manager_ui/backend/
COPY manager_ui/frontend/    /app/manager_ui/frontend/

# db_logger ROS2 패키지 빌드
COPY src/db_logger/          /ros2_ws/src/db_logger/
RUN . /opt/ros/humble/setup.sh \
    && cd /ros2_ws \
    && colcon build --packages-select db_logger

# 프로세스 관리
COPY manager_ui/supervisord.conf  /etc/supervisor/conf.d/robot.conf
COPY manager_ui/entrypoint.sh     /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

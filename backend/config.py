from pathlib import Path
from pydantic_settings import BaseSettings

# .env 를 manager_ui/ 디렉터리에서 찾고, 없으면 환경변수만 사용 (Docker)
_ENV_FILE = Path(__file__).resolve().parents[1] / '.env'


class Settings(BaseSettings):
    db_host:       str = 'localhost'
    db_port:       int = 3306
    db_name:       str = 'robot_admin'
    db_user:       str = 'robot'
    db_password:   str = ''
    mongo_uri:                str = 'mongodb://localhost:27017'
    mongo_db_name:            str = 'robot_admin'
    mongo_command_collection: str = 'command_documents'

    @property
    def database_url(self) -> str:
        return (
            f'mysql+pymysql://{self.db_user}:{self.db_password}'
            f'@{self.db_host}:{self.db_port}/{self.db_name}'
            f'?charset=utf8mb4'
        )

    class Config:
        env_file = str(_ENV_FILE) if _ENV_FILE.exists() else None
        env_file_encoding = 'utf-8'
        extra = 'ignore'


settings = Settings()

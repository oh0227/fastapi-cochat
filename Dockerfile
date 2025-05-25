# 공식 Python 이미지를 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /fastapi-cochat 

# 의존성 먼저 복사 (Docker 캐시 최적화)
COPY requirements.txt .

# 의존성 설치
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 포트 개방 (FastAPI 기본: 8000)
EXPOSE 8000

# 컨테이너 시작 시 FastAPI 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

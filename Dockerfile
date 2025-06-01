# 베이스 이미지
FROM python:3.10.17

# 작업 디렉토리
WORKDIR /

# 필요 패키지 복사 및 설치
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 앱 코드 복사
COPY . .

# 포트 설정
EXPOSE 8080

# 시작 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
import schedule
import time
import os

# 실행할 스크립트 파일명
script_name = "main.py"

def run_script():
    print(f"📢 Running {script_name} at scheduled time...")
    os.system(f"python3 {script_name}")  # Windows 환경에서는 `python` 사용

# 매일 오전 7시에 실행되도록 스케줄 등록
schedule.every().day.at("07:00").do(run_script)

print("✅ Scheduler started. Waiting for the scheduled time to execute...")

# 무한 루프 실행 (스케줄링 유지)
while True:
    schedule.run_pending()
    time.sleep(60)  # 매 분마다 실행 여부 확인

import os

# 🔹 밴드 API 인증 정보
ACCESS_TOKEN = "ZQAAAf68XFkRb_ac35mMV6Ph_B7EC8cNRuOg2eF57PA0vAetszAx5owf_-O9C_B9XvjkP8rDPh2aSrh8kipazwNJvrwtFGPEHQ80FHmJkvpoGN_a"
BAND_KEY = "AACiTwSwFsMYyFcVhAzHHugU"  # 리딩바이블 밴드 키

# 현재 파일이 있는 디렉토리 경로 가져오기
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path=os.path.join(current_dir, "../data/korHRV.db")

# 🔹 CSV 파일 로드
csv_path = os.path.join(current_dir, "../data/reading_bible.csv")
book_map_path = os.path.join(current_dir, "../data/book_map.csv")
import requests
import sqlite3
import datetime
import pandas as pd
import re
from config.settings import ACCESS_TOKEN, BAND_KEY, db_path, csv_path, book_map_path

# 🔹 한글 요일 변환
WEEKDAYS_KOR = ["월", "화", "수", "목", "금", "토", "일"]

# 🔹 데이터 로드 함수
def load_data():
    """
    CSV, DB 데이터를 로드하고 다음 날짜의 성경 본문을 가져옴.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    df = pd.read_csv(csv_path, encoding="utf-8-sig").dropna(subset=['month', 'day'])
    book_map_df = pd.read_csv(book_map_path, encoding="utf-8-sig")
    bible_books = dict(zip(book_map_df["korean_name"], book_map_df["book_id"]))

    # 내일 날짜 계산
    tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)
    tomorrow_date = tomorrow.strftime('%m-%d')

    df['month'] = df['month'].astype(int)
    df['day'] = df['day'].astype(int)
    tomorrow_row = df[(df['month'].astype(str).str.zfill(2) + "-" + df['day'].astype(str).str.zfill(2)) == tomorrow_date]

    if tomorrow_row.empty:
        print("❌ 다음 날짜의 성경 읽기표를 찾을 수 없습니다.")
        exit()

    tomorrow_scriptures = {
        "구약": tomorrow_row.iloc[0]["old"],
        "신약": tomorrow_row.iloc[0]["new"],
        "시편": tomorrow_row.iloc[0]["poem"],
        "잠언": tomorrow_row.iloc[0]["Prov"],
    }
    youtube_link = tomorrow_row.iloc[0]["link"]

    return conn, cursor, bible_books, tomorrow_scriptures, youtube_link


# 🔹 성경 구절 파싱 함수
def parse_scripture_reference(reference):
    """
    성경 구절을 분석하여 책 이름들과 범위를 반환.
    한 책 내 범위 또는 여러 책에 걸친 범위 모두 처리 가능.
    """
    # 여러 책에 걸친 범위인 경우 (예: "창50:1-출2:10")
    if "-" in reference and any(char.isalpha() for char in reference.split("-")[1]):
        start_ref, end_ref = reference.split("-")
        
        # 시작 부분 파싱
        start_match = re.match(r"([가-힣]+)(\d+):(\d+)", start_ref)
        if not start_match:
            return None
        start_book = start_match.group(1)
        start_chapter = int(start_match.group(2))
        start_verse = int(start_match.group(3))
        
        # 끝 부분 파싱
        end_match = re.match(r"([가-힣]+)(\d+):(\d+)", end_ref)
        if not end_match:
            return None
        end_book = end_match.group(1)
        end_chapter = int(end_match.group(2))
        end_verse = int(end_match.group(3))
        
        return {
            "type": "multi_book",
            "start": (start_book, start_chapter, start_verse),
            "end": (end_book, end_chapter, end_verse)
        }
    
    # 기존의 한 책 내 범위 처리
    match = re.match(r"([가-힣]+)(\d+):(\d+)(?:-(\d+):(\d+)|-(\d+))?", reference)
    if match:
        book_name = match.group(1)
        start_chapter = int(match.group(2))
        start_verse = int(match.group(3))

        if match.group(4) and match.group(5):
            end_chapter = int(match.group(4))
            end_verse = int(match.group(5))
        elif match.group(6):
            end_chapter = start_chapter
            end_verse = int(match.group(6))
        else:
            end_chapter = start_chapter
            end_verse = start_verse

        return {
            "type": "single_book",
            "book": book_name,
            "start": (start_chapter, start_verse),
            "end": (end_chapter, end_verse)
        }

    return None


# 🔹 DB에서 성경 본문 가져오기
def get_scripture_text(cursor, bible_books, reference):
    """
    주어진 성경 구절 범위를 SQLite DB에서 가져옴.
    여러 책에 걸친 범위도 처리 가능.
    """
    parsed = parse_scripture_reference(reference)
    if not parsed:
        return f"📌 성경 본문을 찾을 수 없음: {reference}"

    if parsed["type"] == "multi_book":
        start_book, start_chapter, start_verse = parsed["start"]
        end_book, end_chapter, end_verse = parsed["end"]
        
        start_book_number = bible_books.get(start_book)
        end_book_number = bible_books.get(end_book)
        
        if start_book_number is None or end_book_number is None:
            return f"📌 성경 본문을 찾을 수 없음: {reference}"

        cursor.execute("""
            SELECT verse, content FROM bible_korHRV 
            WHERE (
                (book = ? AND chapter = ? AND verse >= ?) OR
                (book = ? AND chapter > ?) OR
                (book > ? AND book < ?) OR
                (book = ? AND chapter < ?) OR
                (book = ? AND chapter = ? AND verse <= ?)
            )
            ORDER BY book, chapter, verse
        """, (
            start_book_number, start_chapter, start_verse,
            start_book_number, start_chapter,
            start_book_number, end_book_number,
            end_book_number, end_chapter,
            end_book_number, end_chapter, end_verse
        ))

    else:  # single_book case
        book_name = parsed["book"]
        start_chapter, start_verse = parsed["start"]
        end_chapter, end_verse = parsed["end"]
        book_number = bible_books.get(book_name)

        if book_number is None:
            return f"📌 성경 본문을 찾을 수 없음: {reference}"

        if start_chapter == end_chapter:
            cursor.execute("""
                SELECT verse, content FROM bible_korHRV 
                WHERE book = ? AND chapter = ? AND verse BETWEEN ? AND ?
                ORDER BY chapter, verse
            """, (book_number, start_chapter, start_verse, end_verse))
        else:
            cursor.execute("""
                SELECT verse, content FROM bible_korHRV 
                WHERE book = ? AND 
                      ((chapter = ? AND verse >= ?) OR 
                       (chapter > ? AND chapter < ?) OR 
                       (chapter = ? AND verse <= ?))
                ORDER BY chapter, verse
            """, (book_number, start_chapter, start_verse, start_chapter, end_chapter, end_chapter, end_verse))

    verses = cursor.fetchall()
    scripture_text = "\n\n".join([f"{vs} {txt}" for vs, txt in verses])

    return scripture_text if scripture_text else f"📌 성경 본문을 찾을 수 없음: {reference}"


# 🔹 게시글 생성 (요청된 형식 유지)
def create_post_content(today_scriptures, scripture_texts, youtube_link):
    """
    게시글 내용을 생성하여 반환.
    """
    tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)
    tomorrow_date = tomorrow.strftime('%Y-%m-%d')
    tomorrow_weekday = WEEKDAYS_KOR[tomorrow.weekday()]  # 한글 요일 변환

    post_content = f"""
📖 {tomorrow_date}({tomorrow_weekday}) 리딩바이블 

{youtube_link}

({today_scriptures["구약"]})

{scripture_texts["구약"]}

({today_scriptures["신약"]})

{scripture_texts["신약"]}

({today_scriptures["시편"]})

{scripture_texts["시편"]}

({today_scriptures["잠언"]})

{scripture_texts["잠언"]}

"""
    return post_content


# 🔹 밴드 API에 게시글 업로드
def post_to_band(post_content):
    """
    밴드 API를 사용해 자동으로 게시글을 업로드.
    """
    url = "https://openapi.band.us/v2.2/band/post/create"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    data = {"band_key": BAND_KEY, "content": post_content, "do_push": True}

    response = requests.post(url, headers=headers, data=data)
    return response.json()


# 🔹 실행
if __name__ == "__main__":
    """
    성경 본문을 가져오고, 게시글을 생성하여 밴드에 자동 업로드.
    """
    conn, cursor, bible_books, today_scriptures, youtube_link = load_data()

    # 성경 본문 가져오기
    scripture_texts = {key: get_scripture_text(cursor, bible_books, value) for key, value in today_scriptures.items()}

    # 게시글 생성
    post_content = create_post_content(today_scriptures, scripture_texts, youtube_link)

    # 밴드에 게시글 업로드
    response = post_to_band(post_content)

    # DB 연결 종료
    conn.close()

    # 결과 출력
    print(response)

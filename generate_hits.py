import requests
import random
import string
import time
import os

# 設定
BASE_URL    = "https://xgf.nu/"
OUTPUT_FILE = "hits.txt"
# 環境変数から読み出し可能（デフォルト：2秒）
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "2"))
# １実行あたりの試行回数（デフォルト：50回）
TRIES = int(os.getenv("TRIES", "50"))

def random_string(max_length=5):
    length = random.randint(1, max_length)
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def main():
    # 既存のヒットコードを読み込み
    hits = set()
    try:
        with open(OUTPUT_FILE, "r") as f:
            hits = set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        pass

    for _ in range(TRIES):
        code = random_string()
        url = BASE_URL + code
        try:
            resp = requests.head(url, timeout=5)
            if resp.status_code == 200 and code not in hits:
                with open(OUTPUT_FILE, "a") as f:
                    f.write(code + "\n")
                hits.add(code)
                print(f"[HIT] {url}")
        except requests.RequestException:
            # タイムアウトや接続エラーは無視
            pass
        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main()

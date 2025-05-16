import os
import asyncio
import aiohttp
import aiofiles
import random
import string
import logging
from datetime import datetime

# Configuration
BASE_URL = os.getenv("BASE_URL", "https://xgf.nu/")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "hits.txt")
TRIES = int(os.getenv("TRIES", "200"))            # total trials per run
CONCURRENCY = int(os.getenv("CONCURRENCY", "10"))  # number of simultaneous requests
DELAY = float(os.getenv("DELAY", "0.5"))          # minimum delay (sec) between batches
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "5"))     # max code length
TIMEOUT = float(os.getenv("TIMEOUT", "5"))         # request timeout

# Setup logger
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
)
logger = logging.getLogger("scanner")


def random_code():
    length = random.randint(1, MAX_LENGTH)
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


async def scan_code(session, code, hits):
    url = BASE_URL + code
    try:
        async with session.head(url, timeout=TIMEOUT) as resp:
            if resp.status == 200 and code not in hits:
                logger.info(f"[HIT] {url}")
                async with aiofiles.open(OUTPUT_FILE, 'a') as f:
                    await f.write(code + "\n")
                hits.add(code)
                return True
            else:
                logger.debug(f"{resp.status} for {url}")
                return False
    except Exception as e:
        # ログに余分なコロンを表示しない
        msg = f"Error checking {url}"
        if str(e):
            msg += f" {e}"
        logger.warning(msg)
        return False


async def main():
    # Load existing hits
    hits = set()
    try:
        async with aiofiles.open(OUTPUT_FILE, 'r') as f:
            async for line in f:
                hits.add(line.strip())
    except FileNotFoundError:
        pass

    initial_hit_count = len(hits)
    conn = aiohttp.TCPConnector(limit=CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    new_hits = 0

    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        for i in range(TRIES):
            code = random_code()
            if i and i % CONCURRENCY == 0:
                await asyncio.sleep(DELAY)
            if await scan_code(session, code, hits):
                new_hits += 1

    return new_hits

if __name__ == '__main__':
    start = datetime.now()
    logger.info(f"Scan started: {start}")
    new_hits = asyncio.run(main())
    end = datetime.now()
    duration = end - start
    success_rate = (new_hits / TRIES * 100) if TRIES > 0 else 0
    logger.info(f"Scan finished: {end} (Duration: {duration})")
    logger.info(f"Total scans: {TRIES}")
    logger.info(f"New hits: {new_hits}")
    logger.info(f"Success rate: {success_rate:.2f}%")

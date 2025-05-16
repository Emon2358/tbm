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
            else:
                logger.debug(f"{resp.status} for {url}")
    except Exception as e:
        logger.warning(f"Error checking {url}: {e}")


async def main():
    # Load existing hits
    hits = set()
    try:
        async with aiofiles.open(OUTPUT_FILE, 'r') as f:
            async for line in f:
                hits.add(line.strip())
    except FileNotFoundError:
        pass

    conn = aiohttp.TCPConnector(limit=CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        tasks = []
        for i in range(TRIES):
            code = random_code()
            # throttle per batch of concurrency
            if i and i % CONCURRENCY == 0:
                await asyncio.sleep(DELAY)
            tasks.append(scan_code(session, code, hits))
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    start = datetime.now()
    logger.info(f"Scan started: {start}")
    asyncio.run(main())
    end = datetime.now()
    logger.info(f"Scan finished: {end} (Duration: {end - start})")

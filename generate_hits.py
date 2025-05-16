import os
import asyncio
import aiohttp
import aiofiles
import random
import string
import logging
import argparse
import sys
from datetime import datetime, timedelta

# Parse CLI arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Random scan of xgf.nu codes.")
    parser.add_argument('--duration', type=str, help="Run duration, e.g. '1h', '30m'. Overrides TRIES.")
    return parser.parse_args()

# Configuration from environment
BASE_URL = os.getenv("BASE_URL", "https://xgf.nu/")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "hits.txt")
TRIES = int(os.getenv("TRIES", "200"))            # total trials if duration not set
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
        msg = f"Error checking {url}"
        if str(e):
            msg += f" {e}"
        logger.warning(msg)
        return False


async def main(run_duration: timedelta = None):
    # Load existing hits
    hits = set()
    try:
        async with aiofiles.open(OUTPUT_FILE, 'r') as f:
            async for line in f:
                hits.add(line.strip())
    except FileNotFoundError:
        pass

    initial_hit_count = len(hits)
    new_hits = 0
    total_scans = 0

    conn = aiohttp.TCPConnector(limit=CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        start_time = datetime.now()
        while True:
            if run_duration and datetime.now() - start_time >= run_duration:
                break
            if not run_duration and total_scans >= TRIES:
                break
            code = random_code()
            if total_scans and total_scans % CONCURRENCY == 0:
                await asyncio.sleep(DELAY)
            if await scan_code(session, code, hits):
                new_hits += 1
            total_scans += 1

    return total_scans, new_hits


if __name__ == '__main__':
    args = parse_args()
    # Determine run duration
    run_duration = None
    if args.duration:
        unit = args.duration[-1]
        value = args.duration[:-1]
        try:
            num = float(value)
            if unit == 'h':
                run_duration = timedelta(hours=num)
            elif unit == 'm':
                run_duration = timedelta(minutes=num)
            else:
                raise ValueError
        except ValueError:
            logger.error("Invalid duration format. Use e.g. '1h' or '30m'.")
            sys.exit(1)

    start = datetime.now()
    logger.info(f"Scan started: {start}")
    total_scans, new_hits = asyncio.run(main(run_duration))
    end = datetime.now()
    duration = end - start
    success_rate = (new_hits / total_scans * 100) if total_scans > 0 else 0

    logger.info(f"Scan finished: {end} (Duration: {duration})")
    logger.info(f"Total scans: {total_scans}")
    logger.info(f"New hits: {new_hits}")
    logger.info(f"Success rate: {success_rate:.2f}%")

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cmd(command, *, check=True):
    print(f"\n[RUN] {' '.join(command)}")
    return subprocess.run(command, cwd=ROOT, check=check)


def run_python(script_path):
    run_cmd([sys.executable, str(ROOT / script_path)])


def start_consumer():
    command = [sys.executable, str(ROOT / "pipeline" / "kafka_consumer.py")]
    print(f"\n[START] {' '.join(command)}")
    return subprocess.Popen(command, cwd=ROOT)


def stop_process(process):
    if process is None:
        return
    if process.poll() is None:
        print("\n[STOP] Stopping Kafka consumer...")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def run_time_series(days_back):
    command = [
        sys.executable,
        "-c",
        (
            "from time_series.pipeline import TimeSeriesPipeline; "
            "p=TimeSeriesPipeline('mongodb://localhost:27017/','sentiment','clean_news'); "
            f"p.run_and_export(days_back={days_back}, export_path='output/sentiment_dashboard.json')"
        ),
    ]
    run_cmd(command)


def main():
    parser = argparse.ArgumentParser(description="One-click pipeline runner for Market Sense.")
    parser.add_argument("--skip-docker", action="store_true", help="Skip docker compose up step.")
    parser.add_argument("--skip-eval", action="store_true", help="Skip evaluation step.")
    parser.add_argument(
        "--consumer-drain-seconds",
        type=int,
        default=20,
        help="Seconds to keep consumer alive after scraping to drain Kafka.",
    )
    parser.add_argument("--days-back", type=int, default=30, help="Days for time-series export.")
    args = parser.parse_args()

    consumer_proc = None
    try:
        if not args.skip_docker:
            print("\n[CLEANUP] Force removing old containers to prevent conflict...")
            # Lệnh này sẽ xóa ép buộc zookeeper và shb-mongodb nếu chúng tồn tại
            subprocess.run(["docker", "rm", "-f", "zookeeper", "shb-mongodb"], 
                           cwd=ROOT, capture_output=True)
            
            # Sau đó mới chạy compose up
            run_cmd(["docker", "compose", "up", "-d"])

        consumer_proc = start_consumer()
        time.sleep(3)

        run_python("scrapers/sbv_scraper.py")
        run_python("scrapers/cafef_scraper.py")

        print(f"\n[WAIT] Draining Kafka for {args.consumer_drain_seconds}s...")
        time.sleep(args.consumer_drain_seconds)
        stop_process(consumer_proc)
        consumer_proc = None

        run_python("ai_engine/sentiment_analyzer.py")
        run_python("database/vector_store.py")

        # if not args.skip_eval:
        #     run_python("evaluation/run_evaluation.py")

        run_time_series(args.days_back)
        print("\n[DONE] Pipeline completed successfully.")
    except subprocess.CalledProcessError as exc:
        print(f"\n[ERROR] Command failed with code {exc.returncode}")
        raise
    finally:
        stop_process(consumer_proc)


if __name__ == "__main__":
    main()

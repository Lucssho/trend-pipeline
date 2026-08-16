import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_DIR = PROJECT_ROOT / "logs"
MODEL_DIR = PROJECT_ROOT / "data" / "bertopic_model"

SCRAPER_SCRIPT = PROJECT_ROOT / "scraper" / "rss_scraper.py"
TRAIN_SCRIPT = PROJECT_ROOT / "modeling" / "train_topics.py"
GENERATE_SCRIPT = PROJECT_ROOT / "dashboard" / "generate_data.py"

RSS_LOG = LOGS_DIR / "rss_scraper.log"
TRAIN_LOG = LOGS_DIR / "train_topics.log"
GENERATE_LOG = LOGS_DIR / "generate_data.log"
ORCHESTRATOR_LOG = LOGS_DIR / "run_pipeline_forever.log"

INTERVAL_SECONDS = 60 * 60
STEP_TIMEOUT_SECONDS = 30 * 60
RETRAIN_WEEKDAY = 6  # datetime.weekday(): Monday=0 ... Sunday=6
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def log_orchestrator(message):
    line = f"[{_timestamp()}] {message}"
    print(line, flush=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ORCHESTRATOR_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_step(script_path, log_path, label):
    """Runs a pipeline script as a subprocess and appends its output to log_path.
    Isolated as a subprocess so a crash in one step can't take down this process."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n=== {_timestamp()} - {label} - run start ===\n")
        f.flush()
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=STEP_TIMEOUT_SECONDS,
            )
            f.write(result.stdout or "")
            f.write(f"=== {_timestamp()} - {label} - run finished (exit code {result.returncode}) ===\n")
            f.flush()
            success = result.returncode == 0
            log_orchestrator(f"{label}: {'OK' if success else 'FAILED (exit ' + str(result.returncode) + ')'}")
            return success
        except subprocess.TimeoutExpired as exc:
            f.write(exc.stdout or "")
            f.write(f"=== {_timestamp()} - {label} - TIMED OUT after {STEP_TIMEOUT_SECONDS}s ===\n")
            f.flush()
            log_orchestrator(f"{label}: TIMED OUT after {STEP_TIMEOUT_SECONDS}s")
            return False
        except Exception as exc:
            f.write(f"=== {_timestamp()} - {label} - FAILED TO LAUNCH: {exc!r} ===\n")
            f.flush()
            log_orchestrator(f"{label}: FAILED TO LAUNCH - {exc!r}")
            return False


def run_cycle(state):
    log_orchestrator("cycle start")

    run_step(SCRAPER_SCRIPT, RSS_LOG, "rss_scraper")

    now = datetime.now()
    this_week = now.isocalendar()[:2]
    due_weekly_retrain = now.weekday() == RETRAIN_WEEKDAY and state["last_retrain_week"] != this_week
    # Bootstrap: a fresh clone has no trained model yet, so generate_data would
    # fail every hour until the first scheduled Sunday retrain. Train once up
    # front instead, then fall back to the normal weekly cadence.
    bootstrap_retrain = not MODEL_DIR.exists() and state["last_retrain_week"] is None

    if bootstrap_retrain or due_weekly_retrain:
        reason = "no trained model yet" if bootstrap_retrain else "weekly retrain"
        log_orchestrator(f"retraining topic model ({reason})")
        if run_step(TRAIN_SCRIPT, TRAIN_LOG, "train_topics"):
            state["last_retrain_week"] = this_week

    run_step(GENERATE_SCRIPT, GENERATE_LOG, "generate_data")
    log_orchestrator("cycle end")


def main():
    log_orchestrator(
        f"run_pipeline_forever starting - scrape+generate every hour, "
        f"retrain every {WEEKDAY_NAMES[RETRAIN_WEEKDAY]}"
    )
    state = {"last_retrain_week": None}
    try:
        while True:
            cycle_start = time.monotonic()
            try:
                run_cycle(state)
            except Exception as exc:
                log_orchestrator(f"UNEXPECTED ERROR in cycle, continuing to next scheduled run: {exc!r}")
            elapsed = time.monotonic() - cycle_start
            sleep_for = max(0.0, INTERVAL_SECONDS - elapsed)
            log_orchestrator(f"next cycle in {int(sleep_for)}s")
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        log_orchestrator("stopped (KeyboardInterrupt)")


if __name__ == "__main__":
    main()

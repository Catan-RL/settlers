import csv
from pathlib import Path
from typing import Any

"""
metrics we are keeping track of:

update_num, curr_entropy_coef, curr_reward_weight

baseline win rate and past win rates
maybe ending dev points per player
total rounds taken
decesions made per game

TODO:
ideally plot which action it is making/choosing
dump the arguments to a file
"""


class MetricsLogger:
    def __init__(self):
        RESULTS_DIR = Path(__file__).parent / "results/train_results"
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        this_run_num = 1
        while (RESULTS_DIR / f"run_{this_run_num:03}").exists():
            this_run_num += 1

        self.log_dir = RESULTS_DIR / f"run_{this_run_num:03}"
        self.log_dir.mkdir()  # Fail if already exists

        # track headers for each file as an ordered list
        self.file_headers = {}

        print("\n" + ("=" * 128) + "\n")
        print(f"Logging results to: {self.log_dir}")
        print("\n" + ("=" * 128) + "\n")

    def _get_log_file(self, name: str) -> Path:
        """Helper to get the full path to a log file."""
        return self.log_dir / f"{name}.csv"

    def _update_headers(self, file_name: str, new_headers: list[str]) -> None:
        """
        Updates the headers for a given file, rewriting the file if necessary.
        :param file_name: Name of the file (without extension).
        :param new_headers: Set of new headers to merge with existing ones.
        """
        log_file = self._get_log_file(file_name)
        current_headers = self.file_headers.get(file_name, [])
        changed = False

        # add new headers in the order they appear
        for header in new_headers:
            if header not in current_headers:
                current_headers.append(header)
                changed = True

        self.file_headers[file_name] = current_headers

        if not changed:
            return

        # rewrite the file with updated headers
        if log_file.exists():
            rows = []
            with open(log_file, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)  # read all existing rows
        else:
            rows = []

        with open(log_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=current_headers)
            writer.writeheader()

            # write back existing rows with updated headers
            for row in rows:
                writer.writerow(
                    {header: row.get(header, "") for header in current_headers}
                )

    def log(self, file_name="metrics", **metrics: dict[str, Any]) -> None:
        """
        Log metrics to a specific file in this_run_dir.
        :param file_name: Name of the file (without extension) to log to.
        :param metrics: Key-value pairs of metrics to log.
        """
        log_file = self._get_log_file(file_name)

        # update headers and rewrite the file if new keys are detected
        self._update_headers(file_name, metrics.keys())

        # Append the new metrics
        with open(log_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.file_headers[file_name])
            writer.writerow(metrics)

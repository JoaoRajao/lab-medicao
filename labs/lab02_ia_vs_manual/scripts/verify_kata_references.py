from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
KATAS_DIR = Path(__file__).resolve().parents[1] / "katas"


def verify_kata(kata_dir: Path) -> tuple[str, bool, str]:
    solution_path = kata_dir / "solution.py"
    reference_path = kata_dir / "reference_solution.py"
    backup_path = kata_dir / "solution.py.stub_backup"

    if not reference_path.exists():
        return kata_dir.name, False, "sem reference_solution.py"

    shutil.copy(solution_path, backup_path)
    try:
        shutil.copy(reference_path, solution_path)
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", str(kata_dir), "-q"],
            cwd=ROOT_DIR,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        passed = completed.returncode == 0
        return kata_dir.name, passed, completed.stdout.strip()
    finally:
        shutil.copy(backup_path, solution_path)
        backup_path.unlink()


def main() -> None:
    kata_dirs = sorted(
        d for d in KATAS_DIR.iterdir() if d.is_dir() and (d / "reference_solution.py").exists()
    )

    results = [verify_kata(d) for d in kata_dirs]

    print("\n=== Resumo ===")
    all_passed = True
    for name, passed, _ in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status} - {name}")
        all_passed = all_passed and passed

    if not all_passed:
        print("\n=== Detalhes das falhas ===")
        for name, passed, output in results:
            if not passed:
                print(f"\n--- {name} ---")
                print(output)
        sys.exit(1)


if __name__ == "__main__":
    main()

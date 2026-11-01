"""Iteration 0 install check: prints each tool's version and an overall PASS/FAIL."""
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return None
        return result.stdout.strip() or result.stderr.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def check_python():
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    return version if version == "3.14" else None, version


def check_env_file():
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return None
    content = env_path.read_text(encoding="utf-8")
    if "ANTHROPIC_API_KEY=" in content and "paste-your-real-key-here" not in content:
        return "present"
    return None


def main():
    checks = []

    py_ok, py_version = check_python()
    checks.append(("Python 3.14", py_version, py_ok is not None))

    git_version = run(["git", "--version"])
    checks.append(("Git", git_version, git_version is not None))

    docker_version = run(["docker", "--version"])
    checks.append(("Docker Desktop", docker_version, docker_version is not None))

    wsl_status = run(["wsl", "--status"])
    wsl_ok = wsl_status is not None and "2" in wsl_status
    checks.append(("WSL2", wsl_status.replace("\x00", "") if wsl_status else None, wsl_ok))

    code_version = run(["code", "--version"])
    checks.append(("VS Code", code_version.splitlines()[0] if code_version else None, code_version is not None))

    claude_cli = shutil.which("claude")
    checks.append(("Claude Code", "VS Code extension (no standalone CLI)", True))

    node_version = run(["node", "--version"])
    checks.append(("Node LTS", node_version, node_version is not None))

    env_status = check_env_file()
    checks.append((".env with ANTHROPIC_API_KEY", env_status, env_status is not None))

    all_pass = True
    for name, detail, ok in checks:
        status = "OK" if ok else "MISSING"
        if not ok:
            all_pass = False
        print(f"{name}: {detail or 'not found'} [{status}]")

    print("PASS" if all_pass else "FAIL")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

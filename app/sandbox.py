"""Runs generated conversion code's pytest suite inside an isolated Docker
container with no network access. Dependencies are baked into the sandbox
image ahead of time (Dockerfile.sandbox) so the validation run itself never
needs the network.
"""
import subprocess
from pathlib import Path

SANDBOX_IMAGE = "c05-skill-factory-sandbox:latest"
SANDBOX_DOCKERFILE = "Dockerfile.sandbox"
DEFAULT_TIMEOUT_SECONDS = 60


def build_sandbox_image() -> None:
    subprocess.run(
        ["docker", "build", "-f", SANDBOX_DOCKERFILE, "-t", SANDBOX_IMAGE, "."],
        check=True,
        capture_output=True,
        text=True,
    )


def write_generated_project(output_dir: Path, generated: dict) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    app_code = "\n\n".join(
        [generated["pydantic_model"], generated["rule_functions"], generated["fastapi_endpoint"]]
    )
    (output_dir / "generated_app.py").write_text(app_code, encoding="utf-8")
    (output_dir / "test_generated.py").write_text(generated["pytest_tests"], encoding="utf-8")


def run_sandboxed_tests(
    output_dir: Path,
    image: str = SANDBOX_IMAGE,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    output_dir = Path(output_dir).resolve()
    result = subprocess.run(
        [
            "docker", "run", "--rm", "--network", "none",
            "-v", f"{output_dir}:/work",
            "-w", "/work",
            image, "pytest", "-v", "test_generated.py",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "passed": result.returncode == 0,
    }

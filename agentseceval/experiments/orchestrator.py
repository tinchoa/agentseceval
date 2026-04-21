"""
EvalOrchestrator — main entrypoint for AgentSecEval runs.

Usage:
    agentseceval --config experiments/configs/baseline.yaml
    agentseceval --config experiments/configs/baseline.yaml --scenario A1_direct_01 --mode none
"""

import json
import os
import uuid
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from agentseceval.harness.agent.ollama_agent import OllamaAgent
from agentseceval.harness.logging.collector import LogCollector
from agentseceval.harness.metrics.asr import compute_asr, evaluate_success
from agentseceval.harness.metrics.breach import compute_breach_rates, detect_fs_breach, detect_net_breach
from agentseceval.harness.metrics.fidelity import classify_attack_layer, compute_fidelity_rate
from agentseceval.harness.metrics.leakage import measure_leakage
from agentseceval.harness.runner import ScenarioRunner
from agentseceval.harness.tools.base import LoggedTool

console = Console()

# Paths relative to the project root (the directory containing pyproject.toml)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_SCENARIOS_DIR = _PROJECT_ROOT / "dataset" / "scenarios"


class EvalOrchestrator:
    """
    Runs the full evaluation matrix.

    For isolation_mode=none : runs agent directly in-process.
    For isolation_mode=docker: spawns a Docker container per scenario run
                               using the Docker Python SDK, mounts results/,
                               then reads back the result JSON.
    """

    def __init__(self, config_path: str) -> None:
        with open(config_path) as f:
            self._config = yaml.safe_load(f)

        results_dir = os.environ.get("RESULTS_DIR") or self._config.get("results_dir", "results/")
        ollama_model = self._config.get("ollama_model", "llama3.2")

        # Override env var if config specifies a model
        os.environ.setdefault("OLLAMA_MODEL", ollama_model)

        self._agent = OllamaAgent()
        self._collector = LogCollector(results_dir=results_dir)
        self._results_dir = Path(results_dir)
        self._all_run_logs: list[dict] = []
        self._scenario_criteria_map: dict[str, list[str]] = {}

    def load_scenarios(self, scenario_ids: list[str]) -> list[dict]:
        """Load and validate YAML scenario files from dataset/scenarios/."""
        scenarios = []
        for sid in scenario_ids:
            matches = list(_SCENARIOS_DIR.rglob(f"{sid}.yaml"))
            if not matches:
                console.print(f"[red]WARNING: scenario file not found for {sid}[/red]")
                continue
            with matches[0].open() as f:
                scenario = yaml.safe_load(f)
            scenarios.append(scenario)
            self._scenario_criteria_map[sid] = scenario.get("success_criteria", [])
        return scenarios

    def run_matrix(self) -> None:
        """For each mode × scenario × repetition, run and collect results."""
        config = self._config
        scenario_ids: list[str] = config.get("scenarios", [])
        isolation_modes: list[str] = config.get("isolation_modes", ["none"])
        repetitions: int = config.get("repetitions", 3)
        run_id_base: str = config.get("run_id", str(uuid.uuid4()))

        scenarios = self.load_scenarios(scenario_ids)
        if not scenarios:
            console.print("[red]No scenarios loaded — aborting.[/red]")
            return

        total = len(isolation_modes) * len(scenarios) * repetitions
        done = 0

        for mode in isolation_modes:
            for scenario in scenarios:
                for rep in range(repetitions):
                    run_id = f"{run_id_base}__{mode}__rep{rep}"
                    sid = scenario.get("id", "unknown")
                    console.print(
                        f"[{done+1}/{total}] mode={mode} scenario={sid} rep={rep}"
                    )

                    if mode == "none":
                        runner = ScenarioRunner(
                            isolation_mode=mode,
                            agent=self._agent,
                            collector=self._collector,
                            model=os.environ.get("OLLAMA_MODEL", "unknown"),
                        )
                        log = runner.run_scenario(scenario, run_id=run_id)
                    elif mode == "docker":
                        log = self._run_in_docker(scenario, run_id=run_id)
                    elif mode == "gvisor":
                        log = self._run_in_gvisor(scenario, run_id=run_id)
                    else:
                        console.print(f"[yellow]Unknown mode '{mode}' — skipping.[/yellow]")
                        continue

                    self._all_run_logs.append(log)
                    done += 1

    def _run_in_docker(self, scenario: dict, run_id: str) -> dict:
        """
        Spawn one Docker container per (scenario, rep) run.
        The container runs the agent in-process (mode=none internally) but the
        result is tagged isolation_mode=docker so metrics treat it correctly.
        Host container logs are captured as host_events.
        """
        try:
            import docker as docker_sdk
        except ImportError:
            console.print("[red]docker SDK not installed — falling back to in-process run.[/red]")
            runner = ScenarioRunner(
                "docker", self._agent, self._collector,
                model=os.environ.get("OLLAMA_MODEL", "unknown"),
            )
            return runner.run_scenario(scenario, run_id=run_id)

        client = docker_sdk.from_env()
        sid = scenario.get("id", "unknown")
        results_abs = str(self._results_dir.resolve())
        ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2")

        # On Linux, host.docker.internal is not automatic — use host-gateway
        ollama_host = f"http://host.docker.internal:11434"

        try:
            container = client.containers.run(
                image="agentseceval:latest",
                command=[
                    "--config", "agentseceval/experiments/configs/baseline.yaml",
                    "--scenario", sid,
                    "--mode", "none",       # runs in-process inside container
                    "--repetitions", "1",   # exactly one rep per container
                    "--run-id", run_id,
                ],
                environment={
                    "OLLAMA_HOST":   ollama_host,
                    "OLLAMA_MODEL":  ollama_model,
                    "RANDOM_SEED":   os.environ.get("RANDOM_SEED", "42"),
                    "RESULTS_DIR":   "/results/",
                    "LOG_LEVEL":     os.environ.get("LOG_LEVEL", "INFO"),
                },
                volumes={results_abs: {"bind": "/results", "mode": "rw"}},
                extra_hosts={"host.docker.internal": "host-gateway"},
                user=f"{os.getuid()}:{os.getgid()}",
                detach=True,
                remove=False,
            )
            exit_status = container.wait(timeout=240)
            host_events = self.collect_host_events(container.id)
            container_exit_code = exit_status.get("StatusCode", -1)
            container.remove()
        except Exception as exc:
            console.print(f"[red]Docker run failed: {exc} — falling back to in-process.[/red]")
            runner = ScenarioRunner(
                "docker", self._agent, self._collector,
                model=ollama_model,
            )
            return runner.run_scenario(scenario, run_id=run_id)

        # Read result JSON written by the container to the mounted volume.
        # run_matrix() inside the container appends "__none__rep0" to the run_id
        # to form the subdirectory name, so the actual path is:
        #   /results/{run_id}__none__rep0/{sid}__none.json
        # We relabel isolation_mode → docker, add host_events, and move the file
        # into the canonical {run_id}/ directory for the host-side log collection.
        container_run_dir = f"{run_id}__none__rep0"
        result_path = self._results_dir / container_run_dir / f"{sid}__none.json"
        if result_path.exists():
            with result_path.open() as f:
                run_log = json.load(f)
            run_log["isolation_mode"] = "docker"
            run_log["host_events"] = host_events
            run_log["container_exit_code"] = container_exit_code
            run_log["run_id"] = run_id  # restore the outer run_id
            # Write to canonical docker path and clean up container artefact
            final_dir = self._results_dir / run_id
            final_dir.mkdir(parents=True, exist_ok=True)
            final_path = final_dir / f"{sid}__docker.json"
            with final_path.open("w") as f:
                json.dump(run_log, f, indent=2)
            result_path.unlink()
            return run_log

        # Container wrote nothing — return error log
        return {
            "run_id": run_id,
            "scenario_id": sid,
            "isolation_mode": "docker",
            "model": ollama_model,
            "timestamp": "",
            "agent_output": "",
            "tool_calls": [],
            "reasoning_trace": [],
            "host_events": host_events,
            "error": f"No result file after container run (exit {container_exit_code})",
        }

    def _run_in_gvisor(self, scenario: dict, run_id: str) -> dict:
        """
        Spawn one gVisor-sandboxed Docker container per (scenario, rep) run.

        Requires:
          - runsc (gVisor) installed on the host: https://gvisor.dev/docs/user_guide/install/
          - Docker configured with the 'runsc' runtime:
            /etc/docker/daemon.json → {"runtimes": {"runsc": {"path": "/usr/local/sbin/runsc"}}}

        The container is identical to the Docker mode but launched with
        --runtime=runsc, giving syscall interception via gVisor's sentry.
        Host events are collected from container logs (gVisor also surfaces
        seccomp-style denials via its sentry log).
        """
        try:
            import docker as docker_sdk
        except ImportError:
            console.print("[red]docker SDK not installed — falling back to in-process run.[/red]")
            runner = ScenarioRunner(
                "gvisor", self._agent, self._collector,
                model=os.environ.get("OLLAMA_MODEL", "unknown"),
            )
            return runner.run_scenario(scenario, run_id=run_id)

        # Verify runsc runtime is registered
        client = docker_sdk.from_env()
        info = client.info()
        if "runsc" not in info.get("Runtimes", {}):
            console.print(
                "[yellow]gVisor runtime 'runsc' not registered in Docker — "
                "falling back to runc (docker mode).[/yellow]"
            )
            log = self._run_in_docker(scenario, run_id=run_id)
            log["isolation_mode"] = "gvisor"   # re-tag for metrics
            return log

        sid = scenario.get("id", "unknown")
        results_abs = str(self._results_dir.resolve())
        ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
        ollama_host = "http://host.docker.internal:11434"

        try:
            container = client.containers.run(
                image="agentseceval:latest",
                command=[
                    "--config", "agentseceval/experiments/configs/baseline.yaml",
                    "--scenario", sid,
                    "--mode", "none",
                    "--repetitions", "1",
                    "--run-id", run_id,
                ],
                environment={
                    "OLLAMA_HOST":  ollama_host,
                    "OLLAMA_MODEL": ollama_model,
                    "RANDOM_SEED":  os.environ.get("RANDOM_SEED", "42"),
                    "RESULTS_DIR":  "/results/",
                    "LOG_LEVEL":    os.environ.get("LOG_LEVEL", "INFO"),
                },
                volumes={results_abs: {"bind": "/results", "mode": "rw"}},
                extra_hosts={"host.docker.internal": "host-gateway"},
                runtime="runsc",                          # ← gVisor sentry
                user=f"{os.getuid()}:{os.getgid()}",
                detach=True,
                remove=False,
            )
            exit_status = container.wait(timeout=300)   # gVisor is slower to start
            host_events = self.collect_host_events(container.id)
            container_exit_code = exit_status.get("StatusCode", -1)
            container.remove()
        except Exception as exc:
            console.print(f"[red]gVisor run failed: {exc} — falling back to in-process.[/red]")
            runner = ScenarioRunner(
                "gvisor", self._agent, self._collector,
                model=ollama_model,
            )
            return runner.run_scenario(scenario, run_id=run_id)

        # Same path logic as _run_in_docker
        container_run_dir = f"{run_id}__none__rep0"
        result_path = self._results_dir / container_run_dir / f"{sid}__none.json"
        if result_path.exists():
            with result_path.open() as f:
                run_log = json.load(f)
            run_log["isolation_mode"] = "gvisor"
            run_log["host_events"] = host_events
            run_log["container_exit_code"] = container_exit_code
            run_log["run_id"] = run_id
            final_dir = self._results_dir / run_id
            final_dir.mkdir(parents=True, exist_ok=True)
            final_path = final_dir / f"{sid}__gvisor.json"
            with final_path.open("w") as f:
                json.dump(run_log, f, indent=2)
            result_path.unlink()
            return run_log

        return {
            "run_id": run_id,
            "scenario_id": sid,
            "isolation_mode": "gvisor",
            "model": ollama_model,
            "timestamp": "",
            "agent_output": "",
            "tool_calls": [],
            "reasoning_trace": [],
            "host_events": host_events,
            "error": f"No result file after gVisor run (exit {container_exit_code})",
        }

    def collect_host_events(self, container_id: str) -> list[str]:
        """Read Docker container logs and parse for notable activity."""
        try:
            import docker as docker_sdk
            client = docker_sdk.from_env()
            container = client.containers.get(container_id)
            raw_logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
        except Exception:
            return []

        events = []
        for line in raw_logs.splitlines():
            line_lower = line.lower()
            # Surface filesystem and network activity lines
            if any(kw in line_lower for kw in ("open(", "read(", "write(", "connect(", "sendto(", "recvfrom(", "error", "warning", "flagged")):
                events.append(line.strip())
        return events

    def summarize(self) -> None:
        """Print final metrics table to console."""
        if not self._all_run_logs:
            console.print("[yellow]No run logs to summarize.[/yellow]")
            return

        # Group logs by (scenario_id, isolation_mode)
        groups: dict[tuple[str, str], list[dict]] = {}
        for log in self._all_run_logs:
            key = (log.get("scenario_id", "?"), log.get("isolation_mode", "?"))
            groups.setdefault(key, []).append(log)

        table = Table(title="Evaluation Summary", show_lines=True)
        table.add_column("scenario_id", style="cyan")
        table.add_column("mode", style="magenta")
        table.add_column("ASR (%)", justify="right")
        table.add_column("fs_breach (%)", justify="right")
        table.add_column("net_breach (%)", justify="right")
        table.add_column("leaked", justify="center")
        table.add_column("fidelity (%)", justify="right")
        table.add_column("exec/intent/none", justify="center")
        table.add_column("TSR", justify="center")

        for (sid, mode), logs in sorted(groups.items()):
            asr = compute_asr(logs, self._scenario_criteria_map)
            breach = compute_breach_rates(logs)
            leaked = any(measure_leakage(log)["leaked"] for log in logs)
            fidelity = compute_fidelity_rate(logs)
            layers = [classify_attack_layer(log) for log in logs]
            layer_summary = (
                f"{layers.count('execution')}/"
                f"{layers.count('intent')}/"
                f"{layers.count('none')}"
            )
            errors = sum(1 for log in logs if log.get("error"))
            tsr = f"{len(logs) - errors}/{len(logs)}"

            table.add_row(
                sid,
                mode,
                f"{asr:.1f}",
                f"{breach['fs_breach_rate']:.1f}",
                f"{breach['net_breach_rate']:.1f}",
                "YES" if leaked else "no",
                f"{fidelity:.1f}",
                layer_summary,
                tsr,
            )

        console.print(table)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="AgentSecEval orchestrator")
    parser.add_argument(
        "--config",
        default="agentseceval/experiments/configs/baseline.yaml",
        help="Path to experiment config YAML",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="Run a single scenario by ID (overrides config scenario list)",
    )
    parser.add_argument(
        "--mode",
        default=None,
        help="Override isolation mode (overrides config isolation_modes list)",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=None,
        help="Override number of repetitions (overrides config value)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        dest="run_id",
        help="Override run_id (used when spawned inside a Docker container)",
    )
    args = parser.parse_args()

    orchestrator = EvalOrchestrator(args.config)

    # Apply CLI overrides
    if args.scenario:
        orchestrator._config["scenarios"] = [args.scenario]
    if args.mode:
        orchestrator._config["isolation_modes"] = [args.mode]
    if args.repetitions is not None:
        orchestrator._config["repetitions"] = args.repetitions
    if args.run_id:
        orchestrator._config["run_id"] = args.run_id

    orchestrator.run_matrix()
    orchestrator.summarize()


if __name__ == "__main__":
    main()

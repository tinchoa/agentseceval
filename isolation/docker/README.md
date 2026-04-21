# Isolation Mode: docker

## Description

The `docker` isolation mode runs each scenario inside a standard Docker container using the
official `python:3.11-slim` base image. The container runs as a non-root user (`evaluser`)
and is evaluated with optional network and filesystem restrictions.

---

## Build the Image

```bash
docker build -t agentseceval -f isolation/docker/Dockerfile .
```

---

## Run a Single Scenario

```bash
docker run --rm \
  -e SCENARIO_ID=A1_direct_01 \
  -e ISOLATION_MODE=docker \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  -e OLLAMA_MODEL=llama3.2 \
  -v $(pwd)/results:/results \
  agentseceval
```

---

## Network Isolation Experiments (RQ1)

To deny all outbound network access (tests sandbox escape via HTTP):

```bash
docker run --rm \
  --network none \
  -e SCENARIO_ID=D2_sandbox_escape_net_01 \
  -e ISOLATION_MODE=docker \
  -v $(pwd)/results:/results \
  agentseceval
```

**Note:** With `--network none`, the Ollama connection will also be blocked. For scenarios
requiring Ollama inference, use a custom bridge network that permits only `host.docker.internal`.

---

## Filesystem Isolation Experiments (RQ1)

To mount the container filesystem as read-only with an explicit writable results volume:

```bash
docker run --rm \
  --read-only \
  --tmpfs /tmp \
  -e SCENARIO_ID=D1_sandbox_escape_fs_01 \
  -e ISOLATION_MODE=docker \
  -v $(pwd)/results:/results \
  agentseceval
```

---

## Ollama Connectivity

Ollama runs on the host. Inside the container, reach it via:

```
http://host.docker.internal:11434
```

Set `OLLAMA_HOST=http://host.docker.internal:11434` (already default in `entrypoint.sh`).
On Linux, add `--add-host=host.docker.internal:host-gateway` to the `docker run` command
if `host.docker.internal` is not automatically resolved.

---

## External Observer

The orchestrator reads container logs after the run using the Docker Python SDK:

```python
orchestrator.collect_host_events(container_id)
```

This captures stdout/stderr lines mentioning syscall-level events, errors, and flagged tool calls
to build the `host_events` field in each run log — fulfilling the external observer pattern.

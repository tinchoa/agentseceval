# Isolation Mode: gVisor

## Description

The `gvisor` isolation mode runs scenarios inside Docker containers that use gVisor's `runsc`
runtime. gVisor interposes on system calls between the container and the host kernel, providing
a much stronger isolation boundary than standard namespaces: most syscalls are handled by gVisor's
user-space kernel rather than reaching the host kernel directly.

---

## Prerequisites

- **Linux x86-64 only** — gVisor does not run on macOS or Windows.
- gVisor `runsc` binary installed. Installation instructions:
  [https://gvisor.dev/docs/user_guide/install/](https://gvisor.dev/docs/user_guide/install/)
- Docker configured to use the `runsc` runtime (see below).

---

## Configure Docker to Use gVisor

Add the `runsc` runtime to Docker's daemon configuration (`/etc/docker/daemon.json`):

```json
{
  "runtimes": {
    "runsc": {
      "path": "/usr/local/bin/runsc",
      "runtimeArgs": [
        "--platform=ptrace"
      ]
    }
  }
}
```

Then restart Docker:

```bash
sudo systemctl restart docker
```

---

## Verify gVisor Is Active

```bash
docker run --runtime=runsc hello-world
```

You should see the normal Hello World output. To confirm gVisor intercepted the syscalls:

```bash
docker run --runtime=runsc --rm ubuntu uname -r
# Output will show a gVisor kernel version string like: 4.4.0
```

---

## Run a Scenario Under gVisor

```bash
docker run --runtime=runsc --rm \
  -e SCENARIO_ID=D1_sandbox_escape_fs_01 \
  -e ISOLATION_MODE=gvisor \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  -v $(pwd)/results:/results \
  agentseceval
```

---

## Known Limitations and Unsupported Syscalls

gVisor does not support all Linux syscalls. The following may affect AgentSecEval:

| Feature | Status | Impact |
|---------|--------|--------|
| `ptrace` | Not supported | Cannot use ptrace-based debuggers inside container |
| `io_uring` | Partial support | Some async I/O patterns may fall back to epoll |
| `/proc` filesystem | Limited | Some `/proc` paths return stub data |
| Raw sockets | Not supported | Tools using raw sockets will fail |
| KVM access | Not supported inside gVisor | Nested virtualisation unavailable |

For AgentSecEval's simulated tools (no real syscalls), these limitations do not affect
correctness. However, if real tool execution is added in a future milestone, verify
tool compatibility under `runsc` before publishing results.

---

## Reference Configuration

See `runsc-config.toml` in this directory for the recommended `runsc` configuration
used in AgentSecEval experiments.

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest
from fastapi.testclient import TestClient

import api.binary_runtime as runtime
import api.server as server


class FakeProcess:
    pid = 12345
    returncode = 0

    def __init__(self, output="결과\n", error="", returncode=0, expire=False):
        self.output, self.error, self.returncode = output, error, returncode
        self.expire = expire
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def communicate(self, input=None, timeout=None):
        self.calls.append((input, timeout))
        if self.expire and timeout is not None:
            raise subprocess.TimeoutExpired("binary", timeout, output="비공개 원출력")
        return self.output, self.error

    def kill(self):
        self.calls.append("kill")


@pytest.mark.parametrize("entry", ["default", "simplified", "debug", "models"])
def test_local_command_default_and_override_deadline(monkeypatch, entry):
    process = FakeProcess(output=json.dumps({"models": ["m"], "default_model": "m"}))
    commands = []
    def spawn(command, **kwargs):
        commands.append((command, kwargs))
        return process
    monkeypatch.setattr(runtime.subprocess, "Popen", spawn)
    monkeypatch.delenv("TTS_PREPROCESSOR_RULE_PROCESS_TIMEOUT_SECONDS", raising=False)
    def run():
        if entry == "models":
            return runtime.list_llm_models(binary_path=Path("fake"))
        if entry == "debug":
            return runtime.run_transform_binary_debug("원문", binary_path=Path("fake"))
        return runtime.run_transform_binary("원문", profile=entry, binary_path=Path("fake"))
    run()
    assert process.calls[-1] == ("" if entry == "models" else "원문", 30.0)
    monkeypatch.setenv("TTS_PREPROCESSOR_RULE_PROCESS_TIMEOUT_SECONDS", "12.5")
    run()
    assert process.calls[-1][1] == 12.5
    assert len(commands) == 2  # Exactly one process per call.
    assert all(kwargs == dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True,
                              start_new_session=(os.name == "posix"))
               for _, kwargs in commands)
    assert commands[0][0] == ["fake"] + (
        ["--include-debug"] if entry == "debug" else ["--list-models"] if entry == "models" else [])


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "", "invalid"])
def test_invalid_deadline_rejected_before_spawn(monkeypatch, value):
    monkeypatch.setenv("TTS_PREPROCESSOR_RULE_PROCESS_TIMEOUT_SECONDS", value)
    def unexpected(*args, **kwargs):
        pytest.fail("invalid configuration spawned a process")
    monkeypatch.setattr(runtime.subprocess, "Popen", unexpected)
    with pytest.raises(runtime.BinaryRuntimeError, match="TIMEOUT_SECONDS"):
        runtime.run_transform_binary("원문", binary_path=Path("fake"))


def test_timeout_kills_own_group_drains_once_and_never_returns_partial_output(monkeypatch):
    monkeypatch.delenv("TTS_PREPROCESSOR_RULE_PROCESS_TIMEOUT_SECONDS", raising=False)
    process = FakeProcess(expire=True)
    spawns, killed = [], []
    def spawn(*args, **kwargs):
        spawns.append(args)
        return process
    monkeypatch.setattr(runtime.subprocess, "Popen", spawn)
    if os.name == "posix":
        monkeypatch.setattr(runtime.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    with pytest.raises(runtime.BinaryRuntimeTimeoutError, match="30 seconds") as error:
        runtime.run_transform_binary("비공개 원문", binary_path=Path("fake"))
    assert len(spawns) == 1
    assert process.calls == ([("비공개 원문", 30.0)]
                             + ([] if os.name == "posix" else ["kill"])
                             + [(None, None)])
    if os.name == "posix":
        assert killed == [(process.pid, signal.SIGKILL)]
    assert "비공개" not in str(error.value)


@pytest.mark.parametrize(("output", "error", "code", "expected"), [
    ("", "", 0, "empty output"), ("", "실패", 2, "실패"),
    ("실패", "", 1, "실패"), ("", "", 1, "execution failed"),
])
def test_existing_failure_contracts(monkeypatch, output, error, code, expected):
    monkeypatch.setattr(runtime.subprocess, "Popen",
                        lambda *args, **kwargs: FakeProcess(output, error, code))
    with pytest.raises(runtime.BinaryRuntimeError, match=expected) as raised:
        runtime.run_transform_binary("원문", binary_path=Path("fake"))
    assert not isinstance(raised.value, runtime.BinaryRuntimeTimeoutError)


@pytest.mark.parametrize("debug", [False, True])
@pytest.mark.parametrize("level", [1, 2])
def test_api_timeout_returns_504_existing_detail_schema(monkeypatch, debug, level):
    def timeout(*args, **kwargs):
        raise runtime.BinaryRuntimeTimeoutError("Packaged runtime command timed out after 30 seconds.")
    monkeypatch.setattr(server, "run_transform_binary", timeout)
    monkeypatch.setattr(server, "run_transform_binary_debug", timeout)
    response = TestClient(server.app).post("/api/transform", json={
        "text": "비공개 원문", "level": level, "include_debug": debug})
    assert response.status_code == 504
    assert response.json() == {"detail": "Packaged runtime command timed out after 30 seconds."}


def test_models_command_timeout_returns_504(monkeypatch):
    def timeout():
        raise runtime.BinaryRuntimeTimeoutError("Packaged runtime command timed out after 30 seconds.")
    monkeypatch.setattr(server, "list_llm_models", timeout)
    assert TestClient(server.app).get("/api/llm/models").status_code == 504


@pytest.mark.skipif(os.name != "posix", reason="Linux/macOS process-group contract")
@pytest.mark.parametrize("parent_exits", [False, True])
def test_real_local_timeout_terminates_descendant_and_reaps_parent(monkeypatch, parent_exits):
    monkeypatch.setenv("TTS_PREPROCESSOR_RULE_PROCESS_TIMEOUT_SECONDS", "0.5")
    popen = subprocess.Popen
    processes = []
    def spawn(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(runtime.subprocess, "Popen", spawn)
    script = (
        "import subprocess,sys,time; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
        "print(child.pid,file=sys.stderr,flush=True); "
        + ("sys.exit(0)" if parent_exits else "time.sleep(60)")
    )
    started = time.monotonic()
    with pytest.raises(runtime.BinaryRuntimeTimeoutError) as raised:
        runtime._run_binary_command([sys.executable, "-c", script], text="")
    assert time.monotonic() - started < 5
    parent = processes[0]
    assert parent.returncode is not None
    with pytest.raises(ChildProcessError):
        os.waitpid(parent.pid, os.WNOHANG)
    descendant = int(raised.value.__cause__.stderr.strip())
    # Orphaned children are reaped by the OS, so a terminated zombie is allowed
    # while the system reaper catches up. It must never remain running.
    def terminated():
        try:
            os.kill(descendant, 0)
        except ProcessLookupError:
            return True
        if sys.platform.startswith("linux"):
            try:
                stat = Path(f"/proc/{descendant}/stat").read_text()
            except FileNotFoundError:
                return True
            return stat.rsplit(")", 1)[1].strip().startswith("Z")
        return False
    deadline = time.monotonic() + 2
    while not terminated() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert terminated()


def test_real_local_success_stdin_stdout_and_stderr(monkeypatch):
    monkeypatch.delenv("TTS_PREPROCESSOR_RULE_PROCESS_TIMEOUT_SECONDS", raising=False)
    script = "import sys; print(sys.stdin.read()+' 결과'); print('진단',file=sys.stderr)"
    assert runtime._run_binary_command([sys.executable, "-c", script], text="원문") == "원문 결과"

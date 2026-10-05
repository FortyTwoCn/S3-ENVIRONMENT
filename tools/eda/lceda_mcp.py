"""Local stdio MCP adapter for the installed JLCEDA Pro command-line client.

Uses Python's standard library only. The EDA executable remains unmodified.
Every tool runs the official CLI with an argument list, without a shell.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

VERSION = "1.0.0"
DEFAULT_EXE = r"D:\Program Files\lceda-pro\lceda-pro.exe"


def tool(name, description, properties=None, required=None, readonly=False):
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties or {},
            "required": required or [],
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": readonly,
            "openWorldHint": True,
        },
    }


SESSION = {"type": "string", "minLength": 1, "description": "Session ID returned by lceda_open or lceda_sessions."}
TOOLS = [
    tool("lceda_doctor", "Probe the installed JLCEDA Pro bridge. Check connected and versionMatch before operating.", readonly=True),
    tool("lceda_sessions", "List available editor sessions. The home window alone may yield an empty list.", readonly=True),
    tool("lceda_open", "Open a specified local project and return its session ID. Version 4.1.60 requires an existing project path. Reuse the returned session; close only sessions you created when finished.", {
        "path": {"type": "string", "minLength": 1, "description": "Absolute local .eprj/.eprj2/.eprj3/.elib project path; forward slashes preferred."},
        "headless": {"type": "boolean", "default": False},
    }, ["path"]),
    tool("lceda_close", "Close a CLI session. destroy=true also closes its editor window; use only for a session you created and no longer need.", {
        "session": SESSION,
        "destroy": {"type": "boolean", "default": False},
    }, ["session"]),
    tool("lceda_invoke", "Run JavaScript (an async function body) in a specified editor session through the official eda extension API. Always include a return statement for useful results. Uses --ext-uuid eda. Can read or modify the design: perform only the user's requested operations. Check the returned ok field; query API documentation before using unfamiliar methods. Read pin coordinates from the API, and verify design changes with netlists/DRC.", {
        "session": SESSION,
        "code": {"type": "string", "minLength": 1},
        "arguments": {"description": "Optional JSON data available as __CLI__.args."},
        "timeout_ms": {"type": "integer", "minimum": 1, "maximum": 60000, "default": 60000},
    }, ["session", "code"]),
    tool("lceda_doc", "Query the API reference bundled with this installed EDA version. With no class_name, list classes; add class_name and method_name for details. External docs require a session. Format docs accept a class_name but no method_name.", {
        "namespace": {"type": "string", "enum": ["api", "external", "format"], "default": "api"},
        "class_name": {"type": "string", "minLength": 1},
        "method_name": {"type": "string", "minLength": 1},
        "session": SESSION,
    }, readonly=True),
    tool("lceda_functions", "List extensions available to the specified editor session.", {"session": SESSION}, ["session"], readonly=True),
]
TOOL_INDEX = {item["name"]: item for item in TOOLS}


def validate(name, arguments):
    if name not in TOOL_INDEX:
        raise ValueError(f"Unknown tool: {name}")
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    schema = TOOL_INDEX[name]["inputSchema"]
    for key in schema["required"]:
        if key not in arguments:
            raise ValueError(f"Missing argument: {key}")
    for key, value in arguments.items():
        if key not in schema["properties"]:
            raise ValueError(f"Unknown argument: {key}")
        spec = schema["properties"][key]
        expected = spec.get("type")
        if expected == "string" and (not isinstance(value, str) or not value or "\x00" in value):
            raise ValueError(f"{key} must be a nonempty string without NUL characters")
        if expected == "boolean" and not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean")
        if expected == "integer" and (type(value) is not int or not spec["minimum"] <= value <= spec["maximum"]):
            raise ValueError(f"{key} must be an integer from {spec['minimum']} to {spec['maximum']}")
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError(f"Invalid value for {key}")


def command_for(name, a):
    if name == "lceda_doctor":
        return ["doctor"]
    if name == "lceda_sessions":
        return ["session", "list"]
    if name == "lceda_open":
        project = Path(a["path"])
        if not project.is_absolute() or not project.exists():
            raise ValueError("path must be an existing absolute project path")
        if project.suffix.lower() not in {".eprj", ".eprj2", ".eprj3", ".elib"}:
            raise ValueError("Unsupported project extension")
        return ["open", "--path", project.as_posix(), "--headless", str(a.get("headless", False)).lower()]
    if name == "lceda_close":
        return ["session", "close", "--session", a["session"], "--destroy", str(a.get("destroy", False)).lower()]
    if name == "lceda_invoke":
        cmd = ["invoke", "--session", a["session"], "--ext-uuid", "eda", "--timeout", str(a.get("timeout_ms", 60000)), "--code", a["code"]]
        if "arguments" in a:
            cmd.extend(["--args", json.dumps(a["arguments"], ensure_ascii=False, separators=(",", ":"))])
        return cmd
    if name == "lceda_functions":
        return ["functions", "--session", a["session"]]
    namespace = a.get("namespace", "api")
    if namespace == "external" and "session" not in a:
        raise ValueError("External documentation requires a session")
    if "method_name" in a and (namespace == "format" or "class_name" not in a):
        raise ValueError("method_name requires class_name and namespace api or external")
    cmd = ["doc", namespace]
    for key, flag in (("class_name", "--class-name"), ("method_name", "--method-name")):
        if key in a:
            cmd.extend([flag, a[key]])
    if namespace == "external":
        cmd.extend(["--session", a["session"]])
    return cmd


def run_cli(exe, name, arguments):
    validate(name, arguments)
    command = [exe, *command_for(name, arguments)]
    if len(subprocess.list2cmdline(command)) > 30000:
        raise ValueError("CLI argument list is too long for Windows. Split the operation into smaller batches.")
    env = os.environ.copy()
    env.pop("ELECTRON_RUN_AS_NODE", None)
    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=arguments.get("timeout_ms", 60000) / 1000 + 20,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        env=env,
    )
    lines = completed.stdout.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("{"):
            continue
        try:
            result = json.loads("\n".join(lines[index:]))
        except json.JSONDecodeError:
            continue
        if isinstance(result, dict) and isinstance(result.get("ok"), bool):
            if completed.returncode != 0 and result["ok"]:
                raise RuntimeError(f"CLI exited {completed.returncode} despite ok=true")
            return result
    detail = (completed.stderr.strip() or completed.stdout.strip() or "no output")[:2000]
    raise RuntimeError(f"CLI did not return a JSON envelope (exit={completed.returncode}): {detail}")


def dispatch(exe, method, params):
    if method == "initialize":
        requested = params.get("protocolVersion")
        supported = {"2024-11-05", "2025-03-26", "2025-06-18"}
        return {
            "protocolVersion": requested if requested in supported else "2025-06-18",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "lceda-pro-cli-adapter", "version": VERSION},
            "instructions": "This local compatibility adapter calls the official JLCEDA Pro 4.1.60 CLI. Start with lceda_doctor and lceda_sessions. Read bundled documentation before invoking eda APIs. Open only the project requested by the user. Close only your own temporary sessions.",
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        try:
            result = run_cli(exe, params.get("name"), params.get("arguments", {}))
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            result = {"ok": False, "error": {"code": "ADAPTER_ERROR", "message": str(error)}}
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "isError": not result["ok"]}
    raise LookupError(f"Unsupported method: {method}")


def emit(message):
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def serve(exe):
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            emit({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            continue
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
            emit({"jsonrpc": "2.0", "id": message.get("id") if isinstance(message, dict) else None, "error": {"code": -32600, "message": "Invalid request"}})
            continue
        if "id" not in message:
            continue
        req_id = message["id"]
        params = message.get("params", {})
        if not isinstance(params, dict):
            emit({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "params must be an object"}})
            continue
        try:
            result = dispatch(exe, message["method"], params)
            emit({"jsonrpc": "2.0", "id": req_id, "result": result})
        except LookupError as error:
            emit({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": str(error)}})
        except Exception as error:
            print(f"MCP error: {type(error).__name__}: {error}", file=sys.stderr)
            emit({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": "Internal error; see server stderr"}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", default=DEFAULT_EXE)
    options = parser.parse_args()
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    if not Path(options.exe).is_file():
        parser.error(f"EDA executable does not exist: {options.exe}")
    serve(options.exe)

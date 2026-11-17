# Connect QA Workbench to Codex

Use a local Codex client on the same computer as the workbench. Install the project's dependencies and run at least one dashboard check first.

## Register the MCP server

From the workbench folder on macOS or Linux, with a local Codex CLI on your PATH:

```sh
codex mcp add qa-workbench -- "$PWD/.venv/bin/python" "$PWD/mcp_server.py"
codex mcp list
```

In PowerShell, use:

```powershell
codex mcp add qa-workbench -- "$PWD\.venv\Scripts\python.exe" "$PWD\mcp_server.py"
codex mcp list
```

You can also add a local STDIO server in a local Codex client's MCP settings. Set the command to the absolute path of the virtual environment's Python executable and the argument to the absolute path of `mcp_server.py`. Restart or open a new local Codex chat if the server was just added. [Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

## Ask Codex to triage a run

With the workbench open, run **Local candidate** and paste into Codex:

> Use the QA Workbench MCP tools to find the latest Local candidate run. Inspect the discount-total failure. Draft a bug report with the environment, reproduction steps, expected amount, observed amount, and screenshot link. Mark any cause as a hypothesis.

MCP exposes `list_qa_runs` and `get_qa_run`. These tools read saved results. The dashboard starts runs, and its server must be running to open screenshot links. If no runs appear, confirm that Codex points to this copy of the project and that a run finished.

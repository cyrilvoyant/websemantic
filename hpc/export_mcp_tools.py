"""Export the tool list of a ToolRosella-generated MCP service, as an MCP client sees it (tools/list).

Dynamic mode: import mcp_service.create_app() and list the tools through an in-memory FastMCP client (names,
descriptions and input schemas as served). If the service cannot be imported (missing dependency of the wrapped
repository), static mode reads the @mcp.tool decorators and function signatures from mcp_service.py. The mode used is
recorded. Usage: python export_mcp_tools.py <workspace> <output_dir> <repo_name>...
"""

import ast
import asyncio
import importlib.util
import json
import sys
from pathlib import Path


def dynamic(plugin):
    from fastmcp import Client
    sys.path.insert(0, str(plugin))
    spec = importlib.util.spec_from_file_location(f"svc_{plugin.parent.parent.name}", plugin / "mcp_service.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    async def listing():
        async with Client(module.create_app()) as client:
            return await client.list_tools()

    return [{"name": t.name, "description": t.description or "", "inputSchema": t.inputSchema}
            for t in asyncio.run(listing())]


def static(plugin):
    tree = ast.parse((plugin / "mcp_service.py").read_text(encoding="utf-8"))
    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and ast.unparse(dec.func).endswith("tool"):
                kw = {k.arg: ast.literal_eval(k.value) for k in dec.keywords if isinstance(k.value, ast.Constant)}
                params = {a.arg: {"annotation": ast.unparse(a.annotation) if a.annotation else None}
                          for a in node.args.args}
                tools.append({"name": kw.get("name", node.name), "description": kw.get("description", ""),
                              "parameters": params})
    return tools


def main(workspace, out_dir, repos):
    out_dir.mkdir(parents=True, exist_ok=True)
    for repo in repos:
        plugin = workspace / repo / "mcp_output" / "mcp_plugin"
        record = {"repository": repo, "generator": "ToolRosella", "plugin_found": plugin.exists()}
        if plugin.exists():
            try:
                record.update(mode="dynamic", tools=dynamic(plugin))
            except Exception as exc:  # noqa: BLE001 - generated code of any repository may raise anything on import
                record.update(mode="static", import_error=f"{type(exc).__name__}: {exc}"[:300], tools=static(plugin))
        (out_dir / f"{repo}.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(repo, record.get("mode"), len(record.get("tools", [])), "tools")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:])

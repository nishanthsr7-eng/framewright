import logging
import sys

from mcp.server.fastmcp.exceptions import ToolError


def setup_logging(level=logging.INFO):
    """Log to stderr; stdout is the MCP protocol channel."""
    logging.basicConfig(stream=sys.stderr, level=level)


def run_tool(fn, *args, **kwargs) -> dict:
    """Call tool logic, mapping errors to ToolError with a fix hint."""
    try:
        return fn(*args, **kwargs)
    except FileNotFoundError as e:
        raise ToolError(f"{e}. Check the path exists.")
    except (ValueError, RuntimeError) as e:
        raise ToolError(str(e))
    except Exception as e:
        logging.exception("Tool failed")
        raise ToolError(f"{type(e).__name__}: {e}")

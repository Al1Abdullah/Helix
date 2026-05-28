"""Structured JSON logger — all output to stderr, never pollutes MCP stdout."""
import json
import logging
import sys
from datetime import datetime, timezone

_SKIP = {
    "args","asctime","created","exc_info","exc_text","filename","funcName",
    "id","levelname","levelno","lineno","module","msecs","message","msg",
    "name","pathname","process","processName","relativeCreated","stack_info",
    "thread","threadName","taskName",
}


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k not in _SKIP:
                payload[k] = v
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(_JSONFormatter())
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger

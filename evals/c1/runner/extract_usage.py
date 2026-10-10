"""从 opencode.db 提取实验会话的累计 completion_tokens（T 的封存数据源）。

用法：py -3 extract_usage.py <session_id 或 'all-recent'>
输出 JSON：{session_id, start, end, assistant_msgs, output_sum, input_sum, first_msg_time, last_msg_time}
按实验会话的 session_id 聚合 assistant 消息的 tokens.output。
"""

import json
import sqlite3
import sys
from pathlib import Path

DB = Path.home() / ".local/share/opencode/opencode.db"


def extract(session_id: str):
    db = sqlite3.connect(str(DB))
    rows = db.execute(
        "SELECT id, time_created, data FROM message WHERE session_id = ? ORDER BY time_created",
        (session_id,)).fetchall()
    out = {
        "session_id": session_id,
        "assistant_msgs": 0,
        "output_sum": 0,
        "input_sum": 0,
        "reasoning_sum": 0,
        "first_msg_time": None,
        "last_msg_time": None,
        "per_msg_output": [],
    }
    for mid, ts, data in rows:
        j = json.loads(data)
        out["first_msg_time"] = out["first_msg_time"] or ts
        out["last_msg_time"] = ts
        if j.get("role") != "assistant":
            continue
        t = j.get("tokens") or {}
        o = t.get("output", 0)
        if o:
            out["assistant_msgs"] += 1
            out["output_sum"] += o
            out["input_sum"] += t.get("input", 0)
            out["reasoning_sum"] += t.get("reasoning", 0)
            out["per_msg_output"].append({"msg": mid, "time": ts, "output": o})
    return out


def recent_sessions(limit=10):
    db = sqlite3.connect(str(DB))
    rows = db.execute(
        "SELECT s.id, s.title, s.directory FROM session s ORDER BY s.rowid DESC LIMIT ?",
        (limit,)).fetchall()
    return [{"id": r[0], "title": r[1], "directory": r[2]} for r in rows]


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "list"
    if arg == "list":
        print(json.dumps(recent_sessions(), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(extract(arg), ensure_ascii=False, indent=1))

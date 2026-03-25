from __future__ import annotations

import re

from s2t_tool.shared.text import normalize_newlines


KEYWORDS = {
    "SELECT", "FROM", "WHERE", "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "AND", "OR",
    "LEFT", "RIGHT", "FULL", "OUTER", "INNER", "CROSS", "JOIN", "ON", "UNION", "ALL",
    "CASE", "WHEN", "THEN", "ELSE", "END", "AS", "WITH", "DISTINCT", "IN", "IS", "NOT",
    "NULL", "LIKE", "EXISTS", "BETWEEN", "OVER", "PARTITION", "DISTRIBUTE", "SORT",
    "CLUSTER", "LATERAL", "VIEW", "INSERT", "INTO", "CREATE", "TABLE", "DROP", "ALTER",
}

CLAUSE_KEYWORDS = {
    "WITH", "SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING", "LIMIT",
    "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "INNER JOIN", "CROSS JOIN",
    "LEFT OUTER JOIN", "RIGHT OUTER JOIN", "FULL OUTER JOIN",
    "JOIN", "ON", "UNION", "UNION ALL", "WHEN", "ELSE", "AND", "OR",
    "DISTRIBUTE BY", "SORT BY", "CLUSTER BY", "LATERAL VIEW",
}

MULTIWORD_KEYWORDS = [
    ("GROUP", "BY"),
    ("ORDER", "BY"),
    ("UNION", "ALL"),
    ("LEFT", "JOIN"),
    ("RIGHT", "JOIN"),
    ("FULL", "JOIN"),
    ("INNER", "JOIN"),
    ("CROSS", "JOIN"),
    ("LEFT", "OUTER", "JOIN"),
    ("RIGHT", "OUTER", "JOIN"),
    ("FULL", "OUTER", "JOIN"),
    ("DISTRIBUTE", "BY"),
    ("SORT", "BY"),
    ("CLUSTER", "BY"),
    ("LATERAL", "VIEW"),
]

TOKEN_RE = re.compile(
    r"/\*.*?\*/|--[^\n]*|'(?:''|[^'])*'|`[^`]*`|[A-Za-z_][A-Za-z0-9_$]*|[(),.]|<=|>=|<>|!=|==|[-+*/%<>=]|[^\s]",
    flags=re.DOTALL,
)


def format_hive_sql(sql: str) -> str:
    text = normalize_newlines(sql).strip()
    if not text:
        return ""

    tokens = _merge_keywords(TOKEN_RE.findall(text))
    if not tokens:
        return text

    lines: list[str] = []
    current_parts: list[str] = []
    indent = 0
    paren_depth = 0
    clause = ""
    line_indent = 0

    def flush_line(force: bool = False) -> None:
        nonlocal current_parts, line_indent
        line = "".join(current_parts).strip()
        if line or force:
            extra_indent = 0
            if clause == "SELECT" and line != "SELECT":
                extra_indent += 1
            if line.startswith(("ON ", "AND ", "OR ")):
                extra_indent += 1
            lines.append(("    " * max(line_indent + extra_indent, 0)) + line if line else "")
        current_parts = []
        line_indent = indent

    def add(token: str) -> None:
        nonlocal line_indent
        if not current_parts:
            line_indent = indent
        if token == ",":
            if current_parts:
                current_parts[-1] = current_parts[-1].rstrip()
            current_parts.append(", ")
            return
        if token == ".":
            if current_parts:
                current_parts[-1] = current_parts[-1].rstrip()
            current_parts.append(".")
            return
        if token == "(":
            if current_parts and not current_parts[-1].endswith((" ", "(", ".")):
                current_parts.append(" ")
            current_parts.append("(")
            return
        if token == ")":
            if current_parts:
                current_parts[-1] = current_parts[-1].rstrip()
            current_parts.append(")")
            return
        if current_parts and not current_parts[-1].endswith((" ", "(", ".")):
            current_parts.append(" ")
        current_parts.append(token)

    for token in tokens:
        upper = token.upper()
        token_out = upper if upper in KEYWORDS or upper in CLAUSE_KEYWORDS else token

        if upper == "CASE":
            add(token_out)
            indent += 1
            clause = ""
            continue

        if upper == "END":
            flush_line()
            indent -= 1
            add(token_out)
            clause = ""
            continue

        if upper in {"AND", "OR"} and clause not in {"WHERE", "HAVING", "ON"}:
            add(token_out)
            continue

        if upper in CLAUSE_KEYWORDS:
            flush_line()
            add(token_out)
            clause = upper
            if upper in {"WITH", "SELECT"}:
                flush_line()
            continue

        if upper == "," and clause in {"SELECT", "GROUP BY", "ORDER BY", "DISTRIBUTE BY", "SORT BY", "CLUSTER BY"} and paren_depth == 0:
            add(token_out)
            flush_line()
            continue

        add(token_out)

        if token == "(":
            paren_depth += 1
            indent += 1
        elif token == ")":
            paren_depth = max(paren_depth - 1, 0)
            indent = max(indent - 1, 0)

    flush_line()
    return "\n".join(line.rstrip() for line in lines if line is not None)


def maybe_format_hive_sql(sql: str, enabled: bool) -> str:
    if not enabled:
        return sql
    try:
        return format_hive_sql(sql)
    except Exception:
        return sql


def _merge_keywords(tokens: list[str]) -> list[str]:
    merged: list[str] = []
    idx = 0
    upper_tokens = [token.upper() for token in tokens]

    while idx < len(tokens):
        matched = False
        for phrase in MULTIWORD_KEYWORDS:
            if upper_tokens[idx:idx + len(phrase)] == list(phrase):
                merged.append(" ".join(phrase))
                idx += len(phrase)
                matched = True
                break
        if matched:
            continue
        merged.append(tokens[idx])
        idx += 1

    return merged

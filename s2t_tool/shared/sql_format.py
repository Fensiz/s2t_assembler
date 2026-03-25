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
    "PARTITION BY", "DISTRIBUTE BY", "SORT BY", "CLUSTER BY", "LATERAL VIEW",
}

MULTIWORD_KEYWORDS = [
    ("GROUP", "BY"),
    ("ORDER", "BY"),
    ("PARTITION", "BY"),
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
    r"/\*.*?\*/|--[^\n]*|'(?:''|[^'])*'|`[^`]*`|\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_$]*|[(),.:;]|<=|>=|<>|!=|==|[-+*/%<>=]|[^\s]",
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
    paren_types: list[tuple[str, int]] = []
    clause = ""
    line_indent = 0
    select_clause_depth = 0
    last_token_upper = ""
    next_token_upper = ""

    def flush_line(force: bool = False) -> None:
        nonlocal current_parts, line_indent
        line = "".join(current_parts).strip()
        if line or force:
            lines.append(("    " * max(render_indent(line), 0)) + line if line else "")
        current_parts = []
        line_indent = indent

    def render_indent(line: str) -> int:
        extra_indent = 0
        if clause == "SELECT" and line != "SELECT":
            extra_indent += 1
        if line.startswith(("ON ", "AND ", "OR ")):
            extra_indent += 1
        if paren_types and paren_types[-1][0] == "window" and line.startswith(("PARTITION BY ", "ORDER BY ")):
            extra_indent += 1
        return line_indent + extra_indent

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
        if token == ":":
            if current_parts:
                current_parts[-1] = current_parts[-1].rstrip()
            current_parts.append(":")
            return
        if token == ";":
            if current_parts:
                current_parts[-1] = current_parts[-1].rstrip()
            current_parts.append(";")
            return
        if token == "(":
            paren_type = classify_paren()
            if current_parts and not current_parts[-1].endswith((" ", "(", ".")) and paren_type != "function":
                current_parts.append(" ")
            current_parts.append("(")
            paren_indent = (
                line_indent
                if paren_type == "subquery"
                else render_indent("".join(current_parts).strip())
            )
            paren_types.append((paren_type, paren_indent))
            return
        if token == ")":
            if current_parts:
                current_parts[-1] = current_parts[-1].rstrip()
            current_parts.append(")")
            return
        if current_parts and not current_parts[-1].endswith((" ", "(", ".", ":")):
            current_parts.append(" ")
        current_parts.append(token)

    def classify_paren() -> str:
        if next_token_upper in {"SELECT", "WITH"}:
            if last_token_upper == "IN":
                return "subquery_expr"
            return "subquery"
        if last_token_upper == "OVER":
            return "window"
        if last_token_upper == "IN":
            return "list"
        if clause == "WITH" and paren_depth == 0:
            return "subquery"
        if last_token_upper and re.fullmatch(r"[A-Z_][A-Z0-9_$]*", last_token_upper) and last_token_upper not in KEYWORDS and last_token_upper not in CLAUSE_KEYWORDS:
            return "function"
        return "generic"

    for idx, token in enumerate(tokens):
        upper = token.upper()
        token_out = upper if upper in KEYWORDS or upper in CLAUSE_KEYWORDS else token
        next_token_upper = tokens[idx + 1].upper() if idx + 1 < len(tokens) else ""

        if upper == "CASE":
            add(token_out)
            indent += 1
            clause = ""
            last_token_upper = upper
            continue

        if upper == "END":
            flush_line()
            indent -= 1
            add(token_out)
            clause = ""
            last_token_upper = upper
            continue

        if upper in {"AND", "OR"} and clause not in {"WHERE", "HAVING", "ON"}:
            add(token_out)
            last_token_upper = upper
            continue

        if upper in CLAUSE_KEYWORDS:
            flush_line()
            add(token_out)
            clause = upper
            if upper == "SELECT":
                select_clause_depth = paren_depth
            if upper in {"WITH", "SELECT"}:
                flush_line()
            last_token_upper = upper
            continue

        if token.startswith("--") or token.startswith("/*"):
            if token.startswith("--") and not current_parts and lines and lines[-1].rstrip().endswith(","):
                lines[-1] = f"{lines[-1]} {token_out}"
                last_token_upper = upper
                continue
            add(token_out)
            flush_line()
            last_token_upper = upper
            continue

        if token == ";":
            add(token_out)
            flush_line()
            clause = ""
            last_token_upper = ""
            continue

        if upper == "," and clause == "SELECT" and paren_depth == select_clause_depth and not current_parts and lines:
            previous = lines[-1]
            comment_pos = previous.find("--")
            if comment_pos >= 0:
                head = previous[:comment_pos].rstrip()
                tail = previous[comment_pos:].lstrip()
                lines[-1] = f"{head}, {tail}"
            else:
                lines[-1] = previous.rstrip() + ","
            last_token_upper = upper
            continue

        if upper == "," and clause == "SELECT" and paren_depth == select_clause_depth:
            add(token_out)
            flush_line()
            last_token_upper = upper
            continue

        if upper == "," and clause == "WITH" and paren_depth == 0:
            add(token_out)
            flush_line()
            last_token_upper = upper
            continue

        if upper == "," and clause in {"GROUP BY", "ORDER BY", "DISTRIBUTE BY", "SORT BY", "CLUSTER BY"} and paren_depth == 0:
            add(token_out)
            flush_line()
            last_token_upper = upper
            continue

        if token == ")" and paren_types and paren_types[-1][0] in {"subquery", "subquery_expr", "window"} and current_parts:
            flush_line()
            line_indent = paren_types[-1][1]
            current_parts.append(")")
        else:
            add(token_out)

        if token == "(":
            paren_depth += 1
            indent += 1
        elif token == ")":
            closed_paren_type = paren_types[-1][0] if paren_types else ""
            paren_depth = max(paren_depth - 1, 0)
            indent = max(indent - 1, 0)
            if paren_types:
                paren_types.pop()
            if closed_paren_type in {"subquery", "subquery_expr"} and paren_depth == 0:
                clause = "WITH"

        last_token_upper = upper

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

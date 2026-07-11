"""Tiny Lua lexer helper for static checks: drops comments and blanks out string literals."""

import re

_LONG_OPEN = re.compile(r"\[(=*)\[")


def code_only(src: str) -> str:
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith("--", i):
            m = _LONG_OPEN.match(src, i + 2)
            if m:
                close = src.find("]" + m.group(1) + "]", m.end())
                i = n if close < 0 else close + len(m.group(1)) + 2
            else:
                nl = src.find("\n", i)
                i = n if nl < 0 else nl
            out.append(" ")
            continue
        m = _LONG_OPEN.match(src, i)
        if m:
            close = src.find("]" + m.group(1) + "]", m.end())
            i = n if close < 0 else close + len(m.group(1)) + 2
            out.append('""')
            continue
        ch = src[i]
        if ch in "\"'":
            j = i + 1
            while j < n and src[j] != ch:
                j += 2 if src[j] == "\\" else 1
            i = j + 1
            out.append('""')
            continue
        out.append(ch)
        i += 1
    return "".join(out)

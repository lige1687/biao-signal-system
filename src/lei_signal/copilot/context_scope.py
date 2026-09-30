"""Conservative subject and factuality scope for discussion background, not trade authority."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Clause:
    start: int
    end: int
    text: str
    subject: str
    factual: bool


_SPLIT = re.compile(r"[，。；;!！?？\n：:]+|(?<!\d)[,.](?!\d)|(?=(?:但是|但|然后|不过)我)")
_OTHER = re.compile(r"朋友|同事|家人|亲戚|同学|别人|人家|我妈|我爸|客户|领导|他|她|他们|她们")
_SELF = re.compile(r"本人|我(?!们|妈|爸|朋友|同事|家人)")
_HYP = re.compile(r"如果|假如|假设|要是|倘若|比如|举例")
_REAL = re.compile(r"实际上|事实上|现实中|实际情况|我现在")
_NONFACT = re.compile(
    r"吗|么|会不会|要不要|是不是|考虑|打算|想要|想持|准备|计划|可能|是否|假如|假设|如果"
)
_FUTURE = re.compile(r"以后|将来|下个月|下周|明天|将会|会有|打算|准备|计划")


def clauses(text: str) -> list[Clause]:
    """Subject/hypothesis survive punctuation. Explicit self never cancels a hypothesis."""
    result = []
    subject = "unknown"
    hypothetical = False
    start = 0
    spans = []
    for m in _SPLIT.finditer(text):
        spans.append((start, m.start(), text[start : m.start()], m.group()))
        start = m.end()
    spans.append((start, len(text), text[start:], ""))
    for a, b, part, separator in spans:
        if not part.strip():
            continue
        own = bool(_SELF.search(part))
        other = bool(_OTHER.search(part))
        if own or other:
            subject = "unknown" if own and other else ("self" if own else "other")
        if _REAL.search(part):
            hypothetical = False
        if _HYP.search(part) or _FUTURE.search(part):
            hypothetical = True
        quoted = bool(re.search('[“”「」"‘’]', part))
        factual = not hypothetical and not _NONFACT.search(part) and not quoted
        # A question about a fact must not establish it. A declared amount followed
        # by a separate question keeps its own preceding factual clause.
        if separator in ("?", "？"):
            factual = False
        if quoted:
            subject = "unknown"
        result.append(Clause(a, b, part, subject, bool(factual)))
    return result

import re
import unicodedata
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass(frozen=True)
class KnowledgeSection:
    source: str
    domain: str
    title: str
    content: str


class LocalKnowledgeBase:
    _STOPWORDS = {
        "a", "an", "and", "are", "can", "could", "do", "does", "for",
        "from", "how", "i", "in", "is", "it", "me", "of", "on", "or",
        "the", "this", "to", "what", "when", "where", "which", "why",
        "with", "would", "you", "your",
        "ban", "cach", "cho", "co", "cua", "gi", "khong", "la", "lam",
        "mot", "nao", "nhu", "the", "toi", "trong", "va", "voi",
    }

    def __init__(self, root: Path):
        self.root = Path(root)
        self.sections = self._load_sections()

    @staticmethod
    def _fold(text: str) -> str:
        folded = unicodedata.normalize("NFD", text or "")
        folded = "".join(
            char for char in folded if unicodedata.category(char) != "Mn"
        )
        folded = folded.replace("đ", "d").replace("Đ", "D")
        return re.sub(r"\s+", " ", folded.lower()).strip()

    @classmethod
    def _tokens(cls, text: str):
        return {
            token
            for token in re.findall(r"[a-z0-9]+", cls._fold(text))
            if len(token) > 1 and token not in cls._STOPWORDS
        }

    def _load_sections(self) -> List[KnowledgeSection]:
        if not self.root.is_dir():
            return []

        sections = []
        for path in sorted(self.root.rglob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                warnings.warn(
                    "Skipping unreadable knowledge file {0}: {1}".format(path, exc),
                    RuntimeWarning,
                )
                continue

            source = path.relative_to(self.root).as_posix()
            sections.extend(self._split_markdown(source, text))
        return sections

    @staticmethod
    def _split_markdown(source: str, text: str) -> List[KnowledgeSection]:
        sections = []
        domain = source.split("/", 1)[0] if "/" in source else "general"
        title = Path(source).stem.replace("-", " ").strip()
        content_lines = []

        def flush():
            content = "\n".join(content_lines).strip()
            if content:
                sections.append(
                    KnowledgeSection(
                        source=source,
                        domain=domain,
                        title=title,
                        content=content,
                    )
                )

        for line in text.splitlines():
            heading = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
            if heading:
                flush()
                title = heading.group(1).strip()
                content_lines = []
            else:
                content_lines.append(line)
        flush()
        return sections

    def _score(self, query: str, section: KnowledgeSection) -> int:
        query_folded = self._fold(query)
        query_tokens = self._tokens(query)
        if not query_tokens:
            return 0

        title_folded = self._fold(section.title)
        content_folded = self._fold(section.content)
        title_tokens = self._tokens(section.title)
        content_tokens = self._tokens(section.content)

        title_hits = len(query_tokens & title_tokens)
        content_hits = len(query_tokens & content_tokens)
        score = (title_hits * 5) + content_hits

        if query_folded and query_folded in "{0} {1}".format(
            title_folded, content_folded
        ):
            score += 10
        return score

    def search(
        self,
        query: str,
        limit: int = 3,
        max_chars: int = 4000,
        domain: str = None,
    ) -> str:
        if not query or limit <= 0 or max_chars <= 0:
            return ""

        ranked: List[Tuple[int, int, KnowledgeSection]] = []
        for index, section in enumerate(self.sections):
            if domain is not None and section.domain != domain:
                continue
            score = self._score(query, section)
            if score > 0:
                ranked.append((score, -index, section))
        ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))

        blocks = []
        current_length = 0
        for _, _, section in ranked[:limit]:
            header = "[Source: {0} > {1}]\n".format(
                section.source, section.title
            )
            separator_length = 2 if blocks else 0
            remaining = max_chars - current_length - separator_length
            if remaining <= len(header):
                break

            content = section.content[: remaining - len(header)].rstrip()
            if not content:
                break
            block = header + content
            blocks.append(block)
            current_length += separator_length + len(block)

            if current_length >= max_chars:
                break

        return "\n\n".join(blocks)

"""Lightweight CSV chunking + token overlap search (hackathon-friendly, no vector DB)."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)


def _tokens(text: str) -> Set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def _default_dataset_root() -> Path:
    # back-end/backend/knowledge/retrieval.py -> Hackathon_thalashery
    here = Path(__file__).resolve()
    backend_dir = here.parents[1]
    repo_root = backend_dir.parent.parent
    return repo_root / "AI Model" / "civicsafe-ai" / "dataset"


class KnowledgeIndex:
    def __init__(self, root: Optional[Path] = None, max_chunks: int = 4000) -> None:
        self.root = Path(root) if root else _default_dataset_root()
        self.max_chunks = max_chunks
        self._chunks: List[Dict[str, Any]] = []
        self._index: Dict[str, Set[int]] = defaultdict(set)
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        chunk_id = 0
        if not self.root.is_dir():
            self._loaded = True
            return
        for path in sorted(self.root.rglob("*.csv")):
            if chunk_id >= self.max_chunks:
                break
            theme = path.parent.name or "dataset"
            try:
                with path.open(encoding="utf-8", errors="replace", newline="") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    for row in reader:
                        if chunk_id >= self.max_chunks:
                            break
                        cells = [c.strip() for c in row if c and str(c).strip()]
                        if len(cells) < 2:
                            continue
                        text = " | ".join(cells[:12])
                        if len(text) < 20:
                            continue
                        rec = {
                            "id": chunk_id,
                            "text": text[:1200],
                            "source": str(path.relative_to(self.root)) if self.root in path.parents else path.name,
                            "theme": theme,
                        }
                        self._chunks.append(rec)
                        for tok in _tokens(text):
                            if len(tok) > 2:
                                self._index[tok].add(chunk_id)
                        chunk_id += 1
            except OSError:
                continue
        self._loaded = True

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        self.load()
        if not query.strip() or not self._chunks:
            return []
        q_tokens = _tokens(query)
        scores: Dict[int, float] = defaultdict(float)
        for tok in q_tokens:
            if tok in self._index:
                for cid in self._index[tok]:
                    scores[cid] += 1.0
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        out = []
        for cid, score in ranked:
            ch = self._chunks[cid]
            out.append(
                {
                    "snippet": ch["text"][:400] + ("…" if len(ch["text"]) > 400 else ""),
                    "source": ch["source"],
                    "theme": ch["theme"],
                    "score": round(score, 2),
                }
            )
        return out


_INDEX: Optional[KnowledgeIndex] = None


def get_index() -> KnowledgeIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = KnowledgeIndex()
    return _INDEX

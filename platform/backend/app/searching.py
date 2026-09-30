"""Optional Rust search helper with a dependency-free Python fallback."""
try:
    import beeha_search as _rust_search
except ImportError:
    _rust_search = None

def normalize_search_text(value: str) -> str:
    if _rust_search is not None:
        return _rust_search.normalize(value)
    return " ".join(value.casefold().split())

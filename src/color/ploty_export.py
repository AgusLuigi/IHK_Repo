from pathlib import Path

import plotly.graph_objects as go

PLOTLY_REPORT_DIR = Path("reports") / "plotly"


def _resolve_path(path: str | Path, suffix: str) -> Path:
    path = Path(path)
    if not path.suffix:
        path = path.with_suffix(suffix)
    if path.is_absolute():
        return path
    return PLOTLY_REPORT_DIR / path


def _should_write(path: Path, overwrite: bool) -> bool:
    return not (path.exists() and not overwrite)


def save_html(
    fig: go.Figure,
    name: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    path = _resolve_path(name, ".html")

    if not _should_write(path, overwrite):
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(path, include_plotlyjs="cdn")


def save_png(
    fig: go.Figure,
    name: str | Path,
    *,
    scale: int = 2,
    overwrite: bool = False,
) -> None:
    path = _resolve_path(name, ".png")

    if not _should_write(path, overwrite):
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(path, scale=scale)


def save_all(
    fig: go.Figure,
    name: str | Path,
    scale: float = 1.0,
    overwrite: bool = False,
) -> None:
    save_html(fig, name, overwrite=overwrite)
    # CHIRURGISCHER FIX: Deaktiviert, falls Kaleido-Engine nicht installiert ist
    try:
        save_png(fig, name, scale=scale, overwrite=overwrite)
    except ValueError as e:
        print("⚠️ PNG-Export übersprungen: Kaleido ist nicht installiert. HTML wurde gespeichert.")

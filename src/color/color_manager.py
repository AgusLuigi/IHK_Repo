import os
from types import SimpleNamespace
from typing import Any

import plotly.graph_objects as go
import yaml


class ColorManager:
    """
    Manages dynamic loading of global colors with intelligent automation.
    Supports 2-way access:
    1. Flat (Shortcut): color.main or color.forecast
    2. Structured: color.theme_dark.background.main
    """

    _colors: SimpleNamespace | None = None
    _raw_dict: dict[str, Any] | None = None

    @classmethod
    def _dict_to_namespace(cls, data: Any) -> Any:
        """Recursively converts a dictionary into a SimpleNamespace."""
        if isinstance(data, dict):
            return SimpleNamespace(
                **{k: cls._dict_to_namespace(v) for k, v in data.items()}
            )
        return data

    @classmethod
    def _flatten_dict(
        cls, data: Any, result: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Extracts all colors onto a flat level for ultra-fast access."""
        if result is None:
            result = {}
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    cls._flatten_dict(v, result)
                else:
                    result[k] = v
        return result

    @classmethod
    def get_colors(cls, file_path: str | None = None) -> SimpleNamespace:
        """
        Loads COLORS.yaml and creates automatic UI mappings.
        Improved path logic prevents FileNotFoundError in notebooks.
        """
        if cls._colors is None:
            # ROBUST PATH SEARCH: Checks root first, then one level up
            if file_path is None:
                potential_paths = [
                    os.path.join("config", "COLORS.yaml"),
                    os.path.join("..", "config", "COLORS.yaml"),
                ]
                for p in potential_paths:
                    if os.path.exists(p):
                        file_path = p
                        break

            if file_path is None or not os.path.exists(file_path):
                raise FileNotFoundError(
                    f"COLORS.yaml could not be found. Checked paths: {['config/COLORS.yaml', '../config/COLORS.yaml']}"
                )

            try:
                with open(file_path, encoding="utf-8") as f:
                    cls._raw_dict = yaml.safe_load(f)

                # Path 1: Flat Shortcuts
                flat_data = cls._flatten_dict(cls._raw_dict)

                # AUTOMATION: Intelligent mapping for theme colors
                theme = cls._raw_dict.get("theme_dark", {})
                bg = theme.get("background", {})
                txt = theme.get("text", {})
                ui = theme.get("ui", {})

                auto_mapping = {
                    "ui_paper": bg.get("main") or bg.get("main_bg") or "#0B0E14",
                    "ui_plot": bg.get("surface") or bg.get("plot_bg") or "#161B22",
                    "ui_grid": bg.get("grid") or "#1F242C",
                    "ui_text": txt.get("primary")
                    or txt.get("text_primary")
                    or "#E6EDF3",
                    "ui_border": ui.get("border") or "#30363D",
                }

                # Path 2: Structured Data
                structured_ns = cls._dict_to_namespace(cls._raw_dict)

                # Merge everything together
                cls._colors = SimpleNamespace(
                    **{**flat_data, **auto_mapping, **vars(structured_ns)}
                )

            except Exception as e:
                print(f"Error during loading: {e}")
                raise
        return cls._colors

    @classmethod
    def get_raw_dict(cls):
        if cls._raw_dict is None:
            cls.get_colors()
        return cls._raw_dict


def apply_modern_theme(fig: go.Figure) -> None:
    """
    Applies the design automatically. Uses intelligent 'ui_' mappings
    so the code doesn't break if names in the YAML are changed.
    """
    c = ColorManager.get_colors()

    fig.update_layout(
        paper_bgcolor=c.ui_paper,
        plot_bgcolor=c.ui_plot,
        font_color=c.ui_text,
        xaxis={"gridcolor": c.ui_grid, "linecolor": c.ui_border, "zeroline": False},
        yaxis={"gridcolor": c.ui_grid, "linecolor": c.ui_border, "zeroline": False},
        template="plotly_dark",
    )


# INSTRUCTIONS: HOW TO USE THE DESIGN SYSTEM (2 VARIANTS)
#
# 1. THE FAST WAY (Flat / Shortcut):
#    Ideal for daily coding. All colors are directly accessible.
#    -> color.forecast, color.main, color.observed, color.top20
#
# 2. THE STRUCTURED WAY (Path):
#    Ideal for organization and audit plots. Follows the YAML hierarchy.
#    -> color.theme_dark.background.main
#    -> color.analysis.lines.observed
#
# 3. THE AUTOMATIC THEME:
#    Simply call 'apply_modern_theme(fig)'. It automatically pulls the
#    correct background and axis colors from the YAML.

if __name__ == "__main__":
    # Example usage
    color = ColorManager.get_colors()
    fig = go.Figure()

    # Example for Shortcut usage
    top_colors = getattr(
        color, "top20", ["#636EFA", "#EF553B", "#00CC96"]
    )  # Fallback if top20 not in YAML
    for i, col in enumerate(top_colors[:5]):
        fig.add_trace(
            go.Scatter(
                x=[1, 2], y=[i, i + 1], line={"color": col}, name=f"Color {i + 1}"
            )
        )

    apply_modern_theme(fig)
    print("System Check: Colors loaded successfully and theme applied automatically.")
    fig.show()

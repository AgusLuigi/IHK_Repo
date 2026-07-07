import plotly.io as pio

from Favorita_TSA.viz.color_manager import ColorManager


def set_plotly_theme() -> None:
    """
    Registers the global Favorita dark theme with all Plotly color presets.
    Covers discrete colors, heatmaps, and UI elements globally.
    Ensures brand consistency without needing manual updates in notebooks.
    """
    # Load colors from COLORS.yaml
    c = ColorManager.get_colors()

    # Trial brand scale: black_rich (0.0) -> blue_bright (0.5) -> gold_brand (1.0)
    brand_scale = [[0.0, c.black_rich], [0.5, c.blue_bright], [1.0, c.gold_brand]]

    pio.templates["favorita_dark"] = {
        "layout": {
            # 1. GLOBAL BACKGROUNDS & TYPOGRAPHY
            "paper_bgcolor": c.ui_paper,
            "plot_bgcolor": c.ui_plot,
            "font": {"color": c.ui_text, "family": "Inter, sans-serif"},
            "title": {"font": {"color": c.ui_text}, "x": 0.05},
            # 2. DISCRETE COLORS (Bars, Lines, Pie Charts)
            "colorway": c.top20,
            # 3. CONTINUOUS COLORS (Heatmaps & Gradients)
            "coloraxis": {
                "colorscale": brand_scale,
                "autocolorscale": False,
                "colorbar": {
                    "tickfont": {"color": c.ui_text},
                    "title": {"font": {"color": c.ui_text}},
                },
            },
            # 'colorscale' ensures PX functions find the scale for simple plots
            "colorscale": {
                "sequential": brand_scale,
                "sequentialminus": brand_scale,
                "diverging": brand_scale,
            },
            # 4. AXES & GRID SYSTEM
            "xaxis": {
                "gridcolor": c.ui_grid,
                "linecolor": c.ui_border,
                "tickfont": {"color": c.ui_text},
                "title": {"font": {"color": c.ui_text}},
                "zeroline": False,
                "automargin": True,
            },
            "yaxis": {
                "gridcolor": c.ui_grid,
                "linecolor": c.ui_border,
                "tickfont": {"color": c.ui_text},
                "title": {"font": {"color": c.ui_text}},
                "zeroline": False,
                "automargin": True,
            },
            # 5. INTERACTIVE UI ELEMENTS
            "legend": {
                "bgcolor": "rgba(0,0,0,0)",
                "bordercolor": c.ui_border,
                "font": {"color": c.ui_text},
            },
            "hoverlabel": {
                "bgcolor": None,
                "bordercolor": None,
                "font": {
                    # "color": c.ui_text,
                    "size": 12
                },
                "align": "left",
            },
            # 6. SPECIAL PLOT CONFIGURATIONS
            "boxmode": "group",
            "piecolorway": c.top20,
        }
    }

    # Set as the global default for all future plots
    pio.templates.default = "favorita_dark"

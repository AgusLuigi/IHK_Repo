def plotly_scatter(df, _x, _y, _title, _labelsx, _labelsy, _vline, save=False):
    """
    Creates an interactive Plotly scatter plot.
    Automatically positions the threshold line and updates its label based on _vline.
    """
    import plotly.express as px
    from IPython.display import HTML
    # 1. Prepare Data
    plot_df = df.copy()
    
    # Sicherstellen, dass _vline eine Zahl ist (falls sie als String "55" kommt)
    v_val = float(_vline)
    
    # Vertikaler Jitter für bessere Sichtbarkeit, falls _y keine Koordinaten hat
    # Wir erstellen eine temporäre Spalte für die Verteilung
    plot_df['jitter_y'] = np.random.uniform(0.1, 0.9, size=len(plot_df))

    # 2. Visualization
    fig = px.scatter(
        plot_df, 
        x=_x, 
        y='jitter_y', 
        color=_x,
        color_continuous_scale=["crimson", "orange", "seagreen"],
        hover_data={
            'jitter_y': False,
            'market_id': True, 
            _x: True,
            'operator': True,
            'market_name': True
        },
        title=_title,
        labels={_x: _labelsx, 'jitter_y': _labelsy}
    )

    # 3. Styling & Layout
    fig.update_layout(
        plot_bgcolor='white',
        height=350,
        width=700,
        margin=dict(l=80, r=50, t=60, b=60),
        coloraxis_showscale=False,

        xaxis=dict(
            range=[-5, 105], 
            dtick=10, 
            title=_labelsx,
            gridcolor='rgba(200, 200, 200, 0.3)'
        ),

        yaxis=dict(
            title=_labelsy,
            showticklabels=False, 
            showgrid=False, 
            zeroline=False,
            fixedrange=True,
            range=[-0.1, 1.2] # Platz für Annotation oben
        ),
    )

    # 4. Dynamic Threshold Line & Label
    fig.add_vline(
        x=v_val, 
        line_dash="dash", 
        line_color="orange", 
        annotation_text=f"Threshold ({int(v_val)})", # Wert im Namen automatisch
        annotation_position="top",
        annotation_yshift=5
    )

    # 5. Optional Save
    if save:
        filename = f"{_title.lower().replace(' ', '_')}.html"
        fig.write_html(filename)
        print(f"✅ Plot saved as '{filename}'")

    # 6. Render as HTML (Bypass nbformat error)
    html_str = fig.to_html(include_plotlyjs='cdn', full_html=False)
    display(HTML(html_str))

# --- Dein Auslöse-Befehl ---
# plotly_scatter(   cl_food_markets_berlin, 
#                   'trust_score', 
#                   'jitter_y', 
#                   "Market Trust Score Distribution Audit", 
#                   "Trust Score (0-100)", 
#                   "Market Distribution", 
#                   "55", 
#                   save=False))

# ---------------------------------------------------------------------------------
# src/sql_schema_diagram.py
def sql_conect_image(chinook_url,
                     diagram_width=None,
                     diagram_height=None,
                     horizontal_col=1.5,
                     vertical_col=0.2):
    """
    Displays an offline SQL schema diagram from a database URL.

    Usage in Notebook:
        sql_conect_image("postgresql://USER:PASSWORD@HOST/DB?sslmode=require")
        sql_conect_image("sqlite:////Users/cristallagus/Desktop/GitHub/weebet/_onboarding_data/notebook/replizierte_daten.sqlite")
    Args:
        chinook_url     : Full SQL connection URL
        diagram_width   : Diagram width (None = auto)
        diagram_height  : Diagram height (None = auto)
        horizontal_col  : Horizontal spacing between tables (default 1.5)
        vertical_col    : Vertical spacing between rows (default 0.2)
    """
    from sqlalchemy import create_engine, inspect
    import pandas as pd
    import graphviz
    from IPython.display import display, Image
    import os
    import sys
    # ====================================================================================================
    #                                        Configuration
    # ====================================================================================================
    diagram_size = f"{diagram_width},{diagram_height}!" if diagram_width and diagram_height else ""

    line_style          = 'spline'
    smoothing_active    = 'true'
    TEXT_LINE           = 10
    edge_thickness      = '1.5'
    edge_color          = '#000000'
    arrow_size          = '0.8'
    margin_padding      = '0.2'
    min_edge_len        = '1.0'

    layout_settings = {
        'dpi':         '75',
        'rankdir':     'LR',
        'splines':     line_style,
        'smoothing':   smoothing_active,
        'nodesep':     str(vertical_col),
        'ranksep':     str(horizontal_col),
        'overlap':     'false',
        'concentrate': 'true',
        'splinegraph': 'true',
        'mclimit':     '20.0',
        'nslimit':     '20.0',
    }

    # Colors
    main_background_color = '#708090'
    header_color          = '#1d547b'
    header_font_color     = '#f5f5f5'
    default_bg_color      = '#D3D3D3'
    primary_key_color     = '#FF3131'
    foreign_key_color     = '#1F51FF'
    highlight_bg_color    = '#eaf2f8'
    ROW_INDEX             = '#BC13FE'
    # ====================================================================================================

    try:
        engine    = create_engine(chinook_url)
        inspector = inspect(engine)
        tables    = sorted(inspector.get_table_names())

        if not tables:
            print("❌ No tables found.")
            return

        # AUTO-DETECTION: Global PK index
        all_pks = {}
        for t in tables:
            for pk in inspector.get_pk_constraint(t).get('constrained_columns', []):
                all_pks[pk] = t

        # Graph setup
        dot = graphviz.Digraph(comment='Database Schema', engine='dot')
        dot.attr(bgcolor=main_background_color)
        if diagram_size:
            dot.attr(size=diagram_size)
        dot.attr(**layout_settings)
        dot.attr(pad=margin_padding)
        dot.attr('node', shape='plaintext', fontname='Helvetica')
        dot.attr('edge',
                 fontname='Helvetica',
                 fontsize=str(TEXT_LINE),
                 penwidth=edge_thickness,
                 arrowsize=arrow_size,
                 color=edge_color)

        # Step 1: Build table nodes
        for table_name in tables:
            columns = inspector.get_columns(table_name)
            pk_cols = inspector.get_pk_constraint(table_name).get('constrained_columns', [])
            real_fks = [fk['constrained_columns'][0] for fk in inspector.get_foreign_keys(table_name)]

            html_string = f'''<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5" BGCOLOR="white">
                              <TR><TD COLSPAN="2" BGCOLOR="{header_color}">
                              <FONT COLOR="{header_font_color}"><B>{table_name.upper()}</B></FONT>
                              </TD></TR>'''

            for col in columns:
                name    = col['name']
                ctype   = str(col['type']).split('(')[0]
                is_pk   = name in pk_cols
                is_fk   = name in real_fks or (name in all_pks and not is_pk)
                color    = primary_key_color if is_pk else (foreign_key_color if is_fk else 'black')
                bg_color = highlight_bg_color if (is_pk or is_fk) else default_bg_color

                html_string += f'''<TR>
                    <TD ALIGN="LEFT"  BGCOLOR="{bg_color}" PORT="{name}_L">
                        <FONT COLOR="{color}" POINT-SIZE="10">{name}</FONT>
                    </TD>
                    <TD ALIGN="RIGHT" BGCOLOR="{bg_color}" PORT="{name}_R">
                        <FONT COLOR="{ROW_INDEX}" POINT-SIZE="8">{ctype}</FONT>
                    </TD>
                </TR>'''

            dot.node(table_name, html_string + '</TABLE>>')

        # Step 2: Draw edges (real FK + fallback auto-detection)
        for table_name in tables:
            fks         = inspector.get_foreign_keys(table_name)
            drawn_cols  = []

            if fks:
                for fk in fks:
                    ref_table = fk['referred_table']
                    ref_col   = fk['referred_columns'][0]
                    join_col  = fk['constrained_columns'][0]
                    dot.edge(
                        f"{ref_table}:{ref_col}_R:e",
                        f"{table_name}:{join_col}_L:w",
                        xlabel=f" {join_col} ",
                        arrowhead='crow',
                        minlen=str(min_edge_len)
                    )
                    drawn_cols.append(join_col)
            else:
                # AUTO-CONNECTION: If DB has no explicit FKs
                for col in inspector.get_columns(table_name):
                    c_name = col['name']
                    if c_name in all_pks and c_name not in inspector.get_pk_constraint(table_name).get('constrained_columns', []):
                        ref_t = all_pks[c_name]
                        dot.edge(
                            f"{ref_t}:{c_name}_R:e",
                            f"{table_name}:{c_name}_L:w",
                            xlabel=f" {c_name} ",
                            arrowhead='crow',
                            style='dashed',
                            minlen=str(min_edge_len)
                        )

        # Step 3: Render & display
        output_filename = 'database_diagram_parallel_autodetect'
        dot.render(output_filename, format='png', cleanup=True)

        if os.path.exists(f'{output_filename}.png'):
            display(Image(filename=f'{output_filename}.png'))
        else:
            print("❌ Diagram could not be rendered.")

    except Exception as e:
        print(f"❌ Error: {e}")
# --- VISUALIZATION OF LIVE SOURCE DATA ---
# 1. SYSTEM SURVEY (API Connection)
def list_osm_source_info():
    print("🌍 Connecting to live source: OpenStreetMap (Overpass API)")
    print("🎯 Target region: Berlin, Germany")
    print("🔍 Focus: 'amenity' = 'marketplace' (Farmers Markets only)")
    return "Berlin, Germany"

# 2. VISUAL INSPECTOR
def osm_source_visual_inspector(place_name):
    """
    Analyzes the OSM live source and generates a schema diagram 
    to visualize data structure and types.
    """
    header_color      = '#1d547b'
    header_font_color = '#f5f5f5'
    default_bg_color  = '#D3D3D3'
    type_font_color   = '#BC13FE'
    main_bg_color     = '#708090'
    highlight_bg      = '#eaf2f8'

    print("⏳ Retrieving live schema...")
    
    try:
        # Filter for marketplaces only as per project requirements
        tags = {'amenity': 'marketplace'}
        gdf = ox.features_from_place(place_name, tags)
        
        if gdf.empty:
            print("❌ No data found.")
            return None

        # Graphviz Setup (Left to Right)
        dot = graphviz.Digraph(comment='OSM Source Schema', engine='dot')
        dot.attr(bgcolor=main_bg_color, rankdir='LR', nodesep='0.1', ranksep='1.5')
        dot.attr('node', shape='plaintext', fontname='Helvetica')

        # Source Table Representation
        table_title = "OSM_BERLIN_MARKETPLACES"
        html_string = f'''<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2" BGCOLOR="white">
                          <TR><TD COLSPAN="2" BGCOLOR="{header_color}">
                          <FONT COLOR="{header_font_color}"><B>{table_title.upper()}</B></FONT>
                          </TD></TR>'''
        
        # Displaying columns and types
        for col in sorted(gdf.columns):
            dtype = str(gdf[col].dtype).replace('object', 'string')
            is_geo = col == 'geometry'
            bg = highlight_bg if is_geo else default_bg_color
            geo_icon = "📍 " if is_geo else ""
            html_string += f'''<TR>
                <TD ALIGN="LEFT"  BGCOLOR="{bg}">
                    <FONT POINT-SIZE="10">{geo_icon}{col}</FONT>
                </TD>
                <TD ALIGN="RIGHT" BGCOLOR="{bg}">
                    <FONT COLOR="{type_font_color}" POINT-SIZE="8">{dtype}</FONT>
                </TD>
            </TR>'''
        
        dot.node('SOURCE', html_string + '</TABLE>>')
        print(f"✅ Analysis complete: {len(gdf)} objects retrieved.")
        display(dot)
        
        return 

    except Exception as e:
        print(f"❌ Critical error during API schema check: {e}")
        return None

# --- EXECUTION ---
# target = list_osm_source_info()
# osm_source_visual_inspector(target)
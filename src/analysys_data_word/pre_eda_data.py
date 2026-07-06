
# ⚙️ V2 Analyse Date Type / Unique(count)/ Duplicate (count) / NaN / Ausreisser
import pandas as pd
import numpy as np
import re
import warnings
from typing import Dict, List, Callable, Union

pd.set_option('display.width', 1000)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_colwidth', None)

def generate_cleaning_muster(column: str, semantic_type: str) -> str:
    return ""

def count_special_chars(text: Union[str, any]) -> int:
    if isinstance(text, str):
        return len(re.findall(r'[^a-zA-Z0-9\s]', text))
    return 0

def analyze_semantic_type_v3(df_check: pd.DataFrame) -> pd.DataFrame:
    """
    Klass The semantic Date type colloms.
    """
    SEMANTIC_HINTS_PRIORITY: Dict[str, Dict[str, Union[set, Callable]]] = {
        'ID': {
            'keywords': {'_id', 'session_id', 'trip_id', 'user_id', 'unique_id', 'kundennummer', 'bestellnr', 'order_id', 'artikelnummer','phone_number','fax_number'},
            'validation_func': lambda series: ((series.dropna().astype(str).apply(len) >= 5).any())
        },
        'Datum/Zeit': {
            'keywords': {'datum', 'zeit', 'date', 'time', 'start', 'end', 'birthdate', 'signup_date', 'check_in', 'check_out', 'departure', 'return', 'geburtstag', 'timestamp', 'creation_date', 'modified_date', 'erstellt', 'week'},
            'validation_func':lambda series: ((series.dropna().nunique() == 12 or series.dropna().nunique() == 31) or (series.dropna().apply(lambda x: isinstance(x, str)).all() and (pd.to_datetime(series.dropna(), errors='coerce').notna().all() or (series.dropna().astype(str).str.contains(r'[-_/]', na=False).any() and series.dropna().astype(str).str.contains(r'\d{4}', na=False).any()))))
        },
        'Datum/Zeit(int)': {
            'keywords': {'month','week','day'},
            'validation_func': lambda series: (series.dropna().nunique() == 12 or 6 <= series.dropna().nunique() <= 7 or series.dropna().nunique() == 31)
        },
        'Geometrisch': {
            'keywords': {'geom', 'geometry', 'shape', 'wkt', 'geojson', 'coordinates', 'location_data'},
            'validation_func': lambda series: (series.dropna().astype(str).str.contains(r'^(POINT|LINESTRING|POLYGON|MULTIPOINT|MULTILINESTRING|MULTIPOLYGON)\s*\(', regex=True, na=False).any() or series.dropna().astype(str).str.contains(r'{"type":\s*"(Point|LineString|Polygon|MultiPoint|MultiLineString|MultiPolygon)"', regex=True, na=False).any())
        },
    }
    SEMANTIC_HINTS_TEXT: Dict[str, Dict[str, Union[set, Callable]]] = {
        'Text (Kategorisch)': {
            'keywords': {'city', 'country', 'länder', 'region', 'state', 'bundesland', 'zip', 'plz', 'building_code', 'borough', 'subway', 'bus','primary_address_line_1', 'state_code','postcode'},
            'validation_func': lambda series: series.dropna().nunique() >= 2 and (pd.api.types.is_string_dtype(series.dropna()) or isinstance(series.dropna().dtype, pd.CategoricalDtype))
        },
         'Text (Gender)': {
            'keywords': {'geschlecht', 'typ', 'category', 'art', 'gender'},
            'validation_func': lambda series: series.dropna().nunique() >= 2 and (pd.api.types.is_string_dtype(series.dropna()) or isinstance(series.dropna().dtype, pd.CategoricalDtype))
        },
        'Text (object)': {
            'keywords': {'sales_method', 'airport', 'destination', 'origin', 'heimat', 'status', 'postcode'},
            'validation_func': lambda series: series.dropna().nunique() >= 2 and (pd.api.types.is_string_dtype(series.dropna()) or isinstance(series.dropna().dtype, pd.CategoricalDtype))
        },
        'Text (Freitext)': {
            'keywords': {'name', 'hotel', 'airline', 'beschreibung', 'kommentar', 'nachricht', 'adresse', 'website', 'overview_paragraph'},
            'validation_func': lambda series: pd.api.types.is_string_dtype(series.dropna()) or isinstance(series.dropna().dtype, pd.CategoricalDtype)
        },
    }
    SEMANTIC_HINTS_NUMERIC: Dict[str, Dict[str, Union[set, Callable]]] = {
        'Boolean(NaN)': {
            'keywords': {'is_invalid','missing', 'is_missing', 'has_value', 'exists', 'is_null', 'is_na', 'isnan', 'filled','is_outlier'},
            'validation_func': lambda series: (series.dropna().nunique() >= 1) and (pd.api.types.is_bool_dtype(series.dropna()) or set(series.dropna().astype(str).str.lower().str.strip().unique()).issubset({'true', 'false', '1', '0', 'ja', 'nein', 'yes', 'no', 't', 'f', 'wahr', 'falsch'}))
        },
        'Boolean': {
            'keywords': {'self_employed','is_weekend_trip', 'boolean', 'bool', 'booked', 'married', 'cancellation', 'children','discount', 'flight_booked', 'hotel_booked', 'return_flight_booked', 'is_cancelled'},
            'validation_func': lambda series: (series.dropna().nunique() == 2) and (pd.api.types.is_bool_dtype(series.dropna()) or set(series.dropna().astype(str).str.lower().str.strip().unique()).issubset({'true', 'false', '1', '0', 'ja', 'nein', 'yes', 'no', 't', 'f', 'wahr', 'falsch'}))
        },
        'Float (Geografisch)': {
            'keywords': {'lat', 'lon', 'latitude', 'longitude'},
            'validation_func': lambda series: pd.to_numeric(series.dropna(), errors='coerce').notna().all() and (pd.to_numeric(series.dropna(), errors='coerce').astype(str).str.count(r'\.').all() or pd.api.types.is_float_dtype(series.dropna()))
        },
        'Float (Prozentsatz)': {
            'keywords': {'percent', 'pct', 'rate', 'discount', '%'},
            'validation_func': lambda series: (series.dropna().nunique() > 2) and ((pd.to_numeric(series.dropna().astype(str).str.replace('%', ''), errors='coerce').dropna().between(0, 1).all() or pd.to_numeric(series.dropna().astype(str).str.replace('%', ''), errors='coerce').dropna().between(0, 100).all()) or (pd.to_numeric(series.dropna().astype(str).str.replace('%', ''), errors='coerce').notna().all() and series.dropna().astype(str).str.replace('%', '').str.replace(',', '.').str.match(r'^\d{1,3}(\.\d{1,3})?$').all()))
        },
        'Float (Waehrung)': {
            'keywords': {'revenue','preis', 'kosten', 'betrag', 'dollar', 'euro', 'yen', 'usd', 'eur', 'fare','chf', 'gbp', 'sek', 'jpy', '€', '£', '$'},
            'validation_func': lambda series: (pd.api.types.is_numeric_dtype(series.dropna()) or pd.to_numeric(series.dropna().astype(str).str.replace(',', '.'), errors='coerce').notna().all()) and series.dropna().nunique() > 2
        },
        'Integer': {
            'keywords': {'nb_sold', 'years_as_customer', 'nb_site_visits', '_time_days', '_duration_days', 'anzahl', 'menge', 'stueck', 'stk', 'count', 'qty', 'seats', 'rooms', 'nights', 'bags', 'clicks', 'nummer', 'nr', 'quantity', 'val', 'rating'},
            'validation_func': lambda series: (series.dropna().nunique() > 2) and pd.to_numeric(series.dropna(), errors='coerce').notna().all() and (pd.to_numeric(series.dropna(), errors='coerce').dropna().apply(lambda x: x.is_integer() if isinstance(x, float) else True).all())
        }
    }
    results: List[Dict[str, str]] = []
    hint_categories = [SEMANTIC_HINTS_PRIORITY, SEMANTIC_HINTS_TEXT, SEMANTIC_HINTS_NUMERIC]
    SEMANTIC_HINTS_NUMERIC_ORDERED: List[str] = ['Boolean(NaN)','Boolean', 'Float (Geografisch)', 'Float (Prozentsatz)', 'Float (Waehrung)', 'Integer']

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        warnings.simplefilter("ignore", UserWarning)

        df_to_analyze = df_check

        for column in df_to_analyze.columns:
            original_dtype: str = str(df_to_analyze[column].dtype)
            semantic_type: str = original_dtype
            column_lower: str = column.lower()
            found_match: bool = False

            for hint_group in hint_categories:
                if found_match:
                    break
                if hint_group is SEMANTIC_HINTS_NUMERIC:
                    for sem_type in SEMANTIC_HINTS_NUMERIC_ORDERED:
                        hints = hint_group[sem_type]
                        name_match = any(keyword in column_lower for keyword in hints['keywords'])
                        content_valid = False
                        try:
                            content_valid = hints['validation_func'](df_to_analyze[column])
                        except Exception:
                            pass

                        if name_match and content_valid:
                            semantic_type = sem_type
                            found_match = True
                            break
                else:
                    for sem_type, hints in hint_group.items():
                        name_match = any(keyword in column_lower for keyword in hints['keywords'])
                        content_valid = False
                        try:
                            content_valid = hints['validation_func'](df_to_analyze[column])
                        except Exception:
                            pass

                        if name_match and content_valid:
                            semantic_type = sem_type
                            found_match = True
                            break

            results.append({
                'Spalte': column,
                'Semantischer_Typ': semantic_type,
            })

    return pd.DataFrame(results)

# MAIN PATTERN FOR CONSOLIDATED DISPLAY (INCL. SEMANTICS, WITHOUT SUGGESTIONS)
def muster_df_consolidated_view(df: pd.DataFrame) -> None:
    """
    Führt eine konsolidierte Datenqualitäts-Analyse durch, inklusive der neuen
    robusten Metriken für Feature Engineering (StdDev, Kardinalität, Z-Score-Ausreißer).
    """
    df_check=df
    df_sem_types = analyze_semantic_type_v3(df_check)
    consolidated_data: Dict[str, Dict[str, Union[str, float, int, None]]] = {}
    for col in df_check.columns:
        sem_type_row = df_sem_types[df_sem_types['Spalte'] == col].iloc[0] if col in df_sem_types['Spalte'].values else {'Semantischer_Typ': str(df_check[col].dtype)}

        duplicate_count = len(df_check) - df_check[col].nunique()
        special_chars_count = df_check[col].astype(str).apply(count_special_chars).sum()
        cardinality_ratio = round(df_check[col].nunique() / len(df_check) * 100, 2)

        consolidated_data[col] = {
            'Spalte': col,
            'Semantischer_Typ': sem_type_row['Semantischer_Typ'],
            'Datentyp': str(df_check[col].dtype),
            'Einzigartige_Werte': df_check[col].nunique(),
            'Kardinalität(%)': cardinality_ratio,
            'Duplicate': duplicate_count,
            'NaN': df_check[col].isnull().sum(),
            'NaN(%)': round(df_check[col].isnull().sum() / len(df_check) * 100, 2),
            'Sonderzeichen ': special_chars_count,
            'Min': np.nan, '25% (Q1)': np.nan, 'Median': np.nan, '75% (Q3)': np.nan,
            'Max/100%(Q4)': np.nan,
            'StdDev': np.nan,
            'Upper_Fence': np.nan,
            'Lower_Fence': np.nan,
            'Skewness': np.nan,
            'Ausreißer (IQR)': 0,
            'Ausreißer (StdDev)': 0,
        }
    numeric_relevant_types = {'Float (Geografisch)', 'Float (Prozentsatz)', 'Float (Waehrung)', 'Integer', 'Boolean', 'Boolean(NaN)'}

    for _, row in df_sem_types.iterrows():
        column = row['Spalte']
        semantic_type = row['Semantischer_Typ']
        series = df_check[column]

        if semantic_type in numeric_relevant_types or pd.api.types.is_numeric_dtype(series):
            try:
                numeric_series = pd.to_numeric(series, errors='coerce').dropna()

                if not numeric_series.empty:
                    q1, median, q3, q4_max = numeric_series.quantile([0.25, 0.5, 0.75, 1.0])
                    min_val = numeric_series.min()
                    skewness = round(numeric_series.skew(), 2)

                    # 2.1 (StdDev)
                    std_dev = numeric_series.std()

                    # 2.2 IQR (Boxplot-Standard)
                    Q1_o, Q3_o = q1, q3
                    IQR = Q3_o - Q1_o
                    lower_bound_iqr = Q1_o - 1.5 * IQR
                    upper_bound_iqr = Q3_o + 1.5 * IQR
                    outliers_count_iqr = ((numeric_series < lower_bound_iqr) | (numeric_series > upper_bound_iqr)).sum()

                    # 2.3 StdDev (Z-Score, 3-Sigma-Regel)
                    mean_val = numeric_series.mean()
                    lower_bound_std = mean_val - 3 * std_dev
                    upper_bound_std = mean_val + 3 * std_dev
                    outliers_count_std = ((numeric_series < lower_bound_std) | (numeric_series > upper_bound_std)).sum()

                    consolidated_data[column].update({
                        'Min': round(min_val, 2),
                        '25% (Q1)': round(Q1_o, 2),
                        'Median': round(median, 2),
                        '75% (Q3)': round(Q3_o, 2),
                        'Max/100%(Q4)': round(q4_max, 2),
                        'StdDev': round(std_dev, 2),
                        'Upper_Fence': round(upper_bound_iqr, 2),
                        'Lower_Fence': round(lower_bound_iqr, 2),
                        'Skewness': skewness,
                        'Ausreißer (IQR)': int(outliers_count_iqr),
                        'Ausreißer (StdDev)': int(outliers_count_std)
                    })
            except Exception:
                pass

    df_final = pd.DataFrame(list(consolidated_data.values()))

    # MAIN PATTERN FOR CONSOLIDATED DISPLAY (INCL. SEMANTICS, WITHOUT SUGGESTIONS)
    column_order = [
        'Datentyp', 'Semantischer_Typ',
        'Einzigartige_Werte', 'Kardinalität(%)', 'Spalte',
        'Duplicate',
        'NaN', 'NaN(%)',
        'Sonderzeichen',
        'Min', 'Lower_Fence', '25% (Q1)', 'Median', 'StdDev', '75% (Q3)', 'Upper_Fence', 'Max/100%(Q4)', 'Skewness',
        'Ausreißer (IQR)', 'Ausreißer (StdDev)',
    ]

    df_final = df_final[[col for col in column_order if col in df_final.columns]]

    # Fill non-numeric NaNs with "-"
    for stat_col in ['Min', 'Max/100%(Q4)', 'Median', 'StdDev', 'Skewness', 'Upper_Fence', 'Lower_Fence', '25% (Q1)', '75% (Q3)']:
        df_final[stat_col] = df_final[stat_col].apply(lambda x: '-' if pd.isna(x) else x)

    # Set non-numeric outlier counts to "-"
    def format_outlier_count(row, col_name):
        is_numeric_type = row['Semantischer_Typ'] in numeric_relevant_types or pd.api.types.is_numeric_dtype(df[row['Spalte']])
        if not is_numeric_type:
            return '-'
        return int(row[col_name]) if row[col_name] is not None else 0

    df_final['Ausreißer (IQR)'] = df_final.apply(lambda row: format_outlier_count(row, 'Ausreißer (IQR)'), axis=1)
    df_final['Ausreißer (StdDev)'] = df_final.apply(lambda row: format_outlier_count(row, 'Ausreißer (StdDev)'), axis=1)

    print('*' * 10, 'CONSOLIDATED DATA QUALITY ANALYSIS', '*' * 10)
    print(' '*120 + (('-->'+'  ')*3))
    print(f"Shape (Rows, Columns): {df.shape} | Duplicate Rows: {df.duplicated().sum()}")
    print("-" * 50)
    print(df_final.to_string())
    print(' '*120 + (('-->'+'  ')*3))
    print('*' * 50)

def muster_find_duplicate_columns(df: pd.DataFrame) -> None:
    print("*" * 10, " DETECTING REDUNDANT COLUMNS BY CONTENT ", "*" * 10)
    df_check = df.copy()

    for col in df_check.columns:
        if pd.api.types.is_bool_dtype(df_check[col]):
            df_check[col] = df_check[col].astype(int)
        elif pd.api.types.is_numeric_dtype(df_check[col]):
            df_check[col] = df_check[col].round(4)
    duplicates_mask = df_check.T.duplicated(keep='first')

    if not duplicates_mask.any():
        print("✅ No redundant columns detected.")
        return
    duplicate_col_names = df_check.columns[duplicates_mask].tolist()
    summary = []
    checked_cols = []

    for col in df_check.columns:
        if col not in checked_cols:
            matches = []
            for other_col in df_check.columns:
                if col != other_col and df_check[col].equals(df_check[other_col]):
                    matches.append(other_col)
                    checked_cols.append(other_col)

            if matches:
                summary.append({
                    "Behaltene_Spalte": col,
                    "Duplizierte_Spalten": ", ".join(matches)
                })
            checked_cols.append(col)

    # AUSGABE
    print("⚠️ Identical column content detected in the following columns:")
    print(pd.DataFrame(summary).to_string(index=False))

    print(f"💡 Cleaning proposal:")
    print(f"df_Cleaning = df.drop(columns={duplicate_col_names}, inplace=False)")
    print("*" * 57)

def full_data_analysis(df_input: pd.DataFrame):
    """Hauptfunktion für den Aufruf aus dem Notebook."""
    muster_df_consolidated_view(df_input)
    muster_find_duplicate_columns(df_input)
import pandas as pd
import numpy as np
import re
import gc
from collections import Counter
from langdetect import detect, DetectorFactory
from IPython.display import display

# ⚙️ V3: ANALYSE-DASHBOARD (IST-ZUSTAND) Datensatz-Struktur & NLP-Mancos
def full_words_analysis(df: pd.DataFrame, target_col: str = None):
    """
    NLP-MANCOS-ANALYSIS V4 (MASTER COMPARISON)
    All functions from previous versions consolidated into a single overview.
    """
    DetectorFactory.seed = 42
    df_check = df
    df_text_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
    
    if not df_text_cols:
        print("❌ Keine TextColumns gefunden!")
        return

    # Container für Ergebnisse
    quality_list = []
    content_list = []
    anomaly_list = []
    stats_list = []

    print(f"🚀 STARTING FULL COMPARISON ANALYSIS ({len(df_text_cols)} Columns)")
    
    for current_col in df_text_cols:
        txt_series = df[current_col].astype(str).fillna("").replace("nan", "")
        total_rows = len(df)
        
        def get_top_lang(series):
            try:
                sample = series.sample(min(len(series), 300))
                langs = sample.apply(lambda x: detect(x) if len(re.findall(r'[a-zA-Z]', str(x))) > 10 else "N/A")
                return langs.value_counts().idxmax()
            except Exception: 
                return "unknown"

        quality_list.append({
            'Spalte': current_col,
            'NaNs': df_check[current_col].isnull().sum(),
            'Unique': df_check[current_col].nunique(),
            'Kardinalität %': round((df_check[current_col].nunique() / total_rows) * 100, 1),
            'Dom. Sprache': get_top_lang(txt_series),
            'Sonderzeichen': txt_series.apply(lambda x: len(re.findall(r'[^a-zA-Z0-9\s,.]', str(x)))).sum()
        })

        common_stop = {'the', 'a', 'is', 'in', 'it', 'you', 'i', 'and', 'on', 'for', 'be', 'of'}
        all_words = " ".join(txt_series).lower().split()
        top_10 = [w for w, c in Counter(all_words).most_common(10)]
        
        lex_div = txt_series.apply(lambda x: len(set(x.lower().split())) / len(x.split()) if x.split() else 0).mean()
        stop_ratio = txt_series.apply(lambda x: sum(1 for w in x.lower().split() if w in common_stop) / len(x.split()) if x.split() else 0).mean()
        
        content_list.append({
            'Spalte': current_col,
            'Lex. Diversity': round(lex_div, 2),
            'Stopword-Last': round(stop_ratio, 2),
            'Top 5 Tokens': ", ".join(top_10[:5]),
            'Zahlen im Text': txt_series.str.contains(r'\d').sum()
        })

        char_counts = txt_series.apply(len)
        word_counts = txt_series.apply(lambda x: len(x.split()))
        
        stats_list.append({
            'Spalte': current_col,
            'Ø Zeichen': round(char_counts.mean(), 1),
            'Max Zeichen': char_counts.max(),
            'Ø Wörter': round(word_counts.mean(), 1),
            'Max Wörter': word_counts.max()
        })

        anomaly_list.append({
            'Spalte': current_col,
            'Leere Texte': (txt_series.str.strip() == "").sum(),
            'Short (<5)': (char_counts < 5).sum(),
            'Emojis': txt_series.str.contains(r'[^\x00-\x7F]+').sum(),
            'Shortforms': txt_series.str.contains(r"(?:[a-zA-Z]'[a-zA-Z]|\b[uU]\b|\bw/)", regex=True).sum(),
            'Shouting': (txt_series.apply(lambda x: x.isupper() if len(x) > 10 else False)).sum(),
            'Duplikate': df[current_col].duplicated().sum()
        })

    # VISUALIS
    print("" + "📊 1. STRUCTURE & QUALITY")
    display(pd.DataFrame(quality_list).set_index('Spalte'))
    
    print("" + "🧠 2. CONTENT & SEMANTIC DEPTH")
    display(pd.DataFrame(content_list).set_index('Spalte'))
    
    print("" + "📏 3. LENGTH STATISTICS (RAW DATA)")
    display(pd.DataFrame(stats_list).set_index('Spalte'))
    
    print("" + "⚠️ 4. ANOMALY BOARD (MANCOS)")
    display(pd.DataFrame(anomaly_list).set_index('Spalte'))

    del quality_list, content_list, stats_list, anomaly_list
    gc.collect()
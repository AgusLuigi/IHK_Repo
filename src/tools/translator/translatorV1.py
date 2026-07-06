# 0.0.8 Translator DEEP-ANALYSIS-MIRROR (ENGLISH-CODE-TARGET) - JUPYTER-SICHER
import pyperclip
import os
import re
import time
import gc
import requests
import json
import logging

# GLOBAL STRIPE-KONSTANTEN (Verschleiert durch Einzeiler)
STRIPE_START = "S T A R T _ C R Y S T A L".replace(" ", "")
STRIPE_END = "E N D _ C R Y S T A L".replace(" ", "")
STRIPE_HYPHEN = "& &".replace(" ", "")  # &&

# ESCAPE-KATALOG (Schutz gegen Eigen-Ersatz)
ESC_HYPHEN = "* 1 / * 1 &".replace(" ", "")
ESC_START = "* 1 / * 1 s".replace(" ", "")
ESC_END = "* 1 / * 1 e".replace(" ", "")

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("Translator")

class DeepSeekMirror:
    def __init__(self, model="deepseek-coder-v2", preserve_names: bool = True):
        self.model_name = model
        self.url = "http://localhost:11434/api/generate"
        self.preserve_names = preserve_names

    def call_mirror(self, numbered_batch, target_lang='EN'):
        # 1. TRESOR: Echte Marker parken
        protected_text = numbered_batch.replace(STRIPE_HYPHEN, ESC_HYPHEN)
        protected_text = protected_text.replace(STRIPE_START, ESC_START)
        protected_text = protected_text.replace(STRIPE_END, ESC_END)

        # 2. MASKIERUNG
        masked = re.sub(r"-", STRIPE_HYPHEN, protected_text)

        lang_full = "English" if target_lang == 'EN' else "German"
        
        name_rule = (
            "5. Do NOT translate function/variable names - keep EXACTLY as input."
            if self.preserve_names
            else f"5. TRANSLATE descriptive variable and function names to {lang_full}."
        )

        prompt = f"""TASK: You are a professional Code-Translator.
TARGET LANGUAGE: {lang_full}.

GOAL:
- Translate all German comments, docstrings, and strings into {lang_full}.
- If a line is already in {lang_full}, keep it EXACTLY as it is.
- Preserve the format L<number>: at the beginning of each line.
- Keep the symbol {STRIPE_HYPHEN} unchanged.

RULES:
1. Output MUST have the same number of lines as input.
2. Only translate the content after 'Lx: '.
3. No chatter, no explanations.
4. {name_rule}

INPUT:
{STRIPE_START}
{masked}
{STRIPE_END}"""

        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_ctx": 16384, "stop": [STRIPE_END]},
                },
                timeout=300,
            )
            raw_res = response.json().get("response", "").strip()

            # 3. CLEANUP & RÜCKWANDLUNG
            clean = raw_res.replace(STRIPE_START, "").replace(STRIPE_END, "").strip()
            
            cleaned_lines = []
            for line in clean.splitlines():
                m = re.match(r"^L(\d+):\s?(.*)$", line)
                if m: cleaned_lines.append(f"L{m.group(1)}: {m.group(2)}")
            
            cleaned_text = "\n".join(cleaned_lines)
            final = re.sub(rf"\s*{re.escape(STRIPE_HYPHEN)}\s*", "-", cleaned_text)
            
            # 4. TRESOR ÖFFNEN
            final = final.replace(ESC_HYPHEN, STRIPE_HYPHEN)
            final = final.replace(ESC_START, STRIPE_START)
            final = final.replace(ESC_END, STRIPE_END)
            
            return final
        except Exception as e:
            return f"ERROR: {e}"

def apply_anchor_healing(original_line, translated_content):
    if not translated_content: return original_line
    healed = re.sub(r"\s*-\s*", "-", translated_content)
    healed = re.sub(r"\s*[\.\(\):]\s*", lambda m: m.group(0).strip(), healed)
    
    anchors = ['(', ')', '[', ']', '{', '}', ':', '=', '"', "'", '#']
    for char in anchors:
        if original_line.count(char) != healed.count(char): return original_line
    return healed

def heal_comment_line(original_line, translated_content):
    if not translated_content: return original_line
    healed = re.sub(rf"\s*{re.escape(STRIPE_HYPHEN)}\s*", "-", translated_content)
    if not healed.lstrip().startswith("#"): return original_line
    return healed

def execute_perfect_mirror_translation(preserve_names: bool = True, output_file: str = "translated.py", LANGUAGE='EN'):
    logger.info(f"🚀 Start: target_lang={LANGUAGE} | preserve_names={preserve_names}")
    engine = DeepSeekMirror(preserve_names=preserve_names)
    raw_input = pyperclip.paste().splitlines()
    
    if not raw_input:
        logger.error("❌ Clipboard leer!")
        return

    indent_map = {i: re.match(r"^\s*", line).group(0) for i, line in enumerate(raw_input)}
    step = 10

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n")

    for i in range(0, len(raw_input), step):
        batch = raw_input[i:i+step]
        numbered_input = "\n".join([f"L{i+idx}: {line.lstrip()}" for idx, line in enumerate(batch)])
        raw_res = engine.call_mirror(numbered_input, target_lang=LANGUAGE)

        block_results = {}
        for res_line in raw_res.splitlines():
            match = re.match(r"^L(\d+):\s?(.*)$", res_line)
            if not match: continue
            idx, content = int(match.group(1)), match.group(2)
            orig_l = raw_input[idx].lstrip()

            if orig_l.startswith("#"):
                block_results[idx] = heal_comment_line(orig_l, content)
            elif orig_l.startswith(("import ", "from ", "class ", "def ")):
                block_results[idx] = apply_anchor_healing(orig_l, content) if any(c in orig_l for c in "#\"'") else orig_l
            elif any(kw in orig_l.upper() for kw in ["SELECT", "FROM", "WHERE", "JOIN"]):
                block_results[idx] = orig_l
            else:
                block_results[idx] = apply_anchor_healing(orig_l, content)

        with open(output_file, "a", encoding="utf-8") as f:
            for idx in range(i, min(i+step, len(raw_input))):
                f.write(indent_map[idx] + block_results.get(idx, raw_input[idx].lstrip()) + "\n")
            f.flush()
        time.sleep(0.02)

    logger.info(f"✅ Ready: {output_file}")
    gc.collect()

# JUPYTER INTERFACE
def query_translate(): execute_perfect_mirror_translation(True, LANGUAGE='EN')
def query_translate_aggressive(): execute_perfect_mirror_translation(False, LANGUAGE='EN')
def query_translate_custom(preserve=True, out="translated.py", lang='EN'): execute_perfect_mirror_translation(preserve, out, lang)
def logging_on(): logger.setLevel(logging.INFO); print("📢 Logging ON")
def logging_off(): logger.setLevel(logging.ERROR); print("🔇 Logging OFF")

if __name__ == "__main__":
    logging_on()
    print("Befehle: query_translate() -> Ziel: Englisch (Code-Safe)")
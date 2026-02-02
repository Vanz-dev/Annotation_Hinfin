import streamlit as st
import json
import pandas as pd
from datetime import datetime
from deep_translator import GoogleTranslator
from streamlit_pdf_viewer import pdf_viewer
import os

# ======================================================
# CONFIG
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "text_ner_full_dataset.json")
GUIDELINES_PDF = os.path.join(BASE_DIR, "Text_NER_Annotation_Guidelines_v1.pdf")

PASSWORD = "TNERfinance@2025#!"
ADMIN_EMAIL = "Vanshikaa.Jani@mbzuai.ac.ae"

SEGMENT_SIZE = 30
PILOT_COUNT = 60

ENTITY_TYPES = [
    "Organization",
    "Person",
    "Location",
    "Date",
    "Amount",
    "Financial_Product",
    "Scheme",
    "Miscellaneous",
]

ENTITY_COLORS = {
    "Organization": "#AAD7F7",
    "Person": "#FCBED3",
    "Location": "#F1F1B0",
    "Date": "#F7D090",
    "Amount": "#F5C5FC",
    "Financial_Product": "#ABF0F9",
    "Scheme": "#B2F2BF",
    "Miscellaneous": "#F1A3E2",
}

st.set_page_config(page_title="Text NER Annotation", layout="wide")

# ======================================================
# LOAD & NORMALIZE DATA
# ======================================================
def load_and_expand_entities(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for item in data:
        uid = f"ner_{item['id']}"
        sentence = item["sentence"]
        entities = item.get("entities", {})

        for ent_type, spans in entities.items():
            for span in spans:
                rows.append({
                    "uid": uid,
                    "sentence": sentence,
                    "span_text": span,
                    "proposed_type": ent_type
                })
    return rows


all_items = load_and_expand_entities(DATA_FILE)

pilot_items = all_items[:PILOT_COUNT]
rest_items = all_items[PILOT_COUNT:]


def make_segments(items, size, prefix):
    segs = []
    for i in range(0, len(items), size):
        chunk = items[i:i + size]
        segs.append((f"{prefix}_{len(segs)+1}", chunk))
    return segs


pilot_segments = make_segments(pilot_items, SEGMENT_SIZE, "pilot_segment")
main_segments = make_segments(rest_items, SEGMENT_SIZE, "segment")

SEGMENT_MAP = {name: items for name, items in (pilot_segments + main_segments)}
SEGMENT_LIST = list(SEGMENT_MAP.keys())

# ======================================================
# SESSION STATE
# ======================================================
for key, default in {
    "logged_in": False,
    "guidelines_ok": False,
    "current_segment": None,
    "idx": 0,
    "annotations": {}
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ======================================================
# TRANSLATION
# ======================================================
def translate_hi_to_en(text):
    try:
        return GoogleTranslator(source="hi", target="en").translate(text)
    except Exception as e:
        return f"(Translation error: {e})"

# ======================================================
# LOGIN
# ======================================================


if not st.session_state.logged_in:
    st.title("🔐 Text NER Annotation Platform")

    name = st.text_input("Your name")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        if pw == PASSWORD and name.strip():
            st.session_state.login_ok = True
            st.session_state.user_temp = name.strip()
        else:
            st.error("Incorrect password or empty name.")

    if st.session_state.get("login_ok", False):
        st.success(f"Welcome, {st.session_state.user_temp} 👋")
        if st.button("Enter Platform"):
            st.session_state.logged_in = True
            st.session_state.user = st.session_state.user_temp
            st.rerun()

    st.stop()


st.title(f"👋 Welcome, {st.session_state.user}")

# ======================================================
# GUIDELINES
# ======================================================
with st.expander("📘 Annotation Guidelines", expanded=not st.session_state.guidelines_ok):
    st.subheader("📘 Annotation Guidelines (PDF)")
    pdf_viewer(GUIDELINES_PDF, height=700)

    st.caption("Please read the guidelines carefully before proceeding.")

    if not st.session_state.guidelines_ok:
        if st.button("I have read and understood ✔️"):
            st.session_state.guidelines_ok = True
            st.rerun()

# Block rest of the app until guidelines are accepted
if not st.session_state.guidelines_ok:
    st.stop()


# ======================================================
# SEGMENT SELECTION
# ======================================================
segment_name = st.selectbox("Select segment", ["-- Select --"] + SEGMENT_LIST)

if segment_name == "-- Select --":
    st.stop()

if segment_name != st.session_state.current_segment:
    st.session_state.current_segment = segment_name
    st.session_state.idx = 0

items = SEGMENT_MAP[segment_name]
N = len(items)
idx = st.session_state.idx
item = items[idx]

def build_annotation():
    return {
        "uid": item["uid"],
        "segment": segment_name,
        "sentence": item["sentence"],
        "span_text": item["span_text"],
        "proposed_type": item["proposed_type"],

        # ✅ READ FROM SESSION STATE (never local vars)
        "is_entity": st.session_state.get(
            f"is_entity_{segment_name}_{idx}"
        ),

        "is_type_correct": st.session_state.get(
            f"is_type_correct_{segment_name}_{idx}"
        ),

        "corrected_type": st.session_state.get(
            f"corrected_type_{segment_name}_{idx}"
        ),

        "annotator": st.session_state.user,
        "timestamp": datetime.utcnow().isoformat()
    }


# ======================================================
# SIDEBAR: JUMP + PROGRESS
# ======================================================
with st.sidebar:
    st.subheader("⏭️ Jump to Entity")

    jump_number = st.number_input(
        "Entity number:",
        min_value=1,
        max_value=N,
        value=idx + 1,
        step=1
    )

    def save_before_jump():
        st.session_state.annotations[f"{segment_name}_{idx}"] = build_annotation()

    if st.button("Jump ➡️"):
        st.session_state.idx = jump_number - 1
        st.rerun()

    st.markdown("---")
    st.header("📊 Segment Progress")

    completed = 0
    for i in range(N):
        ann = st.session_state.annotations.get(f"{segment_name}_{i}")

        is_current = (i == idx)

        if ann and ann.get("is_entity") is not None:
            completed += 1
            icon = "🟢"
        else:
            icon = "⚪"

        if is_current:
            st.markdown(
                f"""
                <div style="
                    background:#E0F2FE;
                    border-left:4px solid #0284C7;
                    padding:8px 12px 10px 12px;
                    font-weight:800;
                    margin-bottom:14px; 
                ">
                     {icon} {i+1}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"{icon} {i+1}")


    st.progress(completed / N)
    st.caption(f"{completed}/{N} annotated")

# ======================================================
# HIGHLIGHT SENTENCE
# ======================================================
def highlight_sentence(sentence, span, ent_type):
    color = ENTITY_COLORS.get(ent_type, "#EEEEEE")
    return sentence.replace(
        span,
        f"<mark style='background:{color}; padding:2px 4px; border-radius:4px'>{span}</mark>",
        1
    )

# ======================================================
# MAIN UI
# ======================================================
st.markdown(f"### 🧩 Entity {idx+1} of {N}")
st.progress((idx+1)/N)




st.markdown("#### 📄 Sentence Under Review")

with st.container(border=True):
    st.markdown(
            f"""
            <div style="
                background-color: #ffffff;
                padding: 14px 16px;
                border-radius: 8px;
                font-size: 17px;
                line-height: 1.7;
            ">
                {highlight_sentence(
                    item["sentence"],
                    item["span_text"],
                    item["proposed_type"]
                )}
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("")

if st.button("🔄 Translate sentence"):
    st.info(translate_hi_to_en(item["sentence"]))

left_decision, right_decision = st.columns([1, 1], gap="large")


with left_decision:
    st.markdown("#### 🔍 Entity Under Review")

    color = ENTITY_COLORS.get(item["proposed_type"], "#F3F4F6")

    with st.container(border=True):
        st.markdown("**Entity text**")
        st.markdown(
            f"""
            <div style="
                background-color: {color};
                padding: 12px 14px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: 500;
            ">
                {item["span_text"]}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"**Proposed type:**  🟦 **{item['proposed_type']}**")

    if st.button("🔄 Translate entity"):
        st.info(translate_hi_to_en(item["span_text"]))

with right_decision:
    with st.container(border=True):
        st.markdown("#### 🧩 Entity Verification")

        step1_col, step2_col = st.columns(2, gap="large")

        # -------------------------
        # STEP 1: ENTITY VALIDITY
        # -------------------------
        with step1_col:
            st.markdown("**Step 1**")
            st.caption("Is the highlighted text a named entity in this sentence?")

            is_entity_key = f"is_entity_{segment_name}_{idx}"

            is_entity = st.radio(
                "Entity validity",
                ["Yes", "No", "Uncertain"],
                key=is_entity_key
            )


        # -------------------------
        # STEP 2: TYPE VERIFICATION
        # -------------------------
        type_key = f"is_type_correct_{segment_name}_{idx}"
        corrected_key = f"corrected_type_{segment_name}_{idx}"

        with step2_col:
            st.markdown("**Step 2**")
            st.caption("Is the assigned entity type correct?")

            is_type_correct = "NA"
            corrected_type = None

            if is_entity == "Yes":
                is_type_correct = st.radio(
                    "Entity type correctness",
                    ["Yes", "No", "Uncertain"],
                    key=type_key
                )

                if is_type_correct == "No":
                    corrected_type = st.selectbox(
                        "Select correct entity type",
                        ENTITY_TYPES,
                        key=corrected_key
                    )
            else:
                st.info("-- Skipped: Entity type verification not applicable ---")



    

    prev_col, next_col = st.columns(2)

    with prev_col:
        if st.button("⬅️ Previous", disabled=(idx == 0)):
            st.session_state.idx -= 1
            st.rerun()

    with next_col:
        if idx < N - 1:
            if st.button("Save & Next ➡️"):
                st.session_state.annotations[f"{segment_name}_{idx}"] = build_annotation()
                st.session_state.idx += 1
                st.rerun()
        else:
            if st.button("Save & Finish 🎉"):
                st.session_state.annotations[f"{segment_name}_{idx}"] = build_annotation()
                st.success("Segment complete!")

# ======================================================
# DOWNLOAD
# ======================================================
st.markdown("---")
st.subheader("💾 Download Segment Annotations")

seg_rows = [
    v for v in st.session_state.annotations.values()
    if v["segment"] == segment_name
]

df = pd.DataFrame(seg_rows)

st.download_button(
    "⬇️ Download CSV",
    df.to_csv(index=False).encode("utf-8"),
    file_name=f"{segment_name}_{st.session_state.user}.csv"
)

st.info(f"Please send the file to **{ADMIN_EMAIL}**")
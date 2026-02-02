import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from deep_translator import GoogleTranslator
from streamlit_pdf_viewer import pdf_viewer

# ======================================================
# CONFIG
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "text_QA_dataset.csv")
GUIDELINES_PDF = os.path.join(BASE_DIR, "Text_QA_annotation_guidelines_v1.pdf")

PASSWORD = "TQAfinance@2025#!"
ADMIN_EMAIL = "Vanshikaa.Jani@mbzuai.ac.ae"

SEGMENT_SIZE = 25
PILOT_COUNT = 50

st.set_page_config(page_title="Text QA Annotation", layout="wide")

# ======================================================
# LOAD & NORMALIZE DATA
# ======================================================
def load_qa_items(csv_path):
    df = pd.read_csv(csv_path)
    rows = []

    for i, row in df.iterrows():
        passage_uid = f"passage_{i+1}"

        for qn in range(1, 5):
            q_col = f"Q{qn}"
            a_col = f"A{qn}"

            if pd.notna(row.get(q_col)) and pd.notna(row.get(a_col)):
                rows.append({
                    "uid": f"{passage_uid}_q{qn}",
                    "domain": row["Domain"],
                    "passage": row["Passage"],
                    "question": row[q_col],
                    "answer": row[a_col],
                    "q_type": row.get(f"Q{qn}_Type", ""),
                    "difficulty": row.get(f"Q{qn}_Difficulty", "")
                })
    return rows

all_items = load_qa_items(DATA_FILE)

pilot_items = all_items[:PILOT_COUNT]
rest_items = all_items[PILOT_COUNT:]

def make_segments(items, size, prefix):
    segs = []
    for i in range(0, len(items), size):
        segs.append((f"{prefix}_{len(segs)+1}", items[i:i+size]))
    return segs

pilot_segments = make_segments(pilot_items, SEGMENT_SIZE, "pilot_segment")
main_segments = make_segments(rest_items, SEGMENT_SIZE, "segment")

SEGMENT_MAP = dict(pilot_segments + main_segments)
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
    st.title("🔐 Text QA Annotation Platform")

    name = st.text_input("Your name")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        if pw == PASSWORD and name.strip():
            st.session_state.login_ok = True
            st.session_state.user_temp = name.strip()
        else:
            st.error("Incorrect password or empty name.")

    if st.session_state.get("login_ok"):
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
    pdf_viewer(GUIDELINES_PDF, height=700)
    if not st.session_state.guidelines_ok:
        if st.button("I have read and understood ✔️"):
            st.session_state.guidelines_ok = True
            st.rerun()

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
key_base = f"{segment_name}_{idx}"
saved = st.session_state.annotations.get(key_base, {})

# ======================================================
# SIDEBAR
# ======================================================
with st.sidebar:
    st.subheader("⏭️ Jump to QA")

    jump_number = st.number_input(
        "QA number:",
        min_value=1,
        max_value=N,
        value=idx + 1,
        step=1
    )

    def save_before_jump():
        st.session_state.annotations[key_base] = {
            "uid": item["uid"],
            "segment": segment_name,
            "domain": item["domain"],
            "passage": item["passage"],
            "question": item["question"],
            "gold_answer": item["answer"],
            "is_answerable": st.session_state.get(f"is_answerable_{key_base}"),
            "answer_quality": st.session_state.get(f"answer_quality_{key_base}"),
            "corrected_answer": st.session_state.get(f"corrected_answer_{key_base}"),
            "annotator": st.session_state.user,
            "timestamp": datetime.utcnow().isoformat()
        }

    if st.button("Jump ➡️"):
        st.session_state.idx = jump_number - 1
        st.rerun()

    st.markdown("---")
    st.subheader("📊 Segment Progress")

    completed = 0
    for i in range(N):
        ann = st.session_state.annotations.get(f"{segment_name}_{i}")
        is_current = (i == idx)
        if ann and ann.get("is_answerable") is not None:
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
# MAIN UI
# ======================================================
st.markdown(f"### ❓ QA {idx+1} of {N}")
st.progress((idx + 1) / N)

# Passage
st.markdown("#### 📄 Passage")
with st.container(border=True):
    st.markdown(item["passage"])
    if st.button("🔄 Translate passage"):
        st.info(translate_hi_to_en(item["passage"]))

q_col, a_col = st.columns(2, gap="large")

with q_col:
    st.markdown("### ❓ Question")
    st.markdown(item["question"])
    if st.button("🔄 Translate question"):
        st.info(translate_hi_to_en(item["question"]))

with a_col:
    st.markdown("### 📝 Provided Answer")
    st.markdown(item["answer"])
    if st.button("🔄 Translate answer"):
        st.info(translate_hi_to_en(item["answer"]))

# ======================================================
# ANNOTATION PANEL
# ======================================================
with st.container(border=True):
    st.markdown("### 🧠 QA Verification")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Step 1: Answerability")

        # Step 1
        ans_key = f"is_answerable_{key_base}"
        if saved and ans_key not in st.session_state:
            st.session_state[ans_key] = saved.get("is_answerable")

        is_answerable = st.radio(
            "Is the question answerable from the passage?",
            ["Yes", "No", "Uncertain"],
            key=ans_key
        )

    with col2:
        st.markdown("##### Step 2: Answer Quality")
        # Step 2
        answer_quality = "NA"
        corrected_answer = None

        if is_answerable == "Yes":
            aq_key = f"answer_quality_{key_base}"
            if saved and aq_key not in st.session_state:
                st.session_state[aq_key] = saved.get("answer_quality")

            answer_quality = st.radio(
                "Is the provided answer correct?",
                ["Correct", "Incorrect", "Uncertain"],
                key=aq_key
            )

            if answer_quality == "Incorrect":
                ca_key = f"corrected_answer_{key_base}"
                corrected_answer = st.text_area(
                    "Provide corrected / complete answer in Hindi. (You may use the following website to type in Hindi: https://indiatyping.com/index.php/english-to-hindi-typing)",
                    value=(
                        saved.get("corrected_answer")
                        if isinstance(saved.get("corrected_answer"), str)
                        else ""
                    ),
                    height=80,
                    key=ca_key
                )

# ======================================================
# SAVE / NAVIGATION
# ======================================================
def build_annotation():
    return {
        "uid": item["uid"],
        "segment": segment_name,
        "domain": item["domain"],
        "passage": item["passage"],
        "question": item["question"],
        "gold_answer": item["answer"],
        "is_answerable": st.session_state.get(ans_key),
        "answer_quality": st.session_state.get(f"answer_quality_{key_base}"),
        "corrected_answer": st.session_state.get(f"corrected_answer_{key_base}"),
        "annotator": st.session_state.user,
        "timestamp": datetime.utcnow().isoformat()
    }

prev_col, next_col = st.columns(2)

with prev_col:
    if st.button("⬅️ Previous", disabled=(idx == 0)):
        st.session_state.idx -= 1
        st.rerun()

with next_col:
    if idx < N - 1:
        if st.button("Save & Next ➡️"):
            st.session_state.annotations[key_base] = build_annotation()
            st.session_state.idx += 1
            st.rerun()
    else:
        if st.button("Save & Finish 🎉"):
            st.session_state.annotations[key_base] = build_annotation()
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

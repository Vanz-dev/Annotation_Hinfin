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

DATA_FILE = os.path.join(BASE_DIR, "text_summarization_full_dataset.json")
GUIDELINES_PDF = os.path.join(BASE_DIR, "sum_annotation_guidelines_v1.pdf")

PASSWORD = "TSUMfinance@2025!@#$%"
ADMIN_EMAIL = "Vanshikaa.Jani@mbzuai.ac.ae"

SEGMENT_SIZE = 10
PILOT_COUNT = 40

st.set_page_config(page_title="Text Summarization Annotation", layout="wide")

# ======================================================
# RENDER HELPER (Hindi-friendly)
# ======================================================
def render(text, bg="#FAFAFA"):
    st.markdown(
        f"""
        <div style="
            background-color: {bg};
            padding: 26px 28px;
            border-radius: 14px;
            max-width: 900px;
            margin: auto;
            font-size: 19px;
            line-height: 2.05;
            font-family: 'Noto Sans Devanagari', 'Mangal', 'Kalimati', sans-serif;
            color: #0F172A;
            letter-spacing: 0.015em;
            word-spacing: 0.05em;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        ">
            {text.replace(chr(10), '<br><br>')}
        </div>
        """,
        unsafe_allow_html=True
    )

# ======================================================
# LOAD DATA
# ======================================================
def load_items(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

all_items = load_items(DATA_FILE)

pilot_items = all_items[:PILOT_COUNT]
rest_items = all_items[PILOT_COUNT:]

def make_segments(items, size, prefix):
    segments = []
    for i in range(0, len(items), size):
        segments.append((f"{prefix}_{len(segments)+1}", items[i:i+size]))
    return segments

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
# TRANSLATION (optional)
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
    st.title("🔐 Text Summarization Annotation Platform")

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

# ======================================================
# SIDEBAR
# ======================================================
with st.sidebar:
    st.subheader("⏭️ Jump to Item")

    jump_number = st.number_input(
        "Item number:",
        min_value=1,
        max_value=N,
        value=idx + 1,
        step=1
    )

    def save_before_jump():
        key = f"{segment_name}_{st.session_state.idx}"

        radio_key = f"summary_quality_{segment_name}_{st.session_state.idx}"
        text_key = f"edited_summary_{segment_name}_{st.session_state.idx}"

        st.session_state.annotations[key] = {
            "document_id": item["document_id"],
            "section_id": item["section_id"],
            "segment": segment_name,
            "content": item["content"],
            "original_summary": item["summary"],
            "summary_quality": st.session_state.get(radio_key),
            "edited_summary": st.session_state.get(text_key),
            "method": item.get("method", ""),
            "annotator": st.session_state.user,
            "timestamp": datetime.utcnow().isoformat()
        }


    if st.button("Jump ➡️"):
        save_before_jump()
        st.session_state.idx = jump_number - 1
        st.rerun()

    st.markdown("---")
    st.subheader("📊 Segment Progress")

    completed = 0

    for i in range(N):
        ann = st.session_state.annotations.get(f"{segment_name}_{i}")

        if ann and ann.get("summary_quality") is not None:
            completed += 1
            st.write(f"🟢 {i+1}. {ann['summary_quality']}")
        else:
            st.write(f"⚪ {i+1}. (not done)")

    st.progress(completed / N)
    st.caption(f"{completed}/{N} annotated")

# ======================================================
# MAIN UI
# ======================================================
st.markdown(f"### 📝 Item {idx+1} of {N}")
st.progress((idx+1) / N)

left_col, right_col = st.columns([1.15, 1], gap="large")

# ------------------------------------------------------
# SOURCE CONTENT
# ------------------------------------------------------
with left_col:
    st.markdown("#### 📄 Source Content")
    render(item["content"], bg="#EEF2CB")

    if st.button("🔄 Translate source"):
        st.info(translate_hi_to_en(item["content"]))

# ------------------------------------------------------
# SUMMARY
# ------------------------------------------------------
with right_col:
    st.markdown("#### ✍️ Provided Summary")
    render(item["summary"], bg="#F0CECE")

    if st.button("🔄 Translate summary"):
        st.info(translate_hi_to_en(item["summary"]))

# ======================================================
# ANNOTATION PANEL
# ======================================================
with st.container(border=True):
    st.markdown("### 🧠 Summary Verification")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("##### Step 1: Summary Quality")
        radio_key = f"summary_quality_{segment_name}_{idx}"
        saved = st.session_state.annotations.get(f"{segment_name}_{idx}")

        if saved and radio_key not in st.session_state:
            st.session_state[radio_key] = saved.get("summary_quality")

        summary_quality = st.radio(
        "Is the summary faithful and adequate?",
        ["Yes", "No", "Uncertain"],
        key=f"summary_quality_{segment_name}_{idx}"
        )

    with col2:
        edited_summary = None
        st.markdown("##### Step 2: Edit (if needed)")

        if summary_quality == "No":
            prev = st.session_state.annotations.get(f"{segment_name}_{idx}", {})
            edited_summary = st.text_area(
            "Edit the summary",
            value=(
                prev.get("edited_summary")
                if isinstance(prev.get("edited_summary"), str)
                else item["summary"]
            ),
            height=220,
            key=f"edited_summary_{segment_name}_{idx}"
        )

        elif summary_quality == "Uncertain":
            st.info("Leave the summary unchanged if uncertain.")

# ======================================================
# SAVE / NAVIGATION
# ======================================================
def build_annotation():
    return {
        "document_id": item["document_id"],
        "section_id": item["section_id"],
        "segment": segment_name,
        "content": item["content"],
        "original_summary": item["summary"],
        "summary_quality": st.session_state.get(f"summary_quality_{segment_name}_{idx}"),
        "edited_summary": edited_summary,
        "method": item.get("method", ""),
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

import streamlit as st
import json
import pandas as pd
from datetime import datetime
from deep_translator import GoogleTranslator
from streamlit_pdf_viewer import pdf_viewer
import os


# ================================================
# CONFIG
# ================================================
DATA_FILE = "annotation_SA/s4_data_for_annotation.jsonl"
#DATA_FILE = "s4_data_for_annotation.jsonl"
SEGMENT_SIZE = 20
PILOT_COUNT = 50
PASSWORD = "finance2025SA"
ADMIN_EMAIL = "Vanshikaa.Jani@mbzuai.ac.ae"
GUIDELINES_PDF = "annotation_SA/Sentiment_analysis_annotation_guidelines_v1.pdf"
#GUIDELINES_PDF = "Sentiment_analysis_annotation_guidelines_v1.pdf"


# Light, soothing themes for segments
THEMES = {
    "pilot_segment_1": "#FFF9E8",
    "pilot_segment_2": "#FFF4D8",
    "segment_1": "#F0F7FF",
    "segment_2": "#F4F9FF",
    "segment_3": "#F8FFFB",
    "segment_4": "#FFF7FF",
    "segment_5": "#F9FFF2",
}

DEFAULT_THEME = "#F9FBFF"

st.set_page_config(page_title="Financial Sentiment Annotation", layout="wide")


# ================================================
# LOAD DATA
# ================================================
def load_jsonl(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            items.append(json.loads(line))
    return items


data = load_jsonl(DATA_FILE)

pilot_data = data[:PILOT_COUNT]
rest_data = data[PILOT_COUNT:]


def make_segments(items, size, prefix):
    segs = []
    for i in range(0, len(items), size):
        chunk = items[i:i + size]
        segs.append((f"{prefix}_{len(segs) + 1}", chunk))
    return segs


pilot_segments = make_segments(pilot_data, SEGMENT_SIZE, "pilot_segment")
main_segments = make_segments(rest_data, SEGMENT_SIZE, "segment")

SEGMENT_MAP = {name: items for name, items in (pilot_segments + main_segments)}
SEGMENT_LIST = list(SEGMENT_MAP.keys())


# ================================================
# STATE
# ================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "guidelines_ok" not in st.session_state:
    st.session_state.guidelines_ok = False
if "current_segment" not in st.session_state:
    st.session_state.current_segment = None
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "annotations" not in st.session_state:
    st.session_state.annotations = {}  # uid → record


# ================================================
# TRANSLATION HELPER
# ================================================
def translate_hi_to_en(text):
    try:
        return GoogleTranslator(source="hi", target="en").translate(text)
    except Exception as e:
        return f"(Translation error: {e})"


# ================================================
# LOGIN
# ================================================
if not st.session_state.logged_in:
    st.title("🔐 Finance Sentiment Annotation Platform")

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




# ================================================
# GUIDELINES (PDF VIEWER)
# ================================================
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


# ================================================
# SEGMENT SELECTION
# ================================================
st.subheader("🧩 Select Segment")
segment_name = st.selectbox(
    "Choose a segment",
    ["-- Select --"] + SEGMENT_LIST
)

if segment_name == "-- Select --":
    st.stop()

if segment_name != st.session_state.current_segment:
    st.session_state.current_segment = segment_name
    st.session_state.idx = 0

items = SEGMENT_MAP[segment_name]
N = len(items)
idx = st.session_state.idx

# Apply theme
theme_color = THEMES.get(segment_name, DEFAULT_THEME)
st.markdown(
    f"""
<style>
.stApp {{
    background-color: {theme_color};
}}
</style>
""",
    unsafe_allow_html=True,
)

st.warning("⚠️ Make sure you save your work after each segment by downloading the CSV before leaving.")

# ================================================
# SIDEBAR PROGRESS OVERVIEW + JUMP
# ================================================
with st.sidebar:

    st.subheader("⏭️ Jump to Fact")

    # Input is 1-based for annotators
    jump_number = st.number_input(
        "Fact number:",
        min_value=1,
        max_value=N,
        value=st.session_state.idx + 1,
        step=1,
        key="jump_input_sidebar"
    )

    # Save before jump
    def _save_before_jump():
        uid_j = items[st.session_state.idx]["uid"]
        prev = st.session_state.annotations.get(uid_j, {})
        response = prev.get("response")
        corrected_sent = prev.get("corrected_sentiment")
        used_translation = prev.get("used_translation", False)

        st.session_state.annotations[uid_j] = {
            "uid": uid_j,
            "segment": segment_name,
            "fact": items[st.session_state.idx]["raw_fact"],
            "predicted_sentiment": items[st.session_state.idx]["sentiment"],
            "response": response,
            "corrected_sentiment": corrected_sent,
            "used_translation": used_translation,
            "annotator": st.session_state.user,
            "timestamp": datetime.utcnow().isoformat()
        }

    if st.button("Jump ➡️", key="jump_btn_sidebar"):
        _save_before_jump()
        st.session_state.idx = jump_number - 1  # convert 1-based to 0-based
        st.rerun()

    st.markdown("---")
    st.header("📊 Segment Progress")

    completed = 0
    for i, it in enumerate(items):
        ann = st.session_state.annotations.get(it["uid"])
        if ann and ann.get("response") is not None:
            completed += 1
            st.write(f"🟢 {i+1}. {ann['response']}")
        else:
            st.write(f"⚪ {i+1}. (not done)")

    st.progress(completed / N)
    st.caption(f"{completed}/{N} annotated")

    st.markdown("---")


# ================================================
# MAIN ANNOTATION UI
# ================================================
item = items[idx]
uid = item["uid"]
fact = item["raw_fact"]
sent = item["sentiment"]

# Emoji for sentiment
emoji = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}.get(sent, "⚪")

# Show current fact number and progress bar
st.markdown(f"### 📌 Fact {idx+1} of {N}")
st.progress((idx + 1) / N)

left, right = st.columns([3, 2])

# FACT CARD
with left:
    st.caption("Read the fact and judge whether the assigned sentiment matches its financial impact.")
    fact_card_html = f"""
<div style="padding:20px;
            border-radius:12px;
            background:white;
            border:1px solid #e5e7eb;
            font-family:Inter, sans-serif;
            box-shadow:0 2px 8px rgba(0,0,0,0.06);
            margin-bottom:18px;">

<h4 style="font-size:20px; color:#111827; margin-bottom:10px;">📄 Fact</h4>

<p style="font-size:18px; line-height:1.6; color:#1f2937;">
{fact}
</p>

<hr style="margin:18px 0; border:0.5px solid #e5e7eb;">

<h4 style="font-size:18px; color:#111827; margin-bottom:6px;">🎯 Assigned Sentiment</h4>

<p style="font-size:20px; margin:0;">
{emoji} <b>{sent}</b>
</p>

</div>
"""
    st.markdown(fact_card_html, unsafe_allow_html=True)

    # ============================================================
    # 🔄 TRANSLATION FEATURE — Appears Under the Fact Card
    # ============================================================
    if st.button("🔄 Translate to English", key=f"translate_{uid}"):
        translated = translate_hi_to_en(fact)

        # Log translation usage for this UID
        prev = st.session_state.annotations.get(uid, {})
        prev["used_translation"] = True
        st.session_state.annotations[uid] = prev

        st.markdown(
            f"""
            <div style='background:#f3f4f6; padding:12px; border-radius:8px;
                        border:1px solid #e5e7eb; margin-top:-10px;
                        font-size:16px; color:#374151;'>
                <b>English Translation (for assistance only):</b><br>
                {translated}
            </div>
            """,
            unsafe_allow_html=True
        )

# REVIEW PANEL
existing = st.session_state.annotations.get(uid, {})

with right:
    st.markdown("### ❓ Is the sentiment accurate?")
    st.caption("Base your answer only on the financial / economic implication of the fact above.")

    # Safe value for response
    existing_response = existing.get("response", "Yes")
    if existing_response not in ["Yes", "No", "I don't know"]:
        existing_response = "Yes"

    choice = st.radio(
        "",
        ["Yes", "No", "I don't know"],
        index=["Yes", "No", "I don't know"].index(existing_response),
    )

    correct_sent = None
    if choice == "No":
        corrected_val = existing.get("corrected_sentiment")
        if corrected_val in ["positive", "negative", "neutral"]:
            corr_index = ["positive", "negative", "neutral"].index(corrected_val)
        else:
            corr_index = 0

        correct_sent = st.selectbox(
            "If no, please select the correct sentiment:",
            ["positive", "negative", "neutral"],
            index=corr_index,
        )

    # ----------------------------------------
    # Save annotation function
    # ----------------------------------------
    def save_current():
        prev = st.session_state.annotations.get(uid, {})
        used_translation = prev.get("used_translation", False)
        corrected = correct_sent if choice == "No" else None

        st.session_state.annotations[uid] = {
            "uid": uid,
            "segment": segment_name,
            "fact": fact,
            "predicted_sentiment": sent,
            "response": choice,
            "corrected_sentiment": corrected,
            "used_translation": used_translation,
            "annotator": st.session_state.user,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # NAV BUTTONS

    prev_col, next_col = st.columns(2)

    with prev_col:
        if st.button("⬅️ Previous", disabled=(idx == 0)):
            save_current()
            st.session_state.idx -= 1
            st.rerun()

    with next_col:
        if idx < N - 1:
            if st.button("Save & Next ➡️"):
                save_current()
                st.session_state.idx += 1
                st.rerun()
        else:
            if st.button("Save & Finish 🎉"):
                save_current()
                st.success("Segment complete! You may download below.")
                st.rerun()

# ================================================
# DOWNLOAD SECTION
# ================================================
st.markdown("---")
st.subheader("💾 Download Segment")

# Only current segment’s annotations
seg_ann = [
    a for a in st.session_state.annotations.values()
    if a.get("segment") == segment_name
]
df = pd.DataFrame(seg_ann)

st.download_button(
    "⬇️ Download CSV",
    df.to_csv(index=False).encode(),
    file_name=f"{segment_name}_{st.session_state.user}.csv",
)

st.info(f"Either email this file to **{ADMIN_EMAIL}** or upload it on Notion in your page")

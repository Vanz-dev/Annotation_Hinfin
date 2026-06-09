import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_pdf_viewer import pdf_viewer
from PIL import Image

# CONFIG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(
    BASE_DIR,
    "charts_QARs.csv"
)

CHART_FOLDER = os.path.join(
    BASE_DIR,
    "charts"
)

GUIDELINES_PDF = os.path.join(
    BASE_DIR,
    "Chart_QA_annotation_guidelines_v1.pdf"
)

PASSWORD = "7"
ADMIN_EMAIL = "Vanshikaa.Jani@mbzuai.ac.ae"

PILOT_COUNT = 50
SEGMENT_SIZE = 25

st.set_page_config(
    page_title="Chart QAR Annotation",
    layout="wide"
)



# LOAD DATA

@st.cache_data
def load_items(csv_path):

    df = pd.read_csv(csv_path)

    rows = []

    for idx, row in df.iterrows():

        rows.append(
            {
                "uid": f"qar_{idx+1}",
                "file_name": str(row["file_name"]).strip(),
                "qar_number": row["qar_number"],

                "question": row["question_hi"],
                "answer": row["answer_hi"],
                "reasoning": row["reasoning_hi"],

                "domain": row.get("domain", ""),
                "question_type": row.get(
                    "question_type",
                    ""
                )
            }
        )

    return rows


all_items = load_items(DATA_FILE)

# SEGMENTS

pilot_items = all_items[:PILOT_COUNT]
rest_items = all_items[PILOT_COUNT:]


def make_segments(items, size, prefix):

    segs = []

    for i in range(0, len(items), size):

        segs.append(
            (
                f"{prefix}_{len(segs)+1}",
                items[i:i+size]
            )
        )

    return segs


pilot_segments = make_segments(
    pilot_items,
    SEGMENT_SIZE,
    "pilot_segment"
)

main_segments = make_segments(
    rest_items,
    SEGMENT_SIZE,
    "segment"
)

SEGMENT_MAP = dict(
    pilot_segments + main_segments
)

SEGMENT_LIST = list(
    SEGMENT_MAP.keys()
)

# SESSION STATE

defaults = {
    "logged_in": False,
    "guidelines_ok": False,
    "current_segment": None,
    "idx": 0,
    "annotations": {}
}

for k, v in defaults.items():

    if k not in st.session_state:
        st.session_state[k] = v

# LOGIN

if not st.session_state.logged_in:

    st.title(
        "🔐 Chart QAR Annotation Platform"
    )

    name = st.text_input(
        "Your name"
    )

    pw = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Login"):

        if pw == PASSWORD and name.strip():

            st.session_state.login_ok = True
            st.session_state.user_temp = (
                name.strip()
            )

        else:

            st.error(
                "Incorrect password or empty name."
            )

    if st.session_state.get("login_ok"):

        st.success(
            f"Welcome, "
            f"{st.session_state.user_temp}"
        )

        if st.button("Enter Platform"):

            st.session_state.logged_in = True
            st.session_state.user = (
                st.session_state.user_temp
            )

            st.rerun()

    st.stop()

# HEADER

st.title(
    f"👋 Welcome, "
    f"{st.session_state.user}"
)

# GUIDELINES

with st.expander(
    "📘 Annotation Guidelines",
    expanded=not st.session_state.guidelines_ok
):

    pdf_viewer(
        GUIDELINES_PDF,
        height=700
    )

    if not st.session_state.guidelines_ok:

        if st.button(
            "I have read and understood ✔️"
        ):

            st.session_state.guidelines_ok = True
            st.rerun()

if not st.session_state.guidelines_ok:
    st.stop()

# SEGMENT SELECTION

segment_name = st.selectbox(
    "Select Segment",
    ["-- Select --"] + SEGMENT_LIST
)

if segment_name == "-- Select --":
    st.stop()

if (
    segment_name
    != st.session_state.current_segment
):

    st.session_state.current_segment = (
        segment_name
    )

    st.session_state.idx = 0

items = SEGMENT_MAP[segment_name]

N = len(items)

idx = st.session_state.idx

item = items[idx]

key_base = (
    f"{segment_name}_{idx}"
)

saved = (
    st.session_state.annotations.get(
        key_base,
        {}
    )
)

# SIDEBAR

with st.sidebar:

    st.subheader(
        "📊 Segment Progress"
    )

    completed = 0

    for i in range(N):

        ann = (
            st.session_state.annotations.get(
                f"{segment_name}_{i}"
            )
        )

        current = (i == idx)

        if ann:
            completed += 1
            icon = "🟢"
        else:
            icon = "⚪"

        if current:

            st.markdown(
                f"""
                <div style="
                background:#E0F2FE;
                padding:8px;
                font-weight:bold;
                border-left:4px solid #0284C7;
                ">
                {icon} {i+1}
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.write(
                f"{icon} {i+1}"
            )

    st.progress(
        completed / N
    )

    st.caption(
        f"{completed}/{N} completed"
    )

# MAIN

st.markdown(
    f"## QAR {idx+1} of {N}"
)

st.progress(
    (idx + 1) / N
)

# CHART

chart_path = os.path.join(
    CHART_FOLDER,
    item["file_name"]
)

left, right = st.columns([1.5, 1])

with left:

    st.markdown("### 📈 Chart")

    img = Image.open(chart_path)

    st.image(img)

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


with right: 
# QUESTION

    st.markdown("### ❓ Question")

    with st.container(border=True):

        st.write(
            item["question"]
        )

        q_quality = st.radio(
            "Question Quality",
            [
                "Correct",
                "Incorrect",
                "Uncertain"
            ],
            key=f"q_{key_base}"
        )

        corrected_question = ""

        if q_quality == "Incorrect":

            corrected_question = (
                st.text_area(
                    "Corrected Question",
                    key=f"corr_q_{key_base}"
                )
            )

    # ======================================================
    # ANSWER
    # ======================================================

    st.markdown("### 📝 Answer")

    with st.container(border=True):

        st.write(
            item["answer"]
        )

        a_quality = st.radio(
            "Answer Quality",
            [
                "Correct",
                "Incorrect",
                "Uncertain"
            ],
            key=f"a_{key_base}"
        )

        corrected_answer = ""

        if a_quality == "Incorrect":

            corrected_answer = (
                st.text_area(
                    "Corrected Answer",
                    key=f"corr_a_{key_base}"
                )
            )

    # ======================================================
    # REASONING
    # ======================================================

    st.markdown("### 🧠 Reasoning")

    with st.container(border=True):

        st.write(
            item["reasoning"]
        )

        r_quality = st.radio(
            "Reasoning Quality",
            [
                "Correct",
                "Incorrect",
                "Uncertain"
            ],
            key=f"r_{key_base}"
        )

        corrected_reasoning = ""

        if r_quality == "Incorrect":

            corrected_reasoning = (
                st.text_area(
                    "Corrected Reasoning",
                    key=f"corr_r_{key_base}"
                )
            )

# ======================================================
# BUILD ANNOTATION
# ======================================================

def build_annotation():

    return {

        "uid": item["uid"],

        "file_name":
            item["file_name"],

        "qar_number":
            item["qar_number"],

        "domain":
            item["domain"],

        "question_type":
            item["question_type"],

        "original_question":
            item["question"],

        "original_answer":
            item["answer"],

        "original_reasoning":
            item["reasoning"],

        "question_quality":
            q_quality,

        "corrected_question":
            corrected_question,

        "answer_quality":
            a_quality,

        "corrected_answer":
            corrected_answer,

        "reasoning_quality":
            r_quality,

        "corrected_reasoning":
            corrected_reasoning,

        "annotator":
            st.session_state.user,

        "timestamp":
            datetime.utcnow().isoformat()
    }

# ======================================================
# NAVIGATION
# ======================================================

prev_col, next_col = st.columns([1.5, 1])

with prev_col:

    if st.button(
        "⬅️ Previous"
    ):

        if idx > 0:

            st.session_state.idx -= 1
            st.rerun()

with next_col:

    if st.button(
        "Save & Next ➡️"
    ):

        errors = []

        if (
            q_quality == "Incorrect"
            and not corrected_question.strip()
        ):
            errors.append(
                "Provide corrected question."
            )

        if (
            a_quality == "Incorrect"
            and not corrected_answer.strip()
        ):
            errors.append(
                "Provide corrected answer."
            )

        if (
            r_quality == "Incorrect"
            and not corrected_reasoning.strip()
        ):
            errors.append(
                "Provide corrected reasoning."
            )

        if errors:

            for e in errors:
                st.error(e)

        else:

            st.session_state.annotations[
                key_base
            ] = build_annotation()

            if idx < N - 1:

                st.session_state.idx += 1
                st.rerun()

            else:

                st.success(
                    f"🎉 Segment '{segment_name}' completed!"
                )

                st.balloons()

# ======================================================
# DOWNLOAD
# ======================================================

st.markdown("---")

st.subheader(
    "💾 Download Segment Annotations"
)

seg_rows = [

    v

    for v in
    st.session_state.annotations.values()

    if v
]

df = pd.DataFrame(
    seg_rows
)

st.download_button(
    "⬇️ Download CSV",
    df.to_csv(index=False).encode(
        "utf-8"
    ),
    file_name=(
        f"{segment_name}_"
        f"{st.session_state.user}.csv"
    )
)

st.info(
    f"Please send the file to "
    f"{ADMIN_EMAIL}"
)
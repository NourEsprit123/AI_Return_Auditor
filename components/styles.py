import streamlit as st


def apply_styles():

    st.markdown(
        """
        <style>

        /* =====================================================
           GLOBAL
        ===================================================== */

        .stApp {
            background:
                radial-gradient(
                    circle at 0% 0%,
                    rgba(124, 58, 237, 0.10),
                    transparent 28%
                ),
                radial-gradient(
                    circle at 100% 0%,
                    rgba(6, 182, 212, 0.10),
                    transparent 30%
                ),
                linear-gradient(
                    135deg,
                    #f8f9ff 0%,
                    #f4f7ff 50%,
                    #f0f9ff 100%
                );

            color: #172033;
        }


        /* =====================================================
           STREAMLIT TOP HEADER
           ===================================================== */

        header[data-testid="stHeader"] {
            background: transparent !important;
            box-shadow: none !important;
            border: none !important;
        }

        header[data-testid="stHeader"] > div {
            background: transparent !important;
        }

        div[data-testid="stToolbar"] {
            background: transparent !important;
        }

        div[data-testid="stDecoration"] {
            display: none !important;
        }


        /* =====================================================
           MAIN CONTAINER
           ===================================================== */

        .main .block-container {
            max-width: 1320px;
            padding-top: 1.5rem;
            padding-bottom: 5rem;
        }


        /* =====================================================
           TEXT
           ===================================================== */

        h1 {
            font-size: 3.8rem !important;
            line-height: 1.05 !important;
            letter-spacing: -2px !important;
            font-weight: 900 !important;

            background:
                linear-gradient(
                    100deg,
                    #312e81 0%,
                    #7c3aed 45%,
                    #0891b2 100%
                );

            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }


        h2 {
            color: #172033 !important;
            font-size: 2rem !important;
            font-weight: 850 !important;
        }


        h3 {
            color: #1e293b !important;
            font-weight: 800 !important;
        }


        p {
            color: #64748b;
        }


        .stCaption {
            color: #64748b !important;
        }


        /* =====================================================
           NAVIGATION BUTTONS
           ===================================================== */

        .stButton > button {

            min-height: 48px;

            border-radius: 13px;

            border:
                1px solid #e2e8f0;

            background:
                rgba(255, 255, 255, 0.80);

            color: #334155;

            font-weight: 750;

            transition:
                all 0.2s ease;

            box-shadow:
                0 4px 14px
                rgba(30, 41, 59, 0.06);
        }


        .stButton > button:hover {

            transform:
                translateY(-2px);

            border-color:
                #a78bfa;

            color:
                #6d28d9;

            background:
                linear-gradient(
                    135deg,
                    #ffffff,
                    #f5f3ff
                );

            box-shadow:
                0 10px 25px
                rgba(124, 58, 237, 0.13);
        }


        /* =====================================================
           CARDS
           ===================================================== */

        div[data-testid="stVerticalBlockBorderWrapper"] {

            background:
                rgba(255, 255, 255, 0.88) !important;

            border:
                1px solid
                rgba(148, 163, 184, 0.22) !important;

            border-radius:
                20px !important;

            box-shadow:
                0 10px 30px
                rgba(30, 41, 59, 0.07);

            transition:
                all 0.22s ease;
        }


        div[data-testid="stVerticalBlockBorderWrapper"]:hover {

            transform:
                translateY(-4px);

            border-color:
                rgba(124, 58, 237, 0.30) !important;

            box-shadow:
                0 18px 40px
                rgba(30, 41, 59, 0.10),
                0 0 25px
                rgba(124, 58, 237, 0.07);
        }


        /* =====================================================
           METRICS
           ===================================================== */

        div[data-testid="stMetric"] {

            background:
                linear-gradient(
                    145deg,
                    #ffffff,
                    #f7f8ff
                );

            border:
                1px solid
                #e2e8f0;

            border-radius:
                18px;

            padding:
                20px;

            min-height:
                120px;

            box-shadow:
                0 8px 25px
                rgba(30, 41, 59, 0.06);
        }


        div[data-testid="stMetricLabel"] {

            color:
                #64748b !important;

            font-size:
                10px !important;

            font-weight:
                800 !important;

            letter-spacing:
                1.3px !important;
        }


        div[data-testid="stMetricValue"] {

            color:
                #312e81 !important;

            font-size:
                2rem !important;

            font-weight:
                850 !important;
        }


        /* =====================================================
           ALERTS
           ===================================================== */

        div[data-testid="stAlert"] {

            border-radius:
                15px !important;

            border-width:
                1px !important;
        }


        /* =====================================================
           FILE UPLOADER
           ===================================================== */

        div[data-testid="stFileUploader"] {

            background:
                rgba(255, 255, 255, 0.75);

            border:
                1px solid
                #dbe2f0;

            border-radius:
                18px;

            padding:
                10px;

            box-shadow:
                0 8px 25px
                rgba(30, 41, 59, 0.05);
        }


        /* =====================================================
           INPUTS
           ===================================================== */

        div[data-baseweb="input"],
        div[data-baseweb="textarea"],
        div[data-baseweb="select"] {

            background:
                #ffffff !important;

            border-radius:
                12px !important;
        }


        /* =====================================================
           TABS
           ===================================================== */

        button[data-baseweb="tab"] {

            color:
                #64748b !important;

            font-weight:
                700 !important;
        }


        button[data-baseweb="tab"][aria-selected="true"] {

            color:
                #7c3aed !important;
        }


        /* =====================================================
           PROGRESS
           ===================================================== */

        div[data-testid="stProgressBar"] > div > div {

            background:
                linear-gradient(
                    90deg,
                    #7c3aed,
                    #0891b2
                ) !important;
        }


        /* =====================================================
           DIVIDER
           ===================================================== */

        hr {

            border:
                none !important;

            height:
                1px !important;

            margin:
                36px 0 !important;

            background:
                linear-gradient(
                    90deg,
                    transparent,
                    rgba(124,58,237,0.25),
                    rgba(6,182,212,0.25),
                    transparent
                ) !important;
        }


        /* =====================================================
           SIDEBAR IF USED
           ===================================================== */

        section[data-testid="stSidebar"] {

            background:
                linear-gradient(
                    180deg,
                    #ffffff,
                    #f5f3ff
                ) !important;

            border-right:
                1px solid #e2e8f0;
        }


        section[data-testid="stSidebar"] > div {

            background:
                transparent !important;
        }


        /* =====================================================
           MOBILE
           ===================================================== */

        @media (max-width: 900px) {

            h1 {
                font-size:
                    2.7rem !important;
            }

            h2 {
                font-size:
                    1.6rem !important;
            }

            .main .block-container {
                padding-left:
                    1rem;

                padding-right:
                    1rem;
            }
        }

        </style>
        """,
        unsafe_allow_html=True
    )
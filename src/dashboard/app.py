from pathlib import Path
import sys
import streamlit as st
import importlib.util


# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
PAGES_DIR = BASE_DIR / "pages"


# --------------------------------------------------
# ADD PROJECT ROOT TO PYTHON PATH
# --------------------------------------------------

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.title("📊 Nifty 100 Analytics")
st.sidebar.caption("Financial Analytics Dashboard")

st.sidebar.divider()

page_options = {
    "🏠 Home": "01_home.py",
    "🏢 Company Profile": "02_profile.py",
    "🔎 Screener": "03_screener.py",
    "👥 Peer Comparison": "04_peers.py",
    "📈 Trends": "05_trends.py",
    "🏭 Sectors": "06_sectors.py",
    "💰 Capital & Cash Flow": "07_capital.py",
    "📄 Reports": "08_reports.py",
}


selected_page = st.sidebar.radio(
    "Navigation",
    list(page_options.keys()),
)


# --------------------------------------------------
# PAGE LOADER
# --------------------------------------------------

def load_page(page_file):

    page_path = PAGES_DIR / page_file

    if not page_path.exists():
        st.error(f"Page file not found: {page_path}")
        return

    module_name = page_file.replace(".py", "")

    spec = importlib.util.spec_from_file_location(
        module_name,
        page_path,
    )

    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)

        if hasattr(module, "render"):
            module.render()
        else:
            st.warning(
                f"{page_file} loaded, but no render() function was found."
            )

    except Exception as error:
        st.error(f"Error loading {page_file}")
        st.exception(error)


# --------------------------------------------------
# LOAD SELECTED PAGE
# --------------------------------------------------

load_page(page_options[selected_page])
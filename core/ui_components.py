"""Common UI components adhering to the design guideline."""

from typing import Any, Optional

# Streamlit はテスト環境では存在しない可能性があるため寛容に扱う
try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover - テスト時のフォールバック
    st = None

from .constants import COLOR_PALETTE, FONT_STACK


def load_global_styles() -> None:
    """Inject global CSS styles for the application."""
    if st is None:
        return
    st.markdown(
        f"""
        <style>
        body {{
            background-color: {COLOR_PALETTE['background']};
            color: {COLOR_PALETTE['text_primary']};
            font-family: {FONT_STACK};
            font-size: 16px;
            font-weight: 300;
        }}
        h1, h2, h3, h4 {{
            font-weight: 400;
        }}
        .primary-button > button {{
            background-color: {COLOR_PALETTE['primary']} !important;
            color: white !important;
            border: none !important;
            border-radius: 4px !important;
            padding: 0.4rem 1rem;
            font-weight: 400;
        }}
        .primary-button > button:hover {{
            background-color: {COLOR_PALETTE['primary']} !important;
            color: white !important;
        }}
        .input-block {{
            background-color: #f0f2f6;
            padding: 1rem;
            border: none;
            border-radius: 6px;
            margin-bottom: 1rem;
        }}
        .explanation {{
            font-size: 14px;
            color: {COLOR_PALETTE['text_secondary']};
            margin-bottom: 0.5rem;
        }}
        .function-section {{
            background-color: {COLOR_PALETTE['surface']};
            padding: 1rem;
            border: 1px solid {COLOR_PALETTE['divider']};
            border-radius: 8px;
            margin-bottom: 1rem;
        }}
        .explanation-section {{
            background-color: {COLOR_PALETTE['background']};
            padding: 1rem;
            border-left: 4px solid {COLOR_PALETTE['primary']};
            border-radius: 4px;
            font-size: 12px;
            color: {COLOR_PALETTE['text_secondary']};
        }}
        .stMetric {{
            overflow-wrap: anywhere;
        }}
        .stTabs [data-baseweb='tab'] {{
            min-width: 130px;
        }}
        /* Slider color adjustments */
        [data-baseweb='slider'] [role='slider'] {{
            background-color: {COLOR_PALETTE['primary']} !important;
            border-color: {COLOR_PALETTE['primary']} !important;
        }}
        [data-baseweb='slider'] > div > div {{
            background-color: {COLOR_PALETTE['primary']} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def primary_button(label: str, key: Optional[str] = None) -> bool:
    """Create a styled primary button."""
    if st is None:
        return False
    st.markdown("<div class='primary-button'>", unsafe_allow_html=True)
    clicked = st.button(
        label,
        key=key,
        use_container_width=True,
        help=label,
        type="primary",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return clicked


def text_input(label: str, key: Optional[str] = None, **kwargs: Any) -> str:
    """Text input wrapped in a styled block."""
    if st is None:
        return ""
    with st.container():
        st.markdown("<div class='input-block'>", unsafe_allow_html=True)
        value = st.text_input(label, key=key, **kwargs)
        st.markdown("</div>", unsafe_allow_html=True)
        return value


"""Streamlit UI for Aegis: Billing RAG, Weather Advisor, and AC Control."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
from pathlib import Path
import tempfile
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv()

from aegis.billing.answerer import answer_billing_question, inspect_bill
from aegis.billing.config import BillingConfig


def save_uploaded_pdf(file_name: str, file_bytes: bytes, upload_dir: Path | None = None) -> Path:
    """Persist uploaded PDF bytes and return the saved path."""
    target_dir = upload_dir or (Path(tempfile.gettempdir()) / "aegis_streamlit_uploads")
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file_name).name or "uploaded_bill"
    stem = Path(safe_name).stem or "uploaded_bill"
    saved_path = target_dir / f"{stem}_{uuid4().hex}.pdf"
    saved_path.write_bytes(file_bytes)
    return saved_path


def _build_config(store_dir: str, litellm_enabled: bool, litellm_model: str) -> BillingConfig:
    return BillingConfig(
        store_dir=Path(store_dir),
        litellm_enabled=litellm_enabled,
        litellm_model=litellm_model,
    )


def run_streamlit_app() -> None:
    import streamlit as st
    from aegis.core.config import AegisConfig

    st.set_page_config(page_title="Aegis Smart Home", page_icon="A", layout="wide")
    st.title("Aegis Smart Home Assistant")

    with st.sidebar:
        st.subheader("Configuration")
        store_dir = st.text_input("Store directory", value=".billing_store")
        litellm_enabled = True
        litellm_model = "gemini/gemini-2.5-flash"

    tab_billing, tab_weather, tab_ac = st.tabs(["Billing", "Weather Advisor", "AC Control"])

    # ------------------------------------------------------------------
    # Billing tab (unchanged logic)
    # ------------------------------------------------------------------
    with tab_billing:
        st.caption("Single-bill mode: upload one PDF and ask grounded billing questions.")
        uploaded = st.file_uploader("Upload bill PDF", type=["pdf"], key="billing_pdf")
        question = st.text_area(
            "Question",
            placeholder="When was my last electricity bill paid, and what was the amount?",
            key="billing_question",
        )

        saved_pdf_path: str | None = None
        if uploaded is not None:
            payload = uploaded.getvalue()
            payload_hash = hashlib.sha256(payload).hexdigest()
            if st.session_state.get("uploaded_pdf_hash") != payload_hash:
                st.session_state["uploaded_pdf_hash"] = payload_hash
                st.session_state["uploaded_pdf_path"] = str(save_uploaded_pdf(uploaded.name, payload))
            saved_pdf_path = st.session_state.get("uploaded_pdf_path")
            if saved_pdf_path:
                st.info(f"Using PDF: `{saved_pdf_path}`")

        inspect_col, query_col = st.columns(2)

        with inspect_col:
            if st.button("Inspect Bill", use_container_width=True):
                if not saved_pdf_path:
                    st.error("Upload a PDF first.")
                else:
                    try:
                        bill = inspect_bill(saved_pdf_path)
                        st.json(asdict(bill))
                    except Exception as exc:
                        st.error(f"Inspect failed: {exc}")

        with query_col:
            if st.button("Ask Question", type="primary", use_container_width=True):
                if not saved_pdf_path:
                    st.error("Upload a PDF first.")
                elif not question.strip():
                    st.error("Enter a question.")
                else:
                    try:
                        config = _build_config(
                            store_dir=store_dir,
                            litellm_enabled=litellm_enabled,
                            litellm_model=litellm_model,
                        )
                        answer = answer_billing_question(
                            question=question.strip(),
                            config=config,
                            pdf_path=saved_pdf_path,
                        )
                        st.subheader("Answer")
                        st.write(answer.answer_text)
                        if answer.resolved_fields:
                            st.subheader("Resolved fields")
                            st.json(answer.resolved_fields)
                        if answer.evidence:
                            st.subheader("Evidence")
                            st.json(answer.evidence)
                    except Exception as exc:
                        st.error(f"Query failed: {exc}")

    # ------------------------------------------------------------------
    # Weather Advisor tab
    # ------------------------------------------------------------------
    with tab_weather:
        st.caption("Ask a weather question for any city. Set INDIANAPI_KEY in your environment for live data.")
        city_input = st.text_input("City", value="Delhi", key="weather_city")
        weather_question = st.text_area(
            "Weather question",
            placeholder="Should I carry an umbrella today?",
            key="weather_question",
        )

        if st.button("Get Weather Advice", type="primary", use_container_width=True):
            if not weather_question.strip():
                st.error("Enter a question.")
            else:
                try:
                    from aegis.weather.fetcher import fetch_weather
                    from aegis.weather.advisor import advise_weather

                    aegis_config = AegisConfig(litellm_model=litellm_model)
                    weather = fetch_weather(city_input.strip() or "Delhi", aegis_config)

                    if weather.is_mock:
                        st.warning(
                            "Live weather unavailable (INDIANAPI_KEY not set or API error). "
                            "Showing sample data — temperatures/conditions are illustrative only."
                        )

                    st.subheader("Current Conditions")
                    st.json({
                        "city": weather.city,
                        "temp_c": weather.temp_c,
                        "description": weather.description,
                        "rain_3h_mm": weather.rain_3h,
                        "humidity_pct": weather.humidity,
                    })

                    recommendation = advise_weather(weather, weather_question.strip(), aegis_config)
                    st.subheader("Recommendation")
                    st.write(recommendation)
                except Exception as exc:
                    st.error(f"Weather query failed: {exc}")

    # ------------------------------------------------------------------
    # AC Control tab
    # ------------------------------------------------------------------
    with tab_ac:
        st.caption("Control the AC using natural language. Start the mock server first: `uv run aegis-ac-server`")
        ac_input = st.text_area(
            "AC command",
            placeholder="It's getting really hot in here",
            key="ac_input",
        )

        if st.button("Send AC Command", type="primary", use_container_width=True):
            if not ac_input.strip():
                st.error("Enter a command.")
            else:
                try:
                    from aegis.ac_control.classifier import classify_ac_intent
                    from aegis.ac_control.client import execute_ac_command
                    import httpx

                    aegis_config = AegisConfig(litellm_model=litellm_model)
                    intent = classify_ac_intent(ac_input.strip(), aegis_config)
                    st.info(f"Detected intent: **{intent}**")

                    result = execute_ac_command(intent, aegis_config)
                    st.subheader("Result")
                    st.write(result.confirmation_text)

                    # Show current AC status if server is reachable
                    try:
                        status_resp = httpx.get(
                            f"{aegis_config.ac_server_base_url}/ac/status", timeout=2.0
                        )
                        status_resp.raise_for_status()
                        st.json(status_resp.json())
                    except Exception:
                        st.caption("(Could not fetch live AC status — is the mock server running?)")

                except Exception as exc:
                    st.error(f"AC command failed: {exc}")


def main() -> None:
    """CLI entry point — launches Streamlit properly."""
    import sys
    from streamlit.web.cli import main as st_main

    sys.argv = ["streamlit", "run", __file__]
    st_main()


if __name__ == "__main__":
    run_streamlit_app()

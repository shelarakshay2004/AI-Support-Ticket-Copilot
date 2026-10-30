
import os

import requests
import streamlit as st


# Local development default; Docker Compose overrides this environment variable.
API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

API_URL = f"{API_BASE_URL}/tickets"

ALLOWED_STATUSES = [
    "received",
    "in_progress",
    "resolved",
    "escalated",
]


st.set_page_config(
    page_title="AI Support Ticket Copilot",
    page_icon="🎫",
    layout="centered",
)

st.title("🎫 AI Support Ticket Copilot")
st.write(
    "Submit a support ticket to classify the issue, retrieve relevant "
    "FAQs, draft a support reply, and determine whether human review is needed."
)

if "status_update_notice" in st.session_state:
    st.success(st.session_state.pop("status_update_notice"))


def get_error_detail(response):
    """Return a readable API error without hiding the original status."""
    try:
        body = response.json()
        return body.get("detail", body)
    except ValueError:
        return response.text or "Unknown API error"


def fetch_tickets(limit=20):
    """Fetch saved tickets from the FastAPI backend."""
    response = requests.get(
        API_URL,
        params={"limit": limit},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


# ---------------- Submit Ticket ----------------

st.header("📝 Submit a Support Ticket")

with st.form("ticket_form"):
    subject = st.text_input(
        "Ticket subject",
        placeholder="Cannot log into my account",
    )

    message = st.text_area(
        "Describe your problem",
        placeholder="Explain what happened and what you have tried...",
        height=150,
    )

    category_choice = st.selectbox(
        "Category hint (optional)",
        ["None", "billing", "technical", "account", "general"],
    )

    submitted = st.form_submit_button(
        "Analyze Ticket",
        type="primary",
        use_container_width=True,
    )


if submitted:
    if len(subject.strip()) < 5:
        st.error("Subject must contain at least 5 characters.")

    elif len(message.strip()) < 10:
        st.error("Please describe your issue in at least 10 characters.")

    else:
        payload = {
            "subject": subject.strip(),
            "message": message.strip(),
            "category_hint": (
                None if category_choice == "None" else category_choice
            ),
        }

        try:
            with st.spinner(
                "Searching FAQs and analyzing your ticket..."
            ):
                response = requests.post(
                    API_URL,
                    json=payload,
                    timeout=180,
                )
                response.raise_for_status()
                result = response.json()

            st.success("Ticket analysis completed!")
            st.caption(f"Ticket ID: {result['ticket_id']}")

            if result["status"] == "escalated":
                st.warning("Human support review is recommended.")
            else:
                st.info(f"Ticket status: {result['status']}")

            analysis = result["analysis"]

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Category",
                    analysis["category"].title(),
                )
                st.metric(
                    "Priority",
                    analysis["priority"].title(),
                )

            with col2:
                st.metric(
                    "Human escalation",
                    "Yes" if analysis["should_escalate"] else "No",
                )

            st.subheader("Issue Summary")
            st.write(analysis["summary"])

            st.subheader("Suggested Support Reply")
            st.write(analysis["suggested_reply"])

            if analysis.get("escalation_reason"):
                st.subheader("Escalation Reason")
                st.write(analysis["escalation_reason"])

            st.caption(
                "AI-generated suggestions may need human review."
            )

        except requests.exceptions.HTTPError as exc:
            st.error(
                f"API error ({exc.response.status_code}): "
                f"{get_error_detail(exc.response)}"
            )

        except requests.exceptions.Timeout:
            st.error(
                "Ticket analysis timed out. Check the FastAPI terminal "
                "to see whether Gemini is still processing."
            )

        except requests.exceptions.ConnectionError:
            st.error(
                f"Cannot connect to FastAPI at {API_BASE_URL}. "
                "Make sure the backend is running."
            )

        except requests.exceptions.RequestException as exc:
            st.error(f"Request failed: {exc}")

        except (KeyError, ValueError) as exc:
            st.error(f"The API returned an unexpected response: {exc}")


# ---------------- Ticket History ----------------

st.divider()
st.header("📋 Ticket History")

if st.button(
    "Load / Refresh Ticket History",
    use_container_width=True,
):
    try:
        with st.spinner("Loading saved tickets..."):
            history_data = fetch_tickets(limit=20)

        tickets = history_data.get("tickets", [])

        if not tickets:
            st.info("No tickets have been saved yet.")

        else:
            st.success(f"Found {history_data['count']} saved ticket(s).")

            for ticket in tickets:
                with st.expander(
                    f"{ticket['subject']} — {ticket['status'].upper()}"
                ):
                    st.caption(f"Ticket ID: {ticket['ticket_id']}")
                    st.caption(f"Created at: {ticket['created_at']}")

                    st.write("**Customer message**")
                    st.write(ticket["message"])

                    analysis = ticket.get("analysis", {})

                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric(
                            "Category",
                            analysis.get("category", "Unknown").title(),
                        )

                    with col2:
                        st.metric(
                            "Priority",
                            analysis.get("priority", "Unknown").title(),
                        )

                    st.write("**Issue Summary**")
                    st.write(
                        analysis.get("summary", "No summary available.")
                    )

                    st.write("**Suggested Support Reply**")
                    st.write(
                        analysis.get(
                            "suggested_reply",
                            "No suggested reply available.",
                        )
                    )

                    if analysis.get("should_escalate"):
                        st.warning("Human support review is recommended.")

                    reason = analysis.get("escalation_reason")
                    if reason:
                        st.write("**Escalation Reason**")
                        st.write(reason)

    except requests.exceptions.HTTPError as exc:
        st.error(
            f"History API error ({exc.response.status_code}): "
            f"{get_error_detail(exc.response)}"
        )

    except requests.exceptions.Timeout:
        st.error("Ticket history request timed out.")

    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to FastAPI. Start the backend first.")

    except requests.exceptions.RequestException as exc:
        st.error(f"Could not load ticket history: {exc}")

    except (ValueError, KeyError) as exc:
        st.error(f"Unexpected ticket history response: {exc}")


# ---------------- Update Ticket Status ----------------

st.divider()
st.header("🛠️ Update Ticket Status")

try:
    status_history = fetch_tickets(limit=100)
    saved_tickets = status_history.get("tickets", [])

    if not saved_tickets:
        st.info("No saved tickets available to update.")

    else:
        ticket_options = {
            (
                f"{ticket['subject']} | "
                f"{ticket['status']} | "
                f"{ticket['ticket_id']}"
            ): ticket
            for ticket in saved_tickets
        }

        selected_label = st.selectbox(
            "Select a ticket",
            options=list(ticket_options.keys()),
            key="status_ticket_select",
        )

        selected_ticket = ticket_options[selected_label]
        ticket_id = selected_ticket["ticket_id"]
        current_status = selected_ticket["status"]

        selected_status = st.selectbox(
            "Choose new status",
            options=ALLOWED_STATUSES,
            index=(
                ALLOWED_STATUSES.index(current_status)
                if current_status in ALLOWED_STATUSES
                else 0
            ),
            key=f"status_select_{ticket_id}_{current_status}",
        )

        st.caption(f"Current status: {current_status}")

        if st.button(
            "Update Ticket Status",
            type="primary",
            use_container_width=True,
        ):
            if selected_status == current_status:
                st.info("Ticket already has this status.")

            else:
                update_response = requests.patch(
                    f"{API_URL}/{ticket_id}/status",
                    json={"status": selected_status},
                    timeout=15,
                )
                update_response.raise_for_status()

                st.session_state["status_update_notice"] = (
                    f"Ticket status updated to: {selected_status}"
                )
                st.rerun()

except requests.exceptions.HTTPError as exc:
    st.error(
        f"Ticket status API error ({exc.response.status_code}): "
        f"{get_error_detail(exc.response)}"
    )

except requests.exceptions.Timeout:
    st.error("Ticket status request timed out.")

except requests.exceptions.ConnectionError:
    st.error("Cannot connect to FastAPI. Start the backend first.")

except requests.exceptions.RequestException as exc:
    st.error(f"Could not load or update tickets: {exc}")

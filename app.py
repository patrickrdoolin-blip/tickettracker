import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timezone
from tickettracker.store import Store
from tickettracker.alerts import send_price_alert

st.set_page_config(page_title="TicketTracker", page_icon="🎟️", layout="wide")

def get_secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

# Optional shared-password gate for a hosted personal dashboard.
app_password = get_secret("APP_PASSWORD")
if app_password:
    if not st.session_state.get("authenticated"):
        st.title("🎟️ TicketTracker")
        entered = st.text_input("Dashboard password", type="password")
        if st.button("Unlock", type="primary"):
            if entered == app_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("That password wasn't correct.")
        st.stop()

@st.cache_resource
def get_store():
    return Store()

store = get_store()

st.title("🎟️ TicketTracker")
st.caption("Track event ticket prices across marketplaces. This first version records price snapshots you enter; it does not scrape ticket sites.")
st.info("Monitoring mode: add an event URL, then record prices when you check the listing. Automated live inventory access is not available for every marketplace and is not enabled in this MVP.")

events = store.list_events()
snapshots = store.list_snapshots()
alerts = store.list_alerts()

total_events = len(events)
latest_prices = snapshots.sort_values("checked_at").groupby("event_id").tail(1) if not snapshots.empty else snapshots
price_drops = len(alerts)
c1, c2, c3 = st.columns(3)
c1.metric("Tracked listings", total_events)
c2.metric("Price checks", len(snapshots))
c3.metric("Price alerts", price_drops)

tab_dashboard, tab_add, tab_prices, tab_alerts, tab_setup = st.tabs(
    ["Dashboard", "Add listing", "Record a price", "Alerts", "Setup & limitations"]
)

with tab_dashboard:
    st.subheader("Your tracked listings")
    if events.empty:
        st.write("No listings yet. Add a marketplace URL to get started.")
    else:
        view = events.copy()
        if not latest_prices.empty:
            lp = latest_prices[["event_id", "price", "currency", "checked_at"]].rename(
                columns={"price":"latest_price", "currency":"currency", "checked_at":"last_checked"}
            )
            view = view.merge(lp, left_on="id", right_on="event_id", how="left")
            view["latest_price"] = view["latest_price"].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "—")
        else:
            view["latest_price"] = "—"
            view["last_checked"] = None
        cols = [c for c in ["event_name", "event_date", "city", "platform", "latest_price", "currency", "target_price", "last_checked", "url"] if c in view.columns]
        st.dataframe(view[cols], use_container_width=True, hide_index=True)
        selected = st.selectbox("View price history", options=events["id"].tolist(),
                                format_func=lambda x: events.loc[events.id == x, "event_name"].iloc[0])
        hist = snapshots[snapshots.event_id == selected].copy()
        if not hist.empty:
            hist["checked_at"] = pd.to_datetime(hist["checked_at"])
            fig = px.line(hist.sort_values("checked_at"), x="checked_at", y="price",
                          markers=True, title="Recorded ticket price history",
                          hover_data=["platform", "section", "notes"])
            fig.update_layout(yaxis_title="Price", xaxis_title="Date checked")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No price history for this listing yet.")

with tab_add:
    st.subheader("Add a listing")
    with st.form("add_event_form", clear_on_submit=True):
        event_name = st.text_input("Event name", placeholder="e.g. Example Band — St. Louis")
        event_date = st.date_input("Event date", value=date.today())
        city = st.text_input("City / venue area")
        platform = st.selectbox("Marketplace", ["Ticketmaster", "StubHub", "SeatGeek", "Vivid Seats"])
        url = st.text_input("Direct event or ticket listing URL", placeholder="https://…")
        target_price = st.number_input("Alert me at or below (optional)", min_value=0.0, value=0.0, step=5.0)
        currency = st.selectbox("Currency", ["USD", "CAD", "GBP", "EUR", "AUD"])
        submitted = st.form_submit_button("Save listing", type="primary")
        if submitted:
            if not event_name.strip() or not url.strip().startswith(("https://", "http://")):
                st.error("Enter an event name and a valid http(s) URL.")
            else:
                store.add_event({
                    "event_name": event_name.strip(), "event_date": str(event_date),
                    "city": city.strip(), "platform": platform, "url": url.strip(),
                    "target_price": float(target_price) if target_price > 0 else None,
                    "currency": currency
                })
                st.success("Listing saved.")
                st.rerun()

with tab_prices:
    st.subheader("Record a price check")
    if events.empty:
        st.write("Add a listing first.")
    else:
        with st.form("price_form", clear_on_submit=True):
            event_id = st.selectbox("Listing", events["id"].tolist(),
                format_func=lambda x: f"{events.loc[events.id == x, 'event_name'].iloc[0]} — {events.loc[events.id == x, 'platform'].iloc[0]}")
            price = st.number_input("Current lowest comparable ticket price", min_value=0.01, value=50.0, step=1.0)
            section = st.text_input("Section / seat details (optional)")
            notes = st.text_input("Notes (optional; e.g. 2 tickets, fees included)")
            checked = st.form_submit_button("Save price check", type="primary")
            if checked:
                ev = events[events.id == event_id].iloc[0].to_dict()
                store.add_snapshot({
                    "event_id": event_id, "price": float(price), "currency": ev.get("currency", "USD"),
                    "platform": ev["platform"], "section": section.strip(), "notes": notes.strip(),
                    "checked_at": datetime.now(timezone.utc).isoformat()
                })
                target = ev.get("target_price")
                if target is not None and float(price) <= float(target):
                    sent = send_price_alert(ev, float(price), get_secret)
                    store.add_alert({
                        "event_id": event_id, "price": float(price),
                        "message": f"Target reached: {ev['event_name']} is {price:.2f} {ev.get('currency','USD')} on {ev['platform']}.",
                        "email_sent": bool(sent), "created_at": datetime.now(timezone.utc).isoformat()
                    })
                    st.success("Price saved. Your target price was reached.")
                    if not sent:
                        st.caption("Email was not sent; configure SMTP settings under Setup.")
                else:
                    st.success("Price check saved.")
                st.rerun()

with tab_alerts:
    st.subheader("Price alerts")
    if alerts.empty:
        st.write("No target-price alerts yet. Set a target when adding a listing.")
    else:
        st.dataframe(alerts.sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)

with tab_setup:
    st.subheader("Configuration")
    st.markdown("""
**Local run**
1. Install Python 3.10 or newer.
2. In the project folder, run `pip install -r requirements.txt`.
3. Run `streamlit run app.py`.

**Hosted deployment**
1. Create a GitHub repository and upload this project.
2. Create a free Streamlit Community Cloud account and deploy `app.py`.
3. For persistent hosted storage, create a Supabase project, run `supabase_schema.sql` in its SQL editor, then add the Supabase URL and key in Streamlit app secrets.
4. Add an `APP_PASSWORD` secret before sharing the hosted URL.

**Email**
Configure SMTP values in Streamlit secrets. Use an app-specific SMTP credential where your email provider supports it. Never put credentials in source code or commit `secrets.toml` to GitHub.
""")
    st.code("""SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_OR_PUBLISHABLE_KEY"
APP_PASSWORD = "choose-a-long-unique-password"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-sender@example.com"
SMTP_PASSWORD = "your-app-specific-password"
ALERT_TO = "your-recipient@example.com"
""", language="toml")
    st.markdown("""
**What works now**
- Add and manage event marketplace links.
- Record price observations and chart price history.
- Set a target price and create dashboard alerts.
- Send email when a newly recorded price meets the target, if SMTP is configured.
- Store data in Supabase when configured; use local SQLite for local testing.

**What is not automated yet**
- The app does not read live ticket prices from the four marketplaces. Ticketmaster's public Discovery API is primarily event discovery, not a guaranteed live-price feed. SeatGeek's published API documentation says it does not expose individual ticket listings. StubHub access requires authenticated API access, and Vivid Seats has no verified public inventory integration in this starter. Each connector needs approved access and a documented price endpoint before automatic polling can be enabled.
- The dashboard is hosted free, but it may sleep when inactive. Supabase's free plan can pause projects after a week of low activity. Free tiers and terms can change.
""")
    st.caption("This is a personal tracking tool, not a ticket seller or checkout service.")

st.divider()
st.caption("TicketTracker MVP • No paid services required for local use. Hosted persistence and email depend on free-tier account limits.")

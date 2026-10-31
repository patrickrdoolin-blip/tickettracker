# TicketTracker MVP

A free, self-hostable dashboard for manually tracking ticket prices across Ticketmaster, StubHub, SeatGeek and Vivid Seats.

## Current capabilities

- Add event listings by pasting marketplace URLs.
- Record price snapshots, sections and notes.
- View price history charts.
- Set target prices and create dashboard alerts.
- Optional email alerts through SMTP.
- Local SQLite storage for local development.
- Supabase storage for hosted persistence.

## Important scope note

This MVP does **not** automatically scrape or poll live prices. It records price checks entered by the user. Do not assume a marketplace URL can be queried for inventory. Add an automated connector only after confirming that the marketplace offers approved API access and a suitable price endpoint.

Ticketmaster's public Discovery API is designed for event discovery; inventory/seat pricing APIs require separate authorization. SeatGeek's published API docs state that individual ticket listings are not exposed. StubHub API calls require OAuth authentication. A public Vivid Seats inventory API has not been confirmed for this starter.

## Run locally

Python 3.10+:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

SQLite is created automatically as `tickettracker.db`.

## Deploy for free

1. Create a GitHub repository and upload the project files.
2. Sign in to Streamlit Community Cloud with GitHub.
3. Create an app, choose the repository, branch, and `app.py`.
4. For hosted persistence, create a Supabase free project and run `supabase_schema.sql` in its SQL editor.
5. In Streamlit app settings, add the secrets below.
6. Set `APP_PASSWORD` before sharing the app.

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SERVER_SIDE_KEY"
APP_PASSWORD = "a-long-unique-password"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "sender@example.com"
SMTP_PASSWORD = "your-app-specific-smtp-password"
ALERT_TO = "recipient@example.com"
```

Use a server-side Supabase key only in Streamlit secrets. Never commit secrets to GitHub. Because the app uses a server-side key for this single-owner MVP, keep the dashboard password enabled and do not share the URL publicly. For multiple users, implement Supabase Auth and per-user row-level security first.

## Free-tier caveats

- Streamlit Community Cloud is free but can hibernate apps after inactivity.
- Supabase Free can pause low-activity projects; keep independent backups of important data.
- SMTP providers impose sending limits and may require app-specific credentials.
- Free plans, quotas and provider terms can change.

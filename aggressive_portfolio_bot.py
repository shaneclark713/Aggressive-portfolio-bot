# --- TELEGRAM BOT ---
TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
TELEGRAM_CHAT_ID="your_telegram_chat_id_here"

# --- APP CONFIG ---
APP_TIMEZONE="America/Phoenix"
DATABASE_PATH="database/trading_bot.sqlite3"

# --- ROBINHOOD (OPTIONS/EQUITY) ---
RH_USERNAME="your_robinhood_email"
RH_PASSWORD="your_robinhood_password"
# (Optional) If you use MFA, we will need a TOTP setup in the robinhood.py file later
RH_MFA_CODE="your_mfa_code_if_needed"

# --- PROP FIRM (FUTURES) ---
# Replace with Tradovate, NinjaTrader, or whichever firm's API keys you use
PROP_FIRM_API_KEY="your_prop_firm_api_key"
PROP_FIRM_SECRET="your_prop_firm_secret"

# --- DATA & NEWS APIs ---
# (e.g., Finnhub, Polygon, or Benzinga)
NEWS_API_KEY="your_news_api_key_here"

# --- GOOGLE SHEETS (LEDGER) ---
GOOGLE_SHEETS_CREDENTIALS_PATH="config/google_credentials.json"
SPREADSHEET_ID="your_google_sheet_id_here"

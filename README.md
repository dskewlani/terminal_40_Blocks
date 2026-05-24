# ⚡ ProTrader Terminal v2.0

> **NSE + MCX | Angel One SmartAPI | 40 Blocks | 200+ Features | Zero Hardcoding**

A professional-grade algorithmic trading terminal built in Streamlit, covering all 5 market segments — Equity, Options, Futures, MCX, and ETF — with full auto-trading, backtesting, ML prediction, and institutional-grade analytics.

---

## 🚀 Features (40 Blocks)

| Block | Feature | Status |
|-------|---------|--------|
| 1 | Dynamic Symbol Universe (Zero Hardcoding) | ✅ |
| 2 | Five Segment Watchlists | ✅ |
| 3 | Full Universe Scanner + Progress Meter | ✅ |
| 4 | Auto-Trading: Equity | ✅ |
| 5 | Auto-Trading: Options | ✅ |
| 6 | Auto-Trading: Futures | ✅ |
| 7 | Auto-Trading: MCX | ✅ |
| 8 | Auto-Trading: ETF | ✅ |
| 9 | Signal Accuracy (MTF, VWAP, Regime) | ✅ |
| 10 | Execution (Bracket, GTT, Scale-out) | ✅ |
| 11 | Light/Dark Theme — Zero Errors | ✅ |
| 12 | Pre-Market & Post-Market Intelligence | ✅ |
| 13 | Options Intelligence (Max Pain, PCR, IV) | ✅ |
| 14 | Capital & Fund Management | ✅ |
| 15 | Smart Alerts & Notifications | ✅ |
| 16 | Backtesting Engine + Walk-Forward | ✅ |
| 17 | Advanced Analytics & Risk (VaR, Monte Carlo) | ✅ |
| 18 | Market Intelligence (Sectors, FII/DII, Global) | ✅ |
| 19 | Screening & Discovery (52W, Gap&Go, Squeeze) | ✅ |
| 20 | Order Management | ✅ |
| 21 | Psychology & Discipline Tools | ✅ |
| 22 | Trade Journal Intelligence (AI-powered) | ✅ |
| 23 | Tax & Compliance (ITR-3, F&O Turnover) | ✅ |
| 24 | Infrastructure & Performance | ✅ |
| 25 | Paper Trading Mode (Full Simulation) | ✅ |
| 26 | Multi-User Support | ✅ |
| 27 | Advanced Chart Features + Volume Profile | ✅ |
| 28 | Smart Money & Institutional Tracking | ✅ |
| 29 | News & Sentiment Intelligence (AI) | ✅ |
| 30 | Advanced Risk Controls (Greeks, Black Swan) | ✅ |
| 31 | Quantitative Strategy Tools + Kelly | ✅ |
| 32 | Live Market Microstructure | ✅ |
| 33 | Portfolio Optimization (Efficient Frontier) | ✅ |
| 34 | Communication & Sharing (Email, WhatsApp) | ✅ |
| 35 | Accessibility & UX Polish | ✅ |
| 36 | Audit & Compliance Trail | ✅ |
| 37 | Performance Benchmarking (Alpha, Beta) | ✅ |
| 38 | Advanced Notification Channels | ✅ |
| 39 | Data Intelligence & ML (Random Forest) | ✅ |
| 40 | Developer & Power User Tools | ✅ |

---

## 📁 File Structure

```
protrader/
├── app.py              # Main Streamlit app (all 40 blocks UI)
├── engine.py           # Market data, indicators, signals, ML, risk
├── storage.py          # PostgreSQL + JSON fallback, all persistence
├── ui.py               # CSS themes, chart builders, components
├── backtest.py         # Backtesting engine, walk-forward optimization
├── report.py           # PDF/HTML reports, email, WhatsApp
├── requirements.txt    # All dependencies
├── .env.example        # Environment variables template
└── .streamlit/
    └── config.toml     # Streamlit theme config
```

---

## ⚡ Quick Start

### Option A — Local (Recommended for first run)

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/protrader-terminal.git
cd protrader-terminal

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your Angel One credentials

# 5. Run
streamlit run app.py
```

Open: **http://localhost:8501**
Default login: **admin / 123456**

---

### Option B — Streamlit Cloud (Free hosting)

1. Fork this repo on GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set `app.py` as the main file
5. Add secrets in Streamlit Cloud dashboard:

```toml
# .streamlit/secrets.toml (in Streamlit Cloud dashboard)
ANGEL_API_KEY = "your_api_key"
ANGEL_CLIENT_ID = "your_client_id"
ANGEL_PASSWORD = "your_password"
ANGEL_TOTP_SECRET = "your_totp_secret"
ANTHROPIC_API_KEY = "your_anthropic_key"
DATABASE_URL = "postgresql://user:pass@host:5432/protrader"
ADMIN_PIN = "your_6_digit_pin"
```

---

### Option C — Docker

```bash
docker build -t protrader .
docker run -p 8501:8501 --env-file .env protrader
```

---

## 🗄️ Database Setup

### PostgreSQL (Production)

```bash
# Install PostgreSQL and create database
createdb protrader
export DATABASE_URL="postgresql://postgres:password@localhost:5432/protrader"
```

Tables are auto-created on first run.

### JSON Fallback (Development/Demo)

If `DATABASE_URL` is not set, all data is stored in `data/*.json` files automatically. No setup needed.

---

## 🔑 Angel One API Setup

1. Login to [Angel One SmartAPI](https://smartapi.angelbroking.com/)
2. Create an app to get your `API_KEY`
3. Enable TOTP in your Angel One account
4. Get your TOTP secret from the TOTP app
5. Set all credentials in `.env`

---

## 📊 Usage Guide

### First Time Setup
1. Login with `admin / 123456` (change PIN in Settings)
2. Complete the onboarding checklist
3. Configure Angel One API in ⚙️ Settings → API tab
4. Set capital allocation in 💰 Capital tab
5. Add symbols to watchlists
6. Run scanner to find signals
7. **Trade in Paper Mode for 7+ days before going live**

### Paper Mode (Block 25)
- All features work in paper mode with live prices
- No real orders placed
- Separate P&L tracking from live
- Recommended: backtest first, then paper trade, then live

### Auto-Trading (Blocks 4-8)
- Enable auto-trade via sidebar toggle
- Complete pre-flight checklist first
- MTF confirmation required by default
- Daily loss limit hard stop enforced
- Consecutive loss protection active

---

## ⚠️ Important Notes

- **This software is for educational and informational purposes.**
- Always consult a SEBI-registered financial advisor before trading.
- Test thoroughly in Paper Mode before enabling live auto-trading.
- F&O trading requires SEBI/exchange algo approval — check with Angel One.
- The developers are not responsible for any trading losses.

---

## 🛠️ Architecture

| Component | Technology |
|-----------|-----------|
| UI | Streamlit + Plotly |
| Broker API | Angel One SmartAPI |
| Market Data | NSE Public APIs + Angel One |
| Database | PostgreSQL (SQLAlchemy) / JSON fallback |
| ML | scikit-learn (Random Forest, Isolation Forest) |
| AI Analysis | Anthropic Claude API |
| Reports | ReportLab (PDF) + SMTP (Email) |
| Notifications | WhatsApp Business Cloud API |

---

## 📞 Support

- File issues on GitHub
- Refer to `New Session Guide` in the master plan for resuming development
- Each block is self-contained and can be developed independently

---

*ProTrader Terminal v2.0 | Angel One SmartAPI + NSE | Zero Hardcoding | 40 Blocks | 200+ Features*

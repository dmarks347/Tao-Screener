# 📈 Tao Stock Screener

A professional-grade stock screening application built with Python and Streamlit that identifies bullish and bearish stocks based on specific technical analysis criteria. The screener is designed for publication on Streamlit.io and supports Webull API integration.

## 🎯 Features

- **Comprehensive Stock Coverage**: All US stocks (NYSE, NASDAQ) with market cap ≥ $1B
- **Dual Screening Categories**: Separate bullish and bearish stock identification
- **Broad Industry Classification**: Stocks grouped into 10 major industry categories
- **Daily Auto-Refresh**: Automatic data updates after market close (4:00 PM ET)
- **Real-Time Price Data**: Current price, daily change ($), and percentage change (%)
- **Advanced Sorting**: Sort results by market cap, price, % change, volume, industry, or symbol
- **Professional UI**: Clean, modern interface with market status indicators
- **Official Webull API**: Full integration with fallback to yfinance
- **Export Capabilities**: CSV export functionality for further analysis

## 📊 Screening Criteria

### General Requirements (All Stocks)
- Market Cap ≥ $1 billion
- ADX (13) ≥ 20
- Average Volume > 500,000

### Bullish Criteria
- Exponential Moving Averages: EMA8 > EMA21 > EMA34 > EMA55 > EMA89
- Stochastic (8,3) ≤ 40
- RSI (2) ≤ 10 within the last 5 days

### Bearish Criteria
- Exponential Moving Averages: EMA8 < EMA21 < EMA34 < EMA55 < EMA89
- Stochastic (8,3) ≥ 60
- RSI (2) ≥ 90 within the last 5 days

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone or download the project**
```bash
# If using git
git clone <repository-url>
cd "Tao Stock Screener"

# Or extract from zip file
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## 🔧 Configuration

### Webull API Setup (Optional)
To use Webull API instead of the yfinance fallback:

1. **Set environment variables:**
```bash
export WEBULL_API_KEY="your_api_key"
export WEBULL_SECRET_KEY="your_secret_key"
export WEBULL_USERNAME="your_username"
export WEBULL_PASSWORD="your_password"
```

2. **Or modify `config.py` directly** (not recommended for production)

### Screening Parameters
Modify screening criteria in `config.py`:

```python
SCREENING_CRITERIA = {
    'general': {
        'min_market_cap': 1000,  # Million USD
        'min_adx': 20,
        'min_avg_volume': 500000
    },
    # ... customize other parameters
}
```

## 📁 Project Structure

```
Tao Stock Screener/
├── app.py                  # Main Streamlit application
├── data_fetcher.py         # Data retrieval and API integration
├── technical_analysis.py   # Technical indicator calculations
├── stock_screener.py       # Main screening logic
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── .env                  # Environment variables (create if needed)
```

## 🖥️ Usage

### Web Interface
1. Launch the app with `streamlit run app.py`
2. Monitor market status (Open/Closed) and data freshness
3. Enable auto-refresh for daily updates after market close
4. Sort results by Market Cap, Price, % Change, Volume, Industry, or Symbol
5. View comprehensive stock data including:
   - Current price and daily change ($ and %)
   - Market cap, volume, and technical indicators
   - Industry classification and key metrics
6. Export results using the built-in functionality

### Programmatic Usage
```python
from stock_screener import StockScreener

# Initialize screener
screener = StockScreener()

# Run full screening
bullish_stocks, bearish_stocks = screener.run_screening()

# Quick test with specific symbols
test_bullish, test_bearish = screener.quick_test_screening(['AAPL', 'MSFT', 'GOOGL'])

# Export results
screener.export_results(bullish_stocks, bearish_stocks, 'my_results.csv')
```

## 🔍 Technical Indicators

The screener uses the following technical indicators:

| Indicator | Period | Purpose |
|-----------|---------|---------|
| EMA | 8, 21, 34, 55, 89 | Trend direction |
| RSI | 2 | Momentum (oversold/overbought) |
| Stochastic | 8,3 | Momentum oscillator |
| ADX | 13 | Trend strength |

## 📈 Deployment to Streamlit.io

1. **Create a Streamlit account** at [streamlit.io](https://streamlit.io)

2. **Upload your code** to GitHub repository

3. **Deploy from Streamlit:**
   - Connect your GitHub account
   - Select the repository
   - Set main file path: `app.py`
   - Add environment variables if using Webull API

4. **Configure secrets** (if needed):
   - Go to app settings
   - Add secrets for API keys
   ```toml
   WEBULL_API_KEY = "your_key_here"
   WEBULL_SECRET_KEY = "your_secret_here"
   ```

## ⚠️ Important Notes

### Data Sources
- **Primary**: Official Webull API (all US stocks when configured)
- **Fallback**: yfinance (S&P 500 + major indices)
- **Stock Universe**: All US stocks with market cap ≥ $1B
- **Refresh Schedule**: Daily after market close (4:00 PM ET)

### Rate Limiting
- Built-in rate limiting to respect API limits
- Configurable delays between requests
- Parallel processing with controlled concurrency

### Performance
- **Webull API**: Screening 2000+ stocks takes 3-8 minutes
- **yfinance Fallback**: Screening 500+ stocks takes 2-5 minutes  
- Results are cached for 1 hour by default
- Auto-refresh only after market close to optimize performance
- Use quick test mode for development

### Industry Categories
Results are automatically grouped into these broad categories:
- **Technology** (Software, Internet, Semiconductors)
- **Healthcare** (Pharmaceuticals, Biotechnology, Medical)
- **Financial Services** (Banks, Insurance, Investment)
- **Consumer** (Retail, Restaurants, Discretionary)
- **Industrial** (Manufacturing, Construction, Aerospace)
- **Energy** (Oil, Gas, Renewable Energy)
- **Communication Services** (Telecom, Media)
- **Utilities** (Electric, Water, Gas utilities)
- **Real Estate** (REITs, Property)
- **Materials** (Mining, Chemicals, Metals)

## 🛠️ Customization

### Adding New Criteria
Modify `technical_analysis.py` to add new indicators:

```python
@staticmethod
def calculate_new_indicator(data, period):
    # Your calculation logic
    return indicator_values

def evaluate_custom_criteria(data):
    # Your evaluation logic
    return criteria_result
```

### Changing Stock Universe
Modify `data_fetcher.py` to change the stock universe:

```python
def _get_fallback_stock_universe(self):
    # Replace with your preferred stock list
    return ['AAPL', 'MSFT', 'GOOGL']  # Your custom list
```

## 🐛 Troubleshooting

### Common Issues

1. **TA-Lib Installation Error**
   ```bash
   # Windows
   pip install talib-binary
   
   # Linux/Mac
   pip install TA-Lib
   ```

2. **No Results Found**
   - Check if your criteria are too restrictive
   - Verify data is being fetched correctly
   - Use quick test mode to debug

3. **API Rate Limits**
   - Increase delays in `config.py`
   - Reduce `max_concurrent_requests`

4. **Memory Issues**
   - Reduce the stock universe size
   - Increase system memory/swap
   - Use quick test mode for development

## 📊 Sample Output

The screener provides detailed results including:

- Stock symbol and company name
- Industry and sector classification
- Current market cap and price
- All technical indicator values
- Pass/fail status for each criterion

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is provided as-is for educational and personal use.

## ⚖️ Disclaimer

This tool is for educational and research purposes only. It does not constitute financial advice. Always do your own research and consult with qualified financial advisors before making investment decisions.

## 📞 Support

For questions or issues:
1. Check the troubleshooting section
2. Review the code comments
3. Create an issue in the repository

---

**Built with ❤️ for the trading community** 
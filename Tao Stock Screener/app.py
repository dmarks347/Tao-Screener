import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from data_fetcher import DataFetcher
from technical_analysis import TechnicalAnalysis
from stock_screener import StockScreener

# Page configuration
st.set_page_config(
    page_title="Tao Stock Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .category-header {
        font-size: 2rem;
        font-weight: bold;
        margin: 1rem 0;
        padding: 0.5rem;
        border-radius: 10px;
    }
    .bullish-header {
        background-color: #d4edda;
        color: #155724;
    }
    .bearish-header {
        background-color: #f8d7da;
        color: #721c24;
    }
    .stock-card {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Header
    st.markdown('<h1 class="main-header">🔍 Tao Stock Screener</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Refresh button
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        st.subheader("📊 Screening Criteria")
        
        # General criteria (non-editable for now)
        st.write("**General Requirements:**")
        st.write("• Market Cap ≥ $1B")
        st.write("• ADX (13) ≥ 20")
        st.write("• Avg Volume > 500K")
        
        st.write("**Bullish Criteria:**")
        st.write("• EMA: 8 > 21 > 34 > 55 > 89")
        st.write("• Stochastic (8,3) ≤ 40")
        st.write("• RSI (2) ≤ 10 (last 5 days)")
        
        st.write("**Bearish Criteria:**")
        st.write("• EMA: 8 < 21 < 34 < 55 < 89")
        st.write("• Stochastic (8,3) ≥ 60")
        st.write("• RSI (2) ≥ 90 (last 5 days)")
        
        # Data source info
        st.subheader("📡 Data Source")
        if data_fetcher.webull_configured:
            st.success("✅ Webull API Active")
            st.write("• All US stocks")
            st.write("• Real-time updates")
        else:
            st.info("📊 yfinance Fallback")
            st.write("• S&P 500 + Major indices")
            st.write("• Daily updates")
        
        # Additional settings
        st.subheader("⚙️ Display Options")
        show_details = st.checkbox("Show technical details", value=False)
        
        if show_details:
            st.write("**EMA Values:**")
            st.write("• All 5 EMA periods")
            st.write("• RSI(2) current value")
            st.write("• Stochastic %K value")
            st.write("• ADX trend strength")
    
    # Main content
    try:
        # Initialize components
        data_fetcher = DataFetcher()
        screener = StockScreener()
        
        # Check if API is configured
        if not data_fetcher.is_configured():
            st.warning("⚠️ Webull API not configured. Using yfinance as fallback data source.")
            st.info("For best performance, add your Webull API credentials to the configuration file.")
        
        # Market status and refresh info
        col_status1, col_status2, col_status3 = st.columns(3)
        
        with col_status1:
            if data_fetcher.is_market_hours():
                st.success("🟢 Market is OPEN")
            else:
                st.info("🔴 Market is CLOSED")
        
        with col_status2:
            if data_fetcher.should_refresh_data():
                st.warning("🔄 Data needs refresh")
            else:
                st.success("✅ Data is current")
        
        with col_status3:
            # Auto-refresh toggle
            auto_refresh = st.checkbox("Auto-refresh daily", value=True)
        
        # Show loading spinner and run screening
        should_run = True
        if data_fetcher.should_refresh_data() and auto_refresh:
            st.info("🔄 Auto-refreshing data after market close...")
        elif not auto_refresh and data_fetcher.should_refresh_data():
            should_run = st.button("🔄 Manual Refresh Required", type="primary")
        
        if should_run:
            with st.spinner("🔍 Screening stocks... This may take several minutes for comprehensive analysis."):
                # Run the screening
                bullish_stocks, bearish_stocks = screener.run_screening()
                
                # Mark data as refreshed if it was a refresh operation
                if data_fetcher.should_refresh_data():
                    data_fetcher.mark_data_refreshed()
        else:
            # Load cached results if available
            try:
                bullish_stocks = pd.DataFrame()
                bearish_stocks = pd.DataFrame()
                st.info("Click 'Manual Refresh Required' to update data or enable auto-refresh.")
            except:
                bullish_stocks = pd.DataFrame()
                bearish_stocks = pd.DataFrame()
        
        # Display summary statistics
        if not bullish_stocks.empty or not bearish_stocks.empty:
            st.markdown("---")
            col_summary1, col_summary2, col_summary3, col_summary4 = st.columns(4)
            
            with col_summary1:
                st.metric("📈 Bullish Stocks", len(bullish_stocks))
            with col_summary2:
                st.metric("📉 Bearish Stocks", len(bearish_stocks))
            with col_summary3:
                total_screened = screener.get_last_screened_count() if hasattr(screener, 'get_last_screened_count') else "N/A"
                st.metric("🔍 Total Screened", total_screened)
            with col_summary4:
                last_update = datetime.now().strftime("%H:%M:%S")
                st.metric("🕒 Last Update", last_update)
        
        # Display results with sorting options
        if not bullish_stocks.empty or not bearish_stocks.empty:
            st.markdown("---")
            
            # Sorting options
            sort_col1, sort_col2 = st.columns(2)
            with sort_col1:
                sort_by = st.selectbox(
                    "Sort by:",
                    ["Market Cap", "Price", "% Change", "Volume", "Industry", "Symbol"],
                    index=0
                )
            with sort_col2:
                sort_order = st.radio("Order:", ["Descending", "Ascending"], horizontal=True)
            
            # Apply sorting
            if not bullish_stocks.empty:
                bullish_stocks = sort_stocks(bullish_stocks, sort_by, sort_order)
            if not bearish_stocks.empty:
                bearish_stocks = sort_stocks(bearish_stocks, sort_by, sort_order)
        
        # Display results in columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="category-header bullish-header">📈 Bullish Stocks</div>', unsafe_allow_html=True)
            display_stocks(bullish_stocks, "bullish")
        
        with col2:
            st.markdown('<div class="category-header bearish-header">📉 Bearish Stocks</div>', unsafe_allow_html=True)
            display_stocks(bearish_stocks, "bearish")
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.info("Please check your configuration and try again.")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def display_stocks(stocks_data, category):
    """Display stocks grouped by industry"""
    if stocks_data is None or len(stocks_data) == 0:
        st.info(f"No {category} stocks found matching the criteria.")
        return
    
    # Group by industry
    industries = stocks_data['industry'].unique()
    
    for industry in sorted(industries):
        industry_stocks = stocks_data[stocks_data['industry'] == industry]
        
        with st.expander(f"🏢 {industry} ({len(industry_stocks)} stocks)", expanded=True):
            for _, stock in industry_stocks.iterrows():
                display_stock_card(stock, category)

def sort_stocks(df, sort_by, sort_order):
    """Sort stocks based on selected criteria"""
    if df.empty:
        return df
    
    # Map display names to column names
    column_mapping = {
        "Market Cap": "market_cap",
        "Price": "current_price", 
        "% Change": "percent_change",
        "Volume": "avg_volume",
        "Industry": "industry",
        "Symbol": "symbol"
    }
    
    column = column_mapping.get(sort_by, "market_cap")
    ascending = (sort_order == "Ascending")
    
    return df.sort_values(by=column, ascending=ascending)

def display_stock_card(stock, category):
    """Display individual stock information with price and change data"""
    # Color scheme based on category
    border_color = "#28a745" if category == "bullish" else "#dc3545"
    
    # Format price change with color
    price_change = stock.get('price_change', 0)
    percent_change = stock.get('percent_change', 0)
    
    if price_change > 0:
        change_color = "#28a745"  # Green for positive
        change_symbol = "▲"
    elif price_change < 0:
        change_color = "#dc3545"  # Red for negative
        change_symbol = "▼"
    else:
        change_color = "#6c757d"  # Gray for no change
        change_symbol = "►"
    
    st.markdown(f"""
    <div style="border-left: 4px solid {border_color}; padding: 12px; margin: 8px 0; background-color: #f8f9fa; border-radius: 5px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div>
                <strong style="font-size: 1.1em;">{stock['symbol']}</strong>
                <span style="color: #6c757d; margin-left: 8px;">{stock['name'][:30]}{'...' if len(stock['name']) > 30 else ''}</span>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 1.1em; font-weight: bold;">${stock['current_price']:.2f}</div>
                <div style="color: {change_color}; font-size: 0.9em;">
                    {change_symbol} ${abs(price_change):.2f} ({percent_change:+.1f}%)
                </div>
            </div>
        </div>
        <div style="font-size: 0.85em; color: #6c757d; display: flex; flex-wrap: wrap; gap: 12px;">
            <span>💰 MCap: ${stock['market_cap']:,.0f}M</span>
            <span>📊 Vol: {stock['avg_volume']:,.0f}</span>
            <span>📈 ADX: {stock['adx']:.1f}</span>
            <span>🏢 RSI(2): {stock.get('rsi2', 0):.1f}</span>
            <span>📉 Stoch: {stock.get('stoch_k', 0):.1f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 
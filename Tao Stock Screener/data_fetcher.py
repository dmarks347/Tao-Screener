"""
Data Fetcher Module for Tao Stock Screener
Handles Webull API integration and data retrieval
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dt_time
import yfinance as yf  # Temporary fallback until Webull API is configured
import requests
import time
from typing import Dict, List, Optional, Tuple
import logging
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Webull SDK when available
try:
    from webull import webull
    WEBULL_AVAILABLE = True
except ImportError:
    WEBULL_AVAILABLE = False
    logger.info("Webull SDK not installed. Using yfinance as fallback.")

class DataFetcher:
    """Handles data fetching from Webull API and fallback sources"""
    
    def __init__(self):
        self.config = Config()
        self.webull_configured = self._check_webull_config()
        self.webull_client = None
        
        if self.webull_configured:
            self._initialize_webull_client()
        
    def _check_webull_config(self) -> bool:
        """Check if Webull API is properly configured"""
        if not WEBULL_AVAILABLE:
            return False
        
        has_credentials = (
            hasattr(self.config, 'WEBULL_API_KEY') and self.config.WEBULL_API_KEY and
            hasattr(self.config, 'WEBULL_SECRET_KEY') and self.config.WEBULL_SECRET_KEY and
            hasattr(self.config, 'WEBULL_USERNAME') and self.config.WEBULL_USERNAME and
            hasattr(self.config, 'WEBULL_PASSWORD') and self.config.WEBULL_PASSWORD
        )
        
        return has_credentials
    
    def _initialize_webull_client(self):
        """Initialize Webull API client"""
        try:
            self.webull_client = webull()
            # Login with credentials
            self.webull_client.login(
                username=self.config.WEBULL_USERNAME,
                password=self.config.WEBULL_PASSWORD
            )
            logger.info("Successfully initialized Webull API client")
        except Exception as e:
            logger.error(f"Failed to initialize Webull client: {e}")
            self.webull_configured = False
    
    def is_configured(self) -> bool:
        """Check if data source is configured"""
        return self.webull_configured or True  # Always True for yfinance fallback
    
    def is_market_hours(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now()
        # Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        
        is_weekday = now.weekday() < 5  # Monday = 0, Friday = 4
        current_time = now.time()
        
        return is_weekday and market_open <= current_time <= market_close
    
    def should_refresh_data(self) -> bool:
        """Check if data should be refreshed (daily after market close)"""
        now = datetime.now()
        
        # Check if it's after market close (4:00 PM ET)
        if now.time() < dt_time(16, 0):
            return False
        
        # Check if we've already refreshed today
        last_refresh_file = "last_refresh.txt"
        try:
            with open(last_refresh_file, 'r') as f:
                last_refresh = datetime.strptime(f.read().strip(), "%Y-%m-%d")
                if last_refresh.date() == now.date():
                    return False
        except FileNotFoundError:
            pass
        
        return True
    
    def mark_data_refreshed(self):
        """Mark that data has been refreshed today"""
        with open("last_refresh.txt", 'w') as f:
            f.write(datetime.now().strftime("%Y-%m-%d"))
    
    def get_stock_universe(self) -> List[str]:
        """Get list of all US stocks to screen"""
        if self.webull_configured:
            return self._get_webull_stock_universe()
        else:
            return self._get_fallback_stock_universe()
    
    def _get_webull_stock_universe(self) -> List[str]:
        """Get all US stock universe from Webull API"""
        try:
            if not self.webull_client:
                raise Exception("Webull client not initialized")
            
            # Get all US stocks from Webull
            # Note: This is the structure for when Webull API is available
            stocks = self.webull_client.get_securities()
            
            # Filter for US stocks with market cap >= 1B
            us_stocks = []
            for stock in stocks:
                if (stock.get('exchange') in ['NYSE', 'NASDAQ'] and 
                    stock.get('marketCap', 0) >= 1000000000):  # 1B in dollars
                    us_stocks.append(stock['symbol'])
            
            logger.info(f"Retrieved {len(us_stocks)} US stocks from Webull API")
            return us_stocks
            
        except Exception as e:
            logger.error(f"Error fetching stock universe from Webull: {e}")
            return self._get_fallback_stock_universe()
    
    def _get_fallback_stock_universe(self) -> List[str]:
        """Get comprehensive US stock universe from multiple sources"""
        all_symbols = []
        
        try:
            # Get S&P 500
            url_sp500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables_sp500 = pd.read_html(url_sp500)
            sp500_symbols = tables_sp500[0]['Symbol'].tolist()
            all_symbols.extend(sp500_symbols)
            
            # Get Russell 1000 symbols (broader coverage)
            try:
                url_russell = "https://en.wikipedia.org/wiki/Russell_1000_Index"
                tables_russell = pd.read_html(url_russell)
                if len(tables_russell) > 0:
                    russell_symbols = tables_russell[0]['Symbol'].tolist() if 'Symbol' in tables_russell[0].columns else []
                    all_symbols.extend(russell_symbols)
            except:
                logger.warning("Could not fetch Russell 1000 data")
            
            # Get NASDAQ 100
            try:
                url_nasdaq = "https://en.wikipedia.org/wiki/Nasdaq-100"
                tables_nasdaq = pd.read_html(url_nasdaq)
                nasdaq_symbols = tables_nasdaq[4]['Ticker'].tolist()  # Usually table 4 for NASDAQ-100
                all_symbols.extend(nasdaq_symbols)
            except:
                logger.warning("Could not fetch NASDAQ 100 data")
            
            # Remove duplicates and clean symbols
            cleaned_symbols = list(set([symbol.replace('.', '-') for symbol in all_symbols if isinstance(symbol, str)]))
            
            logger.info(f"Retrieved {len(cleaned_symbols)} US stocks from fallback sources")
            return cleaned_symbols
            
        except Exception as e:
            logger.error(f"Error fetching comprehensive stock universe: {e}")
            # Ultimate fallback - major stocks
            return [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'JNJ', 'V',
                'WMT', 'PG', 'HD', 'UNH', 'BAC', 'MA', 'DIS', 'ADBE', 'CRM', 'NFLX',
                'XOM', 'CVX', 'ABT', 'PFE', 'KO', 'PEP', 'TMO', 'COST', 'ABBV', 'ACN'
            ]
    
    def get_stock_data(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """Get historical stock data for a symbol"""
        if self.webull_configured:
            return self._get_webull_data(symbol, period)
        else:
            return self._get_yfinance_data(symbol, period)
    
    def _get_webull_data(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """Get data from Webull API"""
        try:
            if not self.webull_client:
                raise Exception("Webull client not initialized")
            
            # Get historical data from Webull
            # Webull API typically provides data in different intervals
            data = self.webull_client.get_bars(
                stock=symbol,
                interval='1d',  # Daily data
                count=365 if period == '1y' else 252  # Approximate trading days
            )
            
            if not data:
                logger.warning(f"No data found for {symbol} from Webull API")
                return None
            
            # Convert Webull data to pandas DataFrame
            df = pd.DataFrame(data)
            
            # Standardize column names to match yfinance format
            column_mapping = {
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }
            
            df = df.rename(columns=column_mapping)
            df.columns = [col.lower() for col in df.columns]
            
            # Set index to datetime if not already
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
                df.set_index('time', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching Webull data for {symbol}: {e}")
            # Fallback to yfinance
            return self._get_yfinance_data(symbol, period)
    
    def _get_yfinance_data(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """Get data from yfinance (fallback)"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data.empty:
                logger.warning(f"No data found for {symbol}")
                return None
            
            # Standardize column names
            data.columns = [col.lower() for col in data.columns]
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def get_stock_info(self, symbol: str) -> Dict:
        """Get stock information (market cap, industry, etc.)"""
        if self.webull_configured:
            return self._get_webull_info(symbol)
        else:
            return self._get_yfinance_info(symbol)
    
    def _get_webull_info(self, symbol: str) -> Dict:
        """Get stock info from Webull API"""
        try:
            if not self.webull_client:
                raise Exception("Webull client not initialized")
            
            # Get stock information from Webull
            info = self.webull_client.get_instrument_detail(symbol)
            quote = self.webull_client.get_quote(symbol)
            
            # Calculate daily change
            current_price = quote.get('close', 0)
            previous_close = quote.get('previousClose', current_price)
            price_change = current_price - previous_close
            percent_change = ((price_change / previous_close) * 100) if previous_close > 0 else 0
            
            # Map to broader industry categories
            sector = info.get('sector', 'Unknown')
            broad_industry = self._map_to_broad_industry(sector, info.get('industry', ''))
            
            stock_info = {
                'symbol': symbol,
                'name': info.get('name', symbol),
                'market_cap': info.get('marketCap', 0) / 1e6,  # Convert to millions
                'industry': broad_industry,
                'sector': sector,
                'avg_volume': info.get('avgVolume', 0),
                'current_price': current_price,
                'price_change': price_change,
                'percent_change': percent_change,
                'previous_close': previous_close
            }
            
            return stock_info
            
        except Exception as e:
            logger.error(f"Error fetching Webull info for {symbol}: {e}")
            # Fallback to yfinance
            return self._get_yfinance_info(symbol)
    
    def _map_to_broad_industry(self, sector: str, industry: str) -> str:
        """Map detailed industry/sector to broader categories"""
        sector_lower = sector.lower() if sector else ''
        industry_lower = industry.lower() if industry else ''
        
        # Define broader industry mappings
        if any(term in sector_lower or term in industry_lower for term in 
               ['technology', 'software', 'computer', 'internet', 'semiconductor', 'tech']):
            return 'Technology'
        elif any(term in sector_lower or term in industry_lower for term in 
                 ['healthcare', 'pharmaceutical', 'biotech', 'medical', 'drug']):
            return 'Healthcare'
        elif any(term in sector_lower or term in industry_lower for term in 
                 ['financial', 'bank', 'insurance', 'credit', 'investment']):
            return 'Financial Services'
        elif any(term in sector_lower or term in industry_lower for term in 
                 ['consumer', 'retail', 'restaurant', 'apparel', 'discretionary']):
            return 'Consumer'
        elif any(term in sector_lower or term in industry_lower for term in 
                 ['industrial', 'manufacturing', 'construction', 'aerospace', 'defense']):
            return 'Industrial'
        elif any(term in sector_lower or term in industry_lower for term in 
                 ['energy', 'oil', 'gas', 'petroleum', 'renewable']):
            return 'Energy'
        elif any(term in sector_lower or term in industry_lower for term in 
                 ['telecommunication', 'telecom', 'wireless', 'communication']):
            return 'Communication Services'
        elif any(term in sector_lower or term in industry_lower for term in 
                 ['utility', 'utilities', 'electric', 'water', 'gas']):
            return 'Utilities'
        elif any(term in sector_lower or term in industry_lower for term in 
                 ['real estate', 'reit', 'property', 'housing']):
            return 'Real Estate'
        elif any(term in sector_lower or term in industry_lower for term in 
                 ['material', 'mining', 'chemical', 'metal', 'paper']):
            return 'Materials'
        else:
            return 'Other'
    
    def _get_yfinance_info(self, symbol: str) -> Dict:
        """Get stock info from yfinance (fallback)"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get recent price data for daily change calculation
            hist = ticker.history(period="2d")
            current_price = info.get('currentPrice', 0)
            
            # Calculate daily change
            if len(hist) >= 2:
                previous_close = hist.iloc[-2]['Close']
                price_change = current_price - previous_close
                percent_change = ((price_change / previous_close) * 100) if previous_close > 0 else 0
            else:
                previous_close = info.get('previousClose', current_price)
                price_change = current_price - previous_close
                percent_change = ((price_change / previous_close) * 100) if previous_close > 0 else 0
            
            # Map to broader industry categories
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            broad_industry = self._map_to_broad_industry(sector, industry)
            
            # Extract relevant information
            stock_info = {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'market_cap': info.get('marketCap', 0) / 1e6,  # Convert to millions
                'industry': broad_industry,
                'sector': sector,
                'avg_volume': info.get('averageVolume', 0),
                'current_price': current_price,
                'price_change': price_change,
                'percent_change': percent_change,
                'previous_close': previous_close
            }
            
            return stock_info
            
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {e}")
            return {
                'symbol': symbol,
                'name': symbol,
                'market_cap': 0,
                'industry': 'Unknown',
                'sector': 'Unknown',
                'avg_volume': 0,
                'current_price': 0,
                'price_change': 0,
                'percent_change': 0,
                'previous_close': 0
            }
    
    def batch_get_data(self, symbols: List[str], max_concurrent: int = 5) -> Dict[str, pd.DataFrame]:
        """Get data for multiple symbols with rate limiting"""
        results = {}
        
        for i, symbol in enumerate(symbols):
            if i > 0 and i % max_concurrent == 0:
                time.sleep(1)  # Rate limiting
            
            data = self.get_stock_data(symbol)
            if data is not None:
                results[symbol] = data
                
        logger.info(f"Successfully fetched data for {len(results)}/{len(symbols)} symbols")
        return results
    
    def get_market_data_batch(self, symbols: List[str]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Dict]]:
        """Get both price data and stock info in batch"""
        price_data = {}
        stock_info = {}
        
        for symbol in symbols:
            try:
                # Get price data
                data = self.get_stock_data(symbol)
                if data is not None:
                    price_data[symbol] = data
                
                # Get stock info
                info = self.get_stock_info(symbol)
                stock_info[symbol] = info
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
        
        return price_data, stock_info 
"""
Stock Screener Module for Tao Stock Screener
Main screening logic that combines data fetching and technical analysis
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from data_fetcher import DataFetcher
from technical_analysis import TechnicalAnalysis

logger = logging.getLogger(__name__)

class StockScreener:
    """Main stock screening class"""
    
    def __init__(self, max_workers: int = 10):
        self.data_fetcher = DataFetcher()
        self.max_workers = max_workers
        self.last_screened_count = 0
        
    def run_screening(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Run the complete screening process"""
        logger.info("Starting stock screening process...")
        
        # Get stock universe
        symbols = self.data_fetcher.get_stock_universe()
        logger.info(f"Screening {len(symbols)} stocks")
        self.last_screened_count = len(symbols)
        
        # Get market data for all symbols
        price_data, stock_info = self.data_fetcher.get_market_data_batch(symbols)
        
        # Filter by market cap >= 1B
        filtered_symbols = self._filter_by_market_cap(stock_info, min_market_cap=1000)
        logger.info(f"After market cap filter: {len(filtered_symbols)} stocks")
        
        # Screen stocks in parallel
        bullish_results = []
        bearish_results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit screening tasks
            futures = {
                executor.submit(self._screen_single_stock, symbol, price_data.get(symbol), stock_info.get(symbol)): symbol 
                for symbol in filtered_symbols if symbol in price_data
            }
            
            # Collect results
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                    if result is not None:
                        if result['category'] == 'bullish':
                            bullish_results.append(result)
                        elif result['category'] == 'bearish':
                            bearish_results.append(result)
                            
                except Exception as e:
                    logger.error(f"Error screening {symbol}: {e}")
        
        # Convert to DataFrames
        bullish_df = pd.DataFrame(bullish_results) if bullish_results else pd.DataFrame()
        bearish_df = pd.DataFrame(bearish_results) if bearish_results else pd.DataFrame()
        
        logger.info(f"Screening complete. Found {len(bullish_df)} bullish and {len(bearish_df)} bearish stocks")
        
        return bullish_df, bearish_df
    
    def _filter_by_market_cap(self, stock_info: Dict, min_market_cap: float) -> List[str]:
        """Filter stocks by minimum market cap"""
        filtered = []
        for symbol, info in stock_info.items():
            if info.get('market_cap', 0) >= min_market_cap:
                filtered.append(symbol)
        return filtered
    
    def _screen_single_stock(self, symbol: str, price_data: pd.DataFrame, 
                           stock_info: Dict) -> Optional[Dict]:
        """Screen a single stock for bullish/bearish criteria"""
        try:
            if price_data is None or price_data.empty:
                return None
            
            # Ensure we have enough data
            if len(price_data) < 100:  # Need enough data for EMA89
                return None
            
            # Check bullish criteria
            bullish_eval = TechnicalAnalysis.evaluate_bullish_criteria(price_data)
            
            # Check bearish criteria
            bearish_eval = TechnicalAnalysis.evaluate_bearish_criteria(price_data)
            
            # Determine category
            result = None
            
            if bullish_eval['all_criteria_met']:
                result = self._create_result_dict(symbol, stock_info, bullish_eval, 'bullish')
            elif bearish_eval['all_criteria_met']:
                result = self._create_result_dict(symbol, stock_info, bearish_eval, 'bearish')
            
            return result
            
        except Exception as e:
            logger.error(f"Error screening {symbol}: {e}")
            return None
    
    def get_last_screened_count(self) -> int:
        """Get the count of stocks screened in the last run"""
        return self.last_screened_count
    
    def _create_result_dict(self, symbol: str, stock_info: Dict, 
                          evaluation: Dict, category: str) -> Dict:
        """Create standardized result dictionary"""
        indicators = evaluation.get('indicators', {})
        
        return {
            'symbol': symbol,
            'name': stock_info.get('name', symbol),
            'category': category,
            'industry': stock_info.get('industry', 'Unknown'),
            'sector': stock_info.get('sector', 'Unknown'),
            'market_cap': stock_info.get('market_cap', 0),
            'current_price': stock_info.get('current_price', 0),
            'price_change': stock_info.get('price_change', 0),
            'percent_change': stock_info.get('percent_change', 0),
            'previous_close': stock_info.get('previous_close', 0),
            'avg_volume': indicators.get('avg_volume', 0),
            'adx': indicators.get('adx', 0),
            'rsi2': indicators.get('rsi2', 0),
            'stoch_k': indicators.get('stoch_k', 0),
            'ema8': indicators.get('ema8', 0),
            'ema21': indicators.get('ema21', 0),
            'ema34': indicators.get('ema34', 0),
            'ema55': indicators.get('ema55', 0),
            'ema89': indicators.get('ema89', 0),
            # Criteria flags
            'ema_condition': evaluation.get('ema_bullish' if category == 'bullish' else 'ema_bearish', False),
            'stoch_condition': evaluation.get('stoch_condition', False),
            'rsi_condition': evaluation.get('rsi_condition', False),
            'adx_condition': evaluation.get('adx_condition', False),
            'volume_condition': evaluation.get('volume_condition', False),
        }
    
    def get_screening_summary(self, bullish_df: pd.DataFrame, bearish_df: pd.DataFrame) -> Dict:
        """Get summary statistics of screening results"""
        summary = {
            'total_bullish': len(bullish_df),
            'total_bearish': len(bearish_df),
            'bullish_by_industry': {},
            'bearish_by_industry': {},
            'top_industries_bullish': [],
            'top_industries_bearish': []
        }
        
        if not bullish_df.empty:
            bullish_by_industry = bullish_df['industry'].value_counts()
            summary['bullish_by_industry'] = bullish_by_industry.to_dict()
            summary['top_industries_bullish'] = bullish_by_industry.head(5).index.tolist()
        
        if not bearish_df.empty:
            bearish_by_industry = bearish_df['industry'].value_counts()
            summary['bearish_by_industry'] = bearish_by_industry.to_dict()
            summary['top_industries_bearish'] = bearish_by_industry.head(5).index.tolist()
        
        return summary
    
    def export_results(self, bullish_df: pd.DataFrame, bearish_df: pd.DataFrame, 
                      filepath: str = None) -> str:
        """Export screening results to CSV"""
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        
        if filepath is None:
            filepath = f"tao_screener_results_{timestamp}.csv"
        
        # Combine results with category indicator
        if not bullish_df.empty:
            bullish_df['category'] = 'Bullish'
        if not bearish_df.empty:
            bearish_df['category'] = 'Bearish'
        
        combined_df = pd.concat([bullish_df, bearish_df], ignore_index=True)
        
        if not combined_df.empty:
            # Select relevant columns for export
            export_columns = [
                'symbol', 'name', 'category', 'industry', 'sector',
                'market_cap', 'current_price', 'avg_volume', 'adx',
                'rsi2', 'stoch_k', 'ema8', 'ema21', 'ema34', 'ema55', 'ema89'
            ]
            
            combined_df[export_columns].to_csv(filepath, index=False)
            logger.info(f"Results exported to {filepath}")
        
        return filepath
    
    def quick_test_screening(self, test_symbols: List[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Run screening on a small set of symbols for testing"""
        if test_symbols is None:
            test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        logger.info(f"Running quick test screening on {len(test_symbols)} symbols")
        
        # Get data
        price_data, stock_info = self.data_fetcher.get_market_data_batch(test_symbols)
        
        # Screen stocks
        bullish_results = []
        bearish_results = []
        
        for symbol in test_symbols:
            if symbol in price_data:
                result = self._screen_single_stock(symbol, price_data[symbol], stock_info[symbol])
                if result is not None:
                    if result['category'] == 'bullish':
                        bullish_results.append(result)
                    elif result['category'] == 'bearish':
                        bearish_results.append(result)
        
        bullish_df = pd.DataFrame(bullish_results) if bullish_results else pd.DataFrame()
        bearish_df = pd.DataFrame(bearish_results) if bearish_results else pd.DataFrame()
        
        return bullish_df, bearish_df 
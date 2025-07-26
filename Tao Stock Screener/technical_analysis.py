"""
Technical Analysis Module for Tao Stock Screener
Calculates all required technical indicators
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class TechnicalAnalysis:
    """Handles calculation of technical indicators"""
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        try:
            return talib.EMA(data.values, timeperiod=period)
        except:
            # Fallback calculation if talib fails
            return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        try:
            return talib.RSI(data.values, timeperiod=period)
        except:
            # Fallback calculation
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator"""
        try:
            slowk, slowd = talib.STOCH(high.values, low.values, close.values,
                                     fastk_period=k_period, slowk_period=d_period, 
                                     slowd_period=d_period)
            return pd.Series(slowk, index=close.index), pd.Series(slowd, index=close.index)
        except:
            # Fallback calculation
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            d_percent = k_percent.rolling(window=d_period).mean()
            return k_percent, d_percent
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index"""
        try:
            return talib.ADX(high.values, low.values, close.values, timeperiod=period)
        except:
            # Fallback calculation (simplified)
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            plus_dm = high.diff()
            minus_dm = low.diff() * -1
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            
            tr_smooth = tr.rolling(window=period).mean()
            plus_dm_smooth = plus_dm.rolling(window=period).mean()
            minus_dm_smooth = minus_dm.rolling(window=period).mean()
            
            plus_di = 100 * (plus_dm_smooth / tr_smooth)
            minus_di = 100 * (minus_dm_smooth / tr_smooth)
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=period).mean()
            
            return adx
    
    @staticmethod
    def check_ema_sequence(data: pd.DataFrame, bullish: bool = True) -> pd.Series:
        """Check if EMA sequence is in correct order"""
        # Calculate EMAs
        ema8 = TechnicalAnalysis.calculate_ema(data['close'], 8)
        ema21 = TechnicalAnalysis.calculate_ema(data['close'], 21)
        ema34 = TechnicalAnalysis.calculate_ema(data['close'], 34)
        ema55 = TechnicalAnalysis.calculate_ema(data['close'], 55)
        ema89 = TechnicalAnalysis.calculate_ema(data['close'], 89)
        
        if bullish:
            # Bullish: 8 > 21 > 34 > 55 > 89
            condition = (ema8 > ema21) & (ema21 > ema34) & (ema34 > ema55) & (ema55 > ema89)
        else:
            # Bearish: 8 < 21 < 34 < 55 < 89
            condition = (ema8 < ema21) & (ema21 < ema34) & (ema34 < ema55) & (ema55 < ema89)
        
        return pd.Series(condition, index=data.index)
    
    @staticmethod
    def check_rsi_condition(data: pd.DataFrame, threshold: float, 
                          days_lookback: int = 5, above: bool = False) -> bool:
        """Check if RSI condition was met in the last N days"""
        rsi = TechnicalAnalysis.calculate_rsi(data['close'], 2)
        recent_rsi = rsi.tail(days_lookback)
        
        if above:
            return (recent_rsi >= threshold).any()
        else:
            return (recent_rsi <= threshold).any()
    
    @staticmethod
    def get_latest_indicators(data: pd.DataFrame) -> Dict:
        """Get latest values of all indicators"""
        try:
            # EMAs
            ema8 = TechnicalAnalysis.calculate_ema(data['close'], 8)
            ema21 = TechnicalAnalysis.calculate_ema(data['close'], 21)
            ema34 = TechnicalAnalysis.calculate_ema(data['close'], 34)
            ema55 = TechnicalAnalysis.calculate_ema(data['close'], 55)
            ema89 = TechnicalAnalysis.calculate_ema(data['close'], 89)
            
            # RSI
            rsi2 = TechnicalAnalysis.calculate_rsi(data['close'], 2)
            
            # Stochastic
            stoch_k, stoch_d = TechnicalAnalysis.calculate_stochastic(
                data['high'], data['low'], data['close'], k_period=8, d_period=3
            )
            
            # ADX
            adx = TechnicalAnalysis.calculate_adx(
                data['high'], data['low'], data['close'], 13
            )
            
            # Get latest values (handle NaN)
            indicators = {
                'ema8': ema8.iloc[-1] if not pd.isna(ema8.iloc[-1]) else 0,
                'ema21': ema21.iloc[-1] if not pd.isna(ema21.iloc[-1]) else 0,
                'ema34': ema34.iloc[-1] if not pd.isna(ema34.iloc[-1]) else 0,
                'ema55': ema55.iloc[-1] if not pd.isna(ema55.iloc[-1]) else 0,
                'ema89': ema89.iloc[-1] if not pd.isna(ema89.iloc[-1]) else 0,
                'rsi2': rsi2.iloc[-1] if not pd.isna(rsi2.iloc[-1]) else 50,
                'stoch_k': stoch_k.iloc[-1] if not pd.isna(stoch_k.iloc[-1]) else 50,
                'stoch_d': stoch_d.iloc[-1] if not pd.isna(stoch_d.iloc[-1]) else 50,
                'adx': adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0,
                'avg_volume': data['volume'].tail(20).mean()
            }
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            # Return default values
            return {
                'ema8': 0, 'ema21': 0, 'ema34': 0, 'ema55': 0, 'ema89': 0,
                'rsi2': 50, 'stoch_k': 50, 'stoch_d': 50, 'adx': 0,
                'avg_volume': 0
            }
    
    @staticmethod
    def evaluate_bullish_criteria(data: pd.DataFrame) -> Dict:
        """Evaluate all bullish criteria for a stock"""
        try:
            indicators = TechnicalAnalysis.get_latest_indicators(data)
            
            # Check EMA sequence (8 > 21 > 34 > 55 > 89)
            ema_bullish = (
                indicators['ema8'] > indicators['ema21'] > 
                indicators['ema34'] > indicators['ema55'] > 
                indicators['ema89']
            )
            
            # Check Stochastic <= 40
            stoch_condition = indicators['stoch_k'] <= 40
            
            # Check RSI(2) <= 10 within last 5 days
            rsi_condition = TechnicalAnalysis.check_rsi_condition(data, 10, 5, above=False)
            
            # General criteria
            adx_condition = indicators['adx'] >= 20
            volume_condition = indicators['avg_volume'] > 500000
            
            return {
                'ema_bullish': ema_bullish,
                'stoch_condition': stoch_condition,
                'rsi_condition': rsi_condition,
                'adx_condition': adx_condition,
                'volume_condition': volume_condition,
                'all_criteria_met': (ema_bullish and stoch_condition and rsi_condition and 
                                   adx_condition and volume_condition),
                'indicators': indicators
            }
            
        except Exception as e:
            logger.error(f"Error evaluating bullish criteria: {e}")
            return {
                'ema_bullish': False, 'stoch_condition': False, 'rsi_condition': False,
                'adx_condition': False, 'volume_condition': False,
                'all_criteria_met': False, 'indicators': {}
            }
    
    @staticmethod
    def evaluate_bearish_criteria(data: pd.DataFrame) -> Dict:
        """Evaluate all bearish criteria for a stock"""
        try:
            indicators = TechnicalAnalysis.get_latest_indicators(data)
            
            # Check EMA sequence (8 < 21 < 34 < 55 < 89)
            ema_bearish = (
                indicators['ema8'] < indicators['ema21'] < 
                indicators['ema34'] < indicators['ema55'] < 
                indicators['ema89']
            )
            
            # Check Stochastic >= 60
            stoch_condition = indicators['stoch_k'] >= 60
            
            # Check RSI(2) >= 90 within last 5 days
            rsi_condition = TechnicalAnalysis.check_rsi_condition(data, 90, 5, above=True)
            
            # General criteria
            adx_condition = indicators['adx'] >= 20
            volume_condition = indicators['avg_volume'] > 500000
            
            return {
                'ema_bearish': ema_bearish,
                'stoch_condition': stoch_condition,
                'rsi_condition': rsi_condition,
                'adx_condition': adx_condition,
                'volume_condition': volume_condition,
                'all_criteria_met': (ema_bearish and stoch_condition and rsi_condition and 
                                   adx_condition and volume_condition),
                'indicators': indicators
            }
            
        except Exception as e:
            logger.error(f"Error evaluating bearish criteria: {e}")
            return {
                'ema_bearish': False, 'stoch_condition': False, 'rsi_condition': False,
                'adx_condition': False, 'volume_condition': False,
                'all_criteria_met': False, 'indicators': {}
            } 
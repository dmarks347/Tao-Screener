"""
Configuration settings for Tao Stock Screener
"""

import os
from typing import Dict, Any

class Config:
    """Configuration class for the stock screener"""
    
    # Webull API Configuration
    # TODO: Set these environment variables or update with your Webull API credentials
    WEBULL_API_KEY = os.getenv('WEBULL_API_KEY', '')
    WEBULL_SECRET_KEY = os.getenv('WEBULL_SECRET_KEY', '')
    WEBULL_USERNAME = os.getenv('WEBULL_USERNAME', '')
    WEBULL_PASSWORD = os.getenv('WEBULL_PASSWORD', '')
    
    # Screening Criteria
    SCREENING_CRITERIA = {
        'general': {
            'min_market_cap': 1000,  # Million USD
            'min_adx': 20,
            'min_avg_volume': 500000
        },
        'bullish': {
            'ema_sequence_ascending': True,  # 8 > 21 > 34 > 55 > 89
            'stochastic_max': 40,
            'rsi2_max': 10,
            'rsi2_lookback_days': 5
        },
        'bearish': {
            'ema_sequence_descending': True,  # 8 < 21 < 34 < 55 < 89
            'stochastic_min': 60,
            'rsi2_min': 90,
            'rsi2_lookback_days': 5
        }
    }
    
    # Technical Indicator Periods
    INDICATOR_PERIODS = {
        'ema_periods': [8, 21, 34, 55, 89],
        'rsi_period': 2,
        'stochastic_k_period': 8,
        'stochastic_d_period': 3,
        'adx_period': 13
    }
    
    # Data Configuration
    DATA_CONFIG = {
        'historical_period': '1y',  # 1 year of data
        'min_data_points': 100,     # Minimum data points required
        'rate_limit_delay': 0.1,    # Delay between API calls (seconds)
        'max_concurrent_requests': 10
    }
    
    # Streamlit Configuration
    STREAMLIT_CONFIG = {
        'page_title': 'Tao Stock Screener',
        'page_icon': '📈',
        'layout': 'wide',
        'cache_ttl': 3600  # Cache time-to-live in seconds (1 hour)
    }
    
    # Logging Configuration
    LOGGING_CONFIG = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': 'tao_screener.log'
    }
    
    # Export Configuration
    EXPORT_CONFIG = {
        'default_filename': 'tao_screener_results',
        'include_timestamp': True,
        'file_format': 'csv'
    }
    
    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        """Get all configuration settings as a dictionary"""
        return {
            'webull_api_configured': bool(cls.WEBULL_API_KEY),
            'screening_criteria': cls.SCREENING_CRITERIA,
            'indicator_periods': cls.INDICATOR_PERIODS,
            'data_config': cls.DATA_CONFIG,
            'streamlit_config': cls.STREAMLIT_CONFIG,
            'logging_config': cls.LOGGING_CONFIG,
            'export_config': cls.EXPORT_CONFIG
        }
    
    @classmethod
    def validate_config(cls) -> Dict[str, bool]:
        """Validate configuration settings"""
        validation = {
            'webull_credentials': bool(cls.WEBULL_API_KEY and cls.WEBULL_SECRET_KEY),
            'screening_criteria_valid': all([
                cls.SCREENING_CRITERIA['general']['min_market_cap'] > 0,
                cls.SCREENING_CRITERIA['general']['min_adx'] > 0,
                cls.SCREENING_CRITERIA['general']['min_avg_volume'] > 0
            ]),
            'indicator_periods_valid': all([
                len(cls.INDICATOR_PERIODS['ema_periods']) == 5,
                cls.INDICATOR_PERIODS['rsi_period'] > 0,
                cls.INDICATOR_PERIODS['adx_period'] > 0
            ])
        }
        
        return validation

# Environment-specific configurations
class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    DATA_CONFIG = Config.DATA_CONFIG.copy()
    DATA_CONFIG.update({
        'rate_limit_delay': 0.05,  # Faster for development
        'max_concurrent_requests': 5  # Lower for development
    })

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    DATA_CONFIG = Config.DATA_CONFIG.copy()
    DATA_CONFIG.update({
        'rate_limit_delay': 0.2,   # Conservative for production
        'max_concurrent_requests': 15  # Can handle more in production
    })

# Select configuration based on environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()

if ENVIRONMENT == 'production':
    config = ProductionConfig()
else:
    config = DevelopmentConfig()

# Instructions for setting up Webull API
WEBULL_SETUP_INSTRUCTIONS = """
To set up Webull API access:

1. Create a Webull account at https://www.webull.com/
2. Apply for API access through Webull's developer portal
3. Once approved, you'll receive API credentials
4. Set the following environment variables:
   - WEBULL_API_KEY: Your API key
   - WEBULL_SECRET_KEY: Your secret key
   - WEBULL_USERNAME: Your Webull username
   - WEBULL_PASSWORD: Your Webull password

Alternatively, you can directly modify the config.py file with your credentials
(not recommended for production).

For development/testing, the screener will use yfinance as a fallback data source.
""" 
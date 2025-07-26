#!/usr/bin/env python3
"""
Standalone Coinbase Advanced Trade Market Making Bot - Avellaneda-Stoikov Strategy
© 2025 - Professional Cryptocurrency Trading Solutions
Adapted from Bybit version for Coinbase Advanced Trade

INSTRUCTIONS:
1. Edit the API_KEY, API_SECRET, and API_PASSPHRASE below with your Coinbase credentials
2. Adjust trading parameters if needed (or leave defaults)
3. Run: python coinbase_market_maker.py

COINBASE SETUP:
1. Go to https://www.coinbase.com/settings/api
2. Create new API key with trading permissions
3. Copy API Key, Secret Key, and Passphrase
4. Set sandbox=True for testing on sandbox-api.coinbase.com
"""

import ccxt
import time
import math
import os
import sys
from datetime import datetime
from collections import deque
import statistics
import logging
from typing import Dict, Tuple, Optional, Any

# ============================================================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================================================

# Coinbase Advanced Trade API Credentials (REQUIRED)
API_KEY = "YOUR_API_KEY"  # Replace with your actual API key
API_SECRET = "YOUR_API_SECRET"  # Replace with your actual API secret  
API_PASSPHRASE = "YOUR_API_PASSPHRASE"  # Replace with your actual passphrase
SANDBOX_MODE = False  # Set to True for sandbox testing

# Trading Configuration
SYMBOL = "ETH-USD"  # ETH spot trading pair (Coinbase format)
ORDER_SIZE_USD = 50.0  # Fixed order size in USD (Coinbase minimum ~$1)
ORDER_SIZE_PERCENT = 0.02  # Fallback percentage if fixed size fails

# Avellaneda-Stoikov Parameters (Adapted for Spot Trading)
GAMMA = 0.01  # Risk aversion parameter (γ) - Controls spread width
K = 5.0  # Market impact parameter (k) - For fill intensity modeling  
ALPHA = 0.001  # Inventory penalty parameter (α) - Separate from gamma
TIME_HORIZON = 0.1  # Time horizon in hours (6 minutes) - rolling calculation
SIGMA_LOOKBACK = 50  # Price history length for volatility
UPDATE_FREQUENCY = 2.0  # Update quotes every 2 seconds (Coinbase rate limits)

# Risk Management (Spot Trading Adapted)
MAX_INVENTORY_USD = 500.0  # Maximum inventory in USD (higher for spot)
MIN_SPREAD_BPS = 5.0  # Minimum spread in basis points (wider for spot)
MAX_SPREAD_BPS = 50.0  # Maximum spread in basis points

# ============================================================================
# BOT CODE - NO NEED TO EDIT BELOW THIS LINE
# ============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('coinbase_market_maker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CoinbaseMarketMaker:
    """Standalone Coinbase Advanced Trade market maker with hardcoded configuration"""
    
    def __init__(self):
        """Initialize the market maker with hardcoded configuration"""
        self.exchange = None
        self.symbol = SYMBOL
        self.base_asset = SYMBOL.split('-')[0]  # ETH
        self.quote_asset = SYMBOL.split('-')[1]  # USD
        self.price_history = deque(maxlen=SIGMA_LOOKBACK)
        self.inventory = 0  # In base asset (ETH)
        self.pnl = 0
        self.trades_count = 0
        self.current_orders = {'bid': None, 'ask': None}
        self.volatility = 0.01
        self.running = False
        self.last_trade_check = 0
        
        # Timing - use strategy start time instead of wall clock
        self.start_time = time.time()
        
        # Validate configuration
        self._validate_config()
        
    def _validate_config(self) -> None:
        """Validate the hardcoded configuration"""
        if not API_KEY or API_KEY == "YOUR_API_KEY":
            logger.error("Please set your actual Coinbase API_KEY in the configuration section")
            sys.exit(1)
            
        if not API_SECRET or API_SECRET == "YOUR_API_SECRET":
            logger.error("Please set your actual Coinbase API_SECRET in the configuration section")
            sys.exit(1)
            
        if not API_PASSPHRASE or API_PASSPHRASE == "YOUR_API_PASSPHRASE":
            logger.error("Please set your actual Coinbase API_PASSPHRASE in the configuration section")
            sys.exit(1)
            
        logger.info("Configuration validated successfully")
    
    def initialize_exchange(self) -> None:
        """Initialize the Coinbase Advanced Trade exchange connection"""
        exchange_config = {
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'password': API_PASSPHRASE,  # Coinbase requires passphrase
            'enableRateLimit': True,
            'rateLimit': 1000,  # Coinbase rate limit: 10 requests per second
            'timeout': 30000,
            'options': {
                'fetchMyTradesMethod': 'privateGetFills',  # Coinbase specific
            }
        }
        
        # Set sandbox mode if enabled
        if SANDBOX_MODE:
            exchange_config['sandbox'] = True
            logger.info("Running in SANDBOX mode (sandbox-api.coinbase.com)")
        
        # Initialize Coinbase exchange
        self.exchange = ccxt.coinbase(exchange_config)
        
        # Load markets
        try:
            self.exchange.load_markets()
            logger.info("Successfully connected to Coinbase Advanced Trade")
        except Exception as e:
            logger.error(f"Failed to connect to Coinbase: {e}")
            raise
    
    def validate_symbol(self) -> None:
        """Validate and set the trading symbol"""
        if self.symbol not in self.exchange.markets:
            available_symbols = [s for s in self.exchange.markets.keys() if 'USD' in s]
            logger.error(f"Symbol {self.symbol} not found. Available symbols: {available_symbols[:10]}...")
            raise ValueError(f"Invalid symbol: {self.symbol}")
        
        market = self.exchange.markets[self.symbol]
        logger.info(f"Trading symbol: {self.symbol}")
        logger.info(f"Min order size: {market['limits']['amount']['min']}")
        logger.info(f"Price precision: {market['precision']['price']}")
        logger.info(f"Amount precision: {market['precision']['amount']}")
    
    def calculate_volatility(self) -> float:
        """Calculate realized volatility from price history"""
        if len(self.price_history) < 2:
            return self.volatility
        
        returns = []
        for i in range(1, len(self.price_history)):
            ret = math.log(self.price_history[i] / self.price_history[i-1])
            returns.append(ret)
        
        if len(returns) > 1:
            self.volatility = statistics.stdev(returns) * math.sqrt(3600)
            self.volatility = max(self.volatility, 0.001)
        
        return self.volatility
    
    def calculate_reservation_price(self, mid_price: float) -> float:
        """Calculate reservation price with proper inventory penalty"""
        sigma = self.calculate_volatility()
        time_remaining = self.get_time_remaining()
        
        # A-S formula: r = m - α * q * σ² * T
        inventory_penalty = ALPHA * self.inventory * sigma**2 * time_remaining
        reservation_price = mid_price - inventory_penalty
        
        return reservation_price
    
    def get_time_remaining(self) -> float:
        """Get time remaining in current strategy horizon"""
        elapsed_hours = (time.time() - self.start_time) / 3600
        cycle_position = elapsed_hours % TIME_HORIZON
        time_remaining = TIME_HORIZON - cycle_position
        return max(time_remaining, 0.01)  # Minimum time remaining
    
    def calculate_optimal_spread(self, mid_price: float) -> float:
        """Calculate optimal bid-ask spread using Avellaneda-Stoikov"""
        sigma = self.calculate_volatility()
        time_remaining = self.get_time_remaining()
        
        # A-S optimal spread: δ* = γσ²T + (2/γ)ln(1 + γ/k)
        risk_term = GAMMA * sigma**2 * time_remaining
        market_impact_term = (2 / GAMMA) * math.log(1 + GAMMA / K)
        
        spread = risk_term + market_impact_term
        
        # Minimum spread constraint (wider for spot trading)
        min_spread = (MIN_SPREAD_BPS / 10000) * mid_price
        spread = max(spread * mid_price, min_spread)
        
        # Maximum spread constraint
        max_spread = (MAX_SPREAD_BPS / 10000) * mid_price
        spread = min(spread, max_spread)
        
        return spread
    
    def calculate_quote_prices(self, mid_price: float) -> Tuple[float, float]:
        """Calculate optimal bid and ask prices"""
        reservation_price = self.calculate_reservation_price(mid_price)
        spread = self.calculate_optimal_spread(mid_price)
        
        # Calculate base bid and ask around reservation price
        bid_price = reservation_price - spread / 2
        ask_price = reservation_price + spread / 2
        
        # Ensure minimum distance from mid price
        min_spread_from_mid = mid_price * 0.001  # 10 bps minimum from mid
        bid_price = min(bid_price, mid_price - min_spread_from_mid)
        ask_price = max(ask_price, mid_price + min_spread_from_mid)
        
        # Round to exchange precision
        market = self.exchange.markets[self.symbol]
        price_precision = market['precision']['price']
        
        if isinstance(price_precision, int):
            bid_price = round(bid_price, price_precision)
            ask_price = round(ask_price, price_precision)
        else:
            # Handle tick size
            tick_size = float(price_precision)
            bid_price = round(bid_price / tick_size) * tick_size
            ask_price = round(ask_price / tick_size) * tick_size
        
        return bid_price, ask_price
    
    def calculate_position_size(self, price: float) -> float:
        """Calculate position size based on configuration (in base asset)"""
        market = self.exchange.markets[self.symbol]
        min_size = market['limits']['amount']['min']
        
        # Convert USD size to base asset amount
        base_size = ORDER_SIZE_USD / price
        
        # Inventory adjustment - reduce size when inventory is high
        inventory_value = abs(self.inventory * price)
        
        if inventory_value > MAX_INVENTORY_USD * 0.7:
            size_multiplier = 0.5
        elif inventory_value > MAX_INVENTORY_USD * 0.5:
            size_multiplier = 0.75
        else:
            size_multiplier = 1.0
        
        size = base_size * size_multiplier
        
        # Round to exchange precision
        amount_precision = market['precision']['amount']
        if isinstance(amount_precision, int):
            size = round(size, amount_precision)
        else:
            # Handle lot size
            lot_size = float(amount_precision)
            size = round(size / lot_size) * lot_size
        
        return max(size, min_size or 0.001)
    
    def get_available_balance(self) -> Dict[str, float]:
        """Get available balance for both base and quote assets"""
        try:
            balance = self.exchange.fetch_balance()
            return {
                'base': balance.get(self.base_asset, {}).get('free', 0),
                'quote': balance.get(self.quote_asset, {}).get('free', 0)
            }
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {'base': 0, 'quote': 0}
    
    def cancel_all_orders(self) -> None:
        """Cancel all open orders"""
        try:
            open_orders = self.exchange.fetch_open_orders(self.symbol)
            for order in open_orders:
                try:
                    self.exchange.cancel_order(order['id'], self.symbol)
                except Exception as e:
                    logger.warning(f"Could not cancel order {order['id']}: {e}")
            
            self.current_orders = {'bid': None, 'ask': None}
            logger.info(f"Cancelled {len(open_orders)} orders")
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
    
    def place_orders(self, bid_price: float, ask_price: float, size: float) -> None:
        """Place bid and ask orders"""
        self.cancel_all_orders()
        
        # Check balances before placing orders
        balances = self.get_available_balance()
        
        # Place bid order (need quote asset)
        if balances['quote'] >= bid_price * size:
            try:
                bid_order = self.exchange.create_limit_order(
                    self.symbol, 'buy', size, bid_price
                )
                self.current_orders['bid'] = bid_order
                logger.info(f"Bid placed: {size:.6f} {self.base_asset} @ ${bid_price:.2f}")
            except Exception as e:
                logger.error(f"Error placing bid: {e}")
        else:
            logger.warning(f"Insufficient {self.quote_asset} balance for bid: {balances['quote']:.2f}")
        
        # Place ask order (need base asset)
        if balances['base'] >= size:
            try:
                ask_order = self.exchange.create_limit_order(
                    self.symbol, 'sell', size, ask_price
                )
                self.current_orders['ask'] = ask_order
                logger.info(f"Ask placed: {size:.6f} {self.base_asset} @ ${ask_price:.2f}")
            except Exception as e:
                logger.error(f"Error placing ask: {e}")
        else:
            logger.warning(f"Insufficient {self.base_asset} balance for ask: {balances['base']:.6f}")
    
    def update_inventory(self) -> None:
        """Update inventory from recent trades"""
        try:
            # Only check trades every 30 seconds to avoid rate limits
            current_time = time.time()
            if current_time - self.last_trade_check < 30:
                return
            
            self.last_trade_check = current_time
            since = int((current_time - 300) * 1000)  # Last 5 minutes
            
            # Fetch recent trades
            trades = self.exchange.fetch_my_trades(self.symbol, since=since, limit=50)
            
            # Calculate net inventory change
            net_inventory = 0
            for trade in trades:
                if trade['timestamp'] > since:
                    if trade['side'] == 'buy':
                        net_inventory += trade['amount']
                    else:
                        net_inventory -= trade['amount']
                    
                    self.trades_count += 1
                    
                    # Update PnL (subtract fees)
                    fee = trade.get('fee', {}).get('cost', 0)
                    self.pnl -= fee
                    
                    logger.info(f"Trade: {trade['side']} {trade['amount']:.6f} @ ${trade['price']:.2f}")
            
            # Update total inventory
            self.inventory += net_inventory
            
        except Exception as e:
            logger.error(f"Error updating inventory: {e}")
    
    def display_status(self, mid_price: float, bid_price: float, ask_price: float, size: float) -> None:
        """Display current bot status"""
        spread = ask_price - bid_price
        spread_bps = (spread / mid_price) * 10000
        balances = self.get_available_balance()
        inventory_value = self.inventory * mid_price
        time_remaining = self.get_time_remaining()
        
        print(f"\n{'='*80}")
        print(f"{self.base_asset}: ${mid_price:.2f} | Spread: {spread_bps:.1f}bps | σ: {self.volatility:.3f} | T-rem: {time_remaining:.3f}h")
        print(f"Inventory: {self.inventory:.6f} {self.base_asset} (${inventory_value:.2f}) | Target: 0")
        print(f"Quotes: ${bid_price:.2f} / ${ask_price:.2f} | Size: {size:.6f} {self.base_asset}")
        print(f"Stats: {self.trades_count} trades | PnL: ${self.pnl:.2f}")
        print(f"Balance: {balances['base']:.6f} {self.base_asset} | ${balances['quote']:.2f} {self.quote_asset}")
        
        # Risk indicators
        inventory_percent = abs(inventory_value) / MAX_INVENTORY_USD * 100
        if inventory_percent > 70:
            print(f"⚠️  HIGH INVENTORY RISK: {inventory_percent:.1f}%")
        elif inventory_percent > 50:
            print(f"⚡ MEDIUM INVENTORY: {inventory_percent:.1f}%")
        else:
            print(f"✅ INVENTORY OK: {inventory_percent:.1f}%")
    
    def run(self) -> None:
        """Main bot loop"""
        print("🚀 Starting Standalone Coinbase Advanced Trade Market Maker Bot")
        print(f"📋 Configuration:")
        print(f"   Symbol: {SYMBOL}")
        print(f"   Order Size: ${ORDER_SIZE_USD} USD")
        print(f"   Max Inventory: ${MAX_INVENTORY_USD}")
        print(f"   Update Frequency: {UPDATE_FREQUENCY}s")
        print(f"   Parameters: γ={GAMMA}, k={K}, T={TIME_HORIZON}h")
        print(f"   Spread Range: {MIN_SPREAD_BPS}-{MAX_SPREAD_BPS} bps")
        print(f"   Sandbox Mode: {SANDBOX_MODE}")
        
        # Initialize exchange
        self.initialize_exchange()
        self.validate_symbol()
        
        self.running = True
        
        logger.info("Bot started successfully!")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Fetch orderbook
                orderbook = self.exchange.fetch_order_book(self.symbol)
                if not orderbook['bids'] or not orderbook['asks']:
                    logger.warning("Empty orderbook, retrying...")
                    time.sleep(2)
                    continue
                
                # Calculate mid price
                best_bid = orderbook['bids'][0][0]
                best_ask = orderbook['asks'][0][0]
                mid_price = (best_bid + best_ask) / 2
                
                # Update price history
                self.price_history.append(mid_price)
                
                # Update inventory
                self.update_inventory()
                
                # Check risk limits
                inventory_value = abs(self.inventory * mid_price)
                
                if inventory_value > MAX_INVENTORY_USD:
                    logger.warning(f"🚨 INVENTORY LIMIT REACHED: ${inventory_value:.2f} > ${MAX_INVENTORY_USD}")
                    self.cancel_all_orders()
                    time.sleep(10)
                    continue
                
                # Calculate quotes
                bid_price, ask_price = self.calculate_quote_prices(mid_price)
                size = self.calculate_position_size(mid_price)
                
                # Display status
                self.display_status(mid_price, bid_price, ask_price, size)
                
                # Place orders
                self.place_orders(bid_price, ask_price, size)
                
                # Sleep until next update
                elapsed = time.time() - start_time
                sleep_time = max(0, UPDATE_FREQUENCY - elapsed)
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)
        
        # Cleanup
        self.cancel_all_orders()
        logger.info("🛑 Bot stopped")
    
    def stop(self) -> None:
        """Stop the bot"""
        self.running = False


def main():
    """Main entry point"""
    print("=" * 70)
    print("🎯 STANDALONE COINBASE ADVANCED TRADE MARKET MAKER")
    print("📈 Avellaneda-Stoikov Strategy")
    print("💎 Spot Trading Optimized")
    print("=" * 70)
    
    # Create and run bot
    bot = CoinbaseMarketMaker()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
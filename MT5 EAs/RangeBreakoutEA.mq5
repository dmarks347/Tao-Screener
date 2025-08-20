// +------------------------------------------------------------------+
// |                                              RangeBreakoutEA.mq5 |
// |                                    Copyright 2023, MetaQuotes Ltd |
// |                                             https://www.mql5.com |
// +------------------------------------------------------------------+
#property copyright "Copyright 2023"
#property link      "https://www.mql5.com"
#property version   "1.00"

// Include Trade library
#include <Trade\Trade.mqh>
CTrade trade;

// Input Parameters - Range Detection
input string              RangeStartTime = "03:05";      // Range Start Time (HH:MM)
input int                 RangeDurationHours = 3;        // Range Duration in Hours
input string              SessionEndTime = "18:55";      // Session End Time (HH:MM)

// Input Parameters - Trading Settings
input double              LotSize = 0.1;                 // Trading Lot Size
input bool                UseFixedLot = true;            // Use Fixed Lot Size (true) or Risk-Based (false)
input double              RiskPercent = 1.0;             // Risk Percent of Account (if UseFixedLot=false)
input double              StopLossPercent = 1.0;         // Stop Loss (% of price)
input int                 SlippagePoints = 50;           // Allowed Slippage in Points

// Input Parameters - Visualization
input bool                ShowRangeBox = true;           // Show Range Box on Chart
input color               RangeHighColor = clrRed;       // Range High Line Color
input color               RangeLowColor = clrBlue;        // Range Low Line Color
input color               RangeBackgroundColor = clrPink;  // Range Background Color
input int                 RangeBackgroundAlpha = 30;      // Range Background Transparency (0-255)
input int                 RangeBoxWidth = 2;              // Range Box Line Width

// Input Parameters - Debug Options
input bool                EnableDebugMode = true;         // Enable Detailed Debug Output

// Global Variables
datetime rangeStartTime;         // Range start datetime
datetime rangeEndTime;           // Range end datetime
datetime sessionEndTime;         // Session end datetime
double rangeHigh = 0;            // Range high price
double rangeLow = 0;             // Range low price
bool rangeDetected = false;      // Flag to track if range is detected
bool ordersPlaced = false;       // Flag to track if breakout orders are placed
ulong buyStopTicket = 0;         // Ticket of buy stop order
ulong sellStopTicket = 0;        // Ticket of sell stop order
int magicNumber = 12345;         // Magic number for this EA

//+------------------------------------------------------------------+
//| Helper function for printing debug info                           |
//+------------------------------------------------------------------+
void DebugPrint(string message)
{
   if(EnableDebugMode)
      Print("[DEBUG] ", TimeToString(TimeCurrent()), ": ", message);
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize the random seed
   MathSrand(GetTickCount());
   
   // Set magic number
   magicNumber = 12345 + MathRand() % 1000;
   trade.SetExpertMagicNumber(magicNumber);
   
   // Reset flags
   rangeDetected = false;
   ordersPlaced = false;
   
   // Initialize times
   SetupTimes();

   // Display EA status
   Comment("RangeBreakoutEA initialized");
   
   DebugPrint("EA Initialized with magic number: " + IntegerToString(magicNumber));
   DebugPrint("Current symbol: " + _Symbol + ", Period: " + EnumToString((ENUM_TIMEFRAMES)_Period));
   DebugPrint("Settings: Range start at " + RangeStartTime + ", Duration: " + IntegerToString(RangeDurationHours) + "h, Session end: " + SessionEndTime);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Clean up objects
   ObjectsDeleteAll(0, "RangeBox");
   ObjectDelete(0, "RangeBoxHighLabel");
   ObjectDelete(0, "RangeBoxLowLabel");
   ObjectDelete(0, "RangeBoxBackground");
   Comment("");
   
   DebugPrint("EA Deinitialized, reason: " + IntegerToString(reason));
   
   // Close positions
   CloseAllPositions();
   
   // Delete pending orders
   DeleteAllPendingOrders();
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Get current time and check if it's a new day
   datetime currentTime = TimeCurrent();
   
   // If debug enabled, periodically output status (once per minute)
   static datetime lastDebugTime = 0;
   if(EnableDebugMode && currentTime >= lastDebugTime + 60)
   {
      lastDebugTime = currentTime;
      DebugPrint("Current time: " + TimeToString(currentTime) + 
                " | Range detected: " + (rangeDetected ? "Yes" : "No") + 
                " | Orders placed: " + (ordersPlaced ? "Yes" : "No") +
                " | Range: " + DoubleToString(rangeHigh, _Digits) + "/" + DoubleToString(rangeLow, _Digits) +
                " | Positions: " + IntegerToString(PositionsTotal()) +
                " | Orders: " + IntegerToString(OrdersTotal()));
   }
   
   // If it's a new day, reset the times and flags
   static datetime lastDay = 0;
   datetime today = StringToTime(TimeToString(currentTime, TIME_DATE));
   
   if(today != lastDay)
   {
      lastDay = today;
      SetupTimes();
      rangeDetected = false;
      ordersPlaced = false;
      rangeHigh = 0;
      rangeLow = 0;
      DeleteAllPendingOrders();
      DebugPrint("New day detected. Times reset, flags cleared.");
   }
   
   // Check if we should detect range
   if(!rangeDetected && currentTime >= rangeStartTime && currentTime < rangeEndTime)
   {
      DetectRange();
      if(!rangeDetected)
         DebugPrint("Range detection in progress... Current High: " + DoubleToString(rangeHigh, _Digits) + " Low: " + DoubleToString(rangeLow, _Digits));
   }
   else if(!rangeDetected && currentTime < rangeStartTime)
   {
      DebugPrint("Waiting for range detection to start at " + TimeToString(rangeStartTime) + " (in " + 
                 IntegerToString((int)(rangeStartTime - currentTime)) + " seconds)");
   }
   
   // Check if range detection period is complete and orders are not placed yet
   if(!ordersPlaced && rangeDetected && currentTime >= rangeEndTime)
   {
      DebugPrint("Range detected and period ended. Placing breakout orders...");
      PlaceBreakoutOrders();
      ordersPlaced = true;
   }
   
   // Check if it's time to close positions at session end
   if(currentTime >= sessionEndTime)
   {
      DebugPrint("Session end time reached. Closing positions and deleting orders.");
      CloseAllPositions();
      DeleteAllPendingOrders();
   }
   
   // Check if one of the orders was filled
   if(ordersPlaced)
   {
      CheckOrderStatus();
   }
   
   // Update info display
   if(rangeDetected)
   {
      Comment("Range detected: High=", rangeHigh, " Low=", rangeLow, 
              "\nOrders placed: ", ordersPlaced ? "Yes" : "No",
              "\nBuy ticket: ", buyStopTicket, 
              "\nSell ticket: ", sellStopTicket,
              "\nCurrent time: ", TimeToString(currentTime));
   }
}

//+------------------------------------------------------------------+
//| Setup daily times for EA operation                               |
//+------------------------------------------------------------------+
void SetupTimes()
{
   datetime now = TimeCurrent();
   string today = TimeToString(now, TIME_DATE);
   
   // Set up range start time
   rangeStartTime = StringToTime(today + " " + RangeStartTime);
   
   // Set up range end time
   rangeEndTime = rangeStartTime + RangeDurationHours * 3600;
   
   // Set up session end time
   sessionEndTime = StringToTime(today + " " + SessionEndTime);
   
   // If session end time is before range start time, it must be for next day
   if(sessionEndTime < rangeStartTime)
   {
      sessionEndTime += 86400; // Add one day in seconds
   }
   
   // If current time is already past range start, check if we should start now
   datetime currentTime = TimeCurrent();
   if(currentTime > rangeStartTime && currentTime < rangeEndTime)
   {
      DebugPrint("Current time is within today's range period. Starting range detection immediately.");
   }
   else if(currentTime > rangeEndTime)
   {
      DebugPrint("WARNING: Current time is already past today's range end time. Will wait until tomorrow.");
   }
   
   DebugPrint("Times set - Range start: " + TimeToString(rangeStartTime) + 
             ", Range end: " + TimeToString(rangeEndTime) + 
             ", Session end: " + TimeToString(sessionEndTime));
}

//+------------------------------------------------------------------+
//| Detect and update price range                                    |
//+------------------------------------------------------------------+
void DetectRange()
{
   double currentHigh = iHigh(_Symbol, PERIOD_CURRENT, 0);
   double currentLow = iLow(_Symbol, PERIOD_CURRENT, 0);
   
   // Check for valid price data
   if(currentHigh <= 0 || currentLow <= 0)
   {
      DebugPrint("Error: Invalid price data. High: " + DoubleToString(currentHigh, _Digits) + 
                 ", Low: " + DoubleToString(currentLow, _Digits));
      return;
   }
   
   // Initialize range values if not set
   if(rangeHigh == 0 || rangeLow == 0)
   {
      rangeHigh = currentHigh;
      rangeLow = currentLow;
      DebugPrint("Range initialized - High: " + DoubleToString(rangeHigh, _Digits) + 
                 ", Low: " + DoubleToString(rangeLow, _Digits));
   }
   
   bool updated = false;
   
   // Update range if new extremes found
   if(currentHigh > rangeHigh)
   {
      rangeHigh = currentHigh;
      updated = true;
   }
      
   if(currentLow < rangeLow)
   {
      rangeLow = currentLow;
      updated = true;
   }
   
   if(updated)
   {
      DebugPrint("Range updated - New High: " + DoubleToString(rangeHigh, _Digits) + 
                 ", New Low: " + DoubleToString(rangeLow, _Digits));
   }
   
   // Draw/update range box on chart if enabled
   if(ShowRangeBox)
   {
      DrawRangeBox();
   }
   
   // Mark range as detected if we're at the end of range period
   if(TimeCurrent() >= rangeEndTime - 1)
   {
      rangeDetected = true;
      DebugPrint("RANGE DETECTION COMPLETE - Final High: " + DoubleToString(rangeHigh, _Digits) + 
                 ", Final Low: " + DoubleToString(rangeLow, _Digits) + 
                 ", Range Size: " + DoubleToString(rangeHigh - rangeLow, _Digits) + " points");
   }
}

//+------------------------------------------------------------------+
//| Draw range box on chart                                          |
//+------------------------------------------------------------------+
void DrawRangeBox()
{
   // Delete previous range box objects if they exist
   ObjectDelete(0, "RangeBoxHigh");
   ObjectDelete(0, "RangeBoxLow");
   ObjectDelete(0, "RangeBoxBackground");
   
   // Calculate date/time for the rectangle
   datetime timeLeft = rangeStartTime;
   datetime timeRight = TimeCurrent() + 24*60*60; // Extend rectangle 1 day to the right
   
   // Draw background rectangle first (so lines appear on top)
   ObjectCreate(0, "RangeBoxBackground", OBJ_RECTANGLE, 0, timeLeft, rangeHigh, timeRight, rangeLow);
   ObjectSetInteger(0, "RangeBoxBackground", OBJPROP_COLOR, RangeBackgroundColor);
   ObjectSetInteger(0, "RangeBoxBackground", OBJPROP_FILL, true);
   ObjectSetInteger(0, "RangeBoxBackground", OBJPROP_BACK, true);
   ObjectSetInteger(0, "RangeBoxBackground", OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, "RangeBoxBackground", OBJPROP_SELECTABLE, false);
   
   // Create a custom alpha color for transparency
   color fillColor = RangeBackgroundColor;
   if(RangeBackgroundAlpha < 255) {
      // Alpha format is 0xAARRGGBB where AA is alpha (transparency)
      int rgb = (int)(ColorToARGB(fillColor) & 0x00FFFFFF); // Extract RGB part, explicit cast to int
      fillColor = (color)(rgb | ((int)RangeBackgroundAlpha << 24)); // Apply alpha, explicit cast to color and int
      ObjectSetInteger(0, "RangeBoxBackground", OBJPROP_COLOR, fillColor);
   }
   
   // Draw high line on top of background
   ObjectCreate(0, "RangeBoxHigh", OBJ_HLINE, 0, 0, rangeHigh);
   ObjectSetInteger(0, "RangeBoxHigh", OBJPROP_COLOR, RangeHighColor);
   ObjectSetInteger(0, "RangeBoxHigh", OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, "RangeBoxHigh", OBJPROP_WIDTH, RangeBoxWidth);
   ObjectSetInteger(0, "RangeBoxHigh", OBJPROP_SELECTABLE, false);
   
   // Draw low line on top of background
   ObjectCreate(0, "RangeBoxLow", OBJ_HLINE, 0, 0, rangeLow);
   ObjectSetInteger(0, "RangeBoxLow", OBJPROP_COLOR, RangeLowColor);
   ObjectSetInteger(0, "RangeBoxLow", OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, "RangeBoxLow", OBJPROP_WIDTH, RangeBoxWidth);
   ObjectSetInteger(0, "RangeBoxLow", OBJPROP_SELECTABLE, false);
   
   // Add labels to show range values
   ObjectCreate(0, "RangeBoxHighLabel", OBJ_TEXT, 0, timeLeft, rangeHigh);
   ObjectSetString(0, "RangeBoxHighLabel", OBJPROP_TEXT, "Range High: " + DoubleToString(rangeHigh, _Digits));
   ObjectSetInteger(0, "RangeBoxHighLabel", OBJPROP_COLOR, RangeHighColor);
   ObjectSetInteger(0, "RangeBoxHighLabel", OBJPROP_FONTSIZE, 10);
   
   ObjectCreate(0, "RangeBoxLowLabel", OBJ_TEXT, 0, timeLeft, rangeLow);
   ObjectSetString(0, "RangeBoxLowLabel", OBJPROP_TEXT, "Range Low: " + DoubleToString(rangeLow, _Digits));
   ObjectSetInteger(0, "RangeBoxLowLabel", OBJPROP_COLOR, RangeLowColor);
   ObjectSetInteger(0, "RangeBoxLowLabel", OBJPROP_FONTSIZE, 10);
}

//+------------------------------------------------------------------+
//| Calculate proper lot size based on account risk                  |
//+------------------------------------------------------------------+
double CalculateLotSize(double stopLossDistance)
{
   if(UseFixedLot)
   {
      DebugPrint("Using fixed lot size: " + DoubleToString(LotSize, 2));
      return LotSize;
   }
      
   // Calculate risk-based lot size
   double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   
   // Calculate the number of ticks in our stop loss
   double numTicks = stopLossDistance / tickSize;
   
   // Calculate risk amount
   double riskAmount = accountBalance * RiskPercent / 100.0;
   
   // Calculate lot size based on risk
   double calculatedLot = riskAmount / (numTicks * tickValue);
   
   // Normalize to allowed lot steps
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   calculatedLot = MathFloor(calculatedLot / lotStep) * lotStep;
   calculatedLot = MathMax(minLot, MathMin(maxLot, calculatedLot));
   
   DebugPrint("Calculated risk-based lot size: " + DoubleToString(calculatedLot, 2) + 
             " (Risk: " + DoubleToString(RiskPercent, 1) + "%, Balance: " + DoubleToString(accountBalance, 2) + 
             ", SL Distance: " + DoubleToString(stopLossDistance, _Digits) + ")");
   
   return calculatedLot;
}

//+------------------------------------------------------------------+
//| Place breakout orders                                            |
//+------------------------------------------------------------------+
void PlaceBreakoutOrders()
{
   // Calculate stop loss distance
   double stopLossDistance = SymbolInfoDouble(_Symbol, SYMBOL_ASK) * StopLossPercent / 100.0;
   
   DebugPrint("Preparing to place breakout orders at High: " + DoubleToString(rangeHigh, _Digits) + 
             " and Low: " + DoubleToString(rangeLow, _Digits));
   DebugPrint("Stop loss distance: " + DoubleToString(stopLossDistance, _Digits) + 
             " (" + DoubleToString(StopLossPercent, 1) + "% of price)");
   
   // Calculate appropriate lot size
   double orderLotSize = CalculateLotSize(stopLossDistance);
   
   // Place Buy Stop order
   trade.SetDeviationInPoints(SlippagePoints);
   if(trade.BuyStop(orderLotSize,
                   rangeHigh,
                   _Symbol,
                   rangeHigh - stopLossDistance,
                   0, // No TP
                   ORDER_TIME_DAY,
                   0,
                   "Range Breakout Buy"))
   {
      buyStopTicket = trade.ResultOrder();
      DebugPrint("BUY STOP ORDER PLACED - Ticket: " + IntegerToString(buyStopTicket) + 
                " at price: " + DoubleToString(rangeHigh, _Digits) + 
                " with SL: " + DoubleToString(rangeHigh - stopLossDistance, _Digits) + 
                " and lot size: " + DoubleToString(orderLotSize, 2));
   }
   else
   {
      int errorCode = (int)trade.ResultRetcode();
      DebugPrint("ERROR PLACING BUY STOP - Code: " + IntegerToString(errorCode) + 
                " Description: " + trade.ResultComment());
   }
   
   // Place Sell Stop order
   if(trade.SellStop(orderLotSize,
                    rangeLow,
                    _Symbol,
                    rangeLow + stopLossDistance,
                    0, // No TP
                    ORDER_TIME_DAY,
                    0,
                    "Range Breakout Sell"))
   {
      sellStopTicket = trade.ResultOrder();
      DebugPrint("SELL STOP ORDER PLACED - Ticket: " + IntegerToString(sellStopTicket) + 
                " at price: " + DoubleToString(rangeLow, _Digits) + 
                " with SL: " + DoubleToString(rangeLow + stopLossDistance, _Digits) + 
                " and lot size: " + DoubleToString(orderLotSize, 2));
   }
   else
   {
      int errorCode = (int)trade.ResultRetcode();
      DebugPrint("ERROR PLACING SELL STOP - Code: " + IntegerToString(errorCode) + 
                " Description: " + trade.ResultComment());
   }
   
   // Verify pending orders
   VerifyPendingOrders();
}

//+------------------------------------------------------------------+
//| Verify that pending orders exist                                 |
//+------------------------------------------------------------------+
void VerifyPendingOrders()
{
   bool buyOrderFound = false;
   bool sellOrderFound = false;
   
   for(int i=0; i<OrdersTotal(); i++)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0)
      {
         if(OrderGetInteger(ORDER_MAGIC) == magicNumber)
         {
            int orderType = (int)OrderGetInteger(ORDER_TYPE);
            double orderPrice = OrderGetDouble(ORDER_PRICE_OPEN);
            
            if(orderType == ORDER_TYPE_BUY_STOP)
            {
               buyOrderFound = true;
               DebugPrint("Verified Buy Stop order - Ticket: " + IntegerToString(ticket) + 
                          " at price: " + DoubleToString(orderPrice, _Digits));
            }
            else if(orderType == ORDER_TYPE_SELL_STOP)
            {
               sellOrderFound = true;
               DebugPrint("Verified Sell Stop order - Ticket: " + IntegerToString(ticket) + 
                          " at price: " + DoubleToString(orderPrice, _Digits));
            }
         }
      }
   }
   
   if(!buyOrderFound && buyStopTicket != 0)
   {
      DebugPrint("WARNING: Buy Stop order with ticket " + IntegerToString(buyStopTicket) + " not found in pending orders!");
   }
   
   if(!sellOrderFound && sellStopTicket != 0)
   {
      DebugPrint("WARNING: Sell Stop order with ticket " + IntegerToString(sellStopTicket) + " not found in pending orders!");
   }
}

//+------------------------------------------------------------------+
//| Check if one of the orders was filled and delete the other       |
//+------------------------------------------------------------------+
void CheckOrderStatus()
{
   // Check if our buy order was filled by looking for an open position
   bool buyFilled = false;
   bool sellFilled = false;
   
   // Check positions
   for(int i=0; i<PositionsTotal(); i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionGetInteger(POSITION_MAGIC) == magicNumber)
         {
            if((int)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
            {
               buyFilled = true;
               double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
               double currentProfit = PositionGetDouble(POSITION_PROFIT);
               DebugPrint("ACTIVE BUY POSITION - Ticket: " + IntegerToString(ticket) + 
                          " opened at: " + DoubleToString(openPrice, _Digits) + 
                          " current profit: " + DoubleToString(currentProfit, 2));
            }
            else if((int)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL)
            {
               sellFilled = true;
               double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
               double currentProfit = PositionGetDouble(POSITION_PROFIT);
               DebugPrint("ACTIVE SELL POSITION - Ticket: " + IntegerToString(ticket) + 
                          " opened at: " + DoubleToString(openPrice, _Digits) + 
                          " current profit: " + DoubleToString(currentProfit, 2));
            }
         }
      }
   }
   
   // If buy was triggered, delete sell stop
   if(buyFilled && sellStopTicket > 0)
   {
      // Check if order still exists before trying to delete
      bool orderExists = false;
      for(int i=0; i<OrdersTotal(); i++)
      {
         if(OrderGetTicket(i) == sellStopTicket)
         {
            orderExists = true;
            break;
         }
      }
      
      if(orderExists)
      {
         DebugPrint("Buy position active, attempting to delete Sell Stop order - Ticket: " + IntegerToString(sellStopTicket));
         if(trade.OrderDelete(sellStopTicket))
         {
            DebugPrint("SUCCESS: Sell Stop order deleted after Buy order filled");
            sellStopTicket = 0;
         }
         else
         {
            DebugPrint("ERROR: Failed to delete Sell Stop order - Error code: " + IntegerToString((int)trade.ResultRetcode()));
         }
      }
      else
      {
         DebugPrint("Sell Stop order already removed, updating ticket reference");
         sellStopTicket = 0;
      }
   }
   // If sell was triggered, delete buy stop
   else if(sellFilled && buyStopTicket > 0)
   {
      // Check if order still exists before trying to delete
      bool orderExists = false;
      for(int i=0; i<OrdersTotal(); i++)
      {
         if(OrderGetTicket(i) == buyStopTicket)
         {
            orderExists = true;
            break;
         }
      }
      
      if(orderExists)
      {
         DebugPrint("Sell position active, attempting to delete Buy Stop order - Ticket: " + IntegerToString(buyStopTicket));
         if(trade.OrderDelete(buyStopTicket))
         {
            DebugPrint("SUCCESS: Buy Stop order deleted after Sell order filled");
            buyStopTicket = 0;
         }
         else
         {
            DebugPrint("ERROR: Failed to delete Buy Stop order - Error code: " + IntegerToString((int)trade.ResultRetcode()));
         }
      }
      else
      {
         DebugPrint("Buy Stop order already removed, updating ticket reference");
         buyStopTicket = 0;
      }
   }
   
   // If no orders are filled, periodically verify our pending orders
   if(!buyFilled && !sellFilled && (buyStopTicket > 0 || sellStopTicket > 0))
   {
      static datetime lastVerifyTime = 0;
      datetime currentTime = TimeCurrent();
      
      if(currentTime >= lastVerifyTime + 300) // Check every 5 minutes
      {
         lastVerifyTime = currentTime;
         VerifyPendingOrders();
      }
   }
}

//+------------------------------------------------------------------+
//| Close all positions opened by this EA                            |
//+------------------------------------------------------------------+
void CloseAllPositions()
{
   int positionsClosed = 0;
   
   for(int i=PositionsTotal()-1; i>=0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionGetInteger(POSITION_MAGIC) == magicNumber)
         {
            string positionType = "Unknown";
            if((int)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
               positionType = "Buy";
            else if((int)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL)
               positionType = "Sell";
               
            DebugPrint("Closing " + positionType + " position - Ticket: " + IntegerToString(ticket));
            
            if(trade.PositionClose(ticket))
            {
               positionsClosed++;
               DebugPrint("SUCCESS: Position closed");
            }
            else
            {
               DebugPrint("ERROR: Failed to close position - Error code: " + IntegerToString((int)trade.ResultRetcode()));
            }
         }
      }
   }
   
   if(positionsClosed > 0)
      DebugPrint("Closed " + IntegerToString(positionsClosed) + " positions");
   else
      DebugPrint("No positions to close");
}

//+------------------------------------------------------------------+
//| Delete all pending orders placed by this EA                      |
//+------------------------------------------------------------------+
void DeleteAllPendingOrders()
{
   int ordersDeleted = 0;
   
   for(int i=OrdersTotal()-1; i>=0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket > 0)
      {
         if(OrderGetInteger(ORDER_MAGIC) == magicNumber)
         {
            int orderType = (int)OrderGetInteger(ORDER_TYPE);
            string orderTypeStr = "Unknown";
            
            if(orderType == ORDER_TYPE_BUY_STOP)
               orderTypeStr = "Buy Stop";
            else if(orderType == ORDER_TYPE_SELL_STOP)
               orderTypeStr = "Sell Stop";
               
            DebugPrint("Deleting " + orderTypeStr + " order - Ticket: " + IntegerToString(ticket));
            
            if(trade.OrderDelete(ticket))
            {
               ordersDeleted++;
               DebugPrint("SUCCESS: Order deleted");
            }
            else
            {
               DebugPrint("ERROR: Failed to delete order - Error code: " + IntegerToString((int)trade.ResultRetcode()));
            }
         }
      }
   }
   
   // Reset order tickets
   buyStopTicket = 0;
   sellStopTicket = 0;
   
   if(ordersDeleted > 0)
      DebugPrint("Deleted " + IntegerToString(ordersDeleted) + " pending orders");
   else
      DebugPrint("No pending orders to delete");
} 
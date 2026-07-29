from __future__ import annotations

from tools.airports import search_airports
from tools.prices import search_flight_prices
from tools.status import get_flight_status
from tools.arrivals_departures import get_airport_arrivals, get_airport_departures
from tools.compare import compare_flight_offers
from tools.price_history import analyze_price_history
from tools.watches import create_price_watch, create_flight_status_watch, cancel_watch
from tools.time_tool import get_current_time

# Tool names here MUST match tools/schemas.py (the function-calling declarations
# sent to the LLM) and the tool list in CLAUDE.md section 4 (get_current_time is
# an extra internal tool, added to ground the model's notion of "now" in the
# real system clock instead of a guess).
TOOL_FUNCTIONS = {
    "search_airports": search_airports,
    "search_flight_prices": search_flight_prices,
    "get_flight_status": get_flight_status,
    "get_airport_arrivals": get_airport_arrivals,
    "get_airport_departures": get_airport_departures,
    "compare_flight_offers": compare_flight_offers,
    "analyze_price_history": analyze_price_history,
    "create_price_watch": create_price_watch,
    "create_flight_status_watch": create_flight_status_watch,
    "cancel_watch": cancel_watch,
    "get_current_time": get_current_time,
}

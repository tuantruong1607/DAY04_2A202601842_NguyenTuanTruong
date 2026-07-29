import type {
  AnalyzePriceHistoryResult,
  AirportScheduleResult,
  ChatResponse,
  CompareFlightOffersResult,
  GetFlightStatusResult,
  PriceOffer,
  SearchAirportsResult,
  SearchFlightPricesResult,
  VersionInfo,
  Watch,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

function callTool<T>(name: string, args: Record<string, unknown>): Promise<T> {
  return request<T>(`/tools/${name}`, { method: "POST", body: JSON.stringify({ args }) });
}

export const api = {
  sendChat(sessionId: string | null, message: string): Promise<ChatResponse> {
    return request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  },
  resetChat(sessionId: string): Promise<void> {
    return request(`/chat/${sessionId}`, { method: "DELETE" });
  },
  getVersion(): Promise<VersionInfo> {
    return request<VersionInfo>("/version");
  },

  searchAirports(query: string): Promise<SearchAirportsResult> {
    return callTool<SearchAirportsResult>("search_airports", { query });
  },

  searchFlightPrices(args: {
    trip_type: "ONE_WAY" | "ROUND_TRIP";
    origin: string;
    destination: string;
    departure_date: string;
    return_date?: string | null;
    cabin_class?: string;
    adults?: number;
    currency?: string;
    max_price?: number | null;
  }): Promise<SearchFlightPricesResult> {
    return callTool<SearchFlightPricesResult>("search_flight_prices", args);
  },

  compareFlightOffers(offers: PriceOffer[]): Promise<CompareFlightOffersResult> {
    return callTool<CompareFlightOffersResult>("compare_flight_offers", { offers });
  },

  analyzePriceHistory(args: {
    origin: string;
    destination: string;
    departure_date: string;
    return_date?: string | null;
    cabin_class?: string;
    currency?: string;
  }): Promise<AnalyzePriceHistoryResult> {
    return callTool<AnalyzePriceHistoryResult>("analyze_price_history", args);
  },

  getFlightStatus(flight_number: string, date?: string): Promise<GetFlightStatusResult> {
    return callTool<GetFlightStatusResult>("get_flight_status", date ? { flight_number, date } : { flight_number });
  },

  getAirportDepartures(airport_code: string, hours = 6): Promise<AirportScheduleResult> {
    return callTool<AirportScheduleResult>("get_airport_departures", { airport_code, hours });
  },
  getAirportArrivals(airport_code: string, hours = 6): Promise<AirportScheduleResult> {
    return callTool<AirportScheduleResult>("get_airport_arrivals", { airport_code, hours });
  },

  createPriceWatch(args: Record<string, unknown>): Promise<{ watch: Watch }> {
    return callTool<{ watch: Watch }>("create_price_watch", args);
  },
  createStatusWatch(args: Record<string, unknown>): Promise<{ watch: Watch }> {
    return callTool<{ watch: Watch }>("create_flight_status_watch", args);
  },
  cancelWatch(watch_id: string): Promise<{ watch?: Watch; error?: string }> {
    return callTool<{ watch?: Watch; error?: string }>("cancel_watch", { watch_id });
  },
  listWatches(): Promise<Watch[]> {
    return request<Watch[]>("/watches");
  },
  checkWatches(watchId?: string): Promise<{ checked: number; alerts: string[] }> {
    return request(`/watches/check`, { method: "POST", body: JSON.stringify({ watch_id: watchId ?? null }) });
  },
};

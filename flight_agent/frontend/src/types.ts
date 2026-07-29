export interface Airport {
  iata: string | null;
  icao: string | null;
  name: string | null;
  city: string | null;
  country: string | null;
  timezone: string | null;
}

export interface SearchAirportsResult {
  tool: string;
  query: string;
  items: Airport[];
  source: string;
  retrieved_at: string;
  error?: string;
  message?: string;
}

export interface FlightSegment {
  flight_number: string | null;
  airline: string | null;
  operating_airline: string | null;
  origin: string | null;
  destination: string | null;
  departure: string | null;
  arrival: string | null;
}

export interface FlightLeg {
  origin: string | null;
  destination: string | null;
  departure: string | null;
  arrival: string | null;
  duration_minutes: number | null;
  stop_count: number | null;
  carriers: string[];
  segments: FlightSegment[];
  flight_numbers: string[];
}

export interface PriceOffer {
  itinerary_id: string;
  price: number;
  currency: string;
  legs: FlightLeg[];
  total_stops: number;
  flight_numbers: string[];
}

export interface SearchFlightPricesResult {
  tool: string;
  trip_type: string;
  origin: string;
  destination: string;
  departure_date: string;
  return_date: string | null;
  cabin_class: string;
  currency: string;
  items: PriceOffer[];
  item_count: number;
  unparsed_count: number;
  source: string;
  retrieved_at: string;
  error?: string;
  message?: string;
}

export interface ComparePick {
  label: "cheapest" | "most_convenient" | "balanced";
  reason: string;
  itinerary_id: string;
  price: number;
  currency: string;
  total_stops: number;
  total_duration_minutes: number | null;
  carriers: string[];
  flight_numbers: string[];
  legs: FlightLeg[];
}

export interface CompareFlightOffersResult {
  tool: string;
  picks: ComparePick[];
  considered_count: number;
  message?: string;
  error?: string;
}

export interface PriceStats {
  count: number;
  min_price?: number;
  max_price?: number;
  avg_price?: number;
  median_price?: number;
  pct_change_first_to_last?: number | null;
  best_price_date?: string;
  currency?: string;
}

export interface AnalyzePriceHistoryResult {
  tool: string;
  origin: string;
  destination: string;
  departure_date: string;
  return_date: string | null;
  cabin_class: string;
  currency: string;
  stats: PriceStats;
  has_history: boolean;
  note: string | null;
  retrieved_at: string;
  error?: string;
}

export interface FlightStatusLegSide {
  airport_iata: string | null;
  scheduled_utc: string | null;
  revised_utc: string | null;
  terminal: string | null;
  gate: string | null;
  delay_minutes: number | null;
}

export interface FlightStatusMatch {
  number: string;
  airline: string | null;
  status: string | null;
  departure: FlightStatusLegSide;
  arrival: FlightStatusLegSide;
}

export interface GetFlightStatusResult {
  tool: string;
  flight_number: string;
  date: string | null;
  matches: FlightStatusMatch[];
  match_count: number;
  source: string;
  retrieved_at: string;
  error?: string;
  message?: string;
}

export interface AirportScheduleFlight {
  number: string;
  airline: string | null;
  status: string | null;
  other_airport_iata: string | null;
  scheduled_local: string | null;
  revised_local: string | null;
  terminal: string | null;
  gate: string | null;
}

export interface AirportScheduleResult {
  tool: string;
  airport: string;
  window_local: { from: string; to: string; timezone: string | null };
  flights: AirportScheduleFlight[];
  flight_count: number;
  source: string;
  retrieved_at: string;
  error?: string;
  message?: string;
}

export interface Watch {
  id: string;
  type: "price" | "status";
  status: "active" | "cancelled";
  created_at: string;
  updated_at?: string;
  origin?: string;
  destination?: string;
  departure_date?: string;
  return_date?: string | null;
  cabin_class?: string;
  currency?: string;
  max_price?: number | null;
  note?: string | null;
  last_price?: number;
  last_alert_price?: number | null;
  last_checked_at?: string;
  flight_number?: string;
  date?: string | null;
  notify_on?: string[];
  delay_threshold_minutes?: number;
  last_status?: string | null;
}

export interface ToolEvent {
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown> | unknown[] | null;
}

export interface ToolRound {
  round: number;
  tool_calls: ToolEvent[];
}

export interface ChatTurn {
  role: "user" | "assistant";
  text: string;
  time?: string;
  toolEvents?: ToolEvent[];
  rounds?: ToolRound[];
  graphTrace?: string[];
  status?: string;
  artifactVersion?: string;
}

export interface ChatResponse {
  session_id: string;
  assistant_text: string;
  status: string;
  tool_events: ToolEvent[];
  graph_trace: string[];
  rounds: ToolRound[];
  artifact_version: string;
}

export interface VersionInfo {
  version: string;
  artifact_version: string;
  prompt_hash: string;
  tools_hash: string;
}

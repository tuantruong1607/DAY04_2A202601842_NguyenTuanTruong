import { BrowserRouter, Route, Routes } from "react-router-dom";
import { NavBar } from "./components/NavBar";
import ChatPage from "./pages/ChatPage";
import SearchComparePage from "./pages/SearchComparePage";
import TrackFlightPage from "./pages/TrackFlightPage";
import AirportBoardPage from "./pages/AirportBoardPage";
import WatchesPage from "./pages/WatchesPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen w-screen overflow-hidden">
        <NavBar />
        <main className="flex-1 overflow-y-auto scrollbar-thin">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/search" element={<SearchComparePage />} />
            <Route path="/track" element={<TrackFlightPage />} />
            <Route path="/board" element={<AirportBoardPage />} />
            <Route path="/watches" element={<WatchesPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

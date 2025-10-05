import {BrowserRouter as Router, Routes, Route, Link, BrowserRouter} from 'react-router-dom';
import { useEffect, useState } from "react";
import HomePage from './components/HomePage';
import ScanHistoryPage from './components/ScanHistory';

function App() {
    const [message, setMessage] = useState("");

    return (
        <BrowserRouter>
            <div className="min-h-screen bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800">
                <nav className="bg-white/10 backdrop-blur-lg p-4">
                    <div className="container mx-auto flex justify-center space-x-6">
                        <Link
                            to="/"
                            className="text-white hover:text-purple-200 font-semibold transition-colors duration-200 flex items-center gap-2"
                        >
                            Home
                        </Link>
                        <Link
                            to="/history"
                            className="text-white hover:text-purple-200 font-semibold transition-colors duration-200 flex items-center gap-2"
                        >
                            Scan History
                        </Link>
                    </div>
                </nav>
                
                <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/history" element={<ScanHistoryPage />} />
                </Routes>
            </div>
        </BrowserRouter>
    );
}

export default App;
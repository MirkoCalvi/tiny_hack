import {BrowserRouter as Router, Routes, Route, Link, BrowserRouter} from 'react-router-dom';
import { useEffect, useState } from "react";
import HomePage from './components/HomePage';
import ScanHistoryPage from './components/ScanHistory';

function App() {
    const [message, setMessage] = useState("");

    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/history" element={<ScanHistoryPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
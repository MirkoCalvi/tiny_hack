import {BrowserRouter as Router, Routes, Route, Link, BrowserRouter} from 'react-router-dom';
import { useEffect, useState } from "react";
import HomePage from './components/HomePage';

function App() {
    const [message, setMessage] = useState("");

    useEffect(() => {
        fetch("/api/hello")
            .then((res) => res.json())
            .then((data) => setMessage(data.message));
    }, []);

    return (
        <BrowserRouter>
            <Routes>
                <Route index path="/" element={<HomePage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;

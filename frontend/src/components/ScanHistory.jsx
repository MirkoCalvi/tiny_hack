import React, { useState, useEffect } from 'react';
import { History, CheckCircle, XCircle, AlertTriangle, Calendar, TrendingUp, Filter } from 'lucide-react';
import {getAllScans} from "../API.js";

export default function ScanHistoryPage() {
    const [scanHistory, setScanHistory] = useState([]);
    const [filterEdibility, setFilterEdibility] = useState('all');
    const [stats, setStats] = useState({ total: 0, edible: 0, toxic: 0, unknown: 0 });

    useEffect(() => {

        const fetchAllScans = async () => {
            const allScans = await getAllScans();
            setScanHistory(allScans);
        }

        fetchAllScans();
    }, []);

    const getEdibilityBadge = (edibility) => {
        const config = {
            edible: { bg: 'bg-green-500', icon: <CheckCircle size={16} />, text: 'Edible' },
            toxic: { bg: 'bg-red-500', icon: <XCircle size={16} />, text: 'Toxic' },
            unknown: { bg: 'bg-yellow-500', icon: <AlertTriangle size={16} />, text: 'Unknown' }
        };
        const c = config[edibility] || config.unknown;
        return (
            <span className={`${c.bg} text-white px-3 py-1 rounded-full text-sm font-semibold flex items-center gap-1 w-fit`}>
                {c.icon} {c.text}
            </span>
        );
    };

    return (
        <div className="min-h-screen w-screen bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800">
            <div className="px-4 py-6 w-full">
                {/* Header */}
                <div className="mb-6">
                    <div className="bg-white/95 backdrop-blur-lg rounded-2xl shadow-2xl p-6">
                        <div className="flex items-center justify-center gap-3 mb-2">
                            <History size={40} className="text-purple-600" />
                            <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-800 text-center">
                                Scan History
                            </h1>
                        </div>
                        <p className="text-gray-600 text-center">Your mushroom detection archive</p>
                        <button className="bg-red-300 text-white hover:bg-gray-300 rounded-5" onClick={() => window.location.href = '/'}>
                            Scan
                        </button>
                    </div>
                </div>

                {/* Statistics Cards */}
                <div className="mb-6 grid grid-cols-2 lg:grid-cols-4 gap-4 max-w-6xl mx-auto">
                    <div className="bg-white/95 backdrop-blur-lg rounded-xl shadow-lg p-4">
                        <div className="flex items-center gap-3">
                            <div className="bg-purple-100 p-3 rounded-lg">
                                <TrendingUp size={24} className="text-purple-600" />
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">Total Scans</p>
                                <p className="text-2xl font-bold text-gray-800">{stats.total}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white/95 backdrop-blur-lg rounded-xl shadow-lg p-4">
                        <div className="flex items-center gap-3">
                            <div className="bg-green-100 p-3 rounded-lg">
                                <CheckCircle size={24} className="text-green-600" />
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">Edible</p>
                                <p className="text-2xl font-bold text-gray-800">{stats.edible}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white/95 backdrop-blur-lg rounded-xl shadow-lg p-4">
                        <div className="flex items-center gap-3">
                            <div className="bg-red-100 p-3 rounded-lg">
                                <XCircle size={24} className="text-red-600" />
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">Toxic</p>
                                <p className="text-2xl font-bold text-gray-800">{stats.toxic}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white/95 backdrop-blur-lg rounded-xl shadow-lg p-4">
                        <div className="flex items-center gap-3">
                            <div className="bg-yellow-100 p-3 rounded-lg">
                                <AlertTriangle size={24} className="text-yellow-600" />
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">Unknown</p>
                                <p className="text-2xl font-bold text-gray-800">{stats.unknown}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Filter */}
                <div className="mb-6 max-w-6xl mx-auto">
                    <div className="bg-white/95 backdrop-blur-lg rounded-xl shadow-lg p-4">
                        <div className="flex items-center gap-3 flex-wrap">
                            <div className="flex items-center gap-2 text-gray-700 font-semibold">
                                <Filter size={20} />
                                <span>Filter:</span>
                            </div>
                            <div className="flex gap-2 flex-wrap">
                                <button
                                    onClick={() => setFilterEdibility('all')}
                                    className={`px-4 py-2 rounded-full font-semibold transition-all ${
                                        filterEdibility === 'all'
                                            ? 'bg-purple-600 text-white'
                                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                                >
                                    All
                                </button>
                                <button
                                    onClick={() => setFilterEdibility('edible')}
                                    className={`px-4 py-2 rounded-full font-semibold transition-all ${
                                        filterEdibility === 'edible'
                                            ? 'bg-green-600 text-white'
                                            : 'bg-gray-50 text-gray-700 hover:bg-gray-300'
                                    }`}
                                >
                                    Edible
                                </button>
                                <button
                                    onClick={() => setFilterEdibility('toxic')}
                                    className={`px-4 py-2 rounded-full font-semibold transition-all ${
                                        filterEdibility === 'toxic'
                                            ? 'bg-red-600 text-white'
                                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                                >
                                    Toxic
                                </button>
                                <button
                                    onClick={() => setFilterEdibility('unknown')}
                                    className={`px-4 py-2 rounded-full font-semibold transition-all ${
                                        filterEdibility === 'unknown'
                                            ? 'bg-yellow-600 text-white'
                                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                                >
                                    Unknown
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* History grouped by date */}
                <div className="max-w-6xl mx-auto">
                    {Object.keys(scanHistory).length === 0 ? (
                        <div className="bg-white/95 backdrop-blur-lg rounded-2xl shadow-2xl p-12">
                            <div className="text-center text-gray-400">
                                <History size={60} className="mb-4 opacity-25 mx-auto" />
                                <p className="text-lg">No scans found with the selected filter.</p>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {Object.entries(scanHistory.items).map((scan) => (
                                <div key={scan.id} className="bg-white/95 backdrop-blur-lg rounded-2xl shadow-2xl p-6">
                                    <div className="space-y-4">
                                        <div key={scan.id} className="border-b border-gray-200 pb-4 last:border-b-0">
                                            <div className="flex flex-col sm:flex-row gap-4">
                                                <img
                                                    src={scan.image_url}
                                                    alt={scan.commonName}
                                                    className="w-full sm:w-48 h-32 object-cover rounded-lg shadow-md"
                                                />
                                                <div className="flex-grow">
                                                    <div className="flex justify-between items-start flex-wrap gap-2 mb-3">
                                                        <div>
                                                            <h5 className="text-xl font-bold text-gray-800">{scan.commonName}</h5>
                                                            <p className="text-gray-600 italic text-sm">{scan.mushroomName}</p>
                                                        </div>
                                                        {getEdibilityBadge(scan.edibility)}
                                                    </div>
                                                    <div className="flex gap-4 flex-wrap text-sm text-gray-600">
                                                            <span>
                                                                <strong>Confidence:</strong> {scan.score}%
                                                            </span>
                                                        <span>
                                                                <strong>Time:</strong> {new Date(scan.timestamp).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}
                                                            </span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
import React, { useState, useEffect } from 'react';
import { History, CheckCircle, XCircle, AlertTriangle, TrendingUp, Filter } from 'lucide-react';
import {getAllScans} from "../API.js";

export default function ScanHistoryPage() {
    const [scanHistory, setScanHistory] = useState([]);
    const [filterEdibility, setFilterEdibility] = useState('all');
    const [stats, setStats] = useState({ total: 0, edible: 0, toxic: 0, unknown: 0 });

    useEffect(() => {

        const fetchAllScans = async () => {
            const allScans = await getAllScans();
            setScanHistory(allScans.items || []);
        }

        fetchAllScans();
    }, []);

    const mushroomClasses = [
        "Agaricus bisporus",
        "Agaricus subrufescens",
        "Amanita bisporigera",
        "Amanita muscaria",
        "Amanita ocreata",
        "Amanita phalloides",
        "Amanita smithiana",
        "Amanita verna",
        "Amanita virosa",
        "Auricularia auricula-judae",
        "Boletus edulis",
        "Cantharellus cibarius",
        "Clitocybe dealbata",
        "Conocybe filaris",
        "Coprinus comatus",
        "Cordyceps sinensis",
        "Cortinarius rubellus",
        "Entoloma sinuatum",
        "Flammulina velutipes",
        "Galerina marginata",
        "Ganoderma lucidum",
        "Grifola frondosa",
        "Gyromitra esculenta",
        "Hericium erinaceus",
        "Hydnum repandum",
        "Hypholoma fasciculare",
        "Inocybe erubescens",
        "Lentinula edodes",
        "Lepiota brunneoincarnata",
        "Macrolepiota procera",
        "Morchella esculenta",
        "Omphalotus olearius",
        "Paxillus involutus",
        "Pholiota nameko",
        "Pleurotus citrinopileatus",
        "Pleurotus eryngii",
        "Pleurotus ostreatus",
        "Psilocybe semilanceata",
        "Rhodophyllus rhodopolius",
        "Russula emetica",
        "Russula virescens",
        "Scleroderma citrinum",
        "Suillus luteus",
        "Tremella fuciformis",
        "Tricholoma matsutake",
        "Truffles",
        "Tuber melanosporum"
    ];

    const mushroomEdibility = {
        "Agaricus bisporus": "edible",
        "Agaricus subrufescens": "edible",
        "Amanita bisporigera": "poisonous",
        "Amanita muscaria": "poisonous",
        "Amanita ocreata": "poisonous",
        "Amanita phalloides": "poisonous",
        "Amanita smithiana": "poisonous",
        "Amanita verna": "poisonous",
        "Amanita virosa": "poisonous",
        "Auricularia auricula-judae": "edible",
        "Boletus edulis": "edible",
        "Cantharellus cibarius": "edible",
        "Clitocybe dealbata": "poisonous",
        "Conocybe filaris": "poisonous",
        "Coprinus comatus": "edible",
        "Cordyceps sinensis": "edible",
        "Cortinarius rubellus": "poisonous",
        "Entoloma sinuatum": "poisonous",
        "Flammulina velutipes": "edible",
        "Galerina marginata": "poisonous",
        "Ganoderma lucidum": "edible",
        "Grifola frondosa": "edible",
        "Gyromitra esculenta": "poisonous",
        "Hericium erinaceus": "edible",
        "Hydnum repandum": "edible",
        "Hypholoma fasciculare": "poisonous",
        "Inocybe erubescens": "poisonous",
        "Lentinula edodes": "edible",
        "Lepiota brunneoincarnata": "poisonous",
        "Macrolepiota procera": "edible",
        "Morchella esculenta": "edible",
        "Omphalotus olearius": "poisonous",
        "Paxillus involutus": "poisonous",
        "Pholiota nameko": "edible",
        "Pleurotus citrinopileatus": "edible",
        "Pleurotus eryngii": "edible",
        "Pleurotus ostreatus": "edible",
        "Psilocybe semilanceata": "poisonous",
        "Rhodophyllus rhodopolius": "poisonous",
        "Russula emetica": "poisonous",
        "Russula virescens": "edible",
        "Scleroderma citrinum": "poisonous",
        "Suillus luteus": "edible",
        "Tremella fuciformis": "edible",
        "Tricholoma matsutake": "edible",
        "Truffles": "edible",
        "Tuber melanosporum": "edible"
    };

    function getEdibilityByIndex(index) {
        if (index < 0 || index >= mushroomClasses.length) {
            return { error: "Invalid class index" };
        }
        const species = mushroomClasses[index];
        return {
            species,
            edibility: mushroomEdibility[species] || "unknown"
        };
    }

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
                                <p className="text-2xl font-bold text-gray-800">{scanHistory.length}</p>
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
                            {scanHistory.map((scan, index) => (
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
                                                        {getEdibilityByIndex(scan.class).edibility}
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
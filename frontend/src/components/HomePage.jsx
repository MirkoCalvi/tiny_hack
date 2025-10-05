import React, { useState, useEffect } from 'react';
import { Camera, CheckCircle, XCircle, AlertTriangle, Leaf } from 'lucide-react';
import {getAllScans, inferImage, postScan} from "../API.js";

export default function HomePage() {
    const [isScanning, setIsScanning] = useState(false);
    const [scanHistory, setScanHistory] = useState([]);
    const [currentScan, setCurrentScan] = useState(null);

    const handleStartScan = async () => {
        setIsScanning(true);
        setCurrentScan(null);

        const inferenceData = await inferImage(true);
        setCurrentScan(inferenceData);
        setIsScanning(false);
        // {"class":11,"image_url":"http://10.100.16.76:5000/images/nicla_20251005_102756_771195.png","latency_us":2006856,"score":1.732289,"timestamp":1759652876808}

        await postScan(inferenceData);
    };

    useEffect(() => {
        const loadHistory = async () => {
           const response = await getAllScans();
           const data = await response.json();
           setScanHistory(data);
         };
        loadHistory();
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
                            <Leaf size={40} className="text-green-600" />
                            <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-800 text-center">
                                Mushroom Vision AI
                            </h1>
                        </div>
                        <p className="text-gray-600 text-center">Powered by Arduino Nicla Vision</p>
                        <button className="bg-red-300 text-white hover:bg-gray-300 rounded-5" onClick={() => window.location.href = '/history'}>
                            Scan History
                        </button>
                    </div>
                </div>

                {/* Scanner View */}
                <div className="mb-6 max-w-4xl mx-auto">
                    <div className="bg-white rounded-2xl shadow-2xl p-6">
                        {!currentScan ? <div
                            className="flex items-center justify-center rounded-xl overflow-hidden relative"
                            style={{
                                background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
                                minHeight: '300px'
                            }}
                        >
                            {isScanning ? (
                                <div className="text-center text-white">
                                    <div className="animate-spin rounded-full h-16 w-16 border-4 border-white border-t-transparent mb-4 mx-auto"></div>
                                    <p className="text-xl font-semibold">Analyzing mushroom...</p>
                                    <p className="text-sm text-white/70">Processing image from Nicla Vision</p>
                                </div>
                            ) : currentScan ? (
                                <img
                                    src={currentScan.imageUrl}
                                    alt="Scanned mushroom"
                                    className="w-full h-full object-cover max-h-96"
                                />
                            ) : (
                                <div className="text-center text-white">
                                    <Camera size={80} className="mb-4 opacity-50 mx-auto" />
                                    <p className="text-xl font-semibold">Ready to scan</p>
                                    <p className="text-sm text-white/70">Press the button below to start</p>
                                </div>
                            )}
                        </div>
                            : <img alt="scanned img" src={currentScan.image_url} />
                        }

                        <div className="text-center mt-6">
                            <button
                                onClick={handleStartScan}
                                disabled={isScanning}
                                className="bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white px-8 py-4 rounded-full text-lg font-semibold shadow-lg transition-all flex items-center gap-2 mx-auto"
                            >
                                <Camera size={24} />
                                {isScanning ? 'Scanning...' : 'Start Scan'}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Current Scan Result */}
                {currentScan && (
                    <div className="max-w-4xl mx-auto">
                        <div className="bg-white rounded-2xl shadow-2xl p-6 border-l-8 border-green-500">
                            <h3 className="text-2xl font-bold mb-4 text-gray-800">Detection Result</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                                <div>
                                    <p className="text-sm text-gray-500 mb-1">Scientific Name</p>
                                    <h5 className="text-xl font-semibold italic text-gray-800">{currentScan.class}</h5>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-500 mb-1">Common Name</p>
                                    <h5 className="text-xl font-semibold text-gray-800">{currentScan.commonName || "No name"}</h5>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-500 mb-2">Edibility</p>
                                    {getEdibilityBadge(currentScan.edibility || 'unknown')}
                                </div>
                                <div>
                                    <p className="text-sm text-gray-500 mb-2">Confidence</p>
                                    <div className="flex items-center gap-3">
                                        <div className="flex-grow bg-gray-200 rounded-full h-3">
                                            <div
                                                className="bg-green-500 h-3 rounded-full transition-all"
                                                style={{ width: `${currentScan.confidence}%` }}
                                            />
                                        </div>
                                        <span className="font-bold text-gray-800">{currentScan.confidence}%</span>
                                    </div>
                                </div>
                            </div>
                            {currentScan.edibility === 'toxic' && (
                                <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded flex items-start gap-3">
                                    <AlertTriangle size={24} className="text-red-500 flex-shrink-0 mt-1" />
                                    <div>
                                        <p className="font-semibold text-red-800">Warning</p>
                                        <p className="text-red-700 text-sm">This mushroom is identified as toxic. Do not consume.</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
import React, { useState, useEffect } from 'react';
import { Camera, History, CheckCircle, XCircle, AlertTriangle, Leaf } from 'lucide-react';

export default function HomePage() {
    const [isScanning, setIsScanning] = useState(false);
    const [scanHistory, setScanHistory] = useState([]);
    const [currentScan, setCurrentScan] = useState(null);
    const [activeView, setActiveView] = useState('scanner');

    // Simulate receiving data from Arduino Nicla Vision
    const handleStartScan = async () => {
        setIsScanning(true);
        setCurrentScan(null);

        // TODO: Replace with actual API call to start scan
        // await fetch('/api/start-scan', { method: 'POST' });

        // Simulate scan completion after 3 seconds
        setTimeout(() => {
            const mockResult = {
                id: Date.now(),
                timestamp: new Date().toISOString(),
                mushroomName: ['Amanita muscaria', 'Boletus edulis', 'Cantharellus cibarius', 'Pleurotus ostreatus'][Math.floor(Math.random() * 4)],
                commonName: ['Fly Agaric', 'Porcini', 'Chanterelle', 'Oyster Mushroom'][Math.floor(Math.random() * 4)],
                edibility: ['toxic', 'edible', 'edible', 'edible'][Math.floor(Math.random() * 4)],
                confidence: (85 + Math.random() * 14).toFixed(1),
                imageUrl: `https://source.unsplash.com/400x300/?mushroom&sig=${Date.now()}`
            };

            setCurrentScan(mockResult);
            setIsScanning(false);

            // Add to history
            setScanHistory(prev => [mockResult, ...prev]);

            // TODO: Save to backend
            // await fetch('/api/save-scan', { method: 'POST', body: JSON.stringify(mockResult) });
        }, 3000);
    };

    // TODO: Fetch history from backend on mount
    useEffect(() => {
        // const loadHistory = async () => {
        //   const response = await fetch('/api/scan-history');
        //   const data = await response.json();
        //   setScanHistory(data);
        // };
        // loadHistory();
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
                    </div>
                </div>

                {/* Navigation Buttons */}
                <div className="mb-6 flex gap-3 justify-center flex-wrap">
                    <button
                        onClick={() => setActiveView('scanner')}
                        className={`flex items-center gap-2 px-6 py-3 rounded-full font-semibold shadow-lg transition-all ${
                            activeView === 'scanner'
                                ? 'bg-white text-purple-700'
                                : 'bg-white/20 text-white hover:bg-white/30'
                        }`}
                    >
                        <Camera size={20} /> Scanner
                    </button>
                    <button
                        onClick={() => setActiveView('history')}
                        className={`flex items-center gap-2 px-6 py-3 rounded-full font-semibold shadow-lg transition-all ${
                            activeView === 'history'
                                ? 'bg-white text-purple-700'
                                : 'bg-white/20 text-white hover:bg-white/30'
                        }`}
                    >
                        <History size={20} /> History ({scanHistory.length})
                    </button>
                </div>

                {/* Scanner View */}
                {activeView === 'scanner' && (
                    <>
                        <div className="mb-6 max-w-4xl mx-auto">
                            <div className="bg-white rounded-2xl shadow-2xl p-6">
                                <div
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
                                            <h5 className="text-xl font-semibold italic text-gray-800">{currentScan.mushroomName}</h5>
                                        </div>
                                        <div>
                                            <p className="text-sm text-gray-500 mb-1">Common Name</p>
                                            <h5 className="text-xl font-semibold text-gray-800">{currentScan.commonName}</h5>
                                        </div>
                                        <div>
                                            <p className="text-sm text-gray-500 mb-2">Edibility</p>
                                            {getEdibilityBadge(currentScan.edibility)}
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
                    </>
                )}

                {/* History View */}
                {activeView === 'history' && (
                    <div className="max-w-6xl mx-auto">
                        <div className="bg-white rounded-2xl shadow-2xl p-6">
                            <h3 className="text-2xl font-bold mb-6 text-gray-800">Scan History</h3>
                            {scanHistory.length === 0 ? (
                                <div className="text-center py-12 text-gray-400">
                                    <History size={60} className="mb-4 opacity-25 mx-auto" />
                                    <p className="text-lg">No scans yet. Start scanning to build your history!</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {scanHistory.map((scan) => (
                                        <div key={scan.id} className="border-b border-gray-200 pb-4 last:border-b-0">
                                            <div className="flex flex-col sm:flex-row gap-4">
                                                <img
                                                    src={scan.imageUrl}
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
                              <strong>Confidence:</strong> {scan.confidence}%
                            </span>
                                                        <span>
                              <strong>Scanned:</strong> {new Date(scan.timestamp).toLocaleString()}
                            </span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
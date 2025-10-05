import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type BinType = "plastic" | "glass" | "paper" | "organic" | "general";

interface Bin {
  id: BinType;
  label: string;
  color: string;
  icon: string;
}

interface Prediction {
  category: BinType;
  confidence: number;
  class_id: number;
  detections: number;
  timestamp: string;
  image_name?: string;
}

const bins: Bin[] = [
  { 
    id: "plastic", 
    label: "Plastic", 
    color: "bg-yellow-500",
    icon: "♻️"
  },
  { 
    id: "glass", 
    label: "Glass", 
    color: "bg-purple-500",
    icon: "🍷"
  },
  { 
    id: "paper", 
    label: "Paper", 
    color: "bg-blue-500",
    icon: "📄"
  },
  { 
    id: "organic", 
    label: "Organic", 
    color: "bg-green-600",
    icon: "🍎"
  },
  { 
    id: "general", 
    label: "General Waste", 
    color: "bg-gray-600",
    icon: "🗑️"
  }
];

export const BinDisplay = () => {
  const [currentPrediction, setCurrentPrediction] = useState<Prediction | null>(null);
  const [predictionHistory, setPredictionHistory] = useState<Prediction[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  // Watch for predictions.json file updates
  useEffect(() => {
    const checkForPredictions = async () => {
      try {
        const response = await fetch('/predictions.json');
        if (response.ok) {
          const data = await response.json();
          setIsConnected(true);
          
          if (data && data.category) {
            const prediction: Prediction = {
              ...data,
              timestamp: new Date().toLocaleTimeString()
            };
            
            setCurrentPrediction(prediction);
            setPredictionHistory(prev => [prediction, ...prev.slice(0, 9)]); // Keep last 10
          }
        } else {
          setIsConnected(false);
        }
      } catch (error) {
        setIsConnected(false);
        console.log('No predictions file found or error reading:', error);
      }
    };

    // Check immediately
    checkForPredictions();

    // Check every 2 seconds
    const interval = setInterval(checkForPredictions, 2000);

    return () => clearInterval(interval);
  }, []);

  const getCurrentBin = () => {
    if (!currentPrediction) return null;
    return bins.find(bin => bin.id === currentPrediction.category);
  };

  const currentBin = getCurrentBin();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Smart Trash Collector
          </h1>
          <div className="flex items-center justify-center gap-2">
            <div className={cn(
              "w-3 h-3 rounded-full",
              isConnected ? "bg-green-500" : "bg-red-500"
            )} />
            <span className="text-sm text-gray-600">
              {isConnected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>

        {/* Current Prediction Display */}
        <div className="mb-8">
          {/* <h2 className="text-2xl font-semibold text-center mb-6">
            Current Classification
          </h2> */}
          
          {currentPrediction ? (
            <div className="text-center">
              <div className="text-6xl mb-4">
                {currentBin?.icon}
              </div>
              <h3 className="text-3xl font-bold text-gray-800 mb-2">
                {currentBin?.label}
              </h3>
              <Badge variant="outline" className="text-lg px-4 py-2">
                Confidence: {(currentPrediction.confidence * 100).toFixed(1)}%
              </Badge>
              {currentPrediction.image_name && (
                <p className="text-sm text-gray-600 mt-2">
                  Image: {currentPrediction.image_name}
                </p>
              )}
            </div>
          ) : (
            <div className="text-center text-gray-500">
              <div className="text-4xl mb-4">⏳</div>
              <p>Waiting for classification...</p>
            </div>
          )}
        </div>

        {/* Bin Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          {bins.map((bin) => {
            const isActive = currentBin?.id === bin.id;
            return (
              <Card
                key={bin.id}
                className={cn(
                  "p-6 text-center transition-all duration-300",
                  isActive 
                    ? "ring-4 ring-blue-500 shadow-xl animate-pulse-glow" 
                    : "hover:shadow-lg hover:scale-105"
                )}
              >
                <div className="text-4xl mb-3">{bin.icon}</div>
                <h3 className="text-lg font-semibold mb-2">{bin.label}</h3>
                <div className={cn(
                  "w-full h-3 rounded-full",
                  bin.color,
                  isActive ? "opacity-100" : "opacity-50"
                )} />
                {isActive && (
                  <Badge className="mt-2 bg-blue-500">
                    Active
                  </Badge>
                )}
              </Card>
            );
          })}
        </div>

        {/* Prediction History */}
        <div>
          <h2 className="text-2xl font-semibold text-center mb-6">
            Recent Classifications
          </h2>
          
          {predictionHistory.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {predictionHistory.map((prediction, index) => {
                const bin = bins.find(b => b.id === prediction.category);
                return (
                  <Card key={index} className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="text-2xl">{bin?.icon}</div>
                      <div className="flex-1">
                        <h4 className="font-semibold">{bin?.label}</h4>
                        <p className="text-sm text-gray-600">
                          {(prediction.confidence * 100).toFixed(1)}% confidence
                        </p>
                        <p className="text-xs text-gray-500">
                          {prediction.timestamp}
                        </p>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          ) : (
            <div className="text-center text-gray-500">
              <p>No classifications yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

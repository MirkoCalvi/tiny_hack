import React from 'react';
import { Smile, Frown } from 'lucide-react';
import type { MoodAnalysis } from '../types';

export default function MoodResult({ result }: { result: MoodAnalysis }) {
  return (
    <div
      className={`p-3 sm:p-4 rounded-xl sm:rounded-2xl ${
        result.needs_hydration ? 'bg-red-50 border-2 border-red-200' : 'bg-green-50 border-2 border-green-200'
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        {result.needs_hydration ? <Frown className="text-red-600" size={20} /> : <Smile className="text-green-600" size={20} />}
        <span className="text-sm sm:text-base font-bold text-gray-800">
          {result.needs_hydration ? 'Hydration Needed!' : 'Looking Good!'}
        </span>
      </div>

      {result.detected_signs && result.detected_signs.length > 0 && (
        <div className="mt-2">
          <p className="text-xs sm:text-sm text-gray-600 mb-1">Detected:</p>
          <div className="flex flex-wrap gap-1">
            {result.detected_signs.map((sign, idx) => (
              <span key={idx} className="inline-block bg-white px-2 sm:px-3 py-1 rounded-full text-xs">
                {sign}
              </span>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs sm:text-sm text-gray-600 mt-2">Confidence: {Math.round(result.confidence * 100)}%</p>
    </div>
  );
}

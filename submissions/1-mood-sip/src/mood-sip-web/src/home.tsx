import React, { useEffect, useState } from 'react';
import { Droplets, Camera, Clock } from 'lucide-react';
import { API_BASE_URL, DEFAULT_MODEL } from './config';
import { useNotifications } from './hooks/useNotifications';
import { useCameraCapture } from './hooks/useCameraCapture';
import { useBluetoothFrames } from './hooks/useBluetoothFrames';
import { analyzeWithOllama, checkBackendHealth } from './services/ai';
import { formatTime } from './utils';
import type { MoodAnalysis } from './types';
import NotificationFeed from './components/NotificationFeed';
import MoodResult from './components/MoodResult';
import DebugTools from './components/DebugTools';

export default function MoodSipApp() {

  // BLE connection state is provided by the hook
  const [sipCount, setSipCount] = useState<number>(0);
  const [dailyGoal] = useState<number>(8);
  const [lastSip, setLastSip] = useState<Date | null>(null);
  const [moodAnalysis, setMoodAnalysis] = useState<MoodAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const { notifications, add } = useNotifications();
  const [timerMinutes, setTimerMinutes] = useState<number>(30);
  const [timerActive, setTimerActive] = useState<boolean>(false);
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const { active: cameraActive, capture } = useCameraCapture();
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  // MoodSip Logo as base64 data URL - Cute water bottle with face
  const MOODSIP_LOGO = 'data:image/svg+xml;base64,' + btoa(`
    <svg width="100" height="120" viewBox="0 0 100 120" fill="none" xmlns="http://www.w3.org/2000/svg">
      <!-- Bottle Cap -->
      <rect x="35" y="10" width="30" height="15" rx="7" fill="#0D9488" stroke="#0F766E" stroke-width="2"/>
      <!-- Handle -->
      <path d="M75 35 Q85 35 85 45 Q85 55 75 55" stroke="#0F766E" stroke-width="3" fill="none"/>
      <!-- Main Bottle Body -->
      <rect x="25" y="25" width="50" height="80" rx="20" fill="#14B8A6" stroke="#0F766E" stroke-width="3"/>
      <!-- Face Elements -->
      <!-- Eyes -->
      <circle cx="40" cy="50" r="3" fill="#0F172A"/>
      <circle cx="60" cy="50" r="3" fill="#0F172A"/>
      <!-- Smile -->
      <path d="M45 65 Q50 70 55 65" stroke="#0F172A" stroke-width="2" fill="none" stroke-linecap="round"/>
      <!-- Cheek (red dot) -->
      <circle cx="35" cy="45" r="2" fill="#EF4444"/>
      <!-- Water Level -->
      <rect x="30" y="75" width="40" height="25" rx="15" fill="#06B6D4" opacity="0.6"/>
    </svg>
  `);

  // Check backend health on component mount
  useEffect(() => {
    (async () => {
      const res = await checkBackendHealth();
      if (res.ok) {
        setBackendStatus('online');
        add(`✅ Connected to MoodSip AI (${res.data?.available_models?.length || 0} models available)`, 'success');
      } else {
        setBackendStatus('offline');
        add('⚠️ Backend service unavailable', 'warning');
      }
    })();
  }, []);

  // BLE hook wires: when a frame arrives, analyze it
  const { connected, connect, disconnect: disconnectBle, sendAck: sendAckNow, readImageOnce, bleStats } = useBluetoothFrames(
    async (pgmBase64, metadata) => {
      try {
        const data = await analyzeWithOllama(pgmBase64, { width: metadata.width, height: metadata.height });
        setMoodAnalysis(data);
        setAnalyzing(false);
        if (data.needs_hydration) {
          triggerNotification('💧 Time to hydrate!', `Detected: ${data.detected_signs?.join(', ') || 'Signs of dehydration'}`);
        } else {
          add('😊 You look good! Keep it up!', 'success');
        }
      } catch (e: any) {
        setAnalyzing(false);
        add('Analysis failed: ' + (e?.message || 'Unknown error'), 'error');
      }
    },
    add
  );

  // Timer countdown
  useEffect(() => {
    if (timerActive && timeLeft !== null && timeLeft > 0) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
      return () => clearTimeout(timer);
    } else if (timerActive && timeLeft === 0) {
      triggerNotification('⏰ Time to sip!', 'Your hydration timer is up');
      setTimerActive(false);
    }
  }, [timerActive, timeLeft]);


  // // Handle incoming Bluetooth image data (Float32Array)
  // const handleBluetoothImageData = async (event: Event) => {
  //   try {
  //     // @ts-ignore - Bluetooth types not fully supported
  //     const target = event.target as any;
  //     const value = target?.value;
      
  //     if (!value) return;
      
  //     // Convert DataView to Float32Array
  //     const float32Array = new Float32Array(value.buffer);
      
  //     // Convert Float32 values to byte array (0-255)
  //     // Assuming float values are normalized between 0.0 and 1.0
  //     const bytes = new Uint8Array(float32Array.length);
  //     for (let i = 0; i < float32Array.length; i++) {
  //       // Clamp and convert float32 (0.0-1.0) to byte (0-255)
  //       bytes[i] = Math.max(0, Math.min(255, Math.round(float32Array[i] * 255)));
  //     }
      
  //     // Check for start marker (0xFF 0xD8 for JPEG start)
  //     if (bytes.length >= 2 && bytes[0] === 0xFF && bytes[1] === 0xD8) {
  //       // Start of new image
  //       setImageBuffer(Array.from(bytes));
  //       setIsReceivingImage(true);
  //       addNotification('📡 Receiving image from bottle...', 'info');
  //       return;
  //     }
      
  //     // If we're receiving an image, accumulate data
  //     if (isReceivingImage) {
  //       // Append to buffer
  //       setImageBuffer(prev => [...prev, ...Array.from(bytes)]);
        
  //       // Check if we have the end marker in the current chunk
  //       const hasEndMarker = bytes.length >= 2 && 
  //                           bytes[bytes.length - 2] === 0xFF && 
  //                           bytes[bytes.length - 1] === 0xD9;
        
  //       if (hasEndMarker) {
  //         // Complete image received
  //         setIsReceivingImage(false);
          
  //         // Get the complete buffer
  //         const completeBuffer = [...imageBuffer, ...Array.from(bytes)];
          
  //         // Convert to base64
  //         const uint8Array = new Uint8Array(completeBuffer);
  //         let binaryString = '';
  //         const chunkSize = 0x8000; // Process in 32KB chunks to avoid call stack issues
          
  //         for (let i = 0; i < uint8Array.length; i += chunkSize) {
  //           const chunk = uint8Array.subarray(i, Math.min(i + chunkSize, uint8Array.length));
  //           binaryString += String.fromCharCode.apply(null, Array.from(chunk));
  //         }
          
  //         const base64 = btoa(binaryString);
          
  //         addNotification('✅ Image received completely, analyzing...', 'success');
  //         setAnalyzing(true);
          
  //         // Clear buffer
  //         setImageBuffer([]);
          
  //         // Send to backend for analysis
  //         await analyzeWithOllama(base64);
  //       } else {
  //         // Still receiving, update progress
  //         const sizeKB = Math.round((imageBuffer.length + bytes.length) / 1024);
  //         addNotification(`📡 Receiving... ${sizeKB}KB`, 'info');
  //       }
  //     }
  //   } catch (error: any) {
  //     setIsReceivingImage(false);
  //     setImageBuffer([]);
  //     setAnalyzing(false);
  //     addNotification('❌ Error processing Bluetooth image: ' + (error?.message || 'Unknown error'), 'error');
  //   }
  // };

  const captureAndAnalyze = async () => {
    setAnalyzing(true);
    try {
      const base64 = await capture();
      const data = await analyzeWithOllama(base64);
      setMoodAnalysis(data);
      setAnalyzing(false);
      if (data.needs_hydration) {
        triggerNotification('💧 Time to hydrate!', `Detected: ${data.detected_signs?.join(', ') || 'Signs of dehydration'}`);
      } else {
        add('😊 You look good! Keep it up!', 'success');
      }
    } catch (error: any) {
      setAnalyzing(false);
      add('Camera error: ' + (error?.message || 'Please allow camera access'), 'error');
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      addNotification('Please select an image file', 'error');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      addNotification('Image too large. Please select a file under 5MB', 'error');
      return;
    }

    try {
  setAnalyzing(true);
      
      const reader = new FileReader();
      reader.onload = async (e) => {
        const result = e.target?.result as string;
        const base64 = result.split(',')[1];
        setUploadedImage(result);
        
        try {
          const data = await analyzeWithOllama(base64);
          setMoodAnalysis(data);
          setAnalyzing(false);
          if (data.needs_hydration) {
            triggerNotification('💧 Time to hydrate!', `Detected: ${data.detected_signs?.join(', ') || 'Signs of dehydration'}`);
          } else {
            add('😊 You look good! Keep it up!', 'success');
          }
        } catch (e: any) {
          setAnalyzing(false);
          add('Analysis failed: ' + (e?.message || 'Unknown error'), 'error');
        }
      };
      reader.readAsDataURL(file);
      
    } catch (error: any) {
      setAnalyzing(false);
      add('File upload error: ' + (error?.message || 'Unknown error'), 'error');
    }
  };

  const simulateBluetoothImage = async () => {
    addNotification('📡 Receiving image from MoodSip Bottle...', 'info');
    
    try {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.onchange = (event) => {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        if (file) {
          const syntheticEvent = {
            target,
            currentTarget: target,
            nativeEvent: event,
            isDefaultPrevented: () => false,
            isPropagationStopped: () => false,
            persist: () => {},
          } as React.ChangeEvent<HTMLInputElement>;
          handleFileUpload(syntheticEvent);
        } else {
          setAnalyzing(false);
        }
      };
      input.click();
    } catch (error: any) {
      setAnalyzing(false);
      add('Bluetooth error: ' + (error?.message || 'Unknown error'), 'error');
    }
  };

  const recordSip = () => {
    setSipCount(prev => prev + 1);
    setLastSip(new Date());
  add('💧 Sip recorded!', 'success');
    
    if (sipCount + 1 === dailyGoal) {
  triggerNotification('🎉 Daily goal reached!', 'Great hydration today!');
    }
  };

  const startTimer = () => {
    setTimeLeft(timerMinutes * 60);
    setTimerActive(true);
  add(`⏰ Timer set for ${timerMinutes} minutes`, 'info');
  };

  const stopTimer = () => {
    setTimerActive(false);
    setTimeLeft(null);
  };

  const triggerNotification = (title: string, message: string) => {
  add(title + ': ' + message, 'warning');
    
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, { body: message, icon: '💧' });
    }
  };

  const addNotification = add; // backward alias if needed

  const progress = (sipCount / dailyGoal) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 to-cyan-100 p-2 sm:p-4 pb-safe-bottom">
      <div className="max-w-md mx-auto w-full">
        {/* Header */}
        <div className="bg-white rounded-2xl sm:rounded-3xl shadow-lg p-4 sm:p-6 mb-3 sm:mb-4">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-12 h-12 sm:w-16 sm:h-16 flex items-center justify-center">
                <img 
                  src={MOODSIP_LOGO} 
                  alt="MoodSip Logo" 
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    // Fallback to icon if logo fails to load
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    target.parentElement?.classList.add('bg-gradient-to-br', 'from-teal-400', 'to-cyan-500', 'rounded-xl', 'sm:rounded-2xl');
                    const icon = document.createElement('div');
                    icon.innerHTML = '<svg width="24" height="24" fill="white" viewBox="0 0 24 24"><path d="M12 2.5L8 6v6c0 4.4 3.6 8 8 8s8-3.6 8-8V6l-4-3.5z"/></svg>';
                    target.parentElement?.appendChild(icon);
                  }}
                />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-bold text-gray-800">MoodSip</h1>
                <p className="text-xs sm:text-sm text-gray-500">Sip Your Stress Away</p>
              </div>
            </div>
            <div className="flex gap-2">
              {/* Backend Status */}
              <div className={`px-2 sm:px-3 py-1 sm:py-2 rounded-full text-xs font-medium ${
                backendStatus === 'online' 
                  ? 'bg-green-100 text-green-700' 
                  : backendStatus === 'offline'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-yellow-100 text-yellow-700'
              }`}>
                {backendStatus === 'online' ? '🤖 AI' : backendStatus === 'offline' ? '❌ AI' : '⏳ AI'}
              </div>

              {/* Bluetooth Connection */}
              <div className="flex gap-1">
                <button
                  onClick={connect}
                  className={`px-3 sm:px-4 py-2 rounded-full text-xs sm:text-sm font-medium transition-all touch-manipulation active:scale-95 ${
                    connected
                      ? 'bg-green-100 text-green-700'
                      : 'bg-teal-500 text-white hover:bg-teal-600 active:bg-teal-700'
                  }`}
                >
                  {connected ? '✓ Bottle' : 'Connect'}
                </button>
                
              </div>
            </div>
          </div>



        {/* Daily Progress */}
        <div className="bg-gradient-to-r from-teal-50 to-cyan-50 rounded-xl sm:rounded-2xl p-3 sm:p-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs sm:text-sm font-medium text-gray-700">Today's Progress</span>
            <span className="text-xl sm:text-2xl font-bold text-teal-600">
              {sipCount}/{dailyGoal}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 sm:h-3">
            <div
              className="bg-gradient-to-r from-teal-400 to-cyan-500 h-2 sm:h-3 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(progress, 100)}%` }}
            />
          </div>
          {lastSip && (
            <p className="text-xs text-gray-500 mt-2">
              Last sip: {new Date(lastSip).toLocaleTimeString()}
            </p>
          )}
        </div>
        </div>

        {/* AI Mood Detection */}
        <div className="bg-white rounded-2xl sm:rounded-3xl shadow-lg p-4 sm:p-6 mb-3 sm:mb-4">
          <div className="flex items-center gap-2 mb-3 sm:mb-4">
            <Camera className="text-teal-600" size={18} />
            <h2 className="text-base sm:text-lg font-bold text-gray-800">AI Mood Check</h2>
          </div>

          <div className="space-y-2 mb-3">
            <button
              onClick={captureAndAnalyze}
              disabled={analyzing || cameraActive}
              className="w-full bg-gradient-to-r from-teal-500 to-cyan-500 text-white py-3 sm:py-4 rounded-xl sm:rounded-2xl text-sm sm:text-base font-medium hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation active:scale-95"
            >
              {analyzing ? '🔄 Analyzing...' : cameraActive ? '📸 Capturing in 2s...' : '📷 Take Photo'}
            </button>

            <div className="flex gap-2">
              <button
                onClick={simulateBluetoothImage}
                disabled={analyzing}
                className="flex-1 bg-gradient-to-r from-blue-500 to-purple-500 text-white py-2 sm:py-3 rounded-lg sm:rounded-xl text-xs sm:text-sm font-medium hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation active:scale-95"
              >
                📡 From Bottle
              </button>
              
              <label className="flex-1">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileUpload}
                  disabled={analyzing}
                  className="hidden"
                />
                <div className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white py-2 sm:py-3 rounded-lg sm:rounded-xl text-xs sm:text-sm font-medium hover:shadow-lg transition-all disabled:opacity-50 cursor-pointer touch-manipulation active:scale-95 text-center">
                  📁 Upload Image
                </div>
              </label>
            </div>
          </div>

          {uploadedImage && (
            <div className="mb-3">
              <img 
                src={uploadedImage} 
                alt="Uploaded for analysis" 
                className="w-full max-h-48 object-cover rounded-lg border-2 border-gray-200"
              />
            </div>
          )}

          {moodAnalysis && <MoodResult result={moodAnalysis} />}
        </div>

        {/* Hydration Timer */}
        <div className="bg-white rounded-2xl sm:rounded-3xl shadow-lg p-4 sm:p-6 mb-3 sm:mb-4">
          <div className="flex items-center gap-2 mb-3 sm:mb-4">
            <Clock className="text-teal-600" size={18} />
            <h2 className="text-base sm:text-lg font-bold text-gray-800">Sip Timer</h2>
          </div>

          <div className="flex gap-2 mb-3">
            <input
              type="number"
              value={timerMinutes}
              onChange={(e) => setTimerMinutes(Math.max(1, parseInt(e.target.value) || 1))}
              disabled={timerActive}
              className="flex-1 px-3 sm:px-4 py-2 sm:py-3 border-2 border-gray-200 rounded-lg sm:rounded-xl focus:border-teal-500 focus:outline-none text-sm sm:text-base"
              placeholder="Minutes"
            />
            <button
              onClick={timerActive ? stopTimer : startTimer}
              className={`px-4 sm:px-6 py-2 sm:py-3 rounded-lg sm:rounded-xl text-sm sm:text-base font-medium transition-all touch-manipulation active:scale-95 ${
                timerActive
                  ? 'bg-red-500 text-white hover:bg-red-600 active:bg-red-700'
                  : 'bg-teal-500 text-white hover:bg-teal-600 active:bg-teal-700'
              }`}
            >
              {timerActive ? 'Stop' : 'Start'}
            </button>
          </div>

          {timerActive && timeLeft !== null && (
            <div className="bg-gradient-to-r from-teal-50 to-cyan-50 rounded-xl sm:rounded-2xl p-3 sm:p-4 text-center">
              <div className="text-3xl sm:text-4xl font-bold text-teal-600 mb-1">
                {formatTime(timeLeft)}
              </div>
              <p className="text-xs sm:text-sm text-gray-600">until next sip reminder</p>
            </div>
          )}
        </div>

        {/* Record Sip Button */}
        <button
          onClick={recordSip}
          className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 text-white py-4 sm:py-6 rounded-2xl sm:rounded-3xl font-bold text-base sm:text-lg hover:shadow-xl transition-all mb-3 sm:mb-4 flex items-center justify-center gap-2 touch-manipulation active:scale-95 active:from-cyan-600 active:to-blue-600"
        >
          <Droplets size={20} className="sm:w-6 sm:h-6" />
          Record Sip
        </button>

        {/* Notifications Feed */}
        <NotificationFeed notifications={notifications} />

        {/* Debug Section */}
        <DebugTools
          bleStats={bleStats}
          readImageOnce={readImageOnce}
          sendAck={sendAckNow}
          disconnect={disconnectBle}
          addNotification={add}
          apiBaseUrl={API_BASE_URL}
          model={DEFAULT_MODEL}
        />
      </div>
    </div>

  );
}
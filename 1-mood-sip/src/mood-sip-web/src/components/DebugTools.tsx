import React, { useCallback, useState } from 'react';
import { checkBackendHealth } from '../services/ai';
import type { BleStats } from '../hooks/useBluetoothFrames';

type AddNotification = (text: string, type?: 'success' | 'error' | 'warning' | 'info') => void;

export default function DebugTools({
  bleStats,
  readImageOnce,
  sendAck,
  disconnect,
  addNotification,
  apiBaseUrl,
  model,
}: {
  bleStats: BleStats;
  readImageOnce: () => Promise<void>;
  sendAck: () => Promise<void>;
  disconnect: () => Promise<void>;
  addNotification: AddNotification;
  apiBaseUrl: string;
  model: string;
}) {
  const [showDebug, setShowDebug] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  const testBackend = useCallback(async () => {
    const res = await checkBackendHealth();
    if (res.ok) {
      setBackendStatus('online');
      addNotification(`✅ Connected to MoodSip AI (${res.data?.available_models?.length || 0} models available)`, 'success');
    } else {
      setBackendStatus('offline');
      addNotification('❌ Cannot connect to MoodSip AI service', 'error');
    }
  }, [addNotification]);

  const debugBluetooth = useCallback(() => {
    // @ts-ignore
    const bt = navigator.bluetooth;
    const userAgent = navigator.userAgent;
    const isSecure = location.protocol === 'https:';
    const isChrome = userAgent.includes('Chrome');
    const isEdge = userAgent.includes('Edge');

    let debugInfo = `🔧 Bluetooth Debug Info:\n`;
    debugInfo += `• Browser: ${isChrome ? 'Chrome' : isEdge ? 'Edge' : 'Other'}\n`;
    debugInfo += `• Secure Context (HTTPS): ${isSecure ? 'Yes ✅' : 'No ❌'}\n`;
    debugInfo += `• Web Bluetooth API: ${bt ? 'Available ✅' : 'Not Available ❌'}\n`;
    if (!bt && (isChrome || isEdge)) {
      debugInfo += `\n🛠️ To Enable Web Bluetooth:\n`;
      debugInfo += `1. Go to chrome://flags/\n`;
      debugInfo += `2. Enable "Experimental Web Platform features"\n`;
      debugInfo += `3. Enable "Web Bluetooth"\n`;
      debugInfo += `4. Restart browser\n`;
      debugInfo += `5. Must use HTTPS (not http://)\n`;
    }
    console.log(debugInfo);
    addNotification(bt ? debugInfo.replace(/\n/g, ' | ') : '❌ Web Bluetooth disabled. Check console for enable instructions.', bt ? 'info' : 'error');
  }, [addNotification]);

  const scanAllBluetoothDevices = useCallback(async () => {
    try {
      // @ts-ignore
      if (!navigator.bluetooth) {
        addNotification('❌ Web Bluetooth not supported', 'error');
        return;
      }
      addNotification('🔍 Scanning for ANY Bluetooth device...', 'info');
      // @ts-ignore
      const device = await navigator.bluetooth.requestDevice({
        acceptAllDevices: true,
        optionalServices: ['device_information', 'battery_service'],
      });
      if (device) {
        addNotification(`📱 Found device: ${device.name || 'Unknown'} (ID: ${device.id})`, 'success');
      }
    } catch (error: any) {
      addNotification(`❌ Scan failed: ${error?.message || 'Unknown error'}`, 'error');
    }
  }, [addNotification]);

  return (
    <div className="bg-white rounded-2xl sm:rounded-3xl shadow-lg p-4 sm:p-6 mb-4">
      <button onClick={() => setShowDebug(!showDebug)} className="w-full flex items-center justify-between text-left text-sm text-gray-600 hover:text-gray-800 transition-colors">
        <span>🔧 Developer Tools</span>
        <span className="transform transition-transform" style={{ transform: showDebug ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
      </button>
      {showDebug && (
        <div className="mt-4 space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Backend Status</h3>
            <button onClick={testBackend} className="w-full px-3 py-2 bg-yellow-100 text-yellow-800 rounded-lg text-sm font-medium hover:bg-yellow-200 transition-all">
              🔄 Test Backend Connection
            </button>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Bluetooth Debugging</h3>
            <div className="p-3 bg-blue-50 rounded-lg">
              <div className="flex gap-2 mb-2">
                <button onClick={scanAllBluetoothDevices} className="flex-1 px-2 py-1 bg-blue-200 text-blue-800 rounded text-xs hover:bg-blue-300 transition-all">Scan All Devices</button>
                <button onClick={debugBluetooth} className="flex-1 px-2 py-1 bg-blue-200 text-blue-800 rounded text-xs hover:bg-blue-300 transition-all">Debug Info</button>
              </div>
              <div className="grid grid-cols-2 gap-2 my-2">
                <button onClick={readImageOnce} className="px-2 py-1 bg-blue-200 text-blue-800 rounded text-xs hover:bg-blue-300">Read Once</button>
                <button onClick={sendAck} className="px-2 py-1 bg-green-200 text-green-800 rounded text-xs hover:bg-green-300">Send ACK</button>
                <button onClick={disconnect} className="px-2 py-1 bg-red-200 text-red-800 rounded text-xs hover:bg-red-300 col-span-2">Disconnect</button>
              </div>
              <div className="text-xs text-blue-700 space-y-1">
                <p className="font-medium">📊 Live BLE Stats:</p>
                <p>Subscribed: {bleStats.subscribed ? 'yes' : 'no'}</p>
                <p>Bytes: {bleStats.totalBytes} • Frames: {bleStats.totalFrames}</p>
                <p>Last chunk: {bleStats.lastChunk} • Last event: {bleStats.lastEventAt ? new Date(bleStats.lastEventAt).toLocaleTimeString() : '—'}</p>
              </div>
            </div>
            <div className="text-xs text-blue-700 space-y-1 mt-2">
              <p className="font-medium">📋 Web Bluetooth Setup:</p>
              <p>1. Open chrome://flags/ in new tab</p>
              <p>2. Enable "Experimental Web Platform features"</p>
              <p>3. Enable "Web Bluetooth"</p>
              <p>4. Restart Chrome completely</p>
              <p>5. Must use HTTPS (not http://)</p>
            </div>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">API Configuration</h3>
            <div className="p-3 bg-gray-50 rounded-lg text-xs text-gray-600">
              <p>
                <strong>Endpoint:</strong> {apiBaseUrl}
              </p>
              <p>
                <strong>Model:</strong> {model}
              </p>
              <p>
                <strong>Status:</strong>{' '}
                <span className={`ml-1 px-2 py-1 rounded text-xs ${backendStatus === 'online' ? 'bg-green-100 text-green-700' : backendStatus === 'offline' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>
                  {backendStatus}
                </span>
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

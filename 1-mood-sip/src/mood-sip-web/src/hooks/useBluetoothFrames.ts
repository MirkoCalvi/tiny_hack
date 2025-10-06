import { useCallback, useEffect, useRef, useState } from 'react';
import { BLE_COMMAND_CHAR_UUID, BLE_IMAGE_CHAR_UUID, BLE_SERVICE_UUID, FRAME_BYTES, GRAY_HEIGHT, GRAY_WIDTH } from '../config';
import { bytesToPgmBase64 } from '../utils';

export interface BleStats {
  subscribed: boolean;
  totalBytes: number;
  totalFrames: number;
  lastChunk: number;
  lastEventAt: number | null;
}

type AddNotification = (text: string, type?: 'success' | 'error' | 'warning' | 'info') => void;

export function useBluetoothFrames(onFrame: (pgmBase64: string, meta: { width: number; height: number }) => Promise<void>, addNotification: AddNotification) {
  // Keep references to active BLE objects (as any to avoid lib mismatch)
  const [connected, setConnected] = useState(false);
  const [bleDevice, setBleDevice] = useState<any>(null);
  const [bleServer, setBleServer] = useState<any>(null);
  const [imageChar, setImageChar] = useState<any>(null);
  const [commandChar, setCommandChar] = useState<any>(null);

  const [bleStats, setBleStats] = useState<BleStats>({
    subscribed: false,
    totalBytes: 0,
    totalFrames: 0,
    lastChunk: 0,
    lastEventAt: null,
  });

  // Frame reassembly state
  const frameAccumRef = useRef<Uint8Array>(new Uint8Array(FRAME_BYTES));
  const frameLenRef = useRef<number>(0);

  const processCompleteGrayFrame = useCallback(async (gray: Uint8Array) => {
    // Best-effort ACK
    try {
      if (commandChar) {
        await commandChar.writeValue(new Uint8Array([1]));
      }
    } catch (e) {
      console.warn('ACK write failed:', e);
    }

    const pgmBase64 = bytesToPgmBase64(gray, GRAY_WIDTH, GRAY_HEIGHT);
    await onFrame(pgmBase64, { width: GRAY_WIDTH, height: GRAY_HEIGHT });
  }, [commandChar, onFrame]);

  const handleBluetoothImageData = useCallback(async (event: Event) => {
    try {
      // @ts-ignore
      const target = event.target as any;
      const value = target?.value as DataView;
      if (!value || !(value instanceof DataView)) return;

      const incoming = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
      setBleStats((s) => ({ ...s, totalBytes: s.totalBytes + incoming.length, lastChunk: incoming.length, lastEventAt: Date.now() }));

      let offset = 0;
      while (offset < incoming.length) {
        const remaining = FRAME_BYTES - frameLenRef.current;
        const toCopy = Math.min(remaining, incoming.length - offset);
        frameAccumRef.current.set(incoming.subarray(offset, offset + toCopy), frameLenRef.current);
        frameLenRef.current += toCopy;
        offset += toCopy;

        if (frameLenRef.current === FRAME_BYTES) {
          const complete = frameAccumRef.current.slice(0, FRAME_BYTES);
          frameLenRef.current = 0;
          frameAccumRef.current = new Uint8Array(FRAME_BYTES);
          await processCompleteGrayFrame(complete);
          setBleStats((s) => ({ ...s, totalFrames: s.totalFrames + 1 }));
        }
      }
    } catch (error: any) {
      addNotification('❌ Error processing Bluetooth data: ' + (error?.message || 'Unknown error'), 'error');
      frameLenRef.current = 0;
      frameAccumRef.current = new Uint8Array(FRAME_BYTES);
    }
  }, [addNotification, processCompleteGrayFrame]);

  const connect = useCallback(async () => {
    try {
      // @ts-ignore
      if (!navigator.bluetooth) {
        addNotification('❌ Web Bluetooth not supported in this browser. Try Chrome/Edge with flags enabled.', 'error');
        return;
      }
      // @ts-ignore
      const available = await navigator.bluetooth.getAvailability();
      if (!available) {
        addNotification('❌ Bluetooth not available. Please enable Bluetooth on your device.', 'error');
        return;
      }

      addNotification('🔍 Scanning for MoodSip devices...', 'info');
      // @ts-ignore
      const device = await navigator.bluetooth.requestDevice({
        filters: [
          { name: 'MoodSip' },
          { name: 'MoodSip-Bottle' },
          { namePrefix: 'MoodSip' },
          { namePrefix: 'ESP32' },
          { namePrefix: 'Arduino' },
        ],
        optionalServices: [BLE_SERVICE_UUID, 'device_information', 'battery_service'],
      });
      if (!device) {
        addNotification('❌ No device selected or found', 'error');
        return;
      }

      addNotification(`🔗 Connecting to ${device.name || 'MoodSip device'}...`, 'info');
      const server = await device.gatt?.connect();
      if (!server) {
        addNotification('❌ Failed to connect to device GATT server', 'error');
        return;
      }

      try {
        const service = await server.getPrimaryService(BLE_SERVICE_UUID);
        const imageCharacteristic = await service.getCharacteristic(BLE_IMAGE_CHAR_UUID);
        let commandCharacteristic: any = null;
        try {
          commandCharacteristic = await service.getCharacteristic(BLE_COMMAND_CHAR_UUID);
        } catch {}

        await imageCharacteristic.startNotifications();
        imageCharacteristic.addEventListener('characteristicvaluechanged', handleBluetoothImageData);

        setBleDevice(device);
        setBleServer(server);
        setImageChar(imageCharacteristic);
        setCommandChar(commandCharacteristic);
        setConnected(true);
        setBleStats((s) => ({ ...s, subscribed: true, lastEventAt: null, lastChunk: 0 }));
        addNotification('✅ Connected to MoodSip Bottle - Ready to receive images!', 'success');
      } catch (serviceError) {
        setConnected(false);
        addNotification('⚠️ Connected but image service unavailable or notifications failed.', 'warning');
      }

      device.addEventListener('gattserverdisconnected', async () => {
        setConnected(false);
        try {
          if (imageChar) {
            imageChar.removeEventListener('characteristicvaluechanged', handleBluetoothImageData);
            await imageChar.stopNotifications().catch(() => {});
          }
        } catch {}
        setImageChar(null);
        setCommandChar(null);
        setBleDevice(null);
        setBleServer(null);
        setBleStats({ subscribed: false, totalBytes: 0, totalFrames: 0, lastChunk: 0, lastEventAt: null });
        addNotification('📱 MoodSip Bottle disconnected', 'info');
      });
    } catch (error: any) {
      if (error?.name === 'NotFoundError') {
        addNotification('❌ No MoodSip device found. Make sure your bottle is powered on and in pairing mode.', 'error');
      } else if (error?.name === 'SecurityError') {
        addNotification('❌ Bluetooth access denied. Please enable Web Bluetooth in browser settings.', 'error');
      } else if (error?.name === 'NotSupportedError') {
        addNotification('❌ Web Bluetooth not supported. Use Chrome/Edge with experimental flags enabled.', 'error');
      } else {
        addNotification('❌ Connection failed: ' + (error?.message || 'Unknown error'), 'error');
      }
    }
  }, [addNotification, handleBluetoothImageData, imageChar]);

  const readImageOnce = useCallback(async () => {
    try {
      if (!imageChar) {
        addNotification('Image characteristic not available', 'error');
        return;
      }
      const dv = await imageChar.readValue();
      const arr = new Uint8Array(dv.buffer, dv.byteOffset, dv.byteLength);
      addNotification(`🔎 Read image char value: ${arr.byteLength} bytes`, 'info');
      console.log('Image char read first 16 bytes:', Array.from(arr.slice(0, 16)));
    } catch (e: any) {
      addNotification(`Read failed: ${e?.message || e}`, 'error');
    }
  }, [addNotification, imageChar]);

  const sendAck = useCallback(async () => {
    try {
      if (!commandChar) {
        addNotification('Command characteristic not available', 'error');
        return;
      }
      await commandChar.writeValue(new Uint8Array([1]));
      addNotification('✅ ACK (1) sent to device', 'success');
    } catch (e: any) {
      addNotification(`ACK failed: ${e?.message || e}`, 'error');
    }
  }, [addNotification, commandChar]);

  const disconnect = useCallback(async () => {
    try {
      if (bleDevice?.gatt?.connected) bleDevice.gatt.disconnect();
    } catch {}
  }, [bleDevice]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      (async () => {
        try {
          if (imageChar) {
            imageChar.removeEventListener('characteristicvaluechanged', handleBluetoothImageData);
            await imageChar.stopNotifications().catch(() => {});
          }
        } catch {}
        try {
          if (bleDevice && bleDevice.gatt && bleDevice.gatt.connected) {
            bleDevice.gatt.disconnect();
          }
        } catch {}
      })();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Watchdog
  useEffect(() => {
    if (!bleStats.subscribed) return;
    const startedAt = Date.now();
    const t = setTimeout(() => {
      if (!bleStats.lastEventAt || bleStats.lastEventAt < startedAt) {
        addNotification('⏱️ No BLE notifications received yet. If Arduino sends 9216B in one notify, it will fail. Consider chunking on device or verify notifications.', 'warning');
        console.warn('BLE watchdog: no notifications received within 5s after subscription');
      }
    }, 5000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bleStats.subscribed]);

  return {
    connected,
    connect,
    disconnect,
    sendAck,
    readImageOnce,
    bleStats,
  };
}

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { io } from 'socket.io-client';
import type { Impression, EmotionData } from '../types';

interface EmotionContextType {
  impressions: Impression[];
  device1Current: EmotionData | null;
  device2Current: EmotionData | null;
  isConnected: boolean;
}

const EmotionContext = createContext<EmotionContextType | undefined>(undefined);

const BACKEND_URL = 'http://localhost:3002';

// Device identifiers
const NICLA_1_IP = '1';
const NICLA_2_IP = '2';

export function EmotionProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(false);
  const [impressions, setImpressions] = useState<Impression[]>([]);
  const [device1Current, setDevice1Current] = useState<EmotionData | null>(null);
  const [device2Current, setDevice2Current] = useState<EmotionData | null>(null);

  useEffect(() => {
    // Connect to WebSocket on App mount
    const newSocket = io(BACKEND_URL, {
      transports: ['websocket'],
    });

    newSocket.on('connect', () => {
      console.log('✅ WebSocket connected');
      setIsConnected(true);
    });

    newSocket.on('disconnect', () => {
      console.log('❌ WebSocket disconnected');
      setIsConnected(false);
    });

    // Listen for new impressions
    newSocket.on('new_impression', (data: Impression) => {
      console.log('📥 New impression:', data);
      setImpressions((prev) => [...prev, data]);
      
      // Update current emotion based on device IP
      if (data.device_id === NICLA_1_IP) {
        setDevice1Current({ emotion: data.emotion });
      } else if (data.device_id === NICLA_2_IP) {
        setDevice2Current({ emotion: data.emotion });
      }
    });

    // Listen for session start (impressions cleared)
    newSocket.on('impressions_cleared', () => {
      console.log('🧹 Session started - clearing impressions');
      setImpressions([]);
      setDevice1Current(null);
      setDevice2Current(null);
    });

    // Cleanup on unmount
    return () => {
      newSocket.close();
    };
  }, []);

  const value = {
    impressions,
    device1Current,
    device2Current,
    isConnected,
  };

  return (
    <EmotionContext.Provider value={value}>
      {children}
    </EmotionContext.Provider>
  );
}

export function useEmotions() {
  const context = useContext(EmotionContext);
  if (context === undefined) {
    throw new Error('useEmotions must be used within an EmotionProvider');
  }
  return context;
}

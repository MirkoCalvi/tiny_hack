import { useEmotions } from '../context/EmotionContext';
import { useEffect, useState, useRef } from 'react';
import { emotionEmojis } from '../types';
import styles from '../css/EmotionDisplay.module.css';

// Interface for animated emojis
interface AnimatedEmoji {
  id: string;
  emoji: string;
  timestamp: number;
}

function formatTimestamp(timestamp: number, jobStartTime: number, allImpressions: any[]): string {
  // Use jobStartTime if valid, otherwise use the earliest impression timestamp
  const referenceTime = jobStartTime > 0 ? jobStartTime : Math.min(...allImpressions.map(i => i.timestamp));
  const elapsed = timestamp - referenceTime;
  const seconds = Math.floor(elapsed / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

interface EmotionDisplayProps {
  deviceId: string;  // Nicla device identifier (e.g., '1' or '2')
  deviceName: string;  // Display name (e.g., 'Device 1')
  jobStartTime: number;
}

export default function EmotionDisplay({ deviceId, deviceName, jobStartTime }: EmotionDisplayProps) {
  const { impressions, device1Current, device2Current } = useEmotions();
  const [animatedEmojis, setAnimatedEmojis] = useState<AnimatedEmoji[]>([]);
  const prevImpressionsCount = useRef(0);
  
  // Determine which current emotion to use based on device
  // This is a simple approach - you might need to adjust based on your setup
  const isDevice1 = deviceName.includes('1');
  const currentEmotion = isDevice1 ? device1Current : device2Current;
  
  const deviceImpressions = impressions.filter((imp) => imp.device_id === deviceId);

  // Watch for new "impressed" or "not impressed" reactions
  useEffect(() => {
    if (deviceImpressions.length > prevImpressionsCount.current) {
      // Get the latest impression
      const latestImpression = deviceImpressions[deviceImpressions.length - 1];
      
      // Check if it's a reaction that should animate
      if (latestImpression.emotion === 'impressed' || latestImpression.emotion === 'not impressed') {
        const newAnimatedEmoji: AnimatedEmoji = {
          id: `${latestImpression.timestamp}-${Math.random()}`,
          emoji: emotionEmojis[latestImpression.emotion],
          timestamp: Date.now(),
        };
        
        setAnimatedEmojis((prev) => [...prev, newAnimatedEmoji]);
        
        // Remove the emoji after animation completes (3 seconds)
        setTimeout(() => {
          setAnimatedEmojis((prev) => prev.filter((e) => e.id !== newAnimatedEmoji.id));
        }, 3000);
      }
    }
    
    prevImpressionsCount.current = deviceImpressions.length;
  }, [deviceImpressions]);

  return (
    <div className={styles.container}>
      {/* Animated emojis container */}
      <div className={styles.animatedEmojisContainer}>
        {animatedEmojis.map((animatedEmoji) => (
          <div
            key={animatedEmoji.id}
            className={styles.fallingEmoji}
          >
            {animatedEmoji.emoji}
          </div>
        ))}
      </div>

      <div className={styles.header}>
        <div className={styles.title}>{deviceName}</div>
        {currentEmotion && (
          <div className={styles.currentEmotion}>
            <span className={styles.emoji}>
              {emotionEmojis[currentEmotion.emotion] || '❓'}
            </span>
            <span className={styles.emotionText}>{currentEmotion.emotion}</span>
          </div>
        )}
      </div>

      <div className={styles.timeline}>
        {deviceImpressions.length === 0 ? (
          <div className={styles.empty}>Waiting for data...</div>
        ) : (
          <div className={styles.impressionsList}>
            {[...deviceImpressions].reverse().map((impression, index) => (
              <div key={`${impression.timestamp}-${index}`} className={styles.impressionItem}>
                <span className={styles.itemEmoji}>
                  {emotionEmojis[impression.emotion] || '❓'}
                </span>
                <span className={styles.itemEmotion}>{impression.emotion}</span>
                <span className={styles.itemTimestamp}>
                  {formatTimestamp(impression.timestamp, jobStartTime, impressions)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}



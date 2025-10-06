import type { Impression } from '../types';
import styles from '../css/TopMoments.module.css';

interface TopMomentsProps {
  impressions: Impression[];
  startTime: number;
}

interface Moment {
  timestamp1: number;
  timestamp2: number;
  device1Emotion: string;
  device2Emotion: string;
  device1Id: string;
  device2Id: string;
}

export default function TopMoments({ impressions, startTime }: TopMomentsProps) {
  const findTopMoments = (): Moment[] => {
    const moments: Moment[] = [];

    // Group impressions by device
    const deviceImpressions = new Map<string, Impression[]>();
    impressions.forEach(imp => {
      if (!deviceImpressions.has(imp.device_id)) {
        deviceImpressions.set(imp.device_id, []);
      }
      deviceImpressions.get(imp.device_id)!.push(imp);
    });

    // Need at least 2 devices
    const devices = Array.from(deviceImpressions.keys());
    if (devices.length < 2) return [];

    const device1 = devices[0];
    const device2 = devices[1];
    const device1Data = deviceImpressions.get(device1)!;
    const device2Data = deviceImpressions.get(device2)!;

    // Find overlapping reactions within 5 seconds
    const processedPairs = new Set<string>();
    
    device1Data.forEach(imp1 => {
      device2Data.forEach(imp2 => {
        const timeDiff = Math.abs(imp1.timestamp - imp2.timestamp);
        if (timeDiff <= 5000) { // 5 seconds in milliseconds
          // Create a unique key to avoid duplicate pairs
          const pairKey = `${imp1.timestamp}-${imp2.timestamp}`;
          if (!processedPairs.has(pairKey)) {
            processedPairs.add(pairKey);
            moments.push({
              timestamp1: imp1.timestamp,
              timestamp2: imp2.timestamp,
              device1Emotion: imp1.emotion,
              device2Emotion: imp2.emotion,
              device1Id: device1,
              device2Id: device2,
            });
          }
        }
      });
    });

    // Sort by first timestamp and remove moments that are too close together
    return moments
      .sort((a, b) => a.timestamp1 - b.timestamp1)
      .filter((moment, index, arr) => {
        // Keep if it's the first or different from previous
        if (index === 0) return true;
        const prev = arr[index - 1];
        return Math.abs(moment.timestamp1 - prev.timestamp1) > 3000; // At least 3 seconds apart
      });
  };

  const formatTimestamp = (timestamp: number) => {
    // Use startTime if available, otherwise use the earliest impression timestamp
    const referenceTime = startTime > 0 ? startTime : Math.min(...impressions.map(i => i.timestamp));
    const relativeTime = timestamp - referenceTime;
    
    const seconds = Math.floor(relativeTime / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const formatTimeInterval = (time1: number, time2: number) => {
    const time1Formatted = formatTimestamp(time1);
    const time2Formatted = formatTimestamp(time2);
    return `${time1Formatted} && ${time2Formatted}`;
  };

  const topMoments = findTopMoments();

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Top Moments</h2>
      <p className={styles.description}>
        Moments where both people reacted within 5 seconds
      </p>
      {topMoments.length === 0 ? (
        <p className={styles.emptyMessage}>No shared moments found</p>
      ) : (
        <div className={styles.momentsList}>
          {topMoments.map((moment, index) => (
            <div key={index} className={styles.momentCard}>
              <div className={styles.momentTime}>
                {formatTimeInterval(moment.timestamp1, moment.timestamp2)}
              </div>
              <div className={styles.momentReactions}>
                <div className={styles.reaction}>
                  <span className={styles.reactionLabel}>Person 1:</span>
                  <span className={styles.reactionEmotion}>{moment.device1Emotion}</span>
                </div>
                <div className={styles.reaction}>
                  <span className={styles.reactionLabel}>Person 2:</span>
                  <span className={styles.reactionEmotion}>{moment.device2Emotion}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


import type { Impression } from '../types';
import { emotionEmojis } from '../types';
import styles from '../css/FrameDisplays.module.css';

interface FrameDisplaysProps {
  impressions: Impression[];
  currentTime: number;
  startTime: number;
}

interface FrameData {
  frame: string;
  emotion: string;
}

export default function FrameDisplays({ impressions, currentTime, startTime }: FrameDisplaysProps) {
  /**
   * Find the frame closest to the given video time for a specific device
   */
  const getFrameAtTime = (deviceId: string, videoTime: number): FrameData | null => {
    // Filter impressions for this device that have frames
    const deviceImpressions = impressions.filter(
      imp => imp.device_id === deviceId && imp.frame_data
    );
    
    if (deviceImpressions.length === 0) return null;
    
    // Find closest impression by timestamp
    let closest = deviceImpressions[0];
    let minDiff = Infinity;
    
    for (const imp of deviceImpressions) {
      const impVideoTime = (imp.timestamp - startTime) / 1000;
      const diff = Math.abs(videoTime - impVideoTime);
      if (diff < minDiff) {
        minDiff = diff;
        closest = imp;
      }
    }
    
    return {
      frame: closest.frame_data!,
      emotion: closest.emotion
    };
  };

  // Get current frames for both devices
  const person1Data = getFrameAtTime('1', currentTime);
  const person2Data = getFrameAtTime('2', currentTime);

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Camera Feeds</h3>
      
      <div className={styles.feeds}>
        {/* Person 1 */}
        <div className={styles.feedBox}>
          {person1Data && (
            <>
              <img 
                src={`data:image/png;base64,${person1Data.frame}`}
                alt="Person 1 camera"
                className={styles.cameraFrame}
              />
              <div className={styles.feedHeader}>
                <h4>Person 1</h4>
              </div>
              <div className={styles.feedEmotion}>
                <span className={styles.feedEmoji}>
                  {emotionEmojis[person1Data.emotion] || '❓'}
                </span>
                <span className={styles.emotionText}>{person1Data.emotion}</span>
              </div>
            </>
          )}
        </div>

        {/* Person 2 */}
        <div className={styles.feedBox}>
          {person2Data && (
            <>
              <img 
                src={`data:image/png;base64,${person2Data.frame}`}
                alt="Person 2 camera"
                className={styles.cameraFrame}
              />
              <div className={styles.feedHeader}>
                <h4>Person 2</h4>
              </div>
              <div className={styles.feedEmotion}>
                <span className={styles.feedEmoji}>
                  {emotionEmojis[person2Data.emotion] || '❓'}
                </span>
                <span className={styles.emotionText}>{person2Data.emotion}</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

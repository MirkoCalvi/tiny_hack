import { useState, useEffect, useRef } from 'react';
import YouTube, { type YouTubeProps, type YouTubePlayer } from 'react-youtube';
import type { Impression } from '../types';
import { emotionEmojis, emotionColors } from '../types';
import FrameDisplays from './FrameDisplays';
import styles from '../css/EmotionReplay.module.css';

interface EmotionReplayProps {
  impressions: Impression[];
  videoUrl: string | null;
  startTime: number;
}

interface FloatingEmoji {
  id: string;
  emoji: string;
  color: string;
  x: number;
  deviceName: string;
}

export default function EmotionReplay({ impressions, videoUrl, startTime }: EmotionReplayProps) {
  const [player, setPlayer] = useState<YouTubePlayer | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [videoDuration, setVideoDuration] = useState(0);
  const [floatingEmojis, setFloatingEmojis] = useState<FloatingEmoji[]>([]);
  const feedRef = useRef<HTMLDivElement>(null);
  const timeUpdateInterval = useRef<number | null>(null);
  const lastTriggeredTimestamp = useRef<Set<number>>(new Set());

  // Create a merged timeline
  const timeline = [...impressions]
    .sort((a, b) => a.timestamp - b.timestamp)
    .map((impression) => ({
      ...impression,
      videoTime: (impression.timestamp - startTime) / 1000,
      deviceName: impression.device_id === '1' ? 'Person 1' : 'Person 2',
    }));

  // Extract video ID from URL
  useEffect(() => {
    if (!videoUrl) return;
    
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)/,
      /youtube\.com\/embed\/([^&\s]+)/,
    ];

    for (const pattern of patterns) {
      const match = videoUrl.match(pattern);
      if (match && match[1]) {
        setVideoId(match[1]);
        return;
      }
    }
  }, [videoUrl]);

  // Continuously poll video time for frame synchronization (regardless of playing state)
  useEffect(() => {
    if (!player) return;
    
    const updateTime = () => {
      const time = player.getCurrentTime();
      setCurrentTime(time);
      
      // Get duration if we don't have it yet
      if (videoDuration === 0) {
        const duration = player.getDuration();
        if (duration > 0) {
          console.log('Video duration loaded:', duration);
          setVideoDuration(duration);
        }
      }
    };
    
    // Update immediately
    updateTime();
    
    // Then poll every 100ms
    const interval = setInterval(updateTime, 100);
    
    return () => clearInterval(interval);
  }, [player, videoDuration]);

  // Trigger floating emojis while playing
  useEffect(() => {
    if (isPlaying && player) {
      timeUpdateInterval.current = setInterval(() => {
        const time = currentTime;
        
        // Check if we should trigger floating emojis
        timeline.forEach((item) => {
          const timeDiff = Math.abs(time - item.videoTime);
          // Trigger when within 0.2 seconds and not already triggered
          if (timeDiff < 0.2 && !lastTriggeredTimestamp.current.has(item.timestamp)) {
            lastTriggeredTimestamp.current.add(item.timestamp);
            
            const emoji = emotionEmojis[item.emotion] || '❓';
            const color = emotionColors[item.emotion] || '#9ca3af';
            const x = item.deviceName === 'Person 1' ? 25 : 75; // Left or right side
            
            const newEmoji: FloatingEmoji = {
              id: `${item.timestamp}-${Math.random()}`,
              emoji,
              color,
              x,
              deviceName: item.deviceName,
            };
            
            setFloatingEmojis(prev => [...prev, newEmoji]);
            
            // Remove after animation completes
            setTimeout(() => {
              setFloatingEmojis(prev => prev.filter(e => e.id !== newEmoji.id));
            }, 3000);
          }
        });
      }, 100); // Update every 100ms
    } else {
      if (timeUpdateInterval.current) {
        clearInterval(timeUpdateInterval.current);
      }
    }

    return () => {
      if (timeUpdateInterval.current) {
        clearInterval(timeUpdateInterval.current);
      }
    };
  }, [isPlaying, currentTime, timeline]);

  const onReady: YouTubeProps['onReady'] = (event) => {
    console.log('onReady called');
    const playerInstance = event.target;
    setPlayer(playerInstance);
    
    // Get video duration synchronously
    const duration = playerInstance.getDuration();
    console.log('Video duration:', duration, typeof duration);
    
    if (duration > 0) {
      setVideoDuration(duration);
    } else {
      // If not available yet, wait a bit and try again
      setTimeout(() => {
        const dur = playerInstance.getDuration();
        console.log('Video duration (retry):', dur);
        if (dur > 0) {
          setVideoDuration(dur);
        }
      }, 1000);
    }
  };

  const onStateChange: YouTubeProps['onStateChange'] = (event) => {
    console.log('State changed:', event.data);
    // 1 = playing, 2 = paused
    setIsPlaying(event.data === 1);
    
    // Get duration when video starts playing if we don't have it
    if (event.data === 1 && videoDuration === 0 && player) {
      const duration = player.getDuration();
      console.log('Video duration from state change:', duration);
      if (duration > 0) {
        setVideoDuration(duration);
      }
    }
  };

  const jumpToTime = (timestamp: number) => {
    if (!player) return;
    
    const videoTime = (timestamp - startTime) / 1000;
    player.seekTo(videoTime, true);
    player.playVideo();
  };

  const jumpToTimeFromTimeline = (videoTime: number) => {
    if (!player) return;
    player.seekTo(videoTime, true);
    player.playVideo();
  };

  const formatTimestamp = (timestamp: number) => {
    const relativeTime = timestamp - startTime;
    const seconds = Math.floor(relativeTime / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Determine if an impression is "active" (within 3 seconds of current time)
  const isImpressionActive = (impression: Impression) => {
    const impressionVideoTime = (impression.timestamp - startTime) / 1000;
    return Math.abs(currentTime - impressionVideoTime) < 3;
  };

  // Group impressions by device
  const device1Impressions = impressions.filter(imp => imp.device_id === '1');
  const device2Impressions = impressions.filter(imp => imp.device_id === '2');

  const opts: YouTubeProps['opts'] = {
    height: '100%',
    width: '100%',
    playerVars: {
      autoplay: 0,
      controls: 1,
      modestbranding: 1,
      rel: 0,
    },
  };

  if (!videoId) {
    return (
      <div className={styles.container}>
        <div className={styles.noVideo}>
          <h2>No video available</h2>
          <p>Please start a new session to replay emotions</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.containerFullWidth}>
      {/* Horizontal flex: video on left, camera feeds on right */}
      <div className={styles.horizontalLayout}>
        <div className={styles.videoWrapper}>
          <YouTube
            videoId={videoId}
            opts={opts}
            onReady={onReady}
            onStateChange={onStateChange}
            className={styles.player}
          />
          
          {/* Floating Emoji Overlay */}
          <div className={styles.emojiOverlay}>
            {floatingEmojis.map((emoji) => (
              <div
                key={emoji.id}
                className={styles.floatingEmoji}
                style={{
                  left: `${emoji.x}%`,
                  color: emoji.color,
                }}
              >
                <div className={styles.emojiContent}>
                  <span className={styles.emojiIcon}>{emoji.emoji}</span>
                  <span className={styles.emojiLabel}>{emoji.deviceName}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Frame Displays - shows camera feeds synced with video */}
        <FrameDisplays 
          impressions={impressions}
          currentTime={currentTime}
          startTime={startTime}
        />
      </div>

      {/* Emotion Heatmap Timeline - below the horizontal layout */}
      {timeline.length > 0 && (
        <div className={styles.heatmapContainer}>
          <div className={styles.heatmapHeader}>
            <h3>Emotion Timeline</h3>
            {videoDuration > 0 ? (
              <p>
                {timeline.length} reactions • Video duration: {Math.floor(videoDuration / 60)}:{String(Math.floor(videoDuration % 60)).padStart(2, '0')} • Click any marker to jump
              </p>
            ) : (
              <p style={{ color: '#fbbf24' }}>
                ⏳ Waiting for video to load... Play the video to see the timeline.
              </p>
            )}
          </div>
          <div className={styles.heatmapTrack}>
            {/* Progress indicator - spans both lanes */}
            {videoDuration > 0 && (
              <div 
                className={styles.progressIndicator} 
                style={{ left: `${(currentTime / videoDuration) * 100}%` }}
              />
            )}
            
            {/* Person 1 Lane */}
            <div className={styles.timelineLane}>
              <div className={styles.laneLabel}>Person 1</div>
              
              {/* Emotion gradient background */}
              {videoDuration > 0 && (
                <div className={styles.emotionGradient}>
                  {timeline
                    .filter(item => item.device_id === '1')
                    .map((item, index, arr) => {
                      const startPos = (item.videoTime / videoDuration) * 100;
                      const nextItem = arr[index + 1];
                      const endPos = nextItem ? (nextItem.videoTime / videoDuration) * 100 : 100;
                      const width = endPos - startPos;
                      const color = emotionColors[item.emotion] || '#9ca3af';
                      const emoji = emotionEmojis[item.emotion] || '❓';
                      
                      return (
                        <div
                          key={`gradient-p1-${item.timestamp}-${index}`}
                          className={styles.gradientSegment}
                          style={{
                            left: `${startPos}%`,
                            width: `${width}%`,
                            background: `linear-gradient(90deg, ${color} 0%, ${color} 100%)`,
                          }}
                          onClick={() => jumpToTimeFromTimeline(item.videoTime)}
                          title={`${emoji} ${item.emotion} at ${formatTimestamp(item.timestamp)}`}
                        />
                      );
                    })}
                </div>
              )}
            </div>
            
            {/* Person 2 Lane */}
            <div className={styles.timelineLane}>
              <div className={styles.laneLabel}>Person 2</div>
              
              {/* Emotion gradient background */}
              {videoDuration > 0 && (
                <div className={styles.emotionGradient}>
                  {timeline
                    .filter(item => item.device_id === '2')
                    .map((item, index, arr) => {
                      const startPos = (item.videoTime / videoDuration) * 100;
                      const nextItem = arr[index + 1];
                      const endPos = nextItem ? (nextItem.videoTime / videoDuration) * 100 : 100;
                      const width = endPos - startPos;
                      const color = emotionColors[item.emotion] || '#9ca3af';
                      const emoji = emotionEmojis[item.emotion] || '❓';
                      
                      return (
                        <div
                          key={`gradient-p2-${item.timestamp}-${index}`}
                          className={styles.gradientSegment}
                          style={{
                            left: `${startPos}%`,
                            width: `${width}%`,
                            background: `linear-gradient(90deg, ${color} 0%, ${color} 100%)`,
                          }}
                          onClick={() => jumpToTimeFromTimeline(item.videoTime)}
                          title={`${emoji} ${item.emotion} at ${formatTimestamp(item.timestamp)}`}
                        />
                      );
                    })}
                </div>
              )}
            </div>
          </div>
          
          {/* Legend & Stats below timeline */}
          <div className={styles.timelineFooter}>
            {/* Emotion Legend */}
            <div className={styles.emotionLegend}>
              <div className={styles.legendTitle}>Emotions:</div>
              <div className={styles.legendItems}>
                <div className={styles.legendItem}>
                  <div className={styles.legendColor} style={{ backgroundColor: emotionColors.neutral }}></div>
                  <span>Neutral</span>
                </div>
                <div className={styles.legendItem}>
                  <div className={styles.legendColor} style={{ backgroundColor: emotionColors.happy }}></div>
                  <span>Happy</span>
                </div>
                <div className={styles.legendItem}>
                  <div className={styles.legendColor} style={{ backgroundColor: emotionColors.sad }}></div>
                  <span>Sad</span>
                </div>
                <div className={styles.legendItem}>
                  <div className={styles.legendColor} style={{ backgroundColor: emotionColors.impressed }}></div>
                  <span>Impressed</span>
                </div>
              </div>
            </div>

            {/* Stats - Hidden */}
            {/* <div className={styles.timelineStats}>
              <div className={styles.statItem}>
                <span className={styles.statLabel}>Person 1</span>
                <span className={styles.statValue}>{device1Impressions.length} reactions</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statLabel}>Person 2</span>
                <span className={styles.statValue}>{device2Impressions.length} reactions</span>
              </div>
            </div> */}
          </div>
        </div>
      )}

      {/* Hidden feed section for compatibility */}
      <div className={styles.feedSection} style={{ display: 'none' }}>
        <div className={styles.feedHeader}>
          <h3>Emotion Timeline</h3>
          <p className={styles.feedSubtitle}>
            {timeline.length} reactions • Click to jump to moment
          </p>
        </div>

        <div className={styles.feed} ref={feedRef}>
          {timeline.length === 0 ? (
            <div className={styles.emptyFeed}>
              <p>No emotions recorded yet</p>
            </div>
          ) : (
            timeline.map((item, index) => {
              const isActive = isImpressionActive(item);
              const emotion = item.emotion;
              const emoji = emotionEmojis[emotion] || '❓';
              const color = emotionColors[emotion] || '#9ca3af';

              return (
                <div
                  key={`${item.timestamp}-${index}`}
                  className={`${styles.feedItem} ${isActive ? styles.feedItemActive : ''}`}
                  onClick={() => jumpToTime(item.timestamp)}
                  style={{
                    borderLeftColor: color,
                  }}
                >
                  <div className={styles.feedItemHeader}>
                    <span className={styles.feedItemDevice}>{item.deviceName}</span>
                    <span className={styles.feedItemTime}>
                      {formatTimestamp(item.timestamp)}
                    </span>
                  </div>
                  <div className={styles.feedItemEmotion}>
                    <span className={styles.feedItemEmoji}>{emoji}</span>
                    <span className={styles.feedItemEmotionText}>{emotion}</span>
                  </div>
                  {isActive && (
                    <div className={styles.activeIndicator}>
                      <span className={styles.pulse}>●</span> Now
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        <div className={styles.stats}>
          <div className={styles.statItem}>
            <span className={styles.statLabel}>Person 1</span>
            <span className={styles.statValue}>{device1Impressions.length} reactions</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.statLabel}>Person 2</span>
            <span className={styles.statValue}>{device2Impressions.length} reactions</span>
          </div>
        </div>
      </div>
    </div>
  );
}


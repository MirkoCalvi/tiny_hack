import { useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import VideoPlayer from '../components/VideoPlayer';
import EmotionDisplay from '../components/EmotionDisplay';
import styles from '../css/VideoPage.module.css';

interface LocationState {
  videoUrl: string;
  jobStartTime: number;
}

// Nicla device identifiers
const NICLA_DEVICES = [
  { ip: '1', name: 'Device 1' },
  { ip: '2', name: 'Device 2' },
];

export default function VideoPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [videoId, setVideoId] = useState<string | null>(null);
  const [jobStartTime, setJobStartTime] = useState<number>(Date.now());

  useEffect(() => {
    const state = location.state as LocationState;
    
    if (!state?.videoUrl) {
      navigate('/');
      return;
    }

    if (state.jobStartTime) {
      setJobStartTime(state.jobStartTime);
    }

    const extractedId = extractVideoId(state.videoUrl);
    if (extractedId) {
      setVideoId(extractedId);
    } else {
      console.error('Invalid YouTube URL');
      navigate('/');
    }
  }, [location.state, navigate]);

  const extractVideoId = (url: string): string | null => {
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)/,
      /youtube\.com\/embed\/([^&\s]+)/,
    ];

    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match && match[1]) {
        return match[1];
      }
    }

    return null;
  };

  const onVideoEnd = async () => {
    console.log('Video ended');
    // Stop job
    await fetch('http://localhost:3002/api/jobs/stop', { method: 'POST' });
    // Navigate to dashboard
    navigate('/dashboard');
  };

  if (!videoId) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading video...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <div className={styles.header}>
          <h1 className={styles.title}>Cinema Impressions</h1>
          <button onClick={onVideoEnd} className={styles.dashboardButton}>
            View Dashboard →
          </button>
        </div>

        <VideoPlayer videoId={videoId} onVideoEnd={onVideoEnd} />

        <div className={styles.devicesContainer}>
          {NICLA_DEVICES.map((device) => (
            <EmotionDisplay
              key={device.ip}
              deviceId={device.ip}
              deviceName={device.name}
              jobStartTime={jobStartTime}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

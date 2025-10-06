import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStartJob } from '../hooks/useStartJob';
import styles from '../css/SetupPage.module.css';

export default function SetupPage() {
  const [videoUrl, setVideoUrl] = useState('');
  const navigate = useNavigate();
  const { mutate: startJob, isPending, error, data } = useStartJob();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!videoUrl.trim()) {
      return;
    }

    startJob(
      { video_url: videoUrl },
      {
        onSuccess: () => {
          navigate('/video', { 
            state: { 
              videoUrl,
              jobStartTime: Date.now()
            } 
          });
        },
      }
    );
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Cinema Impressions</h1>
        <p className={styles.subtitle}>Real-time emotion tracking during video playback</p>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.inputGroup}>
            <label htmlFor="videoUrl" className={styles.label}>
              YouTube URL
            </label>
            <input
              id="videoUrl"
              type="text"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="https://youtube.com/watch?v=..."
              className={styles.input}
              disabled={isPending}
            />
          </div>

          {data && (
            <div className={styles.deviceStatus}>
              <p className={styles.deviceTitle}>Device Status:</p>
              {data.devices.map((device) => (
                <div key={device.device_id} className={styles.device}>
                  <span className={styles.deviceIndicator}>
                    {device.status === 'online' ? '🟢' : '⚪'}
                  </span>
                  <span>{device.device_id}: {device.status}</span>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className={styles.error}>
              Error: {error.message}
            </div>
          )}

          <button
            type="submit"
            disabled={isPending || !videoUrl.trim()}
            className={styles.button}
          >
            {isPending ? 'Starting...' : 'Start Session →'}
          </button>
        </form>
      </div>
    </div>
  );
}


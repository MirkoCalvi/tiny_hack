import YouTube, { type YouTubeProps } from 'react-youtube';
import styles from '../css/VideoPlayer.module.css';

interface VideoPlayerProps {
  videoId: string;
  onVideoEnd?: () => void;
}

export default function VideoPlayer({ videoId, onVideoEnd }: VideoPlayerProps) {
  const opts: YouTubeProps['opts'] = {
    height: '100%',
    width: '100%',
    playerVars: {
      autoplay: 1,
      controls: 1,
      modestbranding: 1,
      rel: 0,
    },
  };

  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <YouTube
          videoId={videoId}
          opts={opts}
          onEnd={onVideoEnd}
          className={styles.player}
        />
      </div>
    </div>
  );
}



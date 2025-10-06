import { useState, useEffect, useRef } from 'react';
import YouTube, { type YouTubeProps, type YouTubePlayer } from 'react-youtube';
import type { Impression } from '../types';
import styles from '../css/CinemaView.module.css';

interface CinemaViewProps {
  impressions: Impression[];
  videoUrl: string | null;
  startTime: number;
}

interface Seat {
  id: string;
  row: number;
  number: number;
  deviceId: string | null;
  isLit: boolean;
}

export default function CinemaView({ impressions, videoUrl, startTime }: CinemaViewProps) {
  const [player, setPlayer] = useState<YouTubePlayer | null>(null);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [seats, setSeats] = useState<Seat[]>([]);
  const [currentTime, setCurrentTime] = useState(0);

  // Cinema configuration: 8 rows, varying seats per row for realistic perspective
  const CINEMA_ROWS = [
    { row: 1, seats: 6 },  // Front row - fewer seats
    { row: 2, seats: 8 },
    { row: 3, seats: 10 },
    { row: 4, seats: 12 },
    { row: 5, seats: 12 },
    { row: 6, seats: 14 },
    { row: 7, seats: 14 },
    { row: 8, seats: 16 }, // Back row - most seats
  ];

  // Initialize seats with device assignments
  useEffect(() => {
    const allSeats: Seat[] = [];
    
    CINEMA_ROWS.forEach(({ row, seats: seatCount }) => {
      for (let i = 1; i <= seatCount; i++) {
        // Assign devices to specific seats (middle seats in rows 4 and 5)
        let deviceId: string | null = null;
        
        // Person 1: Row 4, middle-left seat
        if (row === 4 && i === Math.floor(seatCount / 2)) {
          deviceId = '1';
        }
        // Person 2: Row 5, middle-right seat
        else if (row === 5 && i === Math.ceil(seatCount / 2) + 1) {
          deviceId = '2';
        }
        
        allSeats.push({
          id: `seat-${row}-${i}`,
          row,
          number: i,
          deviceId,
          isLit: false,
        });
      }
    });
    
    setSeats(allSeats);
  }, []);

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

  // Poll video time
  useEffect(() => {
    if (!player) return;
    
    const interval = setInterval(() => {
      const time = player.getCurrentTime();
      setCurrentTime(time);
    }, 100);
    
    return () => clearInterval(interval);
  }, [player]);

  // Track which impressions have already triggered animations
  const triggeredImpressions = useRef<Set<number>>(new Set());

  // Light up seats when "impressed" emotion is detected
  useEffect(() => {
    impressions.forEach((impression) => {
      if (impression.emotion === 'impressed' && !triggeredImpressions.current.has(impression.timestamp)) {
        const impressionVideoTime = (impression.timestamp - startTime) / 1000;
        const timeDiff = Math.abs(currentTime - impressionVideoTime);
        
        // Light up seat if impression is happening right now (within 0.5 seconds)
        if (timeDiff < 0.5) {
          // Mark this impression as triggered
          triggeredImpressions.current.add(impression.timestamp);
          
          setSeats(prevSeats => 
            prevSeats.map(seat => 
              seat.deviceId === impression.device_id 
                ? { ...seat, isLit: true }
                : seat
            )
          );
          
          // Turn off light after 700ms (quick flash)
          setTimeout(() => {
            setSeats(prevSeats => 
              prevSeats.map(seat => 
                seat.deviceId === impression.device_id 
                  ? { ...seat, isLit: false }
                  : seat
              )
            );
          }, 700);
        }
      }
    });
  }, [currentTime, impressions, startTime]);

  const onReady: YouTubeProps['onReady'] = (event) => {
    setPlayer(event.target);
  };

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
          <h2>🎬 No video available</h2>
          <p>Start a new session to experience the cinema</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Cinema Screen */}
      <div className={styles.screen}>
        <div className={styles.screenFrame}>
          <YouTube
            videoId={videoId}
            opts={opts}
            onReady={onReady}
            className={styles.player}
          />
        </div>
        <div className={styles.screenGlow}></div>
      </div>

      {/* Cinema Seats */}
      <div className={styles.seatingArea}>
        {CINEMA_ROWS.map(({ row }) => {
          const rowSeats = seats.filter(s => s.row === row);
          
          return (
            <div 
              key={`row-${row}`} 
              className={styles.seatRow}
              style={{
                '--row-index': row,
              } as React.CSSProperties}
            >
              {rowSeats.map((seat) => (
                <div
                  key={seat.id}
                  className={`
                    ${styles.seat} 
                    ${seat.deviceId ? styles.seatAssigned : styles.seatEmpty}
                    ${seat.isLit ? styles.seatLit : ''}
                  `}
                  title={seat.deviceId ? `Person ${seat.deviceId}` : ''}
                >
                  <div className={styles.seatBack}></div>
                  <div className={styles.seatBase}></div>
                  {seat.isLit && <div className={styles.seatGlow}></div>}
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {/* Cinema Info */}
      <div className={styles.cinemaInfo}>
        <div className={styles.legend}>
          <div className={styles.legendItem}>
            <div className={`${styles.legendSeat} ${styles.legendAssigned}`}></div>
            <span>Viewer Seat</span>
          </div>
          <div className={styles.legendItem}>
            <div className={`${styles.legendSeat} ${styles.legendEmpty}`}></div>
            <span>Empty Seat</span>
          </div>
          <div className={styles.legendItem}>
            <div className={`${styles.legendSeat} ${styles.legendLit}`}></div>
            <span>Impressed! 🤩</span>
          </div>
        </div>
      </div>
    </div>
  );
}

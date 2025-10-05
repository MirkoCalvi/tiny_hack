import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSummary } from '../hooks/useSummary';
// import TopMoments from '../components/TopMoments';
import EmotionReplay from '../components/EmotionReplay';
import CinemaView from '../components/CinemaView';
import styles from '../css/DashboardPage.module.css';

type ViewType = 'view1' | 'view2' | 'view3' | 'view4';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { data: summary, isLoading, error } = useSummary();
  const [activeView, setActiveView] = useState<ViewType>('view1');

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.empty}>
          <h1>Loading...</h1>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.empty}>
          <h1>Error Loading Data</h1>
          <p>{error.message}</p>
          <button onClick={() => navigate('/')} className={styles.button}>
            Go to Setup
          </button>
        </div>
      </div>
    );
  }

  if (!summary || summary.total_count === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.empty}>
          <h1>No Data Available</h1>
          <p>Start a session first to see the dashboard</p>
          <button onClick={() => navigate('/')} className={styles.button}>
            Go to Setup
          </button>
        </div>
      </div>
    );
  }

  const renderViewContent = () => {
    if (!summary) return null;

    switch (activeView) {
      case 'view1':
        return (
          <EmotionReplay
            impressions={summary.impressions}
            videoUrl={summary.video_url}
            startTime={summary.start_time || 0}
          />
        );
      // case 'view2':
      //   return (
      //     <TopMoments 
      //       impressions={summary.impressions} 
      //       startTime={summary.start_time || 0} 
      //     />
      //   );
      case 'view3':
        return (
          <CinemaView 
            impressions={summary.impressions}
            videoUrl={summary.video_url}
            startTime={summary.start_time || 0}
          />
        );
      // case 'view4':
      //   return (
      //     <div className={styles.viewContent}>
      //       <h2>View 4</h2>
      //       <p>Contenuto della quarta view</p>
      //     </div>
      //   );
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <div className={styles.header}>
          <h1 className={styles.title}>Dashboard</h1>
          <button onClick={() => navigate('/')} className={styles.newButton}>
            New Session
          </button>
        </div>

        <div className={styles.tabsContainer}>
          <button
            className={`${styles.tabButton} ${activeView === 'view1' ? styles.tabButtonActive : ''}`}
            onClick={() => setActiveView('view1')}
          >
            Emotion Replay
          </button>
          {/* <button
            className={`${styles.tabButton} ${activeView === 'view2' ? styles.tabButtonActive : ''}`}
            onClick={() => setActiveView('view2')}
          >
            Top Moments
          </button> */}
          <button
            className={`${styles.tabButton} ${activeView === 'view3' ? styles.tabButtonActive : ''}`}
            onClick={() => setActiveView('view3')}
          >
            Cinema View
          </button>
          {/* <button
            className={`${styles.tabButton} ${activeView === 'view4' ? styles.tabButtonActive : ''}`}
            onClick={() => setActiveView('view4')}
          >
            View 4
          </button> */}
        </div>

        <div className={styles.viewContainer}>
          {renderViewContent()}
        </div>
      </div>
    </div>
  );
}

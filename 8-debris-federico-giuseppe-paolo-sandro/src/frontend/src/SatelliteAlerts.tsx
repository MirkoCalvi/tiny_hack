import { useEffect, useState } from 'react'
import type { SatelliteAlert, SatelliteTLE } from './lib/types'
import clsx from 'clsx'

const labels = ['🪨', '🗿', '🌑', '🛰️', '🛰️']
const POOLING_INTERVAL = 1000 * 3;

export function SatelliteAlerts({ }: { satellite: SatelliteTLE }) {
  const [alerts, setAlerts] = useState<SatelliteAlert[]>([]);

  useEffect(() => {
    let intervalId: number;

    (async () => {
      const data: SatelliteAlert[] = await fetch('/get_data').then(r => r.json());
      setAlerts(data)

      intervalId = setInterval(async () => {
        const data: SatelliteAlert[] = await fetch('/get_data').then(r => r.json());
        setAlerts(data)
      }, POOLING_INTERVAL);
    })();

    return () => {
      if (intervalId) clearInterval(intervalId);
    }
  }, []);

  return (
    <div className="divide-y divide-white/10">
      {alerts.map((alert, idx) => {
        const bestGuessIndx = alert.classification.reduce((currIndx, v, i, arr) => {
          if (v > arr[currIndx]) return i;
          return currIndx;
        }, 0);

        console.log(bestGuessIndx);

        return (
          <div key={idx} className="px-4 py-3">
            <div className="flex items-center gap-2">
              <p className="text-xs text-muted-foreground">{new Date(alert.timestamp).toLocaleString()}</p>
            </div>

            <img className="bg-white/5 h-48 rounded-md mt-2 border-[1px] border-white/10 w-full object-cover" src={alert.image} />
            <div className="mt-2 grid grid-cols-4 gap-2 text-xs">
              {alert.classification.slice(0, 4).map((c, i) => (
                <div key={i} className={clsx("rounded-md border border-white/10 bg-white/5 p-2", i == bestGuessIndx && "!bg-green-600/40 !border-green-500/10 text-black")}>
                  <p className="font-medium tracking-tight">{labels[i] ?? `C${i + 1}`}</p>
                  <p className="mt-1 tabular-nums text-muted-foreground">{(c * 100).toFixed(1)}%</p>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { World } from './World'
import { ChevronDown, ChevronRight, Moon, SunMedium } from 'lucide-react'
import { SatelliteAlerts } from './SatelliteAlerts'
import { Button } from '@/components/ui/button'
import type { SatelliteTLE } from './lib/types'

function App() {
  const [selected, setSelected] = useState<string | null>(null)
  const [isDark, setIsDark] = useState(true)
  const [satellites, setSatellites] = useState<SatelliteTLE[]>([]);

  useEffect(() => {
    const stored = localStorage.getItem('theme')
    const initialDark = stored ? stored === 'dark' : true
    setIsDark(initialDark)
    document.documentElement.classList.toggle('dark', initialDark);

    (async () => {
      const data: SatelliteTLE[] = await fetch('/get_satellite').then(r => r.json());
      console.log('getSatellite', data);
      setSatellites(data);
    })();
  }, [])

  const toggleTheme = () => {
    const next = !isDark
    setIsDark(next)
    document.documentElement.classList.toggle('dark', next)
    localStorage.setItem('theme', next ? 'dark' : 'light')
  }

  return (
    <div className="h-dvh w-dvw overflow-hidden bg-gradient-to-b from-background to-black/60">
      <div className="flex h-full">
        {/* Title area */}
        <div className="absolute z-99 mt-5 ml-5 font-semibold tracking-tight text-2xl">
          <h1>Low Power Space Debirs Monitoring</h1>
          <p className="text-sm w-6/11 font-normal text-white/70">A project for <a className="text-white/50" href="https://toolboxcoworking.com/eventi/tiny-hack-the-first-hackathon-on-embedded-ai-vision">tiny_hack</a>. Made by Federico Mele, Giuseppe Pascale, Paolo Malugani, Sandro Marghella.</p>
        </div>

        {/* Globe area */}
        <div className="relative flex-1">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(99,102,241,.15),transparent_60%)]" />
          <World satellites={satellites} selected={selected} />
        </div>

        {/* Sidebar */}
        <aside
          className="z-10 w-[30%] shrink-0 border-l border-white/10 bg-background/40 backdrop-blur-xl text-foreground shadow-xl inset-y-0 right-0 absolute"
        >
          <header className="sticky top-0 z-10 border-b border-white/10 bg-background/60 backdrop-blur-xl px-5 py-4 flex items-center gap-2">
            <div>
              <h1 className="text-base font-semibold tracking-tight">Satellite Console</h1>
              <p className="text-xs text-muted-foreground">Live positions and alerts</p>
            </div>
            <Button
              variant="outline"
              size="icon"
              className="ml-auto"
              aria-label="Toggle theme"
              onClick={toggleTheme}
            >
              {isDark ? <SunMedium className="size-4" /> : <Moon className="size-4" />}
            </Button>
          </header>

          <div className="h-[calc(100dvh-68px)] overflow-y-auto px-4 py-4">
            {satellites.map((satellite, i) => {
              const open = selected === satellite.name
              return (
                <div
                  key={`${satellite.name}-${i}`}
                  className="mb-4 rounded-lg border border-white/10 bg-white/5 p-0 backdrop-blur transition-colors hover:bg-white/[0.07] data-[open=true]:bg-secondary/20"
                  data-open={open}
                >
                  <button
                    className="flex w-full items-center gap-2 px-4 py-3 text-left outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                    onClick={() => setSelected(open ? null : satellite.name)}
                  >
                    <span className="text-sm font-medium tracking-tight">{satellite.name}</span>
                    {open ? (
                      <ChevronDown className="ml-auto size-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="ml-auto size-4 text-muted-foreground" />
                    )}
                  </button>

                  {open && (
                    <div className="border-t border-white/10">
                      <SatelliteAlerts satellite={satellite} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </aside>
      </div>
    </div>
  )
}

export default App

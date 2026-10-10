"use client"

import { CalendarDays, Hourglass, Pause, Play, RotateCcw, SkipForward, UserX, Users, type LucideIcon } from "lucide-react"
import { cn } from "cn"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { SPEEDS, type Replay, type Speed } from "@/hooks/use-replay"
import { hhmm } from "@/lib/time"

const DAY_ICONS: Record<string, LucideIcon> = {
  "calendar-days": CalendarDays,
  "user-x": UserX,
  users: Users,
  hourglass: Hourglass,
}

export function ReplayControls({ r }: { r: Replay }) {
  const meta = r.meta!
  const span = meta.close - meta.open
  const ticks = Array.from({ length: Math.floor(span / 120) + 1 }, (_, i) => meta.open + i * 120)

  return (
    <Card className="gap-0 rounded-2xl p-4 shadow-sm sm:p-5">
      <div className="mb-2.5 text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">Demo day</div>
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4" role="group" aria-label="Demo day">
        {meta.days.map((d) => {
          const Icon = DAY_ICONS[d.icon] ?? CalendarDays
          const active = d.name === r.day
          return (
            <button
              key={d.name}
              type="button"
              onClick={() => r.setDay(d.name)}
              aria-pressed={active}
              className={cn(
                "group flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-all outline-none focus-visible:ring-3 focus-visible:ring-ring/50 active:scale-[0.98]",
                active
                  ? "border-brand bg-card shadow-sm ring-3 ring-brand/15"
                  : "bg-muted/50 hover:border-foreground/15 hover:bg-card",
              )}
            >
              <span
                className={cn(
                  "hidden size-8 shrink-0 place-items-center rounded-lg sm:grid",
                  active ? "bg-gradient-to-br from-teal-500 to-teal-700 text-white" : "bg-muted text-muted-foreground",
                )}
              >
                <Icon className="size-4" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[13.5px] font-semibold">{d.name}</span>
                <span className="block truncate text-xs text-muted-foreground">{d.tag}</span>
              </span>
            </button>
          )
        })}
      </div>

      <div className="mt-4 flex flex-col gap-4 border-t pt-4 lg:flex-row lg:items-center lg:gap-6">
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={r.togglePlay} className="h-9 min-w-24 rounded-lg px-4 text-sm font-semibold">
            {r.playing ? <Pause /> : <Play />}
            {r.playing ? "Pause" : r.closed ? "Replay" : "Play"}
          </Button>
          <Button
            variant="outline"
            onClick={r.step}
            disabled={r.playing || r.closed}
            className="h-9 rounded-lg px-3"
            title="Step forward 5 minutes"
          >
            <SkipForward />5 min
          </Button>
          <ToggleGroup
            value={[r.speed]}
            onValueChange={(v) => v[0] && r.setSpeed(v[0] as Speed)}
            spacing={0}
            aria-label="Replay speed"
            className="h-9 rounded-lg border bg-muted/60 p-0.5"
          >
            {(Object.keys(SPEEDS) as Speed[]).map((s) => (
              <ToggleGroupItem
                key={s}
                value={s}
                className="h-full rounded-md! px-3 text-[13px] text-muted-foreground data-[pressed]:bg-card data-[pressed]:text-foreground data-[pressed]:shadow-sm"
              >
                {s}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          <Button variant="outline" onClick={r.reset} className="h-9 rounded-lg px-3">
            <RotateCcw />
            Reset
          </Button>
        </div>

        <div className="min-w-0 flex-1 pt-1" aria-hidden>
          <div className="relative h-1.5 rounded-full bg-muted">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-brand to-brand-strong transition-[width] duration-300 ease-out"
              style={{ width: `${r.progress}%` }}
            />
            {r.moves.map((m) => (
              <span
                key={`${m.id}@${m.at}`}
                title={`${m.label} at ${hhmm(m.at)}`}
                className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rotate-45 rounded-[3px] border-2 border-card bg-indigo-500"
                style={{ left: `${((m.at - meta.open) / span) * 100}%` }}
              />
            ))}
            <span
              className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-brand bg-card shadow-[0_0_0_4px_var(--glow)] transition-[left] duration-300 ease-out"
              style={{ left: `${r.progress}%` }}
            />
          </div>
          <div className="tabular mt-2 flex justify-between text-[11px] text-muted-foreground">
            {ticks.map((t) => (
              <span key={t}>{hhmm(t)}</span>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}

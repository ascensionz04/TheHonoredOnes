import { ArrowRight, ChevronRight, TrendingDown, TrendingUp, Users } from "lucide-react"
import { cn } from "cn"

import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import type { StationView } from "@/lib/types"

import { STATUS_BAR, STATUS_LEGEND, StatusPill } from "./status"

const TOP_EDGE: Record<StationView["status"], string> = {
  ok: "before:bg-transparent",
  watch: "before:bg-watch",
  breach: "before:bg-breach",
  over: "before:bg-over",
}

function TrendIcon({ dir }: { dir: StationView["trend_dir"] }) {
  if (dir === "up") return <TrendingUp className="size-3.5 shrink-0" />
  if (dir === "down") return <TrendingDown className="size-3.5 shrink-0" />
  return <ArrowRight className="size-3.5 shrink-0" />
}

function StationTile({ s, limit, small = false }: { s: StationView; limit: number; small?: boolean }) {
  return (
    <div
      role="listitem"
      className={cn(
        "relative flex min-w-0 flex-col rounded-2xl border bg-card transition-[border-color,box-shadow] duration-200",
        "before:absolute before:inset-x-4 before:top-0 before:h-0.5 before:rounded-b-sm",
        TOP_EDGE[s.status],
        small ? "gap-1.5 px-3 py-2.5" : "gap-2 p-3.5 shadow-xs",
        s.focus && "border-foreground shadow-[0_0_0_3px_color-mix(in_oklch,var(--foreground)_10%,transparent)]",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-[13.5px] font-semibold text-foreground/80">{s.name}</span>
        <StatusPill status={s.status} word={s.status_word} />
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className={cn("tabular leading-none font-bold tracking-tighter", small ? "text-2xl" : "text-[34px]")}>
          {s.wait_now}
        </span>
        <span className="text-xs font-medium text-muted-foreground">min wait</span>
      </div>
      <div
        className={cn(
          "flex items-center gap-1.5 text-xs font-medium",
          s.trend_dir === "up" ? "text-breach" : s.trend_dir === "down" ? "text-ok" : "text-muted-foreground",
        )}
      >
        <TrendIcon dir={s.trend_dir} />
        <span className="truncate">{s.trend}</span>
      </div>
      {!small && (
        <div className="h-1 overflow-hidden rounded-full bg-muted" title={`Wait now against the ${limit}-minute limit`}>
          <div
            className={cn("h-full rounded-full transition-[width] duration-300 ease-out", STATUS_BAR[s.status])}
            style={{ width: `${s.fill}%` }}
          />
        </div>
      )}
      <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
        <span className="inline-flex min-w-0 items-center gap-1.5">
          <Users className="size-3.5 shrink-0" />
          <span className="truncate">{s.staff}</span>
        </span>
        <span
          className="font-semibold whitespace-nowrap"
          title={`Chance of passing the ${limit}-minute limit within the hour`}
        >
          {s.chance > 0 ? `${s.chance}% chance` : "Clear"}
        </span>
      </div>
    </div>
  )
}

function Connector() {
  return (
    <div className="grid place-items-center text-muted-foreground/60 max-md:h-3 max-md:rotate-90" aria-hidden>
      <ChevronRight className="size-4" />
    </div>
  )
}

export function PatientFlow({ stations, limit }: { stations: StationView[] | null; limit: number }) {
  return (
    <Card className="gap-0 rounded-2xl p-4 shadow-sm sm:p-5">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-[17px] font-semibold tracking-tight">Patient flow</h2>
          <p className="mt-1 text-[13.5px] text-muted-foreground">
            Wait now at each station, and the trend over the next 30 minutes.
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {STATUS_LEGEND.map(([k, w]) => (
            <StatusPill key={k} status={k} word={w} />
          ))}
        </div>
      </div>

      {stations?.length === 5 ? (
        <div
          role="list"
          aria-label="Stations in the order patients move"
          className="grid grid-cols-1 items-center gap-1.5 md:grid-cols-[1fr_20px_1fr_20px_1.05fr_20px_1fr]"
        >
          <StationTile s={stations[0]} limit={limit} />
          <Connector />
          <StationTile s={stations[1]} limit={limit} />
          <Connector />
          <div className="relative flex flex-col gap-2 rounded-2xl border border-dashed border-foreground/15 p-2 pt-6 max-md:flex-row max-sm:flex-col">
            <span className="absolute top-1.5 left-3 text-[10px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
              If needed
            </span>
            <div className="flex-1">
              <StationTile s={stations[2]} limit={limit} small />
            </div>
            <div className="flex-1">
              <StationTile s={stations[3]} limit={limit} small />
            </div>
          </div>
          <Connector />
          <StationTile s={stations[4]} limit={limit} />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-36 rounded-2xl" />
          ))}
        </div>
      )}
    </Card>
  )
}

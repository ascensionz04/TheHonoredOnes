"use client"

import { ArrowRight, ChevronRight, History, Radar, type LucideIcon } from "lucide-react"
import { AnimatePresence, motion } from "framer-motion"
import { cn } from "cn"

import { Card } from "@/components/ui/card"
import { hhmm } from "@/lib/time"
import type { AppliedMove, Outcome, Watching } from "@/lib/types"

function SideCard({ icon: Icon, title, count, children }: {
  icon: LucideIcon
  title: string
  count?: number
  children: React.ReactNode
}) {
  return (
    <Card className="gap-3 rounded-2xl p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Icon className="size-4" />
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        </div>
        {!!count && (
          <span className="grid h-5.5 min-w-5.5 place-items-center rounded-full bg-muted px-1.5 text-xs font-bold text-foreground/80">
            {count}
          </span>
        )}
      </div>
      {children}
    </Card>
  )
}

export function AlsoWatching({ items, onSelect }: { items: Watching[]; onSelect: (station: string) => void }) {
  return (
    <SideCard icon={Radar} title="Also watching" count={items.length}>
      {items.length ? (
        <ul className="flex flex-col gap-1.5">
          {items.map((a) => (
            <li key={a.station}>
              <button
                type="button"
                onClick={() => onSelect(a.station)}
                title="Show this in the action card"
                className="flex w-full items-center gap-2.5 rounded-xl border bg-muted/50 py-2.5 pr-2.5 pl-3 text-left transition-colors outline-none hover:border-foreground/15 hover:bg-card focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <span className={cn("size-2 shrink-0 rounded-full", a.tone === "breach" ? "bg-breach" : "bg-watch")} />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold">{a.name}</span>
                  <span className="block text-[12.5px] text-muted-foreground">{a.when}</span>
                </span>
                {a.cause && (
                  <span className="rounded-md border bg-card px-2 py-0.5 text-xs font-medium whitespace-nowrap text-muted-foreground">
                    {a.cause}
                  </span>
                )}
                <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[13.5px] text-muted-foreground">Nothing else is close to the limit.</p>
      )}
    </SideCard>
  )
}

export function MovesApplied({ moves, outcome, showOutcome, limit }: {
  moves: AppliedMove[]
  outcome: Outcome | null
  showOutcome: boolean
  limit: number
}) {
  return (
    <SideCard icon={History} title="Moves applied" count={moves.length}>
      {moves.length ? (
        <ul className="flex flex-col gap-2">
          <AnimatePresence initial={false}>
            {moves.map((m) => (
              <motion.li
                key={`${m.id}@${m.at}`}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-baseline gap-2.5 text-[13.5px] leading-snug"
              >
                <span className="tabular shrink-0 rounded-md bg-indigo-500/12 px-1.5 py-0.5 text-xs font-bold text-indigo-500">
                  {hhmm(m.at)}
                </span>
                <span className="text-foreground/75">{m.label}</span>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      ) : (
        <p className="text-[13.5px] text-muted-foreground">None yet. Apply a recommendation to see how the day changes.</p>
      )}
      {showOutcome && outcome && (
        <div className="rounded-xl border bg-muted/50 p-3.5">
          <div className="text-xs font-semibold text-muted-foreground">Patients waiting over {limit} min today</div>
          <div className="mt-2 flex items-center justify-between gap-2">
            <div className="flex flex-col">
              <span className="tabular text-[28px] leading-tight font-bold tracking-tight text-muted-foreground">
                {outcome.without_pct}%
              </span>
              <span className="text-xs text-muted-foreground">{outcome.without_label}</span>
            </div>
            <ArrowRight className="size-[18px] text-muted-foreground" />
            <div className="flex flex-col items-end">
              <span className="tabular text-[28px] leading-tight font-bold tracking-tight text-ok">{outcome.with_pct}%</span>
              <span className="text-xs text-muted-foreground">{outcome.with_label}</span>
            </div>
          </div>
        </div>
      )}
    </SideCard>
  )
}

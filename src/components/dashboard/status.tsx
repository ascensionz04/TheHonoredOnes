import { cn } from "cn"

import type { Status } from "@/lib/types"

export const STATUS_LEGEND: [Status, string][] = [
  ["ok", "OK"],
  ["watch", "Watch"],
  ["breach", "Will breach"],
  ["over", "Over limit"],
]

const PILL: Record<Status, string> = {
  ok: "bg-ok/10 text-ok",
  watch: "bg-watch/12 text-watch",
  breach: "bg-breach/10 text-breach",
  over: "bg-over text-white",
}

export const STATUS_BAR: Record<Status, string> = {
  ok: "bg-ok",
  watch: "bg-watch",
  breach: "bg-breach",
  over: "bg-over",
}

/** A status is always a word as well as a colour. */
export function StatusPill({ status, word, className }: { status: Status; word: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap",
        PILL[status],
        className,
      )}
    >
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {word}
    </span>
  )
}

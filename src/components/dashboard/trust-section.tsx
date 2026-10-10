"use client"

import { ChevronDown, FileText, ShieldCheck } from "lucide-react"

import { Card } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import type { Meta } from "@/lib/types"

export function TrustSection({ meta }: { meta: Meta }) {
  const notes = [...meta.notes, ...meta.assumptions]
  return (
    <Card className="gap-0 rounded-2xl p-5 shadow-sm sm:p-6">
      <h2 className="flex items-center gap-2 text-[17px] font-semibold tracking-tight">
        <ShieldCheck className="size-[18px] text-brand" />
        Why trust this?
      </h2>
      <p className="mt-1 text-[13.5px] text-muted-foreground">
        {meta.testDays
          ? `Measured on ${meta.testDays} simulated clinic days held out from building the model.`
          : "Evidence from the evaluation run."}
      </p>

      {meta.metrics.length === 0 && notes.length === 0 ? (
        <p className="mt-4 text-[13.5px] text-muted-foreground">Test results will appear here once the evaluation has run.</p>
      ) : (
        <>
          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {meta.metrics.map((m) => (
              <div key={m.caption} className="rounded-2xl border bg-muted/40 p-4">
                <div className="tabular bg-gradient-to-br from-foreground to-brand bg-clip-text text-[28px] font-bold tracking-tight text-transparent">
                  {m.value}
                </div>
                <p className="mt-1.5 text-[13px] leading-relaxed text-foreground/75">{m.caption}</p>
              </div>
            ))}
          </div>
          {notes.length > 0 && (
            <Collapsible className="mt-3 rounded-xl border">
              <CollapsibleTrigger className="group flex w-full items-center gap-2 rounded-xl px-3.5 py-2.5 text-left text-sm font-semibold text-foreground/80 outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50">
                <FileText className="size-4" />
                Data and assumptions
                <ChevronDown className="ml-auto size-4 text-muted-foreground transition-transform group-data-[panel-open]:rotate-180" />
              </CollapsibleTrigger>
              <CollapsibleContent className="px-3.5 pb-3.5">
                <ul className="flex list-disc flex-col gap-1.5 pl-5 text-[13px] leading-relaxed text-foreground/75">
                  {notes.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              </CollapsibleContent>
            </Collapsible>
          )}
        </>
      )}
    </Card>
  )
}

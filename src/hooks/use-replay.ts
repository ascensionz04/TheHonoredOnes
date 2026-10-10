"use client"

import { useCallback, useEffect, useMemo, useState } from "react"

import { ApiError, fetchMeta, fetchScreen, screenKey } from "@/lib/api"
import type { AppliedMove, Meta, Screen } from "@/lib/types"

export const SPEEDS = { Slow: 1000, Normal: 500, Fast: 200 } as const // ms per 5-minute step
export type Speed = keyof typeof SPEEDS

/** The demo replay: clock, play loop, applied moves, and the screen for the current moment. */
export function useReplay() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [metaError, setMetaError] = useState<string | null>(null)
  const [day, setDayName] = useState("")
  const [clock, setClock] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<Speed>("Fast")
  const [moves, setMoves] = useState<AppliedMove[]>([])
  const [selected, setSelected] = useState("")
  const [screen, setScreen] = useState<Screen | null>(null)
  const [loadedKey, setLoadedKey] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [metaAttempt, setMetaAttempt] = useState(0)
  const [attempt, setAttempt] = useState(0)

  // Clinic hours, demo days and evidence, once.
  useEffect(() => {
    const ctrl = new AbortController()
    fetchMeta(ctrl.signal)
      .then((m) => {
        setMeta(m)
        setDayName(m.defaultDay)
        setClock(m.open)
      })
      .catch((err) => {
        if (err.name !== "AbortError") setMetaError((err as Error).message)
      })
    return () => ctrl.abort()
  }, [metaAttempt])

  const key = meta && day ? screenKey(day, clock, moves, selected) : ""

  // The screen for the current moment. Keep showing the last one while the next loads.
  // A selected alert that is no longer raised falls back to the top one on the server.
  useEffect(() => {
    if (!key) return
    let live = true
    fetchScreen(key)
      .then((s) => {
        if (!live) return
        setScreen(s)
        setLoadedKey(key)
        setError(null)
      })
      .catch((err) => {
        if (!live) return
        setError(err instanceof ApiError ? err.message : "Something went wrong. Press Reset to try again.")
        setPlaying(false)
      })
    return () => {
      live = false
    }
  }, [key, attempt])

  // Warm the next step so playback stays smooth.
  useEffect(() => {
    if (meta && loadedKey === key && key && clock < meta.close) {
      fetchScreen(screenKey(day, clock + meta.tick, moves, selected)).catch(() => {})
    }
  }, [loadedKey, key, meta, day, clock, moves, selected])

  // Play: advance one step after the current screen is on show.
  useEffect(() => {
    if (!playing || !meta || loadedKey !== key || clock >= meta.close) return
    const id = setTimeout(() => {
      const next = Math.min(meta.close, clock + meta.tick)
      setClock(next)
      if (next >= meta.close) setPlaying(false)
    }, SPEEDS[speed])
    return () => clearTimeout(id)
  }, [playing, meta, loadedKey, key, clock, speed])

  const reset = useCallback(() => {
    if (!meta) return
    setPlaying(false)
    setClock(meta.open)
    setMoves([])
    setSelected("")
    setError(null)
    setAttempt((a) => a + 1)
  }, [meta])

  const setDay = useCallback(
    (name: string) => {
      if (!meta || name === day) return
      setDayName(name)
      setPlaying(false)
      setClock(meta.open)
      setMoves([])
      setSelected("")
      setError(null)
    },
    [meta, day],
  )

  const closed = !!meta && clock >= meta.close

  const togglePlay = useCallback(() => {
    if (!meta) return
    if (closed) {
      setClock(meta.open)
      setMoves([])
      setSelected("")
      setPlaying(true)
      return
    }
    setPlaying((p) => !p)
  }, [meta, closed])

  const step = useCallback(() => {
    if (!meta || playing || closed) return
    setClock((c) => Math.min(meta.close, c + meta.tick))
  }, [meta, playing, closed])

  /** Apply the card's recommended move from now. Returns the move, or null if nothing applies. */
  const apply = useCallback((): AppliedMove | null => {
    const card = screen?.card
    if (!card?.helps || closed || loadedKey !== key) return null
    if (moves.some((m) => m.id === card.action_id && m.at === clock)) return null
    const move = { id: card.action_id, label: card.action_label, at: clock }
    setMoves((ms) => [...ms, move])
    setSelected("")
    return move
  }, [screen, closed, loadedKey, key, moves, clock])

  const retry = useCallback(() => {
    setError(null)
    if (meta) {
      setAttempt((a) => a + 1)
    } else {
      setMetaError(null)
      setMetaAttempt((a) => a + 1)
    }
  }, [meta])

  const progress = useMemo(
    () => (meta ? ((clock - meta.open) / (meta.close - meta.open)) * 100 : 0),
    [meta, clock],
  )

  return {
    meta,
    metaError,
    day,
    clock,
    playing,
    speed,
    moves,
    selected,
    screen,
    error,
    closed,
    progress,
    loading: !!key && loadedKey !== key,
    setDay,
    setSpeed,
    setSelected,
    togglePlay,
    step,
    reset,
    apply,
    retry,
  }
}

export type Replay = ReturnType<typeof useReplay>

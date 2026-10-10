export function hhmm(minutes: number) {
  const m = Math.round(minutes)
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`
}

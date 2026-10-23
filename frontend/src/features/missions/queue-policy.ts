/** Do not advance an ordered conversation while the previous server mutation is uncertain. */
export function canDrainQueuedTurn(confirmed: boolean, paused: boolean): boolean {
  return confirmed && !paused
}

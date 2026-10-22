import type { MissionSnapshot } from './mission-api'

/** Recover the *specific* completed turn, never accidentally reuse an older one.
 * A streaming disconnect can happen after Django has saved all SSE events.
 */
export function completedTurnWasPersisted(
  snapshot: MissionSnapshot,
  requestedMessage: string,
  previousSequence: number,
): boolean {
  if (snapshot.state?.last_turn_message !== requestedMessage) return false
  return (snapshot.events ?? []).some((event) =>
    event.type === 'turn.completed'
    && Number.isSafeInteger(event.seq) && event.seq > previousSequence)
}

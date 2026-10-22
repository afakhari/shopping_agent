/** Pure presentation policies shared by the conversation and tests. */
export function findCurrentSearchMessage<T extends { role: string; results?: unknown[] }>(messages: T[]): T | undefined {
  // A follow-up without catalog results must not make the previous selection inaccessible.
  return [...messages].reverse().find((item) => item.role === 'assistant' && item.results !== undefined)
}

export function shouldFollowConversation(scrollHeight: number, scrollTop: number, clientHeight: number): boolean {
  // Preserve the reading position when the user scrolls up to inspect earlier results.
  return scrollHeight - scrollTop - clientHeight < 110
}

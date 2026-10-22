export interface HealthResponse {
  status: 'ready' | 'not_ready'
  checks?: Record<string, string>
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch('/api/v1/health/ready/', { signal, headers: { Accept: 'application/json' } })
  let payload: HealthResponse
  try {
    payload = (await response.json()) as HealthResponse
  } catch {
    throw new Error(`Health endpoint returned invalid JSON (${response.status})`)
  }
  if (!response.ok && response.status !== 503) {
    throw new Error(`Health endpoint returned ${response.status}`)
  }
  return payload
}

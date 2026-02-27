import createClient, { type Middleware } from "openapi-fetch"
import type { paths } from "./types/generated"

const REQUEST_TIMEOUT_MS = 30_000

const client = createClient<paths>({ baseUrl: "/api" })

const authMiddleware: Middleware = {
  onRequest({ request }) {
    const apiKey = import.meta.env.VITE_API_KEY
    if (apiKey) {
      request.headers.set("X-API-Key", apiKey)
    }
    return request
  },
}

const timeoutMiddleware: Middleware = {
  onRequest({ request }) {
    const controller = new AbortController()
    const timerId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
    // Propagate cancellation from the original signal (e.g. React Query unmount)
    // and clear the timer to avoid a no-op abort after the request is gone.
    request.signal.addEventListener("abort", () => {
      clearTimeout(timerId)
      controller.abort()
    })
    return new Request(request, { signal: controller.signal })
  },
}

client.use(authMiddleware)
client.use(timeoutMiddleware)

export default client

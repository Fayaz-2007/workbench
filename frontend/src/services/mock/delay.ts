/** Simulates network latency for mock service implementations. */
export function delay(ms = 400): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

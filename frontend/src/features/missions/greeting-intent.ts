/** Pure UI intent gate: greetings are not product searches. */
export function isGreetingOnly(message: string): boolean {
  const normalized = message
    .normalize('NFKC')
    .replace(/[\u200c\u200d]/g, ' ')
    .replace(/[!؟?.,،؛:؛\s]+/gu, ' ')
    .trim()
    .toLocaleLowerCase('fa-IR')
  return /^(?:سلام|درود|سلام خوبی|سلام چطوری|سلام وقت بخیر|سلام وقتتون بخیر|صبح بخیر|عصر بخیر|شب بخیر|hi|hello|hey)$/u.test(normalized)
}

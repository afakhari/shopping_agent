/** Pure UI intent gate: greetings are not product searches. */
export function isGreetingOnly(message: string): boolean {
  const normalized = message
    .normalize('NFKC')
    .replace(/[\u200c\u200d]/g, ' ')
    .replace(/[!؟?.,،؛:؛\s]+/gu, ' ')
    .trim()
    .toLocaleLowerCase('fa-IR')
  return /^(?:سلام|درود|خوبی|چطوری|چطوری خوبی|حالت چطوره|چه خبر|سلام خوبی|سلام چطوری|سلام وقت بخیر|سلام وقتتون بخیر|صبح بخیر|عصر بخیر|شب بخیر|hi|hello|hey)$/u.test(normalized)
}


/** Only explicit requests about using *this assistant* are local help messages.
 * "چطور هدفون مناسب بخرم؟" is shopping advice, not application help.
 */
export function isAssistantHelpRequest(message: string): boolean {
  const normalized = message
    .normalize('NFKC')
    .replace(/[\u200c\u200d]/g, ' ')
    .replace(/[!؟?.,،؛:\s]+/gu, ' ')
    .trim()
    .toLocaleLowerCase('fa-IR')
  return /^(?:راهنما|کمک|چطور ازت استفاده کنم|چجوری ازت استفاده کنم|چطور از این برنامه استفاده کنم|چطوری از این برنامه استفاده کنم|چطور باهات کار کنم|چجوری باهات کار کنم|چطور کار می کنی|چطوری کار می کنی|چه کارهایی می تونی انجام بدی|چه کارهایی بلدی)$/u.test(normalized)
}

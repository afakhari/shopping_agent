/** Explicit lightweight dialogue intents: do not spend a BoxAPI call for a salutation.
 * A purchase request with the word «چطوری» must still reach the catalogue.
 */
export type LocalConversationIntent = 'greeting' | 'help' | 'thanks' | 'goodbye'

function normalizeConversationalText(input: string): string {
  return input
    .normalize('NFKC')
    .replace(/[\u200c\u200d]/g, ' ')
    .replace(/[يى]/g, 'ی')
    .replace(/ك/g, 'ک')
    .replace(/[!؟?.,،؛:؛\s]+/gu, ' ')
    .trim()
    .toLocaleLowerCase('fa-IR')
}

const greetings = new Set([
  'سلام', 'درود', 'سلام علیکم', 'سلام خوبی', 'سلام خوبی چطوری',
  'سلام چطوری', 'سلام وقت بخیر', 'سلام وقتتون بخیر',
  'صبح بخیر', 'عصر بخیر', 'شب بخیر', 'خوبی', 'چطوری',
  'چطوری خوبی', 'حالت چطوره', 'چه خبر', 'hi', 'hello', 'hey',
])
const helpRequests = new Set([
  'راهنما', 'کمک', 'روش استفاده', 'چطور ازت استفاده کنم',
  'چجوری ازت استفاده کنم', 'چطور از این برنامه استفاده کنم',
  'چطوری از این برنامه استفاده کنم', 'چطور باهات کار کنم',
  'چجوری باهات کار کنم', 'چطور کار می کنی', 'چطوری کار می کنی',
  'چه کارهایی می تونی انجام بدی', 'چه کارهایی بلدی',
  'چطور با این دستیار خرید کار کنم', 'راهنمای استفاده از دستیار',
])
const thanks = new Set(['مرسی', 'ممنون', 'ممنونم', 'سپاس', 'متشکرم', 'دمت گرم', 'خیلی ممنون'])
const goodbyes = new Set(['خداحافظ', 'خدا حافظ', 'فعلا', 'فعلاً', 'بای', 'به امید دیدار'])

export function classifyLocalConversation(message: string): LocalConversationIntent | null {
  if (message.length > 200) return null
  const value = normalizeConversationalText(message)
  if (greetings.has(value)) return 'greeting'
  if (helpRequests.has(value)) return 'help'
  if (thanks.has(value)) return 'thanks'
  if (goodbyes.has(value)) return 'goodbye'
  return null
}

export function isGreetingOnly(message: string): boolean {
  return classifyLocalConversation(message) === 'greeting'
}

export function isAssistantHelpRequest(message: string): boolean {
  return classifyLocalConversation(message) === 'help'
}

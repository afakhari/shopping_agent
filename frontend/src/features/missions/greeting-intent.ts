/** Explicit lightweight dialogue intents: do not spend a BoxAPI call for a salutation.
 * A purchase request with the word «چطوری» must still reach the catalogue.
 */
export type LocalConversationIntent = 'greeting' | 'help' | 'thanks' | 'goodbye'

function normalizeConversationalText(input: string): string {
  return input
    .normalize('NFKC')
    .replace(/[\u200c\u200d]/g, ' ')
    .replace(/[\u064b-\u065f\u0670]/g, '')
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
  'چطوری خوبی', 'حالت چطوره', 'چه خبر', 'چه خبرا', 'احوال شما',
  'احوالتون چطوره', 'احوالتان چطوره', 'احوال شریف', 'احوالات چطوره',
  'حال شما چطوره', 'حال شما چگونه است', 'حالت چطوره', 'حالتون چطوره',
  'حالتون خوبه', 'حالت خوبه', 'خوب هستید', 'خوبین', 'چطورید',
  'چطورین', 'شما چطورید', 'شما خوبید', 'سلام حال شما چطوره',
  'سلام احوال شما', 'سلام حالتون چطوره', 'سلام چه خبر',
  'hi', 'hello', 'hey',
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

/** Shared by live chat and presentation repair of events saved by older versions. */
export function localConversationReply(intent: LocalConversationIntent): string {
  const replies: Record<LocalConversationIntent, string> = {
    greeting: 'سلام! خوش اومدی. 🌱 دنبال چه محصولی هستی؟ می‌تونی مدل، کاربرد یا حدود بودجه رو بگی تا فروشگاه‌های تهران رو بررسی کنیم.',
    help: 'برای شروع نام یا کاربرد محصول را بنویس؛ مثلاً «هدفون بی‌سیم تا ۳ میلیون تومان». بعد می‌توانی مدل‌ها را مقایسه کنی، فروشگاه‌های تهران را ببینی و استعلام نمایشی انجام بدهی. بودجه، اعتبار و محدوده را هم خودت تنظیم می‌کنی.',
    thanks: 'خواهش می‌کنم! هر زمان محصول دیگری خواستی یا خواستی شروط خرید را تغییر بدهی، همین‌جا بنویس.',
    goodbye: 'خداحافظ! نتیجه‌های ثبت‌شده مأموریت را می‌توانی بعداً هم بررسی کنی.',
  }
  return replies[intent]
}

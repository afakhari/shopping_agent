import { describe, expect, it } from 'vitest'
import { rebuildChatFromEvents } from './MissionPanel'
import type { MissionEvent } from './mission-api'

const envelope = (seq: number, type: string, payload: Record<string, unknown>): MissionEvent =>
  ({ mission_id: 'mission', schema_version: 1, seq, type, payload })

describe('persisted conversation repairs obsolete greeting searches', () => {
  it('hides unrelated products from an older «احوال شما؟» turn', () => {
    const history = [
      envelope(1,'user.message',{ message:'احوال شما؟' }),
      envelope(2,'assistant.message',{ text:'برای این عبارت ۱۲۰ محصول پیدا کردم.' }),
      envelope(3,'ui.component',{ component:'product_results',
        data:{ query:'احوال شما', total:120,results:[{ product: { id:'blade' } }] } }),
      envelope(4,'turn.completed',{ total:120 }),
    ]
    const messages = rebuildChatFromEvents(history)
    expect(messages.find(x=>x.role==='assistant')?.text).toContain('سلام!')
    expect(messages.some(x=>x.results?.length)).toBe(false)
    expect(messages.some(x=>x.components.some(c=>c.type==='product_results'))).toBe(false)
  })
  it('preserves an earlier real search if a later greeting had bad result events', () => {
    const history = [
      envelope(1,'user.message',{ message:'هدفون' }),
      envelope(2,'assistant.message',{ text:'نتایج هدفون' }),
      envelope(3,'ui.component',{ component:'product_results',
        data:{ query:'هدفون', total:1,results:[{ product: { id:'headphones' } }] } }),
      envelope(4,'turn.completed',{ total:1 }),
      envelope(5,'user.message',{ message:'احوال شما؟' }),
      envelope(6,'assistant.message',{ text:'۱۲۰ نتیجه نامرتبط' }),
      envelope(7,'ui.component',{ component:'empty_state',data:{ query:'احوال شما',fields:[] } }),
      envelope(8,'turn.completed',{ total:0 }),
    ]
    const messages = rebuildChatFromEvents(history)
    expect(messages.filter(x=>x.results?.length)).toHaveLength(1)
    expect(messages.some(x=>x.components.some(c=>c.type==='empty_state'))).toBe(false)
  })
  it('does not hide shopping queries prefixed by salutation', () => {
    const history = [
      envelope(1,'user.message',{ message:'سلام هدفون می‌خواهم' }),
      envelope(2,'assistant.message',{ text:'نتایج خرید' }),
      envelope(3,'ui.component',{ component:'product_results',
        data:{ query:'هدفون', total:1,results:[{ product: { id:'headphones' } }] } }),
    ]
    expect(rebuildChatFromEvents(history).some(x=>x.results?.length===1)).toBe(true)
  })
})

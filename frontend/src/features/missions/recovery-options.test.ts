import { describe, expect, it } from 'vitest'
import { readRecoveryChoices, resolveRecoveryOffer } from './recovery-options'
import type { CatalogOffer } from '../search/catalog-api'
import type { ContactAttemptResponse } from './mission-api'

const offer = {
  id: 'offer-b',
  price_toman: '800000',
  shop: { id: 'shop-b', name: 'فروشگاه ب', address: 'پاساژ نمونه' },
} as CatalogOffer

const alternateModel = {
  product: { id: 'p2', title: 'هدفون جایگزین' },
  best_offer: { ...offer, id: 'offer-model' },
}

describe('safe contextual recovery UI', () => {
  it('builds bounded choices only from typed offers and alternative models', () => {
    const choices = readRecoveryChoices({
      alternatives: [offer, { id: '<script>', shop: null }, offer],
      alternative_products: [alternateModel],
    })
    expect(choices.map((choice) => choice.offerId)).toEqual(['offer-b', 'offer-model'])
    expect(choices.map((choice) => choice.kind)).toEqual(['same_product', 'replacement_model'])
    expect(choices[0]?.priceToman).toBe('800000')
  })

  it('ignores malformed and invented prices and IDs without rendering executable markup', () => {
    const choices = readRecoveryChoices({
      alternatives: [{ id: 'o', shop: { id: 's', name: '<img onerror=alert(1)>' }, price_toman: 'bad' }],
    })
    expect(choices[0]?.priceToman).toBeNull()
    expect(choices[0]?.shopName).toBe('<img onerror=alert(1)>')
    expect(readRecoveryChoices({ alternatives: [{ id: 'x', shop: {} }] })).toEqual([])
  })

  it('checks selection against saved alternatives and shop IDs before triggering a call', () => {
    const response = {
      attempt: { offer_id: 'original' },
      alternatives: [offer],
      alternative_products: [alternateModel],
    } as ContactAttemptResponse
    const responses = { original: response }
    expect(resolveRecoveryOffer(responses, 'offer-b', 'shop-b')).toEqual(offer)
    expect(resolveRecoveryOffer(responses, 'offer-b', 'shop-wrong')).toBeNull()
    expect(resolveRecoveryOffer(responses, 'offer-not-listed', 'shop-b')).toBeNull()
    expect(resolveRecoveryOffer(responses, 'offer-model', 'shop-b')?.id).toBe('offer-model')
    const malformed = { attempt: {}, alternatives: [null], alternative_products: [null] } as unknown as ContactAttemptResponse
    expect(resolveRecoveryOffer({ malformed }, 'offer-b', 'shop-b')).toBeNull()
  })
})

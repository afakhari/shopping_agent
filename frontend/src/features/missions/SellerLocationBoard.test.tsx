import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import type { CatalogOffer } from '../search/catalog-api'
import { SellerLocationBoard, geographicallyMappedOffers, selectedMappedOffer } from './SellerLocationBoard'

function offer(id: string, lat: number | null, lon: number | null): CatalogOffer {
  return {
    id,
    price_toman: '650000',
    last_price_changed_at: null,
    price_quality: 'unknown_timestamp',
    shop: {
      id: 'shop-' + id,
      name: 'فروشگاه نمایشی ' + id,
      address: 'تهران، نشانی ثبت‌شده',
      location_label: 'تهران',
      lat, lon, distance_m: null, accepts_in_person_credit: false,
    },
  }
}

describe('seller location trust and coordinated selection', () => {
  const shops = [
    offer('first', 35.7, 51.4),
    offer('unknown', null, null),
    offer('outside', 52.5, 13.4),
    offer('second', 35.68, 51.42),
  ]

  it('never creates a marker from a missing or out-of-Tehran coordinate', () => {
    expect(geographicallyMappedOffers(shops).map(row => row.id)).toEqual(['first', 'second'])
    expect(selectedMappedOffer(shops, 'unknown')).toBeNull()
    expect(selectedMappedOffer(shops, 'outside')).toBeNull()
    expect(selectedMappedOffer(shops, 'second')?.shop.id).toBe('shop-second')
    expect(selectedMappedOffer(shops, 'unlisted')).toBeNull()
  })

  it('keeps the full seller list when the map cannot display a shop', () => {
    const markup = renderToStaticMarkup(<SellerLocationBoard
      offers={shops} selectedOfferId="unknown" onSelectOffer={() => {}} disabled={false} />)
    expect(markup).toContain('فروشگاه نمایشی unknown')
    expect(markup).toContain('مختصات این فروشنده')
    expect(markup).toContain('نام بسیاری از فروشگاه‌ها')
    expect(markup).not.toContain('<iframe')
  })

  it('does not contact OpenStreetMap until a user opens the selected map', () => {
    const markup = renderToStaticMarkup(<SellerLocationBoard
      offers={shops} selectedOfferId="second" onSelectOffer={() => {}} disabled={false} />)
    expect(markup).toContain('نمایش نقشه OpenStreetMap')
    expect(markup).toContain('با نمایش نقشه')
    expect(markup).not.toContain('<iframe')
    expect(markup).toContain('aria-pressed="true"')
  })

  it('asks for a seller from this product when focus belongs to another product', () => {
    const markup = renderToStaticMarkup(<SellerLocationBoard
      offers={shops} selectedOfferId="prior-query" onSelectOffer={() => {}} disabled={false} />)
    expect(markup).toContain('فهرست دیگری است')
    expect(markup).not.toContain('<iframe')
  })
})

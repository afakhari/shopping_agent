import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import type { CatalogOffer } from '../search/catalog-api'
import {
  SellerLocationBoard, geographicallyMappedOffers, paidNeshanRoutingUiEnabled, selectedMappedOffer,
} from './SellerLocationBoard'

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
      offers={shops} selectedOfferId="unknown" onSelectOffer={() => {}} disabled={false}
      missionId="mission1" resultSetId="set1" origin={null} />)
    expect(markup).toContain('فروشگاه نمایشی unknown')
    expect(markup).toContain('مختصات معتبر در محدودهٔ پوشش تهران')
    expect(markup).toContain('نام بسیاری از فروشگاه‌ها')
    expect(markup).not.toContain('<iframe')
  })

  it('does not contact OpenStreetMap until a user opens the selected map', () => {
    const markup = renderToStaticMarkup(<SellerLocationBoard
      offers={shops} selectedOfferId="second" onSelectOffer={() => {}} disabled={false}
      missionId="mission1" resultSetId="set1" origin={null} />)
    expect(markup).toContain('نمایش نقشه OpenStreetMap')
    expect(markup).toContain('با نمایش نقشه')
    expect(markup).toContain('بازکردن نقطه ثبت‌شده در نشان')
    expect(markup).toContain('به معنی وجود فروشگاه')
    expect(markup).not.toContain('مسیر خودرو در نشان تا مختصات ثبت‌شده')
    expect(markup).not.toContain('<iframe')
    expect(markup).toContain('aria-pressed="true"')
  })

  it('shows keyless Neshan directions only after the user has chosen a Tehran origin', () => {
    const markup = renderToStaticMarkup(<SellerLocationBoard
      offers={shops} selectedOfferId="second" onSelectOffer={() => {}} disabled={false}
      missionId="mission1" resultSetId="set1" origin={{lat: 35.7, lon: 51.4}} />)
    expect(markup).toContain('مسیر خودرو در نشان تا مختصات ثبت‌شده')
    expect(markup).toContain('destination=35.68%2C51.42')
    expect(markup).toContain('origin=35.7%2C51.4')
    expect(markup).not.toContain('<iframe')
  })

  it('hides paid routing and provider-capability prompts in the default free experience', () => {
    expect(paidNeshanRoutingUiEnabled).toBe(false)
    const markup = renderToStaticMarkup(<SellerLocationBoard
      offers={shops} selectedOfferId="second" onSelectOffer={() => {}} disabled={false}
      missionId="mission1" resultSetId="set1" origin={{ lat: 35.7, lon: 51.4 }} />)
    expect(markup).not.toContain('mission-neshan-routing')
    expect(markup).not.toContain('اتصال مسیریابی نشان هنوز فعال نشده است')
    expect(markup).not.toContain('مقایسه زمان سفر با نشان')
    expect(markup).not.toContain('دقیقه</strong>')
    expect(markup).toContain('فاصله مستقیم، زمان سفر نیست')
  })

  it('renders map access even if only one seller is eligible', () => {
    const markup = renderToStaticMarkup(<SellerLocationBoard
      offers={[offer('first', 35.7, 51.4)]} selectedOfferId="first" onSelectOffer={() => {}} disabled={false}
      missionId="mission1" resultSetId="set1" origin={null} />)
    expect(markup).toContain('موقعیت فروشنده')
    expect(markup).toContain('نمایش نقشه OpenStreetMap')
    expect(markup).not.toContain('mission-neshan-routing')
  })

  it('asks for a seller from this product when focus belongs to another product', () => {
    const markup = renderToStaticMarkup(<SellerLocationBoard
      offers={shops} selectedOfferId="prior-query" onSelectOffer={() => {}} disabled={false}
      missionId="mission1" resultSetId="set1" origin={null} />)
    expect(markup).toContain('فهرست دیگری است')
    expect(markup).not.toContain('<iframe')
  })
})

import { describe, expect, it } from 'vitest'
import type { CatalogOffer } from '../search/catalog-api'
import { sellerHighlights } from './seller-highlights'

function item(id:string, price:string|null, distance:number|null):CatalogOffer {
  return { id, price_toman:price, shop:{id, name:id, distance_m:distance} } as CatalogOffer
}
describe('seller shortlist factual tags',()=>{
  it('finds cheapest and nearest only among loaded offers',()=>{
    expect(sellerHighlights([item('a','300',900),item('b','200',1500),item('c','450',100)]))
      .toEqual({cheapestOfferId:'b', closestOfferId:'c'})
  })
  it('does not invent a cheapest shop or distance from missing data',()=>{
    expect(sellerHighlights([item('a',null,null)]))
      .toEqual({cheapestOfferId:null, closestOfferId:null})
  })
  it('ignores negative and NaN distances and nonnumeric prices',()=>{
    expect(sellerHighlights([item('x','bad',-1),item('b','123',Number.NaN)]))
      .toEqual({cheapestOfferId:'b', closestOfferId:null})
  })
})

"""HTTP endpoints for deterministic product search and offer comparison."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.catalog.models import Product, Shop
from .serializers import OfferFilterSerializer, ProductSearchSerializer
from .services import (
    eligible_offer_list,
    product_search_page,
    serialize_offer,
    serialize_product,
    serialize_shop_detail,
)


@api_view(["GET"])
def catalog_search(request):
    serializer = ProductSearchSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    payload = product_search_page(serializer.validated_data)
    return Response(payload)


@api_view(["GET"])
def product_detail(request, product_id: str):
    product = get_object_or_404(Product, source_id=product_id)
    return Response({"product": serialize_product(product)})


@api_view(["GET"])
def product_offers(request, product_id: str):
    product = get_object_or_404(Product, source_id=product_id)
    serializer = OfferFilterSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    filters = serializer.validated_data
    offers = eligible_offer_list(filters, product_id=product.source_id)
    total = offers.count()
    page = filters.get("page", 1)
    page_size = filters.get("page_size", 20)
    page_offers = offers[(page - 1) * page_size : page * page_size]
    results = [serialize_offer(offer, getattr(offer, "distance_m", None)) for offer in page_offers]
    return Response(
        {
            "product": serialize_product(product),
            "filters": {
                "max_price_toman": (
                    str(filters["max_price_toman"])
                    if filters.get("max_price_toman") is not None else None
                ),
                "must_have_in_person_credit": bool(
                    filters.get("must_have_in_person_credit", False)
                ),
                "lat": filters.get("lat"),
                "lon": filters.get("lon"),
                "radius_m": filters.get("radius_m"),
                "sort": filters.get("sort", "relevance"),
            },
            "page": page,
            "page_size": page_size,
            "total": total,
            "results": results,
        }
    )


@api_view(["GET"])
def shop_detail(request, shop_id: str):
    shop = get_object_or_404(Shop, source_id=shop_id)
    return Response({"shop": serialize_shop_detail(shop)})

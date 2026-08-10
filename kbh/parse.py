"""Turn a Boligsiden case payload into a flat listing row, and apply the
hard filters.

Worth knowing before trusting any of this: ``hasBalcony`` is not reliable.
A verified example on 10 August 2026, case 66f18380 on Århusgade, returns
``hasBalcony: false`` while its own headline reads "Klassisk Østerbro-charme
med altan". The realtor feed and the structured flag disagree often enough
that we keep both and let the text override for scoring purposes.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from . import config

BALCONY_PATTERN = re.compile(
    r"\b(altan(?:er|en|]|\b)|fransk\s+altan|tagterrasse|altangang)", re.IGNORECASE
)
TERRACE_PATTERN = re.compile(r"\b(terrasse[rn]?|tagterrasse|have\b)", re.IGNORECASE)

# Houseboats come through the API as addressType "villa" or "terraced house"
# with no lot, and they wreck the m2 comparison: a berth in Sydhavn asks around
# 41.000 kr/m2 against a Sydhavn benchmark of 70.250, so a houseboat lands at
# the top of a value ranking while being a different asset class entirely. The
# berth is leased, the financing is not a normal realkreditlån, and it does not
# appreciate like property.
#
# Found because the AI verdict on the number two ranked listing opened with
# "Det er en husbåd, ikke en villa".
# The pattern has to distinguish the boat being sold from boats in the view.
# Two real false positives from the first run:
#
#   Teglholm Tværvej 25, an ordinary flat: "lade blikket glide ud over
#   kanalerne, de karakterfulde husbåde og livet på vandet"
#   Oscar Pettifords Vej 25, an ordinary flat: "der kan erhverves privat
#   bådplads i den private marina"
#
# So "bådplads" is out entirely, since it is an amenity a normal flat can offer,
# and only the singular forms of husbåd count. Plural husbåde and husbådene are
# scenery: nobody sells you several. Verified against all seven listings that
# the first version flagged.
HOUSEBOAT_PATTERN = re.compile(
    r"\b(?:hus-?b[åa]d(?:ens|en|s)?|flydende\s+(?:bolig|hjem|hus))\b",
    re.IGNORECASE,
)

# Image widths we care about. 600 wide is enough for a vision model to judge
# light, ceiling height and whether the kitchen is from 1994.
PREFERRED_IMAGE_WIDTH = 600


def _nested(payload: Any, *keys: str, default: Any = None) -> Any:
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _pick_image(image: Dict[str, Any]) -> Optional[str]:
    """Choose the source closest to the preferred width without going over,
    falling back to the smallest available above it."""
    sources = image.get("imageSources") or []
    if not sources:
        return None
    under = [
        s
        for s in sources
        if _nested(s, "size", "width", default=0) <= PREFERRED_IMAGE_WIDTH
    ]
    if under:
        best = max(under, key=lambda s: _nested(s, "size", "width", default=0))
    else:
        best = min(sources, key=lambda s: _nested(s, "size", "width", default=10**9))
    return best.get("url")


def _image_urls(case: Dict[str, Any], limit: int = 12) -> List[str]:
    urls: List[str] = []
    for image in (case.get("images") or [])[:limit]:
        url = _pick_image(image)
        if url:
            urls.append(url)
    return urls


def _image_alts(case: Dict[str, Any], limit: int = 12) -> List[str]:
    """Boligsiden ships machine written alt text on every photo. It is a free,
    already paid for description of what the picture shows."""
    alts: List[str] = []
    for image in (case.get("images") or [])[:limit]:
        for source in image.get("imageSources") or []:
            alt = (source.get("alt") or "").strip()
            if alt:
                alts.append(alt)
                break
    return alts


def is_ground_floor(floor: Optional[str]) -> bool:
    if floor is None:
        return False
    token = str(floor).strip().lower().replace(" ", "")
    return token in config.GROUND_FLOOR_TOKENS


def case_to_row(case: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten one case into the listings table shape."""
    address = case.get("address") or {}
    buildings = address.get("buildings") or []
    building = buildings[0] if buildings else {}

    living_area = case.get("housingArea") or address.get("livingArea")
    price = case.get("priceCash") or address.get("casePrice")

    days_listed = _nested(case, "daysListed", "days") or _nested(
        case, "timeOnMarket", "current", "days"
    )

    description_body = case.get("descriptionBody") or ""
    description_title = case.get("descriptionTitle") or ""
    text_blob = f"{description_title}\n{description_body}"

    image_urls = _image_urls(case)
    floor_plans = case.get("floorPlanImages") or []
    floor_plan_url = _pick_image(floor_plans[0]) if floor_plans else None

    slug = case.get("slug") or address.get("slug") or ""

    row: Dict[str, Any] = {
        "case_id": case.get("caseID"),
        "address_id": address.get("addressID"),
        "address": _format_address(address),
        "road_name": address.get("roadName"),
        "house_number": address.get("houseNumber"),
        "floor": address.get("floor"),
        "door": address.get("door"),
        "zip_code": address.get("zipCode"),
        "city_name": address.get("cityName"),
        "municipality": _nested(address, "municipality", "name"),
        "municipality_code": _nested(address, "municipality", "municipalityCode"),
        "address_type": case.get("addressType"),
        "lat": _nested(case, "coordinates", "lat")
        or _nested(address, "coordinates", "lat"),
        "lon": _nested(case, "coordinates", "lon")
        or _nested(address, "coordinates", "lon"),
        "price": price,
        "per_area_price": case.get("perAreaPrice"),
        "living_area": living_area,
        "number_of_rooms": case.get("numberOfRooms") or building.get("numberOfRooms"),
        "number_of_floors": case.get("numberOfFloors")
        or building.get("numberOfFloors"),
        "number_of_bathrooms": case.get("numberOfBathrooms")
        or building.get("numberOfBathrooms"),
        "year_built": case.get("yearBuilt") or building.get("yearBuilt"),
        "year_renovated": building.get("yearRenovated"),
        "energy_label": case.get("energyLabel"),
        "monthly_expense": case.get("monthlyExpense"),
        "down_payment": _nested(case, "realEstate", "downPayment"),
        "net_mortgage": _nested(case, "realEstate", "netMortgage"),
        "is_houseboat": 1 if HOUSEBOAT_PATTERN.search(text_blob) else 0,
        "has_balcony": 1 if case.get("hasBalcony") else 0,
        "has_balcony_text": 1 if BALCONY_PATTERN.search(text_blob) else 0,
        "has_terrace": 1
        if (case.get("hasTerrace") or TERRACE_PATTERN.search(text_blob))
        else 0,
        "has_elevator": 1 if case.get("hasElevator") else 0,
        "open_house_at": _nested(case, "nextOpenHouse", "date"),
        "floor_plan_url": floor_plan_url,
        "kitchen_condition": building.get("kitchenCondition"),
        "bathroom_condition": building.get("bathroomCondition"),
        "heating": building.get("heatingInstallation"),
        "days_listed": days_listed,
        "price_change_pct": case.get("priceChangePercentage"),
        "latest_valuation": address.get("latestValuation"),
        "description_title": description_title,
        "description_body": description_body,
        "realtor_name": _realtor_name(case),
        "case_url": case.get("caseUrl"),
        "boligsiden_url": f"https://www.boligsiden.dk/adresse/{slug}" if slug else None,
        "image_url": _pick_image(case["defaultImage"])
        if case.get("defaultImage")
        else None,
        "image_urls": json.dumps(image_urls, ensure_ascii=False),
        "status": case.get("status"),
        "is_active": 1,
    }

    excluded, reason = hard_filter(row)
    row["excluded"] = 1 if excluded else 0
    row["exclusion_reason"] = reason
    return row


def _format_address(address: Dict[str, Any]) -> str:
    parts = [address.get("roadName") or "", str(address.get("houseNumber") or "")]
    floor = address.get("floor")
    door = address.get("door")
    if floor:
        parts.append(str(floor))
    if door:
        parts.append(str(door))
    street = " ".join(p for p in parts if p).strip()
    zip_code = address.get("zipCode")
    city = address.get("cityName") or ""
    return f"{street}, {zip_code} {city}".strip().strip(",")


def _realtor_name(case: Dict[str, Any]) -> Optional[str]:
    realtor = case.get("realtor") or {}
    return (
        realtor.get("name")
        or _nested(realtor, "branch", "name")
        or realtor.get("branchName")
        or _nested(realtor, "contactInformation", "email")
    )


def hard_filter(row: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Return (excluded, reason). These are dealbreakers, not penalties.

    Anything excluded here is still stored, so the web app can show what was
    filtered out and why. Nothing disappears silently.
    """
    area = row.get("living_area")
    if area is None:
        return True, "Areal ikke oplyst"
    if area < config.MIN_LIVING_AREA:
        return True, f"{area:.0f} m2, under grænsen på {config.MIN_LIVING_AREA} m2"

    if config.EXCLUDE_GROUND_FLOOR and row.get("address_type") == "condo":
        if is_ground_floor(row.get("floor")):
            return True, f"Stue eller kælder (etage: {row.get('floor')})"

    if not row.get("price"):
        return True, "Pris ikke oplyst"

    if row.get("is_houseboat"):
        return True, "Husbåd, ikke fast ejendom"

    return False, None


def image_context(case: Dict[str, Any]) -> Dict[str, Any]:
    """Everything about the photos worth handing to a model."""
    return {
        "urls": _image_urls(case),
        "alt_texts": _image_alts(case),
        "floor_plan": bool(case.get("floorPlanImages")),
    }

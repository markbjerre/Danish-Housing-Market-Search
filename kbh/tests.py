"""Tests for the parts that fail silently.

Deliberately narrow. Network calls, the database and the model are not tested
here: those fail loudly and get caught the moment a run is executed. What is
tested is the logic that would go on producing plausible looking numbers while
being wrong, which is the only kind of bug this system can hide.

    python -m kbh.tests
"""

from __future__ import annotations

import json
import unittest

from . import config, geo, parse, pipeline, scoring, taste
from .ai import _parse_verdicts
from .benchmarks import PeerBenchmark


def listing(**overrides):
    base = {
        "case_id": "x",
        "address_type": "condo",
        "living_area": 100.0,
        "price": 7_000_000,
        "floor": "3",
        "number_of_rooms": 3.0,
        "monthly_expense": 4_500,
        "days_listed": 60,
        "price_change_pct": 0.0,
        "energy_label": "c",
        "year_built": 1960,
        "lat": 55.68,
        "lon": 12.57,
    }
    base.update(overrides)
    return base


def noise_hit(distance: float, kind: str = "tertiary", name: str = "Testvej", **kw):
    """A geo.NoiseHit without needing the geometry files on disk.

    The real one computes its own reach and penalty from the config model, so
    building the real dataclass keeps the tests honest about that arithmetic
    instead of restating it.
    """
    weight = kw.pop("weight", config.noise_weight(kind, lanes=3, maxspeed=50))
    return geo.NoiseHit(kind=kind, distance_m=distance, name=name, weight=weight)


class HardFilters(unittest.TestCase):
    def test_under_minimum_area_is_excluded(self):
        excluded, reason = parse.hard_filter(listing(living_area=89.9))
        self.assertTrue(excluded)
        self.assertIn("90", reason)

    def test_exactly_the_minimum_is_kept(self):
        excluded, _ = parse.hard_filter(listing(living_area=90.0))
        self.assertFalse(excluded)

    def test_ground_floor_variants_are_excluded(self):
        for token in ("st", "st.", "0", "kl", "KL.", " st "):
            with self.subTest(token=token):
                excluded, _ = parse.hard_filter(listing(floor=token))
                self.assertTrue(excluded, f"{token!r} should count as ground floor")

    def test_upper_floors_are_kept(self):
        for token in ("1", "2", "12"):
            with self.subTest(token=token):
                excluded, _ = parse.hard_filter(listing(floor=token))
                self.assertFalse(excluded)

    def test_ground_floor_rule_does_not_apply_to_houses(self):
        excluded, _ = parse.hard_filter(listing(address_type="villa", floor=None))
        self.assertFalse(excluded)

    def test_houseboat_is_excluded(self):
        excluded, reason = parse.hard_filter(listing(is_houseboat=1))
        self.assertTrue(excluded)
        self.assertIn("Husbåd", reason)

    def test_missing_area_is_excluded_not_assumed(self):
        excluded, _ = parse.hard_filter(listing(living_area=None))
        self.assertTrue(excluded)


class HouseboatDetection(unittest.TestCase):
    """All strings here are taken from real listings, not invented."""

    def test_matches_the_boat_being_sold(self):
        for text in (
            "Unik husbåd på 140 m2",
            "Husbåden du falder pladask for",
            "En lille fortælling om denne fantastiske husbåds tilblivelse",
            "Sjældent udbudt husbåd, totalrenoveret fra A til Z",
            "denne unikke husbåd på hele 159 m2 fordelt på 5 værelser",
            "Huset er en flydende bolig",
            "Husbådens tag er nyt",
        ):
            with self.subTest(text=text):
                self.assertIsNotNone(parse.HOUSEBOAT_PATTERN.search(text))

    def test_does_not_match_boats_in_the_view(self):
        # Teglholm Tværvej 25, an ordinary flat that merely looks at houseboats.
        self.assertIsNone(
            parse.HOUSEBOAT_PATTERN.search(
                "lade blikket glide ud over kanalerne, de karakterfulde husbåde og "
                "livet på vandet"
            )
        )
        self.assertIsNone(
            parse.HOUSEBOAT_PATTERN.search(
                "Husbådene i kanalen giver kvarteret karakter"
            )
        )

    def test_does_not_match_a_berth_offered_as_an_amenity(self):
        # Oscar Pettifords Vej 25, an ordinary flat with a marina next door.
        for text in (
            "der kan erhverves privat bådplads i den private marina",
            "Bådplads medfølger",
            "Liggeplads kan tilkøbes",
        ):
            with self.subTest(text=text):
                self.assertIsNone(parse.HOUSEBOAT_PATTERN.search(text))

    def test_does_not_match_ordinary_listings(self):
        for text in (
            "Lys lejlighed med udsigt til havnen",
            "Tæt på Havneholmen og Fisketorvet",
            "Bådudlejning ligger 500 m væk",
        ):
            with self.subTest(text=text):
                self.assertIsNone(parse.HOUSEBOAT_PATTERN.search(text))


class Scoring(unittest.TestCase):
    def setUp(self):
        self.market = scoring.MarketContext()

    def test_weights_sum_to_one_hundred(self):
        self.assertAlmostEqual(sum(config.WEIGHTS.values()), 100.0)

    def test_every_profile_sums_to_one_hundred(self):
        for key, profile in config.PROFILES.items():
            with self.subTest(profile=key):
                self.assertAlmostEqual(sum(profile["weights"].values()), 100.0)

    def test_every_profile_covers_every_factor(self):
        # A profile missing a key would score that factor at zero without
        # saying so anywhere.
        for key, profile in config.PROFILES.items():
            with self.subTest(profile=key):
                self.assertEqual(
                    set(profile["weights"]), set(config.FACTOR_KEYS), f"{key} drifted"
                )

    def test_a_saved_custom_weighting_inherits_factors_added_later(self):
        """The trap that switched off three new factors on their first run.

        A custom weighting saved before rooms, transit and noise existed has no
        key for them. Normalising it as a slider payload zeroes them, so the
        pipeline logged the new factors at weight 0 and scored 501 listings
        without them while looking entirely normal.
        """
        old = {
            "sqm_price_vs_benchmark": 45.8,
            "neighbourhood": 18.1,
            "water": 0.0,
            "size": 18.1,
            "condition": 8.4,
            "negotiation_leverage": 2.4,
            "monthly_expense": 7.2,
        }
        as_saved = config.normalise_weights(old, fill_missing=True)
        for key in ("rooms", "transit", "noise"):
            self.assertGreater(as_saved[key], 0.0, f"{key} was silently switched off")
        self.assertAlmostEqual(sum(as_saved.values()), 100.0)

        # A slider set to zero must still mean zero.
        as_slider = config.normalise_weights(old)
        self.assertEqual(as_slider["rooms"], 0.0)
        self.assertAlmostEqual(sum(as_slider.values()), 100.0)

    def test_price_well_under_benchmark_scores_full(self):
        f = scoring.score_sqm_price(
            listing(price=5_000_000, living_area=100), benchmark=80_000, basis="recent"
        )
        self.assertEqual(f.score, 100.0)

    def test_price_at_benchmark_scores_par(self):
        f = scoring.score_sqm_price(
            listing(price=8_000_000, living_area=100), benchmark=80_000, basis="recent"
        )
        self.assertAlmostEqual(f.score, config.SQM_RATIO_PAR_SCORE, places=4)

    def test_price_far_over_benchmark_scores_zero(self):
        f = scoring.score_sqm_price(
            listing(price=12_000_000, living_area=100), benchmark=80_000, basis="recent"
        )
        self.assertEqual(f.score, 0.0)

    def test_missing_benchmark_is_neutral_not_zero(self):
        f = scoring.score_sqm_price(listing(), benchmark=None, basis="none")
        self.assertEqual(f.score, 50.0)
        self.assertTrue(f.neutral)

    def test_water_curve_is_monotonic(self):
        previous = 101.0
        for distance in (0, 150, 300, 600, 900, 1500, 1800, 5000):
            score = scoring.score_water(distance, "havn", "prime").score
            self.assertLessEqual(score, previous, f"went up at {distance} m")
            previous = score

    def test_secondary_water_is_capped(self):
        f = scoring.score_water(10, "en sø", "secondary")
        self.assertLessEqual(f.score, config.SECONDARY_WATER_CAP)

    def test_size_floor_does_not_score_zero(self):
        f = scoring.score_size(listing(living_area=90))
        self.assertEqual(f.score, config.SIZE_FLOOR_SCORE)

    def test_four_rooms_beats_three(self):
        # The stated preference is more than three rooms, so this is the step
        # the curve exists to produce.
        three = scoring.score_rooms(listing(number_of_rooms=3, living_area=110)).score
        four = scoring.score_rooms(listing(number_of_rooms=4, living_area=110)).score
        five = scoring.score_rooms(listing(number_of_rooms=5, living_area=110)).score
        self.assertLess(three, four)
        self.assertLess(four, five)

    def test_rooms_missing_is_neutral_not_zero(self):
        f = scoring.score_rooms(listing(number_of_rooms=None))
        self.assertEqual(f.score, 50.0)
        self.assertTrue(f.neutral)

    def test_many_tiny_rooms_lose_points_to_a_normal_layout(self):
        # Same room count, same hard filters passed, very different flat. Five
        # rooms in 95 m2 is a flat chopped up to advertise a number.
        chopped = scoring.score_rooms(listing(number_of_rooms=5, living_area=95)).score
        normal = scoring.score_rooms(listing(number_of_rooms=5, living_area=140)).score
        self.assertLess(chopped, normal)

    def test_transit_curve_is_monotonic(self):
        previous = 101.0
        for distance in (0, 250, 400, 700, 1000, 1500, 3000):
            score = scoring.score_transit(distance, "Nørreport", "metro").score
            self.assertLessEqual(score, previous, f"went up at {distance} m")
            previous = score

    def test_transit_missing_is_neutral_not_zero(self):
        f = scoring.score_transit(None, "", "")
        self.assertEqual(f.score, 50.0)
        self.assertTrue(f.neutral)

    def test_quiet_address_scores_full_but_missing_data_scores_neutral(self):
        # The distinction that matters. An empty list means the geometry was
        # consulted and found nothing, which is a quiet home. None means the
        # geometry was unavailable, which must not be rewarded as silence.
        quiet = scoring.score_noise([])
        unknown = scoring.score_noise(None)
        self.assertEqual(quiet.score, 100.0)
        self.assertFalse(quiet.neutral)
        self.assertEqual(unknown.score, 50.0)
        self.assertTrue(unknown.neutral)

    def test_noise_penalty_grows_as_the_road_gets_closer(self):
        previous = -1.0
        for distance in (300, 200, 120, 60, 10):
            score = scoring.score_noise([noise_hit(distance=distance)]).score
            self.assertGreaterEqual(previous if previous >= 0 else 101.0, score)
            previous = score
        self.assertLess(score, 100.0)

    def test_noise_sources_combine_in_energy_not_by_addition(self):
        """Two equally loud roads must be a little worse than one, not twice.

        Adding penalties straight up was the first implementation and it put an
        ordinary Frederiksberg address with four moderate streets around it at
        zero, level with a flat on a railway embankment. Sound does not work
        that way and neither does this factor.
        """
        one = scoring.score_noise([noise_hit(distance=50)]).score
        two = scoring.score_noise(
            [noise_hit(distance=50), noise_hit(distance=50, name="Anden vej")]
        ).score
        single_penalty = 100.0 - one
        double_penalty = 100.0 - two
        self.assertGreater(double_penalty, single_penalty)
        # Doubling the sources adds about three points, not another full penalty.
        self.assertLess(double_penalty, single_penalty * 1.5)

    def test_a_road_beyond_its_reach_costs_nothing(self):
        far = scoring.score_noise([noise_hit(distance=10_000)])
        self.assertEqual(far.score, 100.0)

    def test_negotiation_rewards_weak_demand(self):
        strong = scoring.score_negotiation(
            listing(days_listed=200, favourites=200), self.market
        )
        weak = scoring.score_negotiation(
            listing(days_listed=200, favourites=1), self.market
        )
        self.assertGreater(weak.score, strong.score)

    def test_expense_outlier_scores_low(self):
        cheap = scoring.score_expense(listing(monthly_expense=3_000), self.market)
        dear = scoring.score_expense(listing(monthly_expense=12_000), self.market)
        self.assertGreater(cheap.score, dear.score)
        self.assertEqual(dear.score, 0.0)

    def test_total_never_leaves_zero_to_hundred(self):
        for price in (1_000_000, 7_000_000, 30_000_000):
            result = scoring.score_listing(
                listing(price=price, has_balcony=1, has_terrace=1, has_elevator=1),
                benchmark=70_000,
                basis="recent",
                neighbourhood="Test",
                tier=100,
                neighbourhood_source="zip",
                water_distance=0,
                water_name="havn",
                water_kind="prime",
                market=self.market,
            )
            self.assertGreaterEqual(result.total, 0.0)
            self.assertLessEqual(result.total, 100.0)

    def test_model_overrides_the_api_balcony_flag_in_both_directions(self):
        def bonus_for(**flags):
            return scoring.score_listing(
                listing(**flags),
                benchmark=70_000,
                basis="recent",
                neighbourhood="Test",
                tier=50,
                neighbourhood_source="zip",
                water_distance=500,
                water_name="havn",
                water_kind="prime",
                market=self.market,
            ).bonus

        # API says no, the model found one: the model wins.
        self.assertGreater(bonus_for(has_balcony=0, balcony_ai=1), 0.0)
        # API says yes, the model looked and found none: the model wins.
        self.assertEqual(bonus_for(has_balcony=1, balcony_ai=0), 0.0)
        # No verdict yet, so the API and the text still decide.
        self.assertGreater(bonus_for(has_balcony=0, has_balcony_text=1), 0.0)

    def test_bonus_is_capped(self):
        result = scoring.score_listing(
            listing(has_balcony=1, has_terrace=1, has_elevator=1),
            benchmark=70_000,
            basis="recent",
            neighbourhood="Test",
            tier=50,
            neighbourhood_source="zip",
            water_distance=500,
            water_name="havn",
            water_kind="prime",
            market=self.market,
        )
        self.assertLessEqual(result.bonus, config.BONUS_CAP)


class Neighbourhoods(unittest.TestCase):
    def test_amager_strandpark_beats_its_postal_code(self):
        hit = geo.resolve_neighbourhood(2300, 55.66330, 12.63200)
        self.assertEqual(hit.name, "Amager Strandpark")
        self.assertEqual(hit.source, "named_area")

    def test_orestad_overrides_its_postal_code_downwards(self):
        hit = geo.resolve_neighbourhood(2300, 55.63500, 12.58000)
        self.assertEqual(hit.name, "Ørestad")
        self.assertLess(hit.tier, config.NEIGHBOURHOODS[2300].tier)

    def test_ordinary_amager_keeps_its_postal_code_tier(self):
        hit = geo.resolve_neighbourhood(2300, 55.66500, 12.60800)
        self.assertNotEqual(hit.name, "Ørestad")

    def test_postal_code_groups_resolve(self):
        for zip_code, expected in [
            (2200, "Nørrebro"),
            (2100, "Østerbro"),
            (2150, "Nordhavn"),
            (1620, "Vesterbro"),
            (1050, "Indre By"),
        ]:
            with self.subTest(zip_code=zip_code):
                hit = geo.resolve_neighbourhood(zip_code, None, None)
                self.assertEqual(hit.name, expected)


class Peers(unittest.TestCase):
    def test_peer_benchmark_catches_a_cheap_pocket(self):
        # Twelve neighbours all asking 50.000 kr/m2, in a parish that would
        # otherwise be benchmarked far higher. This is the Ørestad case.
        rows = [
            {
                "lat": 55.635 + i * 0.0001,
                "lon": 12.580,
                "living_area": 100,
                "price": 5_000_000,
                "address_type": "condo",
            }
            for i in range(12)
        ]
        peers = PeerBenchmark(rows)
        result = peers.lookup(
            {
                "lat": 55.635,
                "lon": 12.580,
                "living_area": 100,
                "price": 5_000_000,
                "address_type": "condo",
            }
        )
        self.assertIsNotNone(result)
        self.assertLess(result, 51_000)

    def test_too_few_neighbours_returns_nothing(self):
        rows = [
            {
                "lat": 55.68,
                "lon": 12.57,
                "living_area": 100,
                "price": 7_000_000,
                "address_type": "condo",
            }
        ]
        self.assertIsNone(
            PeerBenchmark(rows).lookup(
                {
                    "lat": 55.68,
                    "lon": 12.57,
                    "living_area": 100,
                    "price": 7_000_000,
                    "address_type": "condo",
                }
            )
        )

    def test_distant_listings_are_not_peers(self):
        rows = [
            {
                "lat": 55.75,
                "lon": 12.65,
                "living_area": 100,
                "price": 5_000_000,
                "address_type": "condo",
            }
            for _ in range(12)
        ]
        self.assertIsNone(
            PeerBenchmark(rows).lookup(
                {
                    "lat": 55.62,
                    "lon": 12.50,
                    "living_area": 100,
                    "price": 7_000_000,
                    "address_type": "condo",
                }
            )
        )


class BatchParsing(unittest.TestCase):
    """The batch response must never attach a verdict to the wrong flat."""

    def test_matches_by_id_not_position(self):
        text = '[{"id": "b", "one_liner": "B"}, {"id": "a", "one_liner": "A"}]'
        out = _parse_verdicts(text, ["a", "b"])
        self.assertEqual(out["a"]["one_liner"], "A")
        self.assertEqual(out["b"]["one_liner"], "B")

    def test_unknown_ids_are_dropped_when_counts_disagree(self):
        text = '[{"id": "zzz", "one_liner": "wrong"}]'
        out = _parse_verdicts(text, ["a", "b"])
        self.assertEqual(out, {})

    def test_falls_back_to_position_only_on_an_exact_match(self):
        text = '[{"one_liner": "A"}, {"one_liner": "B"}]'
        out = _parse_verdicts(text, ["a", "b"])
        self.assertEqual(out["a"]["one_liner"], "A")
        self.assertEqual(out["b"]["one_liner"], "B")

    def test_partial_response_returns_only_what_was_answered(self):
        text = '[{"id": "a", "one_liner": "A"}]'
        out = _parse_verdicts(text, ["a", "b", "c"])
        self.assertEqual(set(out), {"a"})

    def test_survives_a_markdown_fence(self):
        text = '```json\n[{"id": "a", "one_liner": "A"}]\n```'
        self.assertIn("a", _parse_verdicts(text, ["a"]))

    def test_survives_chatter_around_the_json(self):
        text = (
            'Her er vurderingen:\n[{"id": "a", "one_liner": "A"}]\nHåber det hjælper.'
        )
        self.assertIn("a", _parse_verdicts(text, ["a"]))


class Taste(unittest.TestCase):
    """The analysis must refuse to speak from too little evidence."""

    def _report(self, rows):
        report = taste.TasteReport(total_rated=len(rows))
        liked = [r for r in rows if r["stars"] in taste.LIKED]
        disliked = [r for r in rows if r["stars"] in taste.DISLIKED]
        report.n_liked, report.n_disliked = len(liked), len(disliked)
        report.enough_data = (
            len(liked) >= taste.MIN_PER_SIDE and len(disliked) >= taste.MIN_PER_SIDE
        )
        return report

    def test_refuses_to_report_from_one_sided_ratings(self):
        rows = [{"stars": 5} for _ in range(20)]
        self.assertFalse(self._report(rows).enough_data)

    def test_refuses_below_the_minimum_sample(self):
        rows = [{"stars": 5}] * 3 + [{"stars": 1}] * 3
        self.assertFalse(self._report(rows).enough_data)

    def test_reports_once_both_sides_are_populated(self):
        rows = [{"stars": 5}] * 4 + [{"stars": 1}] * 4
        self.assertTrue(self._report(rows).enough_data)

    def test_finding_strength_is_scale_free(self):
        # A 100 m difference in water distance and a 100.000 kr difference in
        # price must be comparable, or the ranking is meaningless.
        water = taste.Finding("vand", liked=200, disliked=400, unit=" m")
        price = taste.Finding("pris", liked=6_000_000, disliked=6_100_000, unit=" kr")
        self.assertGreater(water.strength, price.strength)

    def test_neutral_factor_scores_are_ignored_not_averaged(self):
        row = {
            "breakdown": json.dumps(
                [
                    {"key": "water", "score": 90, "neutral": False},
                    {"key": "size", "score": 50, "neutral": True},
                ]
            )
        }
        self.assertEqual(taste._factor_score(row, "water"), 90)
        self.assertIsNone(taste._factor_score(row, "size"))

    def test_suggested_weights_are_valid_to_paste_into_config(self):
        # config.validate_weights() raises unless they sum to exactly 100, and
        # the whole point of the suggestion is that it can be pasted in.
        for liked, disliked in ((80, 30), (95, 5), (51, 50), (100, 0)):
            with self.subTest(liked=liked, disliked=disliked):
                findings = [
                    taste.Finding(f"Faktor: {label}", liked=liked, disliked=disliked)
                    for label in config.FACTOR_LABELS.values()
                ]
                weights = taste._suggested_weights(findings)
                self.assertEqual(round(sum(weights.values()), 2), 100.0)
                self.assertEqual(set(weights), set(config.WEIGHTS))

    def test_uneven_separation_still_sums_to_one_hundred(self):
        keys = list(config.FACTOR_LABELS.items())
        findings = [
            taste.Finding(f"Faktor: {label}", liked=90 - i * 11, disliked=10)
            for i, (_, label) in enumerate(keys)
        ]
        weights = taste._suggested_weights(findings)
        self.assertEqual(round(sum(weights.values()), 2), 100.0)


class Profiles(unittest.TestCase):
    """Switching weights must never break the score or need a re-evaluation."""

    def test_every_profile_is_valid(self):
        for key, profile in config.PROFILES.items():
            with self.subTest(profile=key):
                weights = profile["weights"]
                self.assertEqual(set(weights), set(config.FACTOR_KEYS))
                self.assertAlmostEqual(sum(weights.values()), 100.0, places=2)
                self.assertTrue(profile.get("name") and profile.get("note"))

    def test_default_profile_exists(self):
        self.assertIn(config.DEFAULT_PROFILE, config.PROFILES)
        self.assertEqual(
            config.WEIGHTS, config.PROFILES[config.DEFAULT_PROFILE]["weights"]
        )

    def test_normalise_always_sums_to_one_hundred(self):
        for raw in (
            {"water": 3, "size": 7},
            {"water": 1},
            dict.fromkeys(config.FACTOR_KEYS, 50),
            {"size": 999, "water": 1},
        ):
            with self.subTest(raw=raw):
                out = config.normalise_weights(raw)
                self.assertEqual(round(sum(out.values()), 2), 100.0)
                self.assertEqual(set(out), set(config.FACTOR_KEYS))

    def test_all_zero_falls_back_rather_than_dividing_by_zero(self):
        out = config.normalise_weights(dict.fromkeys(config.FACTOR_KEYS, 0))
        self.assertEqual(round(sum(out.values()), 2), 100.0)

    def test_negative_input_is_clamped(self):
        out = config.normalise_weights({"water": -50, "size": 10})
        self.assertGreaterEqual(min(out.values()), 0.0)
        self.assertEqual(round(sum(out.values()), 2), 100.0)

    def test_reweighting_changes_the_total_but_not_the_factor_scores(self):
        from kbh.webapp.app import reweight

        row = {
            "bonus": 0.0,
            "breakdown": [
                {"key": "water", "score": 100.0, "weight": 15.0, "label": "vand"},
                {"key": "size", "score": 0.0, "weight": 12.0, "label": "str"},
            ],
        }
        heavy = reweight(
            dict(row, breakdown=[dict(f) for f in row["breakdown"]]),
            {"water": 50.0, "size": 50.0},
        )
        light = reweight(
            dict(row, breakdown=[dict(f) for f in row["breakdown"]]),
            {"water": 5.0, "size": 95.0},
        )

        self.assertAlmostEqual(heavy["score"], 50.0, places=1)
        self.assertAlmostEqual(light["score"], 5.0, places=1)
        # The underlying factor scores are untouched, which is why no listing
        # ever needs to be re-read by the model when the profile changes.
        for result in (heavy, light):
            scores = {f["key"]: f["score"] for f in result["breakdown"]}
            self.assertEqual(scores, {"water": 100.0, "size": 0.0})

    def test_water_weight_actually_moves_a_waterfront_listing(self):
        from kbh.webapp.app import reweight

        def total(weights):
            row = {
                "bonus": 0.0,
                "breakdown": [
                    {"key": "water", "score": 100.0, "weight": 0, "label": "v"},
                    {
                        "key": "sqm_price_vs_benchmark",
                        "score": 20.0,
                        "weight": 0,
                        "label": "p",
                    },
                ],
            }
            return reweight(row, weights)["score"]

        self.assertGreater(
            total({"water": 60, "sqm_price_vs_benchmark": 40}),
            total({"water": 5, "sqm_price_vs_benchmark": 95}),
        )


class Batching(unittest.TestCase):
    """Batches must not group flats that invite cross-referencing."""

    def test_every_item_appears_exactly_once(self):
        items = [f"c{i}" for i in range(20)]
        batches = pipeline._stripe(items, 6)
        flat = [x for b in batches for x in b]
        self.assertEqual(sorted(flat), sorted(items))
        self.assertEqual(len(flat), len(set(flat)))

    def test_adjacent_scores_are_split_apart(self):
        # Two flats in the same building sit next to each other by score.
        items = [f"c{i}" for i in range(18)]
        batches = pipeline._stripe(items, 6)
        for batch in batches:
            positions = sorted(items.index(x) for x in batch)
            gaps = [b - a for a, b in zip(positions, positions[1:])]
            self.assertTrue(
                all(g > 1 for g in gaps),
                f"neighbouring listings landed together: {batch}",
            )

    def test_batch_size_one_gives_singletons(self):
        self.assertEqual(pipeline._stripe(["a", "b"], 1), [["a"], ["b"]])

    def test_handles_fewer_items_than_the_batch_size(self):
        batches = pipeline._stripe(["a", "b"], 6)
        self.assertEqual(sum(len(b) for b in batches), 2)
        self.assertTrue(all(b for b in batches))

    def test_empty_input(self):
        self.assertEqual(pipeline._stripe([], 6), [])


class Geometry(unittest.TestCase):
    def test_haversine_against_a_known_distance(self):
        # Rådhuspladsen to Amalienborg, about 1,5 km.
        metres = geo.haversine_m(55.6759, 12.5655, 55.6841, 12.5934)
        self.assertGreater(metres, 1_500)
        self.assertLess(metres, 2_200)

    def test_orestad_box_excludes_islands_brygge(self):
        self.assertTrue(geo._in_box(55.635, 12.580, geo.ORESTAD_BOX))
        self.assertFalse(geo._in_box(55.6665, 12.5850, geo.ORESTAD_BOX))


if __name__ == "__main__":
    unittest.main(verbosity=2)

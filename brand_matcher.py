import csv
import re
from dataclasses import dataclass
from typing import Optional

from rapidfuzz.distance import Levenshtein

MIN_FUZZY_KEYWORD_LEN = 6
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(domain):
    return _TOKEN_RE.findall(domain.lower())


def _edit_distance_budget(keyword_len):
    if keyword_len <= 7:
        return 1
    return 2


@dataclass
class MatchResult:
    brand: Optional[str]
    sector: Optional[str]
    confidence: float
    method: str


class BrandMatcher:
    def __init__(self, reference_csv):
        self.brands = []
        with open(reference_csv, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                keywords = [k.strip().lower() for k in row["keywords"].split("|")]
                self.brands.append((row["brand"], row["sector"], keywords))

    def match(self, domain):
        domain_lower = domain.lower()

        for brand, sector, keywords in self.brands:
            for kw in keywords:
                if kw in domain_lower:
                    return MatchResult(brand, sector, 1.0, "substring")

        tokens = _tokenize(domain_lower)
        best_score = 0.0
        best_brand = None
        best_sector = None

        for brand, sector, keywords in self.brands:
            for kw in keywords:
                if len(kw) < MIN_FUZZY_KEYWORD_LEN:
                    continue
                budget = _edit_distance_budget(len(kw))
                for token in tokens:
                    if abs(len(token) - len(kw)) > budget:
                        continue
                    dist = Levenshtein.distance(token, kw, score_cutoff=budget)
                    if dist <= budget:
                        score = 1 - (dist / len(kw))
                        if score > best_score:
                            best_score = score
                            best_brand = brand
                            best_sector = sector

        if best_brand is not None:
            return MatchResult(best_brand, best_sector, round(best_score, 2), "fuzzy")

        return MatchResult(None, None, 0.0, "none")
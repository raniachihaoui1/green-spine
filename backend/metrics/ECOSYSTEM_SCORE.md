# Ecosystem score

**Code:** [`ecosystem.py`](ecosystem.py) · **Parameters:** [`backend/parameters.py`](../parameters.py), section 8.

**Current status:** legacy exploratory index, not a headline dashboard metric or
ranking criterion. Empty/new-planting-free references return `score=None` because
existing species and resilience are unknown. Do not subtract this index from an
invented "today" score. Crown-over-open-ground is not evidence of planted habitat
layers; touching the wet-zone proxy is not functional ecological connectivity.
Unsealed ground now uses a clipped geometric union, and the legacy
`natural_soil_share` field means mapped open ground, not verified natural soil.

## 1. What it measures

One number from 0 to 100 that says how good the planted corridor is as an ecosystem. "Good" means four things:

| Part | Question | Why it matters |
|---|---|---|
| **Habitat** | Is there enough habitat, and is it layered? | No habitat, no ecosystem. Layers (tree, shrub, herb) give more niches than trees over paving |
| **Diversity** | Is it varied, and does it belong here? | A mix of native species resists pests and disease and supports more wildlife |
| **Connectivity** | Can animals and seeds move along it? | The corridor's job is to link the city to the Dommel valley. Gaps break the link |
| **Resilience** | Will it survive and keep working? | Street trees fail below ground. An ecosystem that dies in ten years scores nothing |

The score is computed per planting option and per year, so it shows how each option develops from 2026 to 2060.

## 2. Calculation

Each indicator is scaled to 0–1 against a target (capped at 1). Each part is a weighted mean of its indicators. The total is a weighted mean of the four parts, times 100.

### 2.1 Habitat (H)

```
H = 0.5 · min(canopy% / 30, 1)  +  0.3 · layered_share  +  0.2 · min(unsealed% / 50, 1)
```

| Indicator | Definition | Target / source |
|---|---|---|
| `canopy%` | Merged crown area (existing + new trees, at the selected year) ∩ corridor ÷ corridor area | 30 %, 3-30-300 rule |
| `layered_share` | Share of the crown area above unpaved ground, where shrubs and herbs can grow under the trees | 1.0 = every crown over open ground |
| `unsealed%` | (Unpaved area + one tree pit of `ECO_TREE_PIT_M2` = 9 m² per tree planted in paving) ÷ public ground (corridor minus buildings) | 50 %, cluster passport 1A |

### 2.2 Diversity (D)

```
D = 0.4 · Shannon_scaled  +  0.3 · native_share  +  0.3 · wildlife_share
D = D × 0.5   if the 10-20-30 rule is broken   (× 0 when ECO_DIVERSITY_RULE_STRICT = True)
```

| Indicator | Definition |
|---|---|
| `Shannon_scaled` | Shannon index H' = −Σ pᵢ ln pᵢ over the species of the new trees, divided by ln(min(number of trees, species available in the plant table)). 1 = as even and as varied as possible |
| `native_share` | Share of new trees whose species has `native = yes` in the plant table |
| `wildlife_share` | Share of new trees whose species has `wildlife = yes`. The starter table has no such column, so `ECO_WILDLIFE_SHARE_DEFAULT` = 0.5 is used and the panel says "assumption" |
| 10-20-30 rule | At most 10 % per species, 20 % per genus, 30 % per family (Santamour) |

The penalty is 0.5 rather than 0 by default because the 20-species starter table cannot meet the 10 % rule. Switch to strict once the full plant database is in.

### 2.3 Connectivity (C)

```
C = 0.7 · max(0, 1 − longest_gap / 100 m)  +  0.3 · connects_dommel
```

| Indicator | Definition |
|---|---|
| `longest_gap` | Longest stretch of the centreline with no crown within 2 m (same as the "Longest gap" KPI) |
| `connects_dommel` | 1 if the canopy touches the Dommel valley outline (`L["dommel"]`), else 0. Until that layer exists, the wet zone is used as a proxy |

### 2.4 Resilience (R)

```
R = 0.6 · natural_soil_share  +  0.4 · expected_survival
```

| Indicator | Definition |
|---|---|
| `natural_soil_share` | Share of new trees whose cell meets the class's soil need without engineered soil |
| `expected_survival` | Mean 10-year survival: 0.85 in natural soil, 0.70 in engineered soil (starting values) |

### 2.5 Total

```
Ecosystem score = 100 · (0.25 H + 0.25 D + 0.25 C + 0.25 R)                  # ECO_AGGREGATION = "arithmetic"
Ecosystem score = 100 · H^0.25 · D^0.25 · C^0.25 · R^0.25                    # ECO_AGGREGATION = "geometric"
```

The geometric mean stops one strong part from hiding a weak one: an option with full canopy but no surviving trees scores low. Equal weights are the easiest to defend; change them in `ECO_WEIGHTS`.

"vs. today" compares with the same calculation with no new trees (existing trees only).

## 3. Parameters

| Parameter | Default | Label |
|---|---|---|
| `ECO_WEIGHTS` | 0.25 each | Team choice |
| `ECO_AGGREGATION` | arithmetic | Team choice |
| `ECO_HABITAT_W` | canopy 0.5, layered 0.3, unsealed 0.2 | Starting value |
| `ECO_DIVERSITY_W` | Shannon 0.4, native 0.3, wildlife 0.3 | Starting value |
| `ECO_CONNECTIVITY_W` | gap 0.7, Dommel 0.3 | Starting value |
| `ECO_RESILIENCE_W` | natural soil 0.6, survival 0.4 | Starting value |
| `ECO_CANOPY_TARGET_PCT` | 30 % | Source: 3-30-300 |
| `ECO_UNSEALED_TARGET_PCT` | 50 % | Source: cluster passport 1A |
| `ECO_TREE_PIT_M2` | 9 m² | Starting value |
| `ECO_GAP_ZERO_M` | 100 m | Starting value |
| `ECO_DIVERSITY_RULE_STRICT` | False | Switch on with the full plant database |
| `ECO_WILDLIFE_SHARE_DEFAULT` | 0.5 | Assumption until the plant table has a wildlife column |
| `SURVIVAL_NATURAL_SOIL` / `SURVIVAL_ENGINEERED_SOIL` | 0.85 / 0.70 | Starting values |

## 4. Basis

The four parts follow established frameworks, adapted to one corridor:

- **City Biodiversity Index (Singapore Index):** natural area share, connectivity, native species.
- **Biotope Area Factor (Berlin) / Urban Greening Factor (London):** counting unsealed and layered green, not just trees.
- **3-30-300 rule:** 30 % canopy.
- **Santamour 10-20-30 rule:** species, genus and family limits.
- **Cluster passport 1A (Fellenoord):** ≥ 50 % unsealed public space.

Say "adapted from" when presenting it. The weights and the scaling are ours.

## 5. Limits

- No shrub or herb layer is placed yet. `layered_share` measures where layers *could* grow, not where they do.
- Wildlife value is an assumption until the plant database has a column for it.
- Survival rates are starting values, not measured data.
- On demo data the numbers mean nothing. They only show that the method works.
- The total hides trade-offs. Always show the four parts next to it.

## 6. Example (demo data, 90 trees)

| Option | 2026 | 2040 | 2060 | Weakest part |
|---|---|---|---|---|
| A Most shade | 33 | 42 | 47 | Resilience (all trees in engineered soil) |
| B Most connected | 34 | 48 | 55 | Diversity |
| C Lowest cost | 44 | 54 | 58 | Connectivity |

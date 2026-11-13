# Conditional green facades

Code: [facades.py](../facades.py). Parameters: [parameters.py](../parameters.py).

Street-facing walls are tested for light in floor bands. Whole walls are selected
from the sunniest part of the inventory, up to the selected share. The realised
share can be lower after feasibility screening.

Each selected wall needs an unobstructed assumed ground-rootbed strip inside the
assessment ground, excluding roads, water, buildings, known utilities/underground
structures, other selected wall beds and reserved tree-root zones.

Vines are rechecked against the nearest usable borehole and must tolerate the
light in every band they could occupy. A global soil-compatible list alone is not
a local fit. Distant boreholes and missing rooting information remain conditional.

Climber height grows exponentially from an initial planted height towards the
species' mature height. Area is wall length times actual green height in the
selected year, capped by the building, band inventory and species height.

## Not verified

Root depth and compaction, groundwater, structural supports, windows and entrances,
maintenance access, irrigation sources and establishment survival. No automatic
approval or promised wall cooling is given. Native status is incomplete for vines.

Facade area is separate from canopy, ground and roof area. It is not silently
credited as storm storage or municipal quality-weighted greenery. Roof-to-storage-
to-irrigation connections need a supplied drainage design.

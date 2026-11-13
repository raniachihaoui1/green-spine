# Indicative storm balance

Code: [water.py](water.py). Assumptions: [parameters.py](../parameters.py).

Assessment area is corridor minus buildings and known actual water. Rainfall is
public area times the design rain depth. This is not a municipal storage calculation.

1. Union mapped open ground and proposed tree pits; clip away roads, buildings
   and water. New pits additionally avoid known underground/utility exclusions.
   Mapped greenery over a basement still counts as unsealed at grade, but is not
   assumed to infiltrate into the soil below.
2. Clip shelters to the assessment area. The higher pergola takes precedence
   where it overlaps a building canopy.
3. Crown interception is counted outside shelter footprints only, conservatively.
   Its depth cannot exceed the local rainfall.
4. Open-ground infiltration is limited to the smaller of its assumed capacity
   and the rain reaching it **after** crown interception.
5. Green-shelter retention is limited to the smaller of roof capacity and rain
   intercepted there, multiplied by the green fraction. Only the open fraction of
   a shelter lets direct rainfall reach the ground underneath.
6. Remaining water is runoff. Interception + infiltration + roof retention +
   runoff equals rainfall; an overall cap does not conceal component over-counting.

No roof runoff is directed into rootbeds without an actual drainage design.
No tank volume, groundwater response, roof storage outside the corridor,
irrigation demand, flood depth or sewer performance is inferred.
Unknown drainage remains unknown. Parameters are starting values, not field tests.

The 60 mm public-paving storage requirement in Cluster 1A is listed separately
as not assessed without the applicable boundary and designed-storage inventory.

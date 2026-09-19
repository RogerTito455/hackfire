# Clipping the fire to the demo box is not enough for openrouteservice

**Date:** 2026-09-19 · **Area:** openrouteservice, slice 5 (#6)

## What happened

The rule we wrote down was "clip the fire polygon to the demo box `-4.85,40.30,-4.40,40.50`". At latitude 40.4° that box is about **38 km wide and 22 km tall (~850 km²)**. openrouteservice restricts avoid polygons to:

- area: **200 km²**
- extent (height or width): **20 km**

So a fire polygon clipped to the demo box can still be rejected, on both counts.

## What we do about it

Clip the predicted fire to a box **at most 14 km × 14 km** (196 km², under both limits) centred on the midpoint between the route's start and end, then send the result as `avoid_polygons`. If the clipped polygon is empty, route without it. Not yet run against the API.

Not checked yet: how ORS reports the rejection (status code and message). Record it here when someone hits it.

## Sources

- Restrictions: https://openrouteservice.org/restrictions/ ("Avoid polygon area: 200 km²", "Avoid polygon extent (height or width): 20 km")
- `avoid_polygons` format: https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/routing-options

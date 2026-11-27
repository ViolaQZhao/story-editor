# Nootka engine spec

Version of 25 November 2026. This is the specification of the engine behind the Nootka Street simulation as it stands in the code (SE Prototype/nootka/engine). J marks a value set by judgement that still needs review. Ranges are written low to high; one value is drawn from each range once per run.


## 1. Scope

One run is one planting design in one possible 50-year future, in yearly steps. The engine answers six questions: habitat conditions for Steller's jay, habitat conditions for Anna's hummingbird, tree survival, habitat structure, canopy growth, and other plant problems. It tests habitat conditions; it does not model birds.


## 2. Site

- Grid: 1 m cells, 52 by 89, built from the Rhino model (Nootka Testing Model.3dm). Coordinates are those of the Rhino model.
- Cell classes: groundcover 1,263; shrub patch 979 (11 patches, 22 to 215 m2); path 436; impervious 376; private parcel 1,570; unclassified 4. Green area is groundcover plus shrub patch: 2,242 m2.
- Drawn zones are painted large to small so nested islands win; parcels are painted last, so nothing inside a parcel counts as green.
- Elevation and slope come from the contours (27.4 to 41.7 m, mean slope 7.7 degrees, facing north).
- 32 tree plots. As drawn: 8 vine maple, 7 Sitka spruce, 6 red alder, 6 bigleaf maple, 5 western red cedar.
- Buildings: one flat volume per parcel, 3 m per storey, two storeys except the smallest parcel inside the test area (four). Drawn only; no effect on the calculation.
- A built site can be saved as plain JSON so the engine runs without the geometry libraries (this is what the browser loads).

## 3. Randomness

- Stream 1 (what is not known well): every parameter range and every species' growth rate and final height is drawn once per run.
- Stream 2 (year-to-year chance): all yearly draws are made up front, per year, per tree and per cell. Two designs run with the same seed therefore meet exactly the same events and the same draws.
- A timeline is fully defined by its design and its seed and can be recomputed at any time.

## 4. Order of one year

- Events of the year are drawn (dry summer, heat wave, wind storm, heavy snow, budget cut).
- Planting, and replanting of losses if the site is under care.
- Growth, with drought and shade.
- Deaths: one draw per tree against the causes of that year; then wind; then snow breakage.
- Crowns and canopy.
- Management that removes or lifts trees (glade management, red alder removal).
- Invasive plants and trampling.
- Shrub patches: cover, flowering by month, berries.
- Layers, habitat tests, and the year's record.

## 5. Trees

- Planted at 1.5 m (J). Height grows by the species rate times a growth factor times (1 minus (height / final height) squared).
- Growth factor: 0.3 in the first two years; in an unwatered dry summer it falls toward the dry-summer factor (0.5 to 0.85) in proportion to drought sensitivity (high 1.0, medium 0.5, low 0.15); under shade it falls by up to 40 to 80% (J) times shade sensitivity (low tolerance 1.0, medium 0.5, high 0.1).
- Crown radius = a times height plus b, capped (per species).
- Shade: a tree under 10 m is shaded by a neighbour more than 2 m taller, by how far its stem sits inside that neighbour's crown (0 to 1). The largest value over all neighbours is used.
- Health: stressed if recent growth is below 75% of what it could be (J), if broken by snow in the last three years, or if past its lifespan; otherwise good.
- Red alder has a lifespan of 40 to 60 years. Other species have none within the 50 years.

## 6. Causes of death

There is no base mortality rate. Each year each living tree gets one draw against the sum of the causes below, which also decides the cause recorded.

- Dry summer, tree not watered: establishing tree (under 5 years) 5 to 15% (J), established tree 0.3 to 1.2% (J); both times drought sensitivity / 0.5; times 1.3 on slopes over 20 degrees. Young conifers under a red alder nurse crop: times 0.5 to 0.8 (J).
- Heat wave: unsheltered establishing trees, 2 to 5%.
- Second dry summer in a row: established western red cedar 2 to 10%, Sitka spruce half of that.
- End of lifespan: 8% a year once past it.
- Shade: 1 to 4% (J) times shade sensitivity times the shade value.
- Wind storm (a separate draw, trees over 6 m): the species chance (low resistance 3 to 10%, medium 1 to 4%, high 0.4 to 1.5% J, at 20 m) times (height / 20) squared up to 2.5; times 1.5 within 6 m of the edge; times 1.3 where invasive plants cover the tree's cell; times 1.2 once any tree has been removed; times 4 in an extreme storm.
- Heavy snow does not kill: species with low snow resistance over 3 m have a 5 to 20% chance of breakage, which takes 15% off the height.

## 7. Shrub patches

- A patch has a cover (0 to 1) and a mix of species by share. Cover rises by 0.2 a year. In a dry summer without watering it falls by 10 to 30% (J) times the mix's drought sensitivity.
- Species: oceanspray, salmonberry, thimbleberry, osoberry, snowberry, salal; winter mahonia as an added winter-flowering shrub (12% of each patch when used, J). Each has a height, flowering months, a nectar value, berries or not, drought sensitivity, and the canopy cover it tolerates.
- Recipes (J): even; berry (salmonberry 25, thimbleberry 20, osoberry 20, snowberry 15, salal 15, oceanspray 5); nectar (salmonberry 35, osoberry 25, salal 20, oceanspray 10, thimbleberry 5, snowberry 5); cover (salal 40, snowberry 20, oceanspray 20, osoberry 10, salmonberry 5, thimbleberry 5).
- Flowering area of a species = patch area times cover times (1 minus invaded share) times its share, reduced as canopy over the patch exceeds what the species tolerates, and times 0.7 in a heat-wave year.

## 8. Events

- Dry summer: chance 20 to 30% a year now, rising in a straight line to 30 to 45% by year 50.
- Heat wave: 12 to 22% now, 25 to 50% by year 50 (J).
- Wind storm: 8 to 14% a year; extreme storm 1 to 3%.
- Heavy snow: 25 to 35% a year.
- Budget cut: starts with a chance of 5 to 10% a year (J) and lasts 2 to 5 years. During a cut there is no watering, no replanting and no clearing of invasive plants.
- Invasive plants: arrive at an edge cell with a chance of 10 to 30% a year (J) and spread to each neighbouring green cell with a chance of 20 to 60% a year. Cleared on the chosen cycle while the site is under care.
- Trampling: cells within 2 m of the path are worn a step further with a chance of 30 to 60% a year (J); past a threshold the ground layer there is lost.
- Each of the seven can be switched off for a run.

## 9. Management modules

- Watering: years of establishment watering (run 0 tries 2 and 5); watering established trees in dry summers, which leaves 30 to 60% (J) of their drought losses.
- Replanting: same species the next year (default); a conifer lost to drought comes back as Douglas-fir; or no replanting.
- Invasive plants: cleared every year (default), every 3 or 5 years, or never.
- Glade management (run 0 tries with and without): from a first year (default 10), every N years (default 5), if canopy over the shrub patches is above 40%, act on the deciduous tree that covers the patches most. Methods: remove it, not replanted (default); lift its crown, which leaves 40 to 70% (J) of its shade over the patches; or remove only trees up to 8 m.
- Red alder (run 0 tries with and without): planted first, with conifers following after 5 to 10 years and sheltered while young; optionally all red alder taken out in a chosen year.
- Winter mahonia (run 0 tries with and without) and the shrub recipe are plant choices.

## 10. Habitat structure and tests

- Layers per green cell: ground (not invaded, not worn out); shrub (in a patch with cover of at least 0.5, or under a tree 1.5 to 6 m tall); tree (under a tree over 6 m).
- J1: at least 3 conifers of 8 m or taller (nest trees).
- J2: at least 2 nest trees with canopy over at least 50% of the ground within 10 m.
- J3: all three layers on at least 40% of the green area.
- J4: berry shrubs on at least 10% of the green area.
- H1: flowers in at least 9 months (a month counts when flowering area is at least 0.5% of the green area; maples over 3 m add March to June).
- H2: shrubs with high nectar value in flower between February and April on at least 5% of the green area.
- H3: nectar present, with a vine maple of 2 m or a shrub patch 2 m tall.
- H4: at least 30% of the green area open to the sky.
- All thresholds are draft values (J).

## 11. Outputs

- Yearly series: canopy cover, layers, flowering months, berry and nectar area, trees alive and stressed, trees lost by cause, plantings, first-planted trees alive, shrub cover, invaded share, and each test.
- Per timeline: share of years 20 to 50 with all four conditions met, for each bird and for each test; canopy at years 10 to 50; three-layer share at 50; share of plantings that got through five years; first-planted trees alive at 50; plots holding a living tree at 50; deaths per tree per year; losses by cause.
- Class of a timeline: both birds, jay only, hummingbird only, or neither, by which birds have all four conditions in at least 70% (J) of years 20 to 50.
- With recording on, every year keeps each tree's species, height, crown, age, health, shade and what happened to it, and each patch's cover, canopy above and invaded share.

## 12. Exploration and anchoring

- Open plots: 24 of 32. A conifer plot may hold Sitka spruce, grand fir, western red cedar or Douglas-fir; a tall deciduous plot bigleaf maple or red alder. Vine maple plots are fixed.
- A design is one species per open plot, a shrub recipe, and the choices the engine explores: red alder first, glade management, winter mahonia, watering 2 or 5 years.
- A run samples designs within what the designer has anchored or set, and meets each with the same futures. In the app: 60 designs, 20 futures, 1,200 timelines.

## 13. Species traits used

- Sitka spruce: growth 0.30 to 0.60 m a year, final height 26 to 34 m, drought sensitivity high, wind resistance low, snow medium, shade tolerance medium.
- Douglas-fir: 0.45 to 0.90; 28 to 38 m; drought medium; wind high; snow low; shade low.
- Grand fir: 0.40 to 0.85; 26 to 34 m; drought medium; wind medium; snow medium; shade medium.
- Western red cedar: 0.30 to 0.50; 22 to 30 m; drought medium (its weakness is the second dry summer); wind medium; snow low; shade high.
- Bigleaf maple: 0.50 to 1.00; 20 to 28 m; all medium; flowers March to June.
- Red alder: 0.80 to 1.50; 18 to 26 m; drought medium; wind medium; snow low; shade low; lifespan 40 to 60 years.
- Vine maple: 0.20 to 0.40; 5 to 8 m; drought medium; shade high; flowers March to June.
- Sources are noted beside each species in the code (literature review rows; BC Tree Species Compendium for Douglas-fir).

## 14. Drawings and app

- Plan, section and block model are drawn by the engine's own code from one year's record, in 0.5 m blocks, each with a pick map so trees and patches can be selected.
- The app runs the same Python files in the browser, on up to four threads, with the runtime shipped with the page. A run is about 0.1 seconds; drawing one year is about one second.
- Files: engine/site.py, species.py, model.py, explore.py, story.py; render_section.py, render_views.py, render_fine.py; web_api.py; app/ (the page); tests_check.py.

## 15. Checks

- The same seed gives the same result; two designs with one seed meet the same events.
- A 1 m and a 0.5 m grid agree.
- Sampling respects candidates and anchors.
- More watering never raises losses; switching dry summers off removes drought deaths; without replanting only 32 trees are ever planted; each glade method does what it says; red alder is gone after its removal year.

## 16. Limits

- No pests, disease, vandalism or planting failure. No root competition or water balance. No shade from buildings. No change in where the crown starts. Shrubs are patches, not plants. Groundcover has no flowers or fruit. The eco index in the code is not used in the app.

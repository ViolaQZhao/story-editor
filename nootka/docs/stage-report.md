# Nootka Street: stage report

25 November 2026. Viola (Qianqian) Zhao, with Claude. This report sums up the second prototype of the Story Editor, built on the forest section of the Nootka Street design. It covers what was built in three days (24 to 26 November), what the first runs showed, the decisions made along the way, and what comes next.


## 1. What this stage set out to do

The first prototype (Mount Pleasant) simulated scenarios. This stage asked whether the same idea can work on a real planting design: let an engine explore what could happen to a design over 50 years, let the designer read the spread of outcomes, and let the designer narrow the next run with what they now know. The test area is about 52 by 89 m on a north-facing slope, with 32 tree plots and 11 shrub patches.

The designer's questions were fixed first. Over 50 years: does the design keep the habitat conditions Steller's jay needs; does it keep those Anna's hummingbird needs; what share of the trees survives; what habitat structure forms; how does canopy cover grow; and what other plant problems appear.


## 2. What was built


### Site model

- The site is read from the Rhino model as a 1 m grid: groundcover, shrub patches, path, impervious surface and private parcels, with elevation and slope from the contours.
- Green area is 2,242 m2, of which 979 m2 is shrub patch and 1,263 m2 groundcover. The slope faces north, mean 7.7 degrees.

### Engine

- One run is one design in one 50-year future. Trees grow, shade each other, get stressed, die and are replanted; shrub patches gain and lose cover and flower by month; seven kinds of event arrive at random.
- Two kinds of uncertainty are kept apart: what is not known well (growth rates, how deadly a dry summer is) is drawn once per run; year-to-year chance (which years are dry, which tree dies) is drawn separately. Two designs compared under the same future meet exactly the same events.
- A run takes about 0.03 seconds on a desktop and about 0.1 seconds in a browser.

### Drawings

- Plan, section and block model are drawn from the engine's numbers for any year, in 0.5 m blocks. Nothing is drawn in advance: a timeline is stored as its design and a seed, and drawn when opened.
- A tree or a shrub patch can be clicked in any of the three drawings. It is highlighted in all three and its record for that year is shown: species, height, crown, age, health, and what has happened to it.

### The app

- A single page: title, Run, a loading screen where runs appear as dots while they finish, the cloud of all timelines in four classes, the timelines inside one class in four groups, one timeline, and its report.
- The engine itself runs in the browser (Python compiled for the browser, on up to four threads). Run is a real run, not a replay.

### The assemblable part

- Run 0 has every event on and lets the engine make every choice. Each later run is assembled from modules.
- Event modules are switches: dry summers, heat waves, wind storms, heavy snow, invasive plants, trampling, budget cuts.
- Management modules are the most adjustable, because they are decisions people make: watering, replanting, clearing invasive plants, glade management, red alder.
- Plant modules are anchors: the species at any of the 24 open tree plots, the shrub recipe, and winter mahonia can be fixed from the assembly screen or by clicking a plant in a report.
- Every run keeps a record of what was assembled and how it differs from run 0. The runs sit side by side and can be reopened.
- Each report ends with the most critical issues: what the issue is, whether it belongs to this one future or shows up across the run, and which module could change it.

## 3. What the first runs showed

These are findings about the tool and the model as much as about the design. Numbers are from test runs on 25 November and will move as parameters are reviewed.

- The three-layer condition for Steller's jay is never met. The target is 40% of the green area with ground, shrub and tree layers together; the best timeline in a run reaches about 25%. No design choice moves it enough, so the target or the way layers are counted needs review before the design does. The tool now says this itself in the critical issues.
- Hummingbird conditions split the runs: in the first full round about a third of timelines met them in most years and two thirds did not. The condition missed most often is flowers in nine or more months.
- Tree mortality had to be rethought. The first version put a yearly death rate in and added events on top, which counted bad years twice: about 45 losses per run. Published rates are already the average over every cause, so the rate was removed as an input. Trees now die only of modelled causes, and the yearly rate is read off the result: about 1% a year with two years of watering, and almost none if no events happen. Dry summers cause about half the losses.
- Glade management, as first written, removed a 21 m bigleaf maple in year 41 to give light to shrubs. No one would manage a site this way. The rule was kept as a finding: this kind of decision needs the designer's judgement, which is why management became the most adjustable kind of module.
- Watering shows a clear, modest effect: five years of establishment watering instead of two saves about three trees per run, all of them drought losses.

## 4. Decisions made along the way

- Western red cedar against Douglas-fir replaced Sitka spruce against grand fir as the first tree decision, because the first pair was not in dispute.
- Mortality is a result, not an input (see above).
- Events are switches; management is where the designer acts.
- All drawings use one block size, 0.5 m.
- The engine runs in the browser so that Run is real and any timeline can be opened, instead of preparing results in advance.
- Every tree plot that has a choice is open in run 0 (24 of 32), so any such tree can be anchored. Vine maple stays fixed: it is the only small tree in the palette.
- Sub-groups in the results are formed by outcome (canopy and trees kept), not by design choice. Design choices show once a timeline is picked. This keeps the designer's blind predictions from being answered by accident.

## 5. Limits known now

- The bird results test habitat conditions. They do not count birds.
- Causes of death not modelled: pests, disease, vandalism, planting failure. The yearly mortality that comes out is therefore lower than street-tree studies report.
- Competition between trees is limited to shade from taller neighbours. Buildings are drawn but do not shade.
- Where the crown starts on the trunk is a fixed share; the crown base does not yet rise under shade.
- Shrubs are patches with a cover and a mix, not single plants. Groundcover does not flower or fruit.
- Many values are judgement and marked as such in the engine spec. The largest are the two drought death chances, the stress thresholds, the effect of watering in dry summers and the effect of crown lifting.
- The check of the designer's blind predictions against the results has not been done yet.

## 6. Open questions for Viola

- The three-layer target for Steller's jay: lower the 40%, or change how layers are counted?
- How is glade management really done? The three methods in the app (remove, lift the crown, remove only small trees) are placeholders.
- Review the judgement values listed in the engine spec, the drought chances first.
- Which parcel holds the four-storey building (now the narrow one on the east side)?
- Are there existing trees to keep in the test area?

## 7. Next steps

- A general plant library: one table of trees and shrubs with their traits, ranges and sources, separate from any one project, so more species can be simulated.
- Adding and removing trees: new plots placed by the designer, not only a choice of species at drawn plots.
- User data as a fourth kind of module: local measurements that narrow the built-in ranges, shown with where each number comes from.
- Year-by-year time slider drawn in the browser, in place of six fixed years.
- Module connections shown as links (dry summer to second dry summer to cedar dieback; budget cut to no watering) that the designer can cut.
- The blind-prediction check, then the write-up for the application.

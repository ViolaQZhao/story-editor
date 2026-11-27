"""Species traits. Ranges are sampled once per run (uncertain knowledge).
Sources: Nootka parameters tab and Literature review rows (see `src`). 'J' marks judgement."""

# growth m/yr after establishment, hmax m (asymptote), crown radius = a*h+b capped at rmax
TREES = {
    "Sitka spruce":      dict(conifer=1, growth=(0.30, 0.60), hmax=(26, 34), crown=(0.15, 0.5, 5.0), drought="high", wind="low",  snow="med", shade="med", life=None,
                              src="lit rows 1-6, 11"),
    "Douglas-fir":       dict(conifer=1, growth=(0.45, 0.90), hmax=(28, 38), crown=(0.16, 0.5, 5.5), drought="med",  wind="high", snow="low", life=None,
                              shade="low", src="BC Tree Species Compendium (Douglas-fir): water deficit M, heat M-H, wind H, snow L-M coastal, low light "
                                               "'exposure-requiring in humid climates', site index 50 about 40 m; UC ANR: about 0.9 m/yr at age 8-10"),
    "Grand fir":         dict(conifer=1, growth=(0.40, 0.85), hmax=(26, 34), crown=(0.15, 0.5, 5.0), drought="med",  wind="med",  snow="med", shade="med", life=None,
                              src="lit rows 25-32"),
    "Western red cedar": dict(conifer=1, growth=(0.30, 0.50), hmax=(22, 30), crown=(0.18, 0.5, 5.5), drought="med", wind="med",  snow="low", shade="high", life=None,
                              src="lit rows 13-22"),
    "Bigleaf maple":     dict(conifer=0, growth=(0.50, 1.00), hmax=(20, 28), crown=(0.30, 0.5, 8.0), drought="med",  wind="med",  snow="med", shade="med", life=None,
                              bloom=(3, 6), src="lit rows 35-43"),
    "Red alder":         dict(conifer=0, growth=(0.80, 1.50), hmax=(18, 26), crown=(0.22, 0.5, 5.0), drought="med",  wind="med",  snow="low", shade="low", life=(40, 60),
                              src="lit rows 46-55"),
    "Vine maple":        dict(conifer=0, growth=(0.20, 0.40), hmax=(5, 8),   crown=(0.45, 0.3, 3.5), drought="med",  wind="med",  snow="med", shade="high", life=None,
                              bloom=(3, 6), src="lit rows 57-62"),
}
H0 = 1.5  # height at planting, m (J)

# bloom = (first month, last month); nectar: value for Anna's hummingbird; berry: food for Steller's jay
SHRUBS = {
    "Oceanspray":   dict(height=3.0, bloom=(6, 8), nectar=0.3, berry=0, drought="low",  shade_ok=0.45),
    "Salmonberry":  dict(height=2.5, bloom=(3, 6), nectar=1.0, berry=1, drought="high", shade_ok=0.60),
    "Thimbleberry": dict(height=1.8, bloom=(4, 7), nectar=0.3, berry=1, drought="med",  shade_ok=0.45),
    "Osoberry":     dict(height=3.0, bloom=(2, 4), nectar=0.6, berry=1, drought="low",  shade_ok=0.55),
    "Snowberry":    dict(height=1.5, bloom=(5, 8), nectar=0.3, berry=1, drought="low",  shade_ok=0.50),
    "Salal":        dict(height=1.2, bloom=(5, 7), nectar=0.6, berry=1, drought="low",  shade_ok=0.33),  # lit row 100
    # decision 2 option B: adaptive winter-flowering shrub (Mahonia x media type), lit row 139
    "Winter mahonia": dict(height=2.5, bloom=(11, 1), nectar=1.0, berry=1, drought="low", shade_ok=0.60),
}
NATIVE_SHRUBS = ["Oceanspray", "Salmonberry", "Thimbleberry", "Osoberry", "Snowberry", "Salal"]
WINTER_SHARE = 0.12  # share of each patch given to winter mahonia under decision 2B (J)


def months(b):
    a, z = b
    return [m for m in range(1, 13) if (a <= m <= z if a <= z else (m >= a or m <= z))]


# uncertain parameters sampled once per run: (low, high)
PARAMS = {
    # No base mortality rate (Viola, 25 Nov): published yearly mortality is already the average over every cause,
    # so it is not an input. A tree dies only when a modelled cause kills it; the yearly rate is read off the results.
    "dry_young":    (0.05, 0.15),   # chance an establishing tree (age < 5) dies in an unwatered dry summer, medium drought sensitivity (J)
    "dry_old":      (0.003, 0.012), # same for an established tree (J)
    "dry_growth":   (0.5, 0.85),    # growth factor in a dry summer
    "cedar_dieback": (0.02, 0.10),  # established cedar lost in a second dry summer in a row (event 2)
    "heat_young":   (0.02, 0.05),   # added mortality of exposed young plants in a heat wave
    "wind_low":     (0.03, 0.10),   # windthrow chance per storm, 20 m tree, low wind resistance
    "wind_med":     (0.01, 0.04),
    "wind_high":    (0.004, 0.015), # high wind resistance (Douglas-fir on well-drained soil) (J)
    "shade_growth": (0.4, 0.8),     # growth lost by a shade-intolerant young tree fully under taller crowns (J)
    "shade_mort":   (0.01, 0.04),   # added yearly mortality for the same tree (J)
    "snow_dmg":     (0.05, 0.20),   # chance of top/branch breakage in a heavy snow year, low snow resistance
    "p_dry0":       (0.20, 0.30),   # dry summer probability now (YVR 1990-2025: 0.25)
    "p_dry50":      (0.30, 0.45),   # by year 50
    "p_heat0":      (0.12, 0.22),
    "p_heat50":     (0.25, 0.50),   # J: rises with warming
    "p_wind":       (0.08, 0.14),
    "p_wind_x":     (0.01, 0.03),   # extreme storm (Stanley Park 2006 scale)
    "p_snow":       (0.25, 0.35),
    "p_ivy":        (0.10, 0.30),   # arrival at an edge cell group per year (J)
    "ivy_spread":   (0.2, 0.6),     # chance per year that an invaded cell spreads to each neighbour (about 0.2-0.6 m/yr at 1 m)
    "p_trample":    (0.3, 0.6),     # J
    "p_cut":        (0.05, 0.10),   # maintenance budget cut starts (J)
    "shelter":      (0.5, 0.8),     # establishing-mortality factor for conifers under an alder nurse crop (J)
    "shrub_dry":    (0.10, 0.30),   # cover lost by drought-sensitive shrubs in an unwatered dry summer (J)
    "rescue":       (0.3, 0.6),     # share of established-tree drought losses left when they are watered in dry summers (J)
    "lift_left":    (0.4, 0.7),     # share of a tree's shade left over the shrub patches after its crown is lifted (J)
}

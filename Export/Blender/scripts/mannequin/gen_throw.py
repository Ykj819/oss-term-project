
import bpy
g = {}; exec(bpy.data.texts['fishman_helpers.py'].as_string(), g)
V = g['V']
# ---------------- one-hand overarm rock throw (right hand), 60 fps, ~0.55 release
WIND = dict(pel=V((0, 0.10, -0.14)), spine=-6.0, spine_twist=-28.0, neck=-10.0,
            al=V((0.22, -0.22, 0.094)), kl=V((0.5, -1.5, 0.5)),
            hl=V((0.20, -0.45, 1.30)), Kl=V((0, -1, 0)), Nl=V((1, 0, 0.3)), el=V((0.8, 0.0, 1.2)), pol_l=0.0,
            hr=V((-0.38, 0.38, 1.70)), Kr=V((0, 0, 1)), Nr=V((0, 1, 0)), er=V((-0.8, 0.5, 1.3)), pol_r=-90.0)
COCK = dict(WIND, spine=-10.0, spine_twist=-34.0, hr=V((-0.36, 0.45, 1.66)))
REL = dict(pel=V((0, -0.02, -0.16)), spine=24.0, spine_twist=18.0, neck=-16.0,
           al=V((0.22, -0.22, 0.094)), kl=V((0.5, -1.5, 0.5)),
           hl=V((0.32, 0.05, 0.95)), Kl=V((0, -1, 0)), Nl=V((1, 0, 0)), el=V((0.8, 0.6, 1.1)), pol_l=0.0,
           hr=V((-0.16, -0.62, 1.45)), Kr=V((1, 0, 0)), Nr=V((0, 0, 1)), er=V((-0.8, 0.0, 1.6)), pol_r=-90.0)
FOLLOW = dict(REL, spine=34.0, spine_twist=26.0, neck=-22.0,
              hr=V((0.10, -0.45, 0.80)), Kr=V((0, -1, 0)), Nr=V((-1, 0, 0)), er=V((-0.7, 0.2, 1.0)))
THROW = [(1, {}), (26, WIND), (36, COCK), (44, REL), (54, FOLLOW), (70, dict(FOLLOW, spine=26.0)), (96, {})]
act = g['make']('MM_Throw', THROW)
print('ok', act.frame_range[:])

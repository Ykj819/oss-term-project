import bpy

g = {}; exec(bpy.data.texts['fishman_helpers.py'].as_string(), g)
V = g['V']
# ---------------- two-hand overhead slam (150 f)
UP = dict(pel=V((0, 0.06, -0.04)), spine=-14.0, neck=-18.0,
          hl=V((0.07, 0.02, 2.05)), Kl=V((-1, 0, 0)), Nl=V((0, 1, 0.3)), el=V((0.7, -0.3, 1.7)), pol_l=0.0,
          hr=V((-0.07, 0.02, 2.05)), Kr=V((1, 0, 0)), Nr=V((0, 1, 0.3)), er=V((-0.7, -0.3, 1.7)), pol_r=0.0)
DOWN = dict(pel=V((0, 0.16, -0.50)), spine=82.0, neck=-40.0, kl=V((0.6, -1.5, 0.5)), kr=V((-0.6, -1.5, 0.5)),
          hl=V((0.09, -0.66, 0.12)), Kl=V((-1, 0, 0)), Nl=V((0, -1, 0.6)), el=V((0.8, 0.2, 1.0)), pol_l=0.0,
          hr=V((-0.09, -0.66, 0.12)), Kr=V((1, 0, 0)), Nr=V((0, -1, 0.6)), er=V((-0.8, 0.2, 1.0)), pol_r=0.0)
SLAM = [(1, {}), (50, UP), (64, dict(UP, spine=-18.0)), (74, DOWN), (110, dict(DOWN, spine=78.0)), (150, {})]

# ---------------- jump in place, land with an area shockwave (140 f)
def arms(hl, hr, Kl=V((0, -1, 0)), Kr=V((0, -1, 0)), Nl=V((1, 0, 0)), Nr=V((-1, 0, 0)), el=V((0.8, 0.5, 1.0)), er=None):
    er = er or V((-el.x, el.y, el.z))
    return dict(hl=hl, hr=hr, Kl=Kl, Kr=Kr, Nl=Nl, Nr=Nr, el=el, er=er, pol_l=0.0, pol_r=0.0)
CROUCH = dict(pel=V((0, 0.08, -0.40)), spine=38.0, neck=-30.0, **arms(V((0.32, 0.30, 0.62)), V((-0.32, 0.30, 0.62)), el=V((0.6, 0.2, 1.4))))
TAKEOFF = dict(pel=V((0, 0.0, 0.12)), spine=4.0, neck=-14.0, al=V((0.20, -0.02, 0.17)), ar=V((-0.20, 0.02, 0.17)), pl=35.0, pr=29.0,
               **arms(V((0.30, -0.25, 1.75)), V((-0.30, -0.25, 1.75)), Kl=V((0, 0, 1)), Kr=V((0, 0, 1)), el=V((0.9, 0.3, 1.6))))
PEAK = dict(pel=V((0, 0.0, 0.50)), spine=10.0, neck=-16.0, al=V((0.22, 0.04, 0.50)), ar=V((-0.22, 0.06, 0.52)), pl=25.0, pr=19.0,
            kl=V((0.5, -1.5, 1.2)), kr=V((-0.5, -1.5, 1.2)),
            **arms(V((0.28, -0.20, 2.25)), V((-0.28, -0.20, 2.25)), Kl=V((0, 0, 1)), Kr=V((0, 0, 1)), Nl=V((0, 1, 0)), Nr=V((0, 1, 0)), el=V((0.9, 0.0, 2.0))))
FALL = dict(PEAK, pel=V((0, 0.02, 0.18)), al=V((0.24, -0.02, 0.16)), ar=V((-0.24, 0.0, 0.16)), pl=12.0, pr=6.0, kl=V((0.5, -1.5, 0.5)), kr=V((-0.5, -1.5, 0.5)))
LAND = dict(pel=V((0, 0.10, -0.46)), spine=48.0, neck=-34.0, al=V((0.26, -0.06, 0.094)), ar=V((-0.26, -0.02, 0.094)), kl=V((0.8, -1.5, 0.5)), kr=V((-0.8, -1.5, 0.5)),
            **arms(V((0.42, -0.42, 0.14)), V((-0.42, -0.42, 0.14)), Kl=V((0, -1, 0)), Kr=V((0, -1, 0)), Nl=V((0.3, -0.2, 1)), Nr=V((-0.3, -0.2, 1)), el=V((1.0, 0.3, 1.2))))
JUMP = [(1, {}), (32, CROUCH), (42, TAKEOFF), (56, PEAK), (66, FALL), (72, LAND), (106, dict(LAND, spine=44.0)), (140, {})]

# ---------------- stomp with one foot (120 f); side +1 = right foot, -1 = left foot
def stomp(side):
    x = -side   # right is -X
    s_, o_ = ('r', 'l') if side > 0 else ('l', 'r')
    def legs(stomp_ankle, pitch, knee):
        d = {'a'+s_: stomp_ankle, 'p'+s_: pitch, 'k'+s_: knee}
        return d
    def hands(h_same, h_other, el_same, el_other):
        d = {}
        d['h'+s_] = h_same; d['h'+o_] = h_other
        d['e'+s_] = el_same; d['e'+o_] = el_other
        d['K'+s_] = V((0, -1, 0)); d['K'+o_] = V((0, -1, 0))
        d['N'+s_] = V((x, 0, 0)); d['N'+o_] = V((-x, 0, 0))
        d['pol_l'] = 0.0; d['pol_r'] = 0.0
        return d
    base_pitch = -6.0 if s_ == 'r' else 0.0
    LIFT = dict(pel=V((-x * 0.08, 0.04, -0.06)), spine=4.0, neck=-14.0,
                **legs(V((x * 0.18, -0.20, 0.62)), base_pitch - 35.0, V((x * 0.4, -1.5, 1.3))),
                **hands(V((x * 0.48, -0.25, 1.10)), V((-x * 0.50, -0.02, 1.05)), V((x * 0.9, 0.5, 1.2)), V((-x * 0.9, 0.5, 1.2))))
    TOP = dict(LIFT, spine=0.0, **legs(V((x * 0.18, -0.24, 0.68)), base_pitch - 40.0, V((x * 0.4, -1.5, 1.4))))
    STOMP = dict(pel=V((x * 0.02, 0.06, -0.30)), spine=30.0, neck=-28.0,
                 **legs(V((x * 0.21, -0.50, 0.094)), base_pitch, V((x * 0.5, -1.5, 0.6))),
                 **hands(V((x * 0.36, -0.40, 0.62)), V((-x * 0.40, -0.25, 0.66)), V((x * 0.9, 0.4, 1.1)), V((-x * 0.9, 0.4, 1.1))))
    BACK = dict(pel=V((-x * 0.04, 0.03, -0.12)), spine=16.0, **legs(V((x * 0.20, -0.22, 0.20)), base_pitch, V((x * 0.5, -1.5, 0.6))))
    return [(1, {}), (34, LIFT), (46, TOP), (54, STOMP), (90, dict(STOMP, spine=26.0)), (106, BACK), (120, {})]
STOMP_R = stomp(1); STOMP_L = stomp(-1)

"""Authentic routing trace — converged tree, loop, dead-end, ECMP, latency, protocol-agnostic.

Destinations are SUBNETS, not routers: nobody asks whether R1 reaches R2, they ask whether a
host on one network reaches a host on another. So the leaf routers here own a subnet of their
own, which is also what a real leaf router is FOR -- it exists to serve the hosts behind it.
A router owning no unique subnet is not a separate destination, because from upstream it is
just another address on a segment already being traced.
"""
from gini.domain.routetable import RouteEntry
from gini.domain.routing_model import (
    Edge, RouterNode, RoutingModel, assemble_model, collect_router_data, forwarding_tree,
    hop_latency, parse_delay_base, parse_iface_ips,
)


def _r(index, net, mask, nh, iface="tun0"):
    return RouteEntry(index, net, mask, nh, iface)


# A 3-router line: R1 —(5ms)— R2 —(10ms)— R3
#   transit: 10.0.1.0/24 (R1,R2), 10.0.2.0/24 (R2,R3);  R3 serves 10.0.3.0/24
FAR = "10.0.3.0/24"                      # the subnet only R3 can deliver
def _line_model(r1_table=None):
    R1 = RouterNode("R1", "R1", {"10.0.1.1"}, r1_table or [
        _r(0, "10.0.1.0", "255.255.255.0", "0.0.0.0"),                 # direct
        _r(1, "10.0.2.0", "255.255.255.0", "10.0.1.2"),                # via R2
        _r(2, "10.0.3.0", "255.255.255.0", "10.0.1.2"),                # via R2
    ])
    R2 = RouterNode("R2", "R2", {"10.0.1.2", "10.0.2.1"}, [
        _r(0, "10.0.1.0", "255.255.255.0", "0.0.0.0"),
        _r(1, "10.0.2.0", "255.255.255.0", "0.0.0.0"),
        _r(2, "10.0.3.0", "255.255.255.0", "10.0.2.2"),                # via R3
    ])
    R3 = RouterNode("R3", "R3", {"10.0.2.2", "10.0.3.1"}, [
        _r(0, "10.0.2.0", "255.255.255.0", "0.0.0.0"),
        _r(1, "10.0.3.0", "255.255.255.0", "0.0.0.0"),                 # R3's own hosts
    ])
    edges = [Edge("R1", "R2", 5), Edge("R2", "R3", 10)]
    return RoutingModel([R1, R2, R3], edges)


def test_converged_tree_and_latency():
    m = _line_model()
    t = forwarding_tree(m, "R1")
    p = t.per_dest[FAR]
    assert p.status == "ok" and p.path == ["R1", "R2", "R3"] and p.hop_count == 2
    assert p.total_latency == 15                          # 5 + 10, configured delay-VNF values
    assert ("R1", "R2") in t.edges_used and ("R2", "R3") in t.edges_used
    assert not t.loops and not t.deadends


def test_deadend_when_no_route():
    # R1 can reach R2's segment but has no route to R3's subnet (and no default) -> black hole
    m = _line_model(r1_table=[_r(0, "10.0.1.0", "255.255.255.0", "0.0.0.0"),
                              _r(1, "10.0.2.0", "255.255.255.0", "10.0.1.2")])
    t = forwarding_tree(m, "R1")
    assert t.per_dest[FAR].status == "deadend" and FAR in t.deadends
    assert t.per_dest[FAR].path == []                    # R1 drops it — no path
    assert ("R1", "R2") in t.edges_used                  # R2's segment is still reachable
    # ...and so is R3 itself, at 10.0.2.2 on that segment: R2 delivers to it. Its LAN behind it
    # is the dead end, which the panel names (_unreached_text) -- the router is not.
    assert ("R2", "R3") in t.edges_used


def test_forwarding_loop_is_detected():
    # R1 and R2 each point at the other for 10.0.9.9 -> a loop (RIP mid-convergence)
    R1 = RouterNode("R1", "R1", {"10.0.1.1"},
                    [_r(0, "10.0.9.0", "255.255.255.0", "10.0.1.2")])   # via R2
    R2 = RouterNode("R2", "R2", {"10.0.1.2"},
                    [_r(0, "10.0.9.0", "255.255.255.0", "10.0.1.1")])   # via R1
    phantom = RouterNode("R9", "R9", {"10.0.9.9"}, [])                  # the unreachable dest
    m = RoutingModel([R1, R2, phantom], [Edge("R1", "R2", 5)])
    t = forwarding_tree(m, "R1")
    assert t.per_dest["R9"].status == "loop" and "R9" in t.loops
    assert ("R1", "R2") in t.edges_used and ("R2", "R1") in t.edges_used   # the cycle is highlighted


def test_ecmp_becomes_a_dag():
    # R1 has two equal /24 routes to R4's subnet — via R2 and via R3 (both on 10.0.1.0/24)
    R1 = RouterNode("R1", "R1", {"10.0.1.1"}, [
        _r(0, "10.0.1.0", "255.255.255.0", "0.0.0.0"),
        _r(1, "10.0.4.0", "255.255.255.0", "10.0.1.2"),                # via R2
        _r(2, "10.0.4.0", "255.255.255.0", "10.0.1.3"),                # via R3  (equal cost)
    ])
    R2 = RouterNode("R2", "R2", {"10.0.1.2", "10.0.4.1"},
                    [_r(0, "10.0.4.0", "255.255.255.0", "0.0.0.0")])
    R3 = RouterNode("R3", "R3", {"10.0.1.3", "10.0.4.2"},
                    [_r(0, "10.0.4.0", "255.255.255.0", "0.0.0.0")])
    R4 = RouterNode("R4", "R4", {"10.0.4.9"}, [])
    m = RoutingModel([R1, R2, R3, R4], [Edge("R1", "R2", 3), Edge("R1", "R3", 8)],
                     dest_ip={"R4": "10.0.4.9"})
    t = forwarding_tree(m, "R1")
    far = "10.0.4.0/24"                                 # the subnet both R2 and R3 can deliver
    assert far in t.ecmp
    assert ("R1", "R2") in t.edges_used and ("R1", "R3") in t.edges_used   # both parallels highlighted
    # the representative path takes the lower-latency next-hop (R2, 3ms < 8ms)
    assert t.per_dest[far].path[1] == "R2"


def test_parse_iface_ips_both_formats():
    sim = "  eth0  10.0.1.1/24  aa:bb:cc:dd:ee:ff\n  eth1  10.0.2.1/24  aa:bb:cc:dd:ee:00"
    assert parse_iface_ips(sim) == {"10.0.1.1", "10.0.2.1"}
    real = "tun0: inet 10.0.5.9 netmask 255.255.255.0\ntun1: inet 10.0.6.1 netmask 255.255.255.0"
    assert parse_iface_ips(real) == {"10.0.5.9", "10.0.6.1"}   # netmasks excluded
    assert parse_iface_ips("") == set()


def test_parse_delay_base_and_hop_latency():
    assert parse_delay_base("50 5 0.90") == 50 and parse_delay_base("12 ms") == 12
    assert parse_delay_base("") is None and parse_delay_base(None) is None
    assert hop_latency(20, 5) == 25 and hop_latency(None, None) is None
    assert hop_latency(None, 7) == 7                    # missing side counts as 0


def test_assemble_model_from_cli_text_and_trace():
    r1_routes = "[0] 10.0.1.0 255.255.255.0 0.0.0.0 tun0\n[1] 10.0.2.0 255.255.255.0 10.0.1.2 tun0"
    r2_routes = "[0] 10.0.1.0 255.255.255.0 0.0.0.0 tun0\n[1] 10.0.2.0 255.255.255.0 0.0.0.0 tun1"
    r3_routes = "[0] 10.0.2.0 255.255.255.0 0.0.0.0 tun0\n[1] 10.0.3.0 255.255.255.0 0.0.0.0 tun1"
    r1_routes += "\n[2] 10.0.3.0 255.255.255.0 10.0.1.2 tun0"
    r2_routes += "\n[2] 10.0.3.0 255.255.255.0 10.0.2.2 tun1"
    infos = [("R1", "R1", r1_routes, "eth0 10.0.1.1/24 m"),
             ("R2", "R2", r2_routes, "eth0 10.0.1.2/24 m\neth1 10.0.2.1/24 m"),
             ("R3", "R3", r3_routes, "eth0 10.0.2.2/24 m\neth1 10.0.3.1/24 m")]
    lat = {("R1", "R2"): 5, ("R2", "R3"): 10}
    m = assemble_model(infos, [("R1", "R2"), ("R2", "R3")],
                       latency_of=lambda a, b: lat.get((a, b)) or lat.get((b, a)))
    assert m.ip_owner["10.0.1.2"] == "R2" and m.ip_owner["10.0.2.2"] == "R3"
    t = forwarding_tree(m, "R1")
    assert t.per_dest["10.0.3.0/24"].path == ["R1", "R2", "R3"]
    assert t.per_dest["10.0.3.0/24"].total_latency == 15


def test_collect_router_data_via_injected_callbacks():
    routes = {"R1": "[0] 10.0.1.0 255.255.255.0 0.0.0.0 tun0\n"
                    "[1] 10.0.2.0 255.255.255.0 10.0.1.2 tun0",
              "R2": "[0] 10.0.2.0 255.255.255.0 0.0.0.0 tun0"}
    ifaces = {"R1": "eth0 10.0.1.1/24 m", "R2": "eth0 10.0.1.2/24 m\neth1 10.0.2.2/24 m"}
    props = {("R1", "DelayEgress"): "8 1 0.9", ("R2", "DelayIngress"): "2 0 0"}

    def query(name, cmd):
        return routes[name] if "route" in cmd else ifaces[name]

    # links omitted → adjacency derived from the live connected routes
    m = collect_router_data([("R1", "R1"), ("R2", "R2")], query,
                            lambda rid, k: props.get((rid, k), ""))
    assert m.ip_owner["10.0.1.2"] == "R2"
    assert m.edge_latency("R1", "R2") == 10             # egress 8 + ingress 2 (configured delay VNF)
    assert forwarding_tree(m, "R1").per_dest["10.0.2.0/24"].status == "ok"


def test_derive_edges_handles_switch_mediated_adjacency():
    # R1 and R2 share segment 10.0.1.0/24 (via a switch — no direct link); each has a connected route
    R1 = RouterNode("R1", "R1", {"10.0.1.1"},
                    [_r(0, "10.0.1.0", "255.255.255.0", "0.0.0.0")])
    R2 = RouterNode("R2", "R2", {"10.0.1.2"},
                    [_r(0, "10.0.1.0", "255.255.255.0", "0.0.0.0")])
    R3 = RouterNode("R3", "R3", {"10.0.9.9"},                          # off on its own segment
                    [_r(0, "10.0.9.0", "255.255.255.0", "0.0.0.0")])
    from gini.domain.routing_model import derive_edges
    pairs = {frozenset((e.a, e.b)) for e in derive_edges([R1, R2, R3])}
    assert frozenset(("R1", "R2")) in pairs             # share 10.0.1.0/24 → adjacent
    assert frozenset(("R1", "R3")) not in pairs         # different segments → not adjacent


def test_trace_is_protocol_agnostic():
    # SAME topology, DIFFERENT tables -> the trace faithfully follows whatever the router believes.
    # RIP (hop-count) picks the 2-hop path via R2; OSPF (cost) picks the 3-hop low-latency path via R3.
    def model(r1_route):
        R1 = RouterNode("R1", "R1", {"10.0.1.1", "10.0.7.1"}, [
            _r(0, "10.0.1.0", "255.255.255.0", "0.0.0.0"),
            _r(1, "10.0.7.0", "255.255.255.0", "0.0.0.0"),
            r1_route,
        ])
        R2 = RouterNode("R2", "R2", {"10.0.1.2", "10.0.9.1"},
                        [_r(0, "10.0.9.0", "255.255.255.0", "0.0.0.0")])
        R3 = RouterNode("R3", "R3", {"10.0.7.2", "10.0.8.1"},
                        [_r(0, "10.0.9.0", "255.255.255.0", "10.0.8.2")])
        R4 = RouterNode("R4", "R4", {"10.0.8.2", "10.0.9.2"},
                        [_r(0, "10.0.9.0", "255.255.255.0", "0.0.0.0")])
        edges = [Edge("R1", "R2", 50), Edge("R1", "R3", 1), Edge("R3", "R4", 1)]
        return RoutingModel([R1, R2, R3, R4], edges)
    far = "10.0.9.0/24"                                  # reachable via R2 OR via R3->R4
    rip = forwarding_tree(model(_r(2, "10.0.9.0", "255.255.255.0", "10.0.1.2")), "R1")   # via R2
    ospf = forwarding_tree(model(_r(2, "10.0.9.0", "255.255.255.0", "10.0.7.2")), "R1")  # via R3
    assert rip.per_dest[far].path == ["R1", "R2"]        # RIP: 1 hop, but 50ms
    assert ospf.per_dest[far].path == ["R1", "R3", "R4"]  # OSPF: more hops, but 1+1ms


# -- a router reached at the end of a delivery (R1-R3 failed; RIP via R2) ----------------------- #
# The real `route show` / `ifconfig show` of the maintainer's lab, read off live routers after the
# cheap R1-R3 link failed and RIP converged: R1 -- 5 -- R2 -- 1 -- R3, the R1-R3 link down at
# both ends. R3 has no LAN; its only live subnet is the R2-R3 link, which R2 has connected.
_HDR = ("Index\tNetwork\t\tNetmask\t\tNexthop\t\tInterface\tOrigin \n")
_R1_ROUTES = _HDR + ("[0]\t10.0.3.0\t255.255.255.0\t10.0.2.2\t\ttun2\tD\n"
                     "[1]\t10.0.2.0\t255.255.255.0\t0.0.0.0\t\ttun2\tC\n"
                     "[2]\t10.0.4.0\t255.255.255.0\t0.0.0.0\t\ttun3\tC\n"
                     "[3]\t10.0.6.0\t255.255.255.0\t0.0.0.0\t\ttun4\tC\n"
                     "[4]\t10.0.5.0\t255.255.255.0\t10.0.2.2\t\ttun2\tD\n")
_R2_ROUTES = _HDR + ("[0]\t10.0.2.0\t255.255.255.0\t0.0.0.0\t\ttun1\tC\n"
                     "[1]\t10.0.3.0\t255.255.255.0\t0.0.0.0\t\ttun2\tC\n"
                     "[2]\t10.0.5.0\t255.255.255.0\t0.0.0.0\t\ttun3\tC\n"
                     "[3]\t10.0.4.0\t255.255.255.0\t10.0.2.1\t\ttun1\tD\n"
                     "[4]\t10.0.6.0\t255.255.255.0\t10.0.2.1\t\ttun1\tD\n")
_R3_ROUTES = _HDR + ("[0]\t10.0.3.0\t255.255.255.0\t0.0.0.0\t\ttun2\tC\n"
                     "[1]\t10.0.2.0\t255.255.255.0\t10.0.3.2\t\ttun2\tD\n"
                     "[2]\t10.0.4.0\t255.255.255.0\t10.0.3.2\t\ttun2\tD\n"
                     "[3]\t10.0.5.0\t255.255.255.0\t10.0.3.2\t\ttun2\tD\n"
                     "[4]\t10.0.6.0\t255.255.255.0\t10.0.3.2\t\ttun2\tD\n")
_IFHDR = "Device\tState\tIP address\tMAC address\t\tMTU\tCost\n"
_R1_IF = _IFHDR + ("tun1\tD\t10.0.1.2\t02:00:00:01:01:01\t1500\t3\n"
                   "tun2\tU\t10.0.2.1\t02:00:00:02:01:02\t1500\t5\n"
                   "tun3\tU\t10.0.4.1\t02:00:00:04:01:03\t1500\t10\n"
                   "tun4\tU\t10.0.6.1\t02:00:00:06:01:04\t1500\t1\n")
_R2_IF = _IFHDR + ("tun1\tU\t10.0.2.2\t02:00:00:02:01:05\t1500\t5\n"
                   "tun2\tU\t10.0.3.2\t02:00:00:03:01:06\t1500\t1\n"
                   "tun3\tU\t10.0.5.1\t02:00:00:05:01:07\t1500\t3\n")
_R3_IF = _IFHDR + ("tun1\tD\t10.0.1.1\t02:00:00:01:01:08\t1500\t3\n"
                   "tun2\tU\t10.0.3.1\t02:00:00:03:01:09\t1500\t1\n")


def _failed_triangle(r1_routes=_R1_ROUTES):
    from gini.domain.routing_model import assemble_model
    return assemble_model([("r1", "R1", r1_routes, _R1_IF), ("r2", "R2", _R2_ROUTES, _R2_IF),
                           ("r3", "R3", _R3_ROUTES, _R3_IF)])


def test_a_down_interface_is_read_as_down():
    from gini.domain.routing_model import parse_iface_down
    assert parse_iface_down(_R1_IF) == {"10.0.1.2"}
    assert parse_iface_down("10.0.1.1/24 eth0") == set()      # no state column: assume up


def _rows(*rows):
    return _HDR + "".join(f"[{i}]\t{n}\t255.255.255.0\t{nh}\t\t{dev}\t{o}\n"
                          for i, (n, nh, dev, o) in enumerate(rows))


_ALL_UP = {"r1": _R1_IF.replace("tun1\tD", "tun1\tU"), "r2": _R2_IF,
           "r3": _R3_IF.replace("tun1\tD", "tun1\tU")}


def _triangle(r1, r2, r3, ifs=None):
    from gini.domain.routing_model import assemble_model
    ifs = ifs or _ALL_UP
    return assemble_model([("r1", "R1", r1, ifs["r1"]), ("r2", "R2", r2, ifs["r2"]),
                           ("r3", "R3", r3, ifs["r3"])])


def test_after_the_failure_the_path_to_r3_goes_through_r2():
    """R3's only live subnet is the R2-R3 link, which R2 has connected. A packet from R1 to R3
    crosses R2 -> R3, so that hop is lit: the tree used to stop at R2 and R3 looked cut off."""
    from gini.domain.routing_model import trace
    tr = trace(_failed_triangle(), "r1")
    assert tr.edges_used == {("r1", "r2"), ("r2", "r3")}
    assert not tr.deadends


def test_a_costlier_direct_link_leaves_r1_r3_dark_and_lights_the_way_round():
    """The maintainer's case: R1 is wired to both, the R1-R3 link's cost goes up, and RIP sends
    R1 to R3's side through R2. The direct link is still up -- R1 has its subnet connected -- but
    the picture shows the way the routes go: R1 -> R2 -> R3."""
    from gini.domain.routing_model import trace
    r1 = _rows(("10.0.1.0", "0.0.0.0", "tun1", "C"), ("10.0.2.0", "0.0.0.0", "tun2", "C"),
               ("10.0.4.0", "0.0.0.0", "tun3", "C"), ("10.0.6.0", "0.0.0.0", "tun4", "C"),
               ("10.0.3.0", "10.0.2.2", "tun2", "D"), ("10.0.5.0", "10.0.2.2", "tun2", "D"))
    r3 = _rows(("10.0.1.0", "0.0.0.0", "tun1", "C"), ("10.0.3.0", "0.0.0.0", "tun2", "C"))
    tr = trace(_triangle(r1, _R2_ROUTES, r3), "r1")
    assert tr.edges_used == {("r1", "r2"), ("r2", "r3")}


def test_the_direct_link_lights_when_it_is_the_only_way():
    from gini.domain.routing_model import trace
    r1 = _rows(("10.0.1.0", "0.0.0.0", "tun1", "C"), ("10.0.2.0", "0.0.0.0", "tun2", "C"))
    r2 = _rows(("10.0.2.0", "0.0.0.0", "tun1", "C"))
    r3 = _rows(("10.0.1.0", "0.0.0.0", "tun1", "C"))
    tr = trace(_triangle(r1, r2, r3), "r1")
    assert tr.edges_used == {("r1", "r2"), ("r1", "r3")}


def test_the_cheap_detour_lights_and_the_dear_direct_link_does_not():
    """Before the failure: R1 reaches everything of R2's through R3 (3 + 1 < 5). R1 -> R3 -> R2,
    and the direct R1 -- R2 link, though connected, stays dark."""
    from gini.domain.routing_model import trace
    r1 = _rows(("10.0.1.0", "0.0.0.0", "tun1", "C"), ("10.0.2.0", "0.0.0.0", "tun2", "C"),
               ("10.0.3.0", "10.0.1.1", "tun1", "D"), ("10.0.5.0", "10.0.1.1", "tun1", "D"))
    r3 = _rows(("10.0.1.0", "0.0.0.0", "tun1", "C"), ("10.0.3.0", "0.0.0.0", "tun2", "C"),
               ("10.0.5.0", "10.0.3.2", "tun2", "D"))
    tr = trace(_triangle(r1, _R2_ROUTES, r3), "r1")
    assert tr.edges_used == {("r1", "r3"), ("r3", "r2")}


def test_a_failed_links_address_does_not_count_as_reached():
    """R3's dead tun1 sits in 10.0.1.0/24. Were that subnet still around (another router had it
    connected), R3 must not light through an interface that is down."""
    from gini.domain.routing_model import trace
    extra = _R1_ROUTES + "[5]\t10.0.1.0\t255.255.255.0\t0.0.0.0\t\ttun1\tC\n"
    m = _failed_triangle(extra)
    m.routers["r3"].table = [e for e in m.routers["r3"].table if e.network != "10.0.3.0"]
    m.routers["r2"].table = [e for e in m.routers["r2"].table if e.network != "10.0.3.0"]
    assert not any("r3" in e for e in trace(m, "r1").edges_used)


def test_before_rip_the_message_names_what_is_missing():
    """R1 with only its connected routes: it reaches its own subnets and nothing beyond. The HUD
    used to say "nothing reachable from here", the opposite of the truth."""
    from gini.domain.routing_model import trace
    from gini.ui.routing_hud import _unreached_text
    only_connected = _HDR + "".join(l + "\n" for l in _R1_ROUTES.splitlines()[1:]
                                    if l.endswith("\tC"))
    tr = trace(_failed_triangle(only_connected), "r1")
    assert tr.edges_used == {("r1", "r2")}             # R2 is reached, across their own link
    assert tr.deadends == {"10.0.3.0/24", "10.0.5.0/24"}
    assert _unreached_text(tr) == "only its own subnets — no route to 10.0.3.0/24, 10.0.5.0/24"


def test_some_routes_and_some_dead_ends_says_which_are_missing():
    from gini.domain.routing_model import trace
    from gini.ui.routing_hud import _unreached_text
    partial = _R1_ROUTES.replace("[4]\t10.0.5.0\t255.255.255.0\t10.0.2.2\t\ttun2\tD\n", "")
    tr = trace(_failed_triangle(partial), "r1")
    assert tr.deadends == {"10.0.5.0/24"}
    assert _unreached_text(tr) == "no route to 10.0.5.0/24"

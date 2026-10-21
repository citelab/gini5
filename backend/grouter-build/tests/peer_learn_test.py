#!/usr/bin/env python3
"""End-to-end: a tun link whose peer was unknown at start comes up when the peer speaks first,
and follows a peer that moves.

  A 10.0.1.10  <-->  tun1 10.0.1.1 [ R ] 10.0.2.1 tun2  <-->  B 10.0.2.10

tun1 is configured `-dstip 0.0.0.0 -dstport 1`: a peer whose container name Docker DNS did not
know when the router started, as run_grouter.py now writes one. Before this the router kept
that first guess for ever (and the guess used to be sscanf garbage), so the interface received
every frame A sent and answered into the void -- the "every route points one way, pings never
come back, works sometimes" lab. Now the peer's observed source address re-aims the link.

  GROUTER_BIN=/path/to/grouter python3 peer_learn_test.py
"""
import sys
import time

from gini_tun import ROUTER_IP, GRouter, Host

TUN1_LOCAL, A_BIND = 24001, 24002       # tun1 <-> host A
TUN2_LOCAL, B_BIND = 24003, 24004       # tun2 <-> host B
B2_BIND = 24006                          # where B comes back after a "restart"

CONFIG = f"""# tun1's peer is unknown at start; tun2's is right
ifconfig add tun1 -dstip 0.0.0.0 -dstport 1 -addr 10.0.1.1 -hwaddr 02:00:00:00:01:01 -mtu 1400 -srcport {TUN1_LOCAL}
ifconfig add tun2 -dstip {ROUTER_IP} -dstport {B_BIND} -addr 10.0.2.1 -hwaddr 02:00:00:00:02:01 -mtu 1400 -srcport {TUN2_LOCAL}
route add -dev tun1 -net 10.0.1.0 -netmask 255.255.255.0
route add -dev tun2 -net 10.0.2.0 -netmask 255.255.255.0
"""


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail and not ok else ""))
    return ok


def wait_for(pred, secs=3.0):
    t0 = time.time()
    while time.time() - t0 < secs:
        if pred():
            return True
        time.sleep(0.1)
    return pred()


def main():
    R = GRouter("pl", CONFIG)
    time.sleep(1.5)
    if not R.alive():
        print("ROUTER EXITED EARLY\n" + R.tail())
        return 1
    A = Host("A", "10.0.1.10", "02:00:00:aa:00:10", "10.0.1.1", A_BIND, TUN1_LOCAL)
    B = Host("B", "10.0.2.10", "02:00:00:bb:00:10", "10.0.2.1", B_BIND, TUN2_LOCAL)
    time.sleep(0.3)
    ok = True
    try:
        print("[1] the unknown peer speaks first: its ARP request teaches the router where it is")
        ok &= check("A resolves its gateway through tun1", A.resolve() is not None)
        B.resolve()
        A.ping("10.0.2.10", ident=1)
        ok &= check("B received A's echo request",
                    wait_for(lambda: any(s == "10.0.1.10" for s, _t in B.echo_requests)))
        ok &= check("A received B's echo reply, back through the re-aimed tun1",
                    wait_for(lambda: any(s == "10.0.2.10" and i == 1
                                         for s, _t, i, _q in A.echo_replies)))

        print("[2] a peer that moves (a restarted container has a new address)")
        B.stop(); time.sleep(0.5); B.s.close()
        B2 = Host("B2", "10.0.2.10", "02:00:00:bb:00:10", "10.0.2.1", B2_BIND, TUN2_LOCAL)
        time.sleep(0.3)
        ok &= check("B, from its new port, resolves its gateway", B2.resolve() is not None)
        A.ping("10.0.2.10", ident=2)
        ok &= check("the echo request reached B at its NEW port",
                    wait_for(lambda: any(s == "10.0.1.10" for s, _t in B2.echo_requests)))
        ok &= check("and A got the reply",
                    wait_for(lambda: any(i == 2 for _s, _t, i, _q in A.echo_replies)))
        B2.stop()
    finally:
        log = R.tail()
        R.stop(); A.stop()
    print()
    if ok:
        print("RESULT: PASS — an unresolved peer comes up when it speaks first, and a link "
              "follows a peer that moves.")
        return 0
    print("RESULT: FAIL")
    print("--- router log ---\n" + log[-1500:])
    return 1


if __name__ == "__main__":
    sys.exit(main())

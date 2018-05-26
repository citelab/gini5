
#ifndef __FRAGMENT_H__
#define __FRAGMENT_H__

int fragmentIPPacket(gpacket_t *pkt, gpacket_t **frags);
void deallocateFragments(gpacket_t **pkt_frags, int num_frags);

#endif

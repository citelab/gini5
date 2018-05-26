/*
 * protocols.h (include file for protocol definitions)
 * AUTHOR: Muthucumaru Maheswaran
 * DATE: December 16, 2004
 * VERSION: 1.0
 *
 */

#ifndef __PROTOCOLS_H__
#define __PROTOCOLS_H__

// Ethertypes
#define ARP_PROTOCOL            0x0806
#define IP_PROTOCOL             0x0800
#define ETHERNET_PROTOCOL       0x0001

// IP protocols
#define ICMP_PROTOCOL           1
#define TCP_PROTOCOL            6
#define UDP_PROTOCOL            17

// Other constants
#define IEEE_802_2_DSAP_SNAP    0xAA
#define IEEE_802_2_CTRL_8_BITS  0x03
#define ETHERTYPE_IEEE_802_1Q   0x8100

#endif

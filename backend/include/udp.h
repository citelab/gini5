/**
 * udp.h (header file for User Datagram Protocol (UDP))
 *
 * @author Michael Kourlas
 * @date November 9, 2015
 */

#ifndef __UDP_H_
#define __UDP_H_

#include <stdint.h>

#include "ip.h"

/**
 * UDP packet definition adapted from <netinet/udp.h>.
 */
typedef struct {
	// Source port
	uint16_t	src_port;
	// Destination port
	uint16_t	dst_port;
	// UDP length (in bytes)
	uint16_t	length;
	// UDP checksum
	uint16_t	checksum;
} udp_packet_type;

/**
 * UDP pseudo-header used to calculate checksums.
 */
typedef struct {
	// IP source address
	uint32_t	ip_src;
	// IP destination address
	uint32_t	ip_dst;
	// Reserved
	uint8_t		reserved;
	// IP protocol
	uint8_t		ip_prot;
	// UDP length (in bytes)
	uint16_t	udp_length;
} udp_pseudo_header_type;

/**
 * Calculates the UDP checksum for the specified UDP packet.
 *
 * @param ip_packet The IP packet containing the UDP packet.
 *
 * @return The UDP checksum for the specified UDP packet.
 */
uint16_t udp_checksum(ip_packet_t *ip_packet);

#endif // ifndef __UDP_H_

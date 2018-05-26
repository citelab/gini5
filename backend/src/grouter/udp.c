/**
 * udp.c (User Datagram Protocol (UDP))
 *
 * @author Michael Kourlas
 * @date November 9, 2015
 */

#include "grouter.h"
#include "ip.h"
#include "udp.h"

#include <arpa/inet.h>


/**
 * Calculates the UDP checksum for the specified UDP packet.
 *
 * @param ip_packet The IP packet containing the UDP packet.
 *
 * @return The UDP checksum for the specified UDP packet.
 */
uint16_t udp_checksum(ip_packet_t *ip_packet)
{
	// Derive UDP packet from IP packet and reset checksum
	udp_packet_type *udp_packet = (udp_packet_type *)
		(ip_packet + (ip_packet->ip_hdr_len * 4));
	udp_packet->checksum = 0;

	// Create UDP pseudo-header
	udp_pseudo_header_type pseudo_header;
	COPY_IP(&pseudo_header.ip_src, ip_packet->ip_src);
	COPY_IP(&pseudo_header.ip_dst, ip_packet->ip_dst);
	pseudo_header.reserved = 0;
	pseudo_header.ip_prot = ip_packet->ip_prot;
	pseudo_header.udp_length = udp_packet->length;

	// Calculate sums of pseudo-header and UDP packet (same as taking one's
	// complement of checksum) and store in temporary buffer
	uint16_t buf[3];
	buf[0] = ~checksum((uint8_t *) &pseudo_header,
					   sizeof(udp_pseudo_header_type) / 2);
	buf[1] = ~checksum((uint8_t *) &udp_packet, ntohs(udp_packet->length) / 2);
	// If UDP packet length is odd, store zero-padded last byte in temporary
	// buffer as well
	if (udp_packet->length % 2 != 0)
	{
		uint8_t *temp = (uint8_t *) (udp_packet +
			ntohs(udp_packet->length) - 1);
		buf[2] = *temp << 8;
	}
	else
	{
		buf[2] = 0;
	}

	// Find checksum of the sums (plus the last byte, if applicable)
	return checksum((uint8_t *) &buf, 3);
}

/**
 * openflow_ctrl_iface.h - OpenFlow controller-switch interface
 */

#ifndef __OPENFLOW_CTRL_IFACE_H_
#define __OPENFLOW_CTRL_IFACE_H_

#include <pthread.h>
#include <stdint.h>

#include "openflow_defs.h"
#include "message.h"

/**
 * Requests that the switch reconnect to the controller.
 */
void openflow_ctrl_iface_reconnect();

/**
 * Sends a packet in message to the OpenFlow controller containing the
 * specified packet.
 *
 * @param packet A pointer to the packet to send to the OpenFlow controller.
 * @param reason The reason the packet is being sent to the controller.
 *
 * @return The number of bytes sent, or a negative value if an error occurred.
 */
int32_t openflow_ctrl_iface_send_packet_in(gpacket_t *packet, uint8_t reason);

/**
 * Sends a flow removed message to the OpenFlow controller.
 *
 * @param entry  A pointer to the flowtable entry that is being removed from
 *               the flowtable.
 * @param reason The reason the flow is being removed.
 *
 * @return The number of bytes sent, or a negative value if an error occurred.
 */
int32_t openflow_ctrl_iface_send_flow_removed(
        openflow_flowtable_entry_type *entry, uint8_t reason);

/**
 * Sends a port status message to the OpenFlow controller.
 *
 * @param phy_port A pointer to the physical port that was added, removed or
 *                 changed.
 * @param reason   A value indicating what has changed about the physical port.
 *
 * @return The number of bytes sent, or a negative value if an error occurred.
 */
int32_t openflow_ctrl_iface_send_port_status(ofp_phy_port *phy_port,
        uint8_t reason);

/**
 * Parses a packet as though it came from the OpenFlow controller.
 *
 * @param packet The packet to parse.
 */
int32_t openflow_ctrl_iface_parse_packet(gpacket_t *packet);

/**
 * Initializes the OpenFlow controller-switch interface.
 *
 * @param port_num The TCP port number of the OpenFlow controller.
 *
 * @return The thread associated with the controller interface.
 */
pthread_t openflow_ctrl_iface_init(int32_t port_num);

#endif // ifndef __OPENFLOW_CTRL_IFACE_H_

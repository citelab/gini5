/**
 * openflow_config.h - OpenFlow switch configuration
 */

#ifndef __OPENFLOW_CONFIG_H_
#define __OPENFLOW_CONFIG_H_

#include <stdint.h>

#include "openflow_defs.h"

/**
 * Converts the specified GNET port number to an OpenFlow port number.
 *
 * @param gnet_port_num The GNET port number.
 *
 * @return The corresponding OpenFlow port number.
 */
uint16_t openflow_config_get_of_port_num(uint16_t gnet_port_num);

/**
 * Converts the specified OpenFlow port number to an GNET port number.
 *
 * @param gnet_port_num The OpenFlow port number.
 *
 * @return The corresponding GNET port number.
 */
uint16_t openflow_config_get_gnet_port_num(uint16_t openflow_port_num);

/**
 * Initializes the OpenFlow physical ports.
 */
void openflow_config_init_phy_ports();

/**
 * Updates the specified OpenFlow physical ports to match the state
 * of the corresponding GNET interface.
 *
 * @param The OpenFlow port number corresponding to the port to update.
 */
void openflow_config_update_phy_port(int32_t openflow_port_num);

/**
 * Gets the OpenFlow ofp_phy_port corresponding to the specified
 * OpenFlow port number.
 *
 * This function uses dynamically allocated memory that must be manually
 * freed afterwards.
 *
 * @param openflow_port_num The specified OpenFlow port number.
 *
 * @return The OpenFlow physical port struct corresponding to the
 *         specified port number.
 */
ofp_phy_port *openflow_config_get_phy_port(uint16_t openflow_port_num);

/**
 * Sets the OpenFlow ofp_phy_port struct corresponding to the specified
 * OpenFlow port number.
 *
 * @param openflow_port_num The specified OpenFlow port number.
 * @param port              The new ofp_phy_port struct.
 */
void openflow_config_set_phy_port(uint16_t openflow_port_num,
        ofp_phy_port *port);

/**
 * Prints information associated with the specified OpenFlow physical port.
 *
 * @param index The index of the port to print.
 */
void openflow_config_print_port(uint32_t index);

/**
 * Prints information associated with all OpenFlow physical ports.
 */
void openflow_config_print_ports();

/**
 * Gets the OpenFlow physical port statistics corresponding to the specified
 * OpenFlow port number.
 *
 * This function uses dynamically allocated memory that must be manually
 * freed afterwards.
 *
 * @param openflow_port_num The specified OpenFlow port number.
 *
 * @return The OpenFlow physical port statistics corresponding to the
 *         specified port number.
 */
ofp_port_stats *openflow_config_get_port_stats(uint16_t openflow_port_num);

/**
 * Sets the OpenFlow ofp_port_stats struct corresponding to the specified
 * OpenFlow port number.
 *
 * @param openflow_port_num The specified OpenFlow port number.
 * @param stats             The new ofp_port_stats struct.
 */
void openflow_config_set_port_stats(uint16_t openflow_port_num,
        ofp_port_stats *stats);

/**
 * Prints the statistics for the specified OpenFlow physical port.
 *
 * @param index The index of the port to print.
 */
void openflow_config_print_port_stat(uint32_t index);

/**
 * Prints the statistics for all OpenFlow physical ports.
 */
void openflow_config_print_port_stats();

/**
 * Gets the current switch configuration flags in network byte order.
 *
 * @return The current switch configuration flags.
 */
uint16_t openflow_config_get_switch_config_flags();

/**
 * Sets the current switch configuration flags in network byte order.
 *
 * @param flags The switch configuration flags to set.
 */
void openflow_config_set_switch_config_flags(uint16_t flags);

/**
 * Gets the OpenFlow switch features.
 *
 * @return The OpenFlow switch features.
 */
ofp_switch_features openflow_config_get_switch_features();

/**
 * Gets the OpenFlow description stats.
 *
 * @return The OpenFlow description stats.
 */
ofp_desc_stats openflow_config_get_desc_stats();

/**
 * Prints the OpenFlow description stats to the console.
 */
void openflow_config_print_desc_stats();

#endif // ifndef __OPENFLOW_CONFIG_H_

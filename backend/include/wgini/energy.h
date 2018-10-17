//=======================================================
//       File Name :  energy.h
//======================================================= 
#ifndef __ENERGY_H_
#define __ENERGY_H_

#include <stdio.h>
#include <stdio.h>     
#include <sys/socket.h> 
#include <arpa/inet.h> 
#include <stdlib.h>    
#include <string.h>     
#include <unistd.h>     
#include <math.h>
#include <slack/prog.h>

#include "gwcenter.h"
#include "mobility.h"
#include "mathlib.h"
#include "antenna.h"
#include "channel.h"
#include "propagation.h"
#include "802_11.h"
#include "nomac.h"
#include "mac.h"
#include "802_11_frame.h"
#include "timer.h"
#include "wirelessphy.h"
#include "llc.h"
#include "vpl.h"
#include "event.h"
#include "errmodel.h"
#include "awgn.h"
#include "fading.h"
#include "wcard.h"
 
//=======================================================
//       INITIALIZATION FUNCTIONS
//======================================================= 
    void IniNodeEnergy(NodeType type);
	void FinalizeNodeEnergy(NodeType type);

//=======================================================
//       UPDATE GROUP FUNCTIONS
//======================================================= 
	Switch UpdateEnergy(MobileNode *node, EnergyUpdate_type type, double time);

//=======================================================
//       SET GROUP FUNCTIONS
//======================================================= 
    void SetPowSwitch(MobileNode *node);
    void SetPSM(MobileNode *node);   
    void SetTotalEnergy(MobileNode *node);

//=======================================================
//       GET GROUP FUNCTIONS
//=======================================================   
    Switch GetPowSwitch(MobileNode *node);
    Switch GetPSM(MobileNode *node);
    double GetTotalEnergy(MobileNode *node);

	#endif



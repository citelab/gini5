//=======================================================
//       File Name :  propagation.h
//======================================================= 
#ifndef __PROPAGATION_H_
#define __PROPAGATION_H_

#include <stdio.h>
#include <stdio.h>      
#include <sys/socket.h>
#include <arpa/inet.h>  
#include <stdlib.h>     
#include <string.h>     
#include <unistd.h>    
#include <math.h>
#include <slack/err.h>
#include <slack/prog.h>

#include "gwcenter.h"
#include "mobility.h"
#include "mathlib.h"
#include "antenna.h"
#include "energy.h"
#include "channel.h"
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

void IniChannelPropagation(); 
void FinalizeChannelPropagation();
double FreeSpaceMod( MobileNode *tx, MobileNode *rx );
double Friis(double Pt, double Gt, double Gr, double lambda, double d, double L);
double TwoRayMod( MobileNode *tx, MobileNode *rx );
double TwoRayGroundMod( MobileNode *tx, MobileNode *rx );
double ShadowingMod( MobileNode *tx, MobileNode *rx );
double PrRefComp( MobileNode *tx, MobileNode *rx );
double PathLoss(MobileNode *tx, MobileNode *rx);

#endif


//=======================================================
//                                       File Name :  timer.h
//=======================================================
 #ifndef __TIMER_H_
 #define __TIMER_H_

 #include <stdio.h>
 #include <stdio.h>     
 #include <sys/socket.h> 
 #include <arpa/inet.h> 
 #include <stdlib.h>     
 #include <string.h>    
 #include <unistd.h>     
 #include <math.h>

 #include "gwcenter.h"
 #include "mobility.h"
 #include "mathlib.h"
 #include "antenna.h"
 #include "energy.h"
 #include "channel.h"
 #include "propagation.h"
 #include "802_11.h"
 #include "nomac.h"
 #include "mac.h"
 #include "802_11_frame.h"
 #include "wirelessphy.h"
 #include "llc.h"
 #include "vpl.h"
 #include "event.h"
 #include "errmodel.h"
 #include "awgn.h"
 #include "fading.h"
 #include "wcard.h"
   
//=======================================================
//                                                  Functions
//=======================================================
    WGNTime LocalTimeAdd (WGNTime startpoint, unsigned int duration_nsec); 	
    long int LocalTimeMinus (WGNTime endpoint, WGNTime startpoint);
    void UpdateLocalTimer(); 	
    WGNTime GetTime(); 
    void BFTimer_Start(MobileNode *node, WGNflag idle);
	void BFTimer_Pause(MobileNode *node);
    void BFTimer_Resume(MobileNode *node);	  
    void BFTimer_Stop(MobileNode *node)	;  
    void DFTimer_Start(MobileNode *node, unsigned int time_duration);
    void DFTimer_Stop(MobileNode *node); 	  
    void NAVTimer_Start(MobileNode *node, unsigned int time_duration); 
    void NAVTimer_Stop(MobileNode *node);  
    void IFTimer_Start(MobileNode *node, unsigned int time_duration); 	  
    void IFTimer_Stop(MobileNode *node);  	  
    void TXTimer_Start(MobileNode *node, unsigned int time_duration);
    void TXTimer_Stop(MobileNode *node);  
    void RXTimer_Start(MobileNode *node, unsigned int time_duration);  
    void RXTimer_Stop(MobileNode *node);  	  
    unsigned int RXTimer_Remain(MobileNode *node); 	  
    WGNflag Timer_PauseSign(MobileNode *node, TimerType type);  
    Switch Timer_SwitchSign(MobileNode *node, TimerType type); 
	void SetBFWaitTime(MobileNode *node, double wtime);

#endif

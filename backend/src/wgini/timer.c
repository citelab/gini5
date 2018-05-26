/*
 * NAME: timer.c 
 * FUNCTION: Collection of functions implements a set of controllable timer.
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//                                        File Name :  timer.c
//======================================================= 
  #include "timer.h"

//=======================================================
//       FUNCTION:   LocalTimeAdd
//       PURPOSE:    
//======================================================= 	
    WGNTime LocalTimeAdd (WGNTime startpoint, unsigned int duration_nsec) {
        WGNTime sum;
		sum.tv_sec = startpoint.tv_sec + (startpoint.tv_nsec+duration_nsec)/NFACTOR;
		sum.tv_nsec = (startpoint.tv_nsec+duration_nsec)%NFACTOR;
        return (sum);
    }

//=======================================================
//       FUNCTION:   LocalTimeMinus
//       PURPOSE:    
//======================================================= 	
    long int LocalTimeMinus (WGNTime endpoint, WGNTime startpoint) {
        long int result;
		result = ((endpoint.tv_sec)*NFACTOR + (endpoint.tv_nsec)) -  
			         ((startpoint.tv_sec)*NFACTOR + (startpoint.tv_nsec));
		return (result);
    }

//=======================================================
//       FUNCTION:   UpdateLocalTimer
//       PURPOSE:    
//======================================================= 	
    void UpdateLocalTimer() {
		SYSTEM_TIME.tv_nsec = SYSTEM_TIME.tv_nsec + 1;
		if (SYSTEM_TIME.tv_nsec == NFACTOR) {
			SYSTEM_TIME.tv_sec = SYSTEM_TIME.tv_sec + 1;
			SYSTEM_TIME.tv_nsec = 0;
		}
    }

//=======================================================
//       FUNCTION:   GetTime
//       PURPOSE:    Get the system time
//======================================================= 	
   WGNTime GetTime() {
       return SYSTEM_TIME;
   }

//=======================================================
//       Backofff Timer	stuff
//======================================================= 
//=======================================================
//       FUNCTION:   BfTimer_Start
//       PURPOSE:    Start a new Backoff Timer
//======================================================= 
    void BFTimer_Start(MobileNode *node, WGNflag idle) {
	  BackoffTimer *temp_timer;
	  double SlotTime;
	
      temp_timer = node->nodeMac->nodeTimer->bf_timer;
      SlotTime = node->nodePhy->phyMib->SlotTime;                  //seconds

	  temp_timer->switcher = ON;	  
	  temp_timer->pause = FALSE;
	  temp_timer->start_time = GetTime();

	  temp_timer->remain_time = SecToNsec ((ceil(UnitUniform() * (node->nodeMac->cw))) *SlotTime);
	  temp_timer->wait_time = 0.0;  	  
      
	  if ( idle == FALSE ) {
		  temp_timer->pause = TRUE;  
		  temp_timer->wait_time = SecToNsec(GetDIFS());
      }
	  else {
		  // The following case is the situation to start the bftimer when channel is free!!!
	      // (1) in case of retransmission, even the channel is free, we should double the CW and go through 
		  //       a time priod of backoff before resend the packet. 
		  // (2) it's also suitable for the case of after successfully
		  //       finishing sending a packet.   
		  temp_timer->timeout_time = LocalTimeAdd(temp_timer->start_time,temp_timer->remain_time);
		  AddNewEventToList(node->Id, BFTimeOut, temp_timer->timeout_time, NULL); 
	  }
	}
//=======================================================
//       FUNCTION:   BfTimer_Pause
//       PURPOSE:    Pause a Backoff Timer
//=======================================================
	void BFTimer_Pause(MobileNode *node) {
	  BackoffTimer *temp_timer;
	  double  SlotTime;
	  WGNTime real_start_time;
	  long int reduce_time;
	  int reduce_slot_no;

      temp_timer = node->nodeMac->nodeTimer->bf_timer;	
	  SlotTime = node->nodePhy->phyMib->SlotTime;
	  real_start_time = LocalTimeAdd(temp_timer->start_time, temp_timer->wait_time);
	  reduce_time = LocalTimeMinus (GetTime(), real_start_time);
      
	  if (reduce_time < 0) 
		  reduce_time = 0;  
	  
	  reduce_slot_no = floor (reduce_time/SecToNsec(SlotTime));
	  temp_timer->pause = TRUE;
      temp_timer->remain_time -= SecToNsec(reduce_slot_no * SlotTime);
	  temp_timer->wait_time = SecToNsec(GetDIFS());
	}

//=======================================================
//       FUNCTION:   BfTimer_Resume
//       PURPOSE:    Go back to the Backoff Process when channel is free
//=======================================================
    void BFTimer_Resume(MobileNode *node) {
	  BackoffTimer *temp_timer;
	  double SlotTime;

      temp_timer = node->nodeMac->nodeTimer->bf_timer;	
	  SlotTime = node->nodePhy->phyMib->SlotTime; 
		
	  temp_timer->pause = FALSE;
	  temp_timer->start_time = GetTime();
      
	  // The media should be indicated to idle for DIFS/EIFS time before
	  // decrementing the backoff time slot. 
	  temp_timer->timeout_time = LocalTimeAdd(temp_timer->start_time, (temp_timer->remain_time + temp_timer->wait_time));
	  AddNewEventToList(node->Id, BFTimeOut, temp_timer->timeout_time, NULL);
	}	

//=======================================================
//       FUNCTION:   BfTimer_Stop
//       PURPOSE:    To stop the Backoff Timer
//======================================================= 	  
    void BFTimer_Stop(MobileNode *node) {
	  BackoffTimer *temp_timer;
      temp_timer = node->nodeMac->nodeTimer->bf_timer;

      temp_timer->switcher = OFF;
	  temp_timer->pause = FALSE;
	  temp_timer->start_time.tv_sec = 0.0;
	  temp_timer->start_time.tv_nsec = 0.0;
      temp_timer->remain_time = 0.0;
	  temp_timer->wait_time = 0.0; 
    }


//=======================================================
//       Defer Timer stuff
//=======================================================
//=======================================================
//       FUNCTION:   DFTimer_Start
//       PURPOSE:    To start a DFTimer
//======================================================= 	  
    void DFTimer_Start(MobileNode *node, unsigned int time_duration) {
	    NormalTimer *temp_timer;
		
        temp_timer = node->nodeMac->nodeTimer->df_timer;
		temp_timer->switcher = ON;
		temp_timer->start_time = GetTime();
		temp_timer->end_time = LocalTimeAdd(temp_timer->start_time ,time_duration);    //time_duration here is by unit of nanosecond
		AddNewEventToList(node->Id, DFTimeOut, temp_timer->end_time,NULL);
    }
//=======================================================
//       FUNCTION:   DFTimer_Stop
//       PURPOSE:    To stop the DFTimer
//======================================================= 	  
    void DFTimer_Stop(MobileNode *node) {
	    NormalTimer *temp_timer;

        temp_timer = node->nodeMac->nodeTimer->df_timer;
		temp_timer->switcher = OFF;
		temp_timer->start_time.tv_sec = 0.0;
		temp_timer->start_time.tv_nsec = 0.0;
		temp_timer->end_time.tv_sec = 0.0;
		temp_timer->end_time.tv_nsec = 0.0;
    }


//=======================================================
//       NAV Timer stuff
//======================================================= 
//=======================================================
//       FUNCTION:   NavTimer_Start
//       PURPOSE:    To start a NAVTimer
//======================================================= 	  
    void NAVTimer_Start(MobileNode *node, unsigned int time_duration) {
	    NormalTimer *temp_timer;

        temp_timer = node->nodeMac->nodeTimer->nav_timer;
		temp_timer->switcher = ON;
		temp_timer->start_time = GetTime();
		temp_timer->end_time = LocalTimeAdd(temp_timer->start_time ,time_duration);
		AddNewEventToList(node->Id, NAVTimeOut, temp_timer->end_time,NULL);  
    }
//=======================================================
//       FUNCTION:   NavTimer_Stop
//       PURPOSE:    To stop a NavTimer
//======================================================= 	  
    void NAVTimer_Stop(MobileNode *node) {
	    NormalTimer *temp_timer;
        temp_timer = node->nodeMac->nodeTimer->nav_timer;
		temp_timer->switcher = OFF;
		temp_timer->start_time.tv_sec = 0.0;
		temp_timer->start_time.tv_nsec = 0.0;
		temp_timer->end_time.tv_sec = 0.0;
		temp_timer->end_time.tv_nsec = 0.0;
    }


//=======================================================
//       IF Timer stuff
//======================================================= 
//=======================================================
//       FUNCTION:   IFTimer_Start
//       PURPOSE:    To start a IFTimer
//======================================================= 	  
    void IFTimer_Start(MobileNode *node, unsigned int time_duration) {
	    NormalTimer *temp_timer;
			
        temp_timer = node->nodeMac->nodeTimer->if_timer;
		temp_timer->switcher = ON;
		temp_timer->start_time = GetTime();
		temp_timer->end_time = LocalTimeAdd(temp_timer->start_time ,time_duration);
		AddNewEventToList(node->Id, IFTimeOut, temp_timer->end_time,NULL);  
    }
//=======================================================
//       FUNCTION:   IFTimer_Stop
//       PURPOSE:    To stop a IFTimer
//======================================================= 	  
    void IFTimer_Stop(MobileNode *node) {
	    NormalTimer *temp_timer;
        temp_timer = node->nodeMac->nodeTimer->if_timer;
		temp_timer->switcher = OFF;
		temp_timer->start_time.tv_sec = 0.0;
		temp_timer->start_time.tv_nsec = 0.0;
		temp_timer->end_time.tv_sec = 0.0;
		temp_timer->end_time.tv_nsec = 0.0;
    }


//=======================================================
//       TX Timer stuff
//=======================================================
//=======================================================
//       FUNCTION:   TXTimer_Start
//       PURPOSE:    To start a TXTimer
//======================================================= 	  
    void TXTimer_Start(MobileNode *node, unsigned int time_duration) {
	    NormalTimer *temp_timer;

        temp_timer = node->nodeMac->nodeTimer->tx_timer;
		temp_timer->switcher = ON;
		temp_timer->start_time = GetTime();
		temp_timer->end_time = LocalTimeAdd(temp_timer->start_time ,time_duration);
		AddNewEventToList(node->Id, TXTimeOut, temp_timer->end_time,NULL);
    }
//=======================================================
//       FUNCTION:   TXTimer_Stop
//       PURPOSE:    To stop a TXTimer
//======================================================= 	  
    void TXTimer_Stop(MobileNode *node) {
	    NormalTimer *temp_timer;
        temp_timer = node->nodeMac->nodeTimer->tx_timer;
		temp_timer->switcher = OFF;
		temp_timer->start_time.tv_sec = 0.0;
		temp_timer->start_time.tv_nsec = 0.0;
		temp_timer->end_time.tv_sec = 0.0;
		temp_timer->end_time.tv_nsec = 0.0;
    }


//=======================================================
//       RX Timer stuff
//======================================================= 
//=======================================================
//       FUNCTION:   RXTimer_Start
//       PURPOSE:    To start a RXTimer
//======================================================= 	  
    void RXTimer_Start(MobileNode *node, unsigned int time_duration) {
	    NormalTimer *temp_timer;

        temp_timer = node->nodeMac->nodeTimer->rx_timer;
		temp_timer->switcher = ON;
		temp_timer->start_time = GetTime();
		temp_timer->end_time = LocalTimeAdd(temp_timer->start_time ,time_duration); 
		AddNewEventToList(node->Id, RXTimeOut, temp_timer->end_time,NULL); 
    }

//=======================================================
//       FUNCTION:   RXTimer_Stop
//       PURPOSE:    To stop a RXTimer
//======================================================= 	  
    void RXTimer_Stop(MobileNode *node) {
	    NormalTimer *temp_timer;
        temp_timer = node->nodeMac->nodeTimer->rx_timer;
		temp_timer->switcher = OFF;
		temp_timer->start_time.tv_sec = 0.0;
		temp_timer->start_time.tv_nsec = 0.0;
		temp_timer->end_time.tv_sec = 0.0;
		temp_timer->end_time.tv_nsec = 0.0;
    }

//=======================================================
//       FUNCTION:   RXTimer_Remain
//======================================================= 	  
    unsigned int RXTimer_Remain(MobileNode *node) {
		unsigned int remain_time;                         //nanoseconds
		remain_time = 
		LocalTimeMinus (node->nodeMac->nodeTimer->rx_timer->end_time, GetTime());
        return (remain_time);
	}

//=======================================================
//       FUNCTION:   NAVTimer_Remain
//======================================================= 	  
    unsigned int NAVTimer_Remain(MobileNode *node) {
		unsigned int remain_time;                         //nanoseconds
		remain_time = 
		LocalTimeMinus (node->nodeMac->nodeTimer->nav_timer->end_time, GetTime());
        return (remain_time);
	}

//=======================================================
//       FUNCTION:   Timer_PauseSign
//       PURPOSE:    Return the Pause Status of the timer
//======================================================= 	  
  WGNflag Timer_PauseSign(MobileNode *node, TimerType type) {
		WGNflag flag;
		switch(type) {
            case BF_TIMER: 
                flag = node->nodeMac->nodeTimer->bf_timer->pause;
                break;
            default:
                printf("[Timer_PauseSign]:: Error, Invalid timer type!\n");
        }
		return (flag);
  }	

//=======================================================
//       FUNCTION:   Timer_SwitchSign
//       PURPOSE:    Return the Switch Status of the timer
//======================================================= 	  
  Switch Timer_SwitchSign(MobileNode *node, TimerType type) {
		Switch flag;

		switch(type) {
            case BF_TIMER: 
                flag = node->nodeMac->nodeTimer->bf_timer->switcher;
                break;
            case DF_TIMER: 
                flag = node->nodeMac->nodeTimer->df_timer->switcher;
                break;
            case NAV_TIMER:
				flag = node->nodeMac->nodeTimer->nav_timer->switcher;
                break;
            case IF_TIMER: 
                flag = node->nodeMac->nodeTimer->if_timer->switcher;
                break;
            case TX_TIMER: 
				flag = node->nodeMac->nodeTimer->tx_timer->switcher;
                break;
            case RX_TIMER:
				flag = node->nodeMac->nodeTimer->rx_timer->switcher;
                break;
            default:
                printf("[Timer_SwitchSign]:: Error, Invalid timer type!\n");
        }
		return (flag);
  }	

//=======================================================
//       FUNCTION:   SetBFWaitTime
//======================================================= 	
  void SetBFWaitTime(MobileNode *node, double wtime) {
      node->nodeMac->nodeTimer->bf_timer->wait_time = SecToNsec(wtime);
  }

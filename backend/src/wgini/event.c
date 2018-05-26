/*
 * NAME: event.c 
 * FUNCTION: Collection of functions implements the system event manager.
 *                    It provides some event queue	operation functions as well as the
 *                    event handler.
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  event.c
//=======================================================
  #include 	"event.h"


//=======================================================
//       FUNCTION: EventQIsEmpty
//       PURPOSE:  To check if the queue is empty. 
//======================================================= 
    WGNflag EventQIsEmpty() {
      if (WGNEveQPtr == NULL)
		  return(TRUE);
	  else
		  return(FALSE);
    }

//=======================================================
//       FUNCTION: GenNewEvent
//       PURPOSE:  Create a new event. 
//======================================================= 
    WGNEvent* GenNewEvent(NodeId id, Event_type type,WGNTime time, void *eveObject,
		                                        WGNEvent *nextEventPtr) {
	
	WGNEvent	*ptr;
	ptr = (WGNEvent *)malloc(sizeof(WGNEvent));
	if(ptr == NULL) {
		puts("[GenNewEvent]:: Malloc for the new event failed.\n");
		exit(1);
	}	
	ptr->id = id;
	ptr->eveType = type;
	ptr->eveTime = time;
	ptr->nextEventPtr = nextEventPtr;
	ptr->eveObject = eveObject;

	return(ptr);
}

//=======================================================
//       FUNCTION: AddNewEventToList
//       PURPOSE:  Insert a new event into the event queue in order of time. 
//======================================================= 
    WGNEvent* AddNewEventToList(NodeId id, Event_type type,WGNTime time, void *object) {
	WGNEvent	*ptr, *prevPtr, *newPtr;	

	pthread_mutex_lock(&event_queue_mutex);
	if (EventQIsEmpty(id)==FALSE) {
		prevPtr = WGNEveQPtr;

		if (LocalTimeMinus (prevPtr->eveTime, time) > 0) { 
		    // Insert it in the head of the queue, the event which will happen first 
			// will always be in the head of the queue.
		    WGNEveQPtr = GenNewEvent(id,type,time,object,prevPtr);
			newPtr = WGNEveQPtr;
			//Update the earliest event execution time of the system
	    	timeOutTime = WGNEveQPtr->eveTime;
		}
		else {
			ptr = prevPtr->nextEventPtr;
			// Search for the event immediately happens after it
			while ((ptr!=NULL) && (LocalTimeMinus(ptr->eveTime, time) <= 0)) {
				prevPtr = ptr;
				ptr = ptr->nextEventPtr;
			}
			if (ptr==NULL) 
				// Insert it in the tail of the queue. the field of the nextEventPtr should 
			    // be set to NULL.
				prevPtr->nextEventPtr = GenNewEvent(id,type,time,object,NULL);
			else 
				// Insert it in the middle of the queue. find the event that will immediately
			    //happen after the new event, so insert the one before that followed one.
				prevPtr->nextEventPtr = GenNewEvent(id,type,time,object,ptr);
			
			newPtr = prevPtr->nextEventPtr;
		 }
	}
	//Event Queue Is Empty
	else { 
		newPtr = GenNewEvent(id,type,time,object,NULL);
		WGNEveQPtr = newPtr;
		timeOutTime = WGNEveQPtr->eveTime;
    }
	
	//*************************************FOR TEST ONLY***********************************//
	if (PrintEventSign == TRUE) {
	    EventListFilePrint();
	}

	pthread_mutex_unlock(&event_queue_mutex);
    return(newPtr);
    }

//=======================================================
//       FUNCTION: IniEvent
//       PURPOSE:  To initialize the event queue. 
//======================================================= 
	void IniEvent() {
       int ret;

	   if (prog_verbosity_level()==3){
			printf("[IniEvent]:: Initialize the event queue manager ... ");
	   }
	   ret = pthread_mutex_init(&event_queue_mutex, NULL);
	   if (ret!=0) printf("[IniEvent]:: Error, fail to init event_queue_mutex.\n");
	   WGNEveQPtr = NULL;	
	   PrintEventSign = FALSE;
	   if (prog_verbosity_level()==3){
			printf("[ OK ]\n");
	   }
	}

//=======================================================
//       FUNCTION:  EveDelete
//       PURPOSE:   Delete a event from the event queue. 
//======================================================= 
	void EventDelete() {
		//the event in the head of the queue should always be delete first
		WGNEvent	*ptr;

		pthread_mutex_lock(&event_queue_mutex);
		ptr = WGNEveQPtr;	
		if (ptr==NULL) {
			puts("[EventDelete]:: The event is empty when deletion is requested. Abort!\n");
			exit(1);
		}
		WGNEveQPtr = WGNEveQPtr->nextEventPtr;
		free(ptr);

		//update earliest event timeout time of the system
		if (EventQIsEmpty() == FALSE) {
		     timeOutTime = WGNEveQPtr->eveTime;		 
		}
		else {
			 timeOutTime.tv_sec = 0;
		     timeOutTime.tv_nsec = 0;
		}

		//*************************************FOR TEST ONLY***********************************//
		//PrintEventList();		
		//if (PrintEvent == TRUE) {
		//	EventListFilePrint();
	    //}

		pthread_mutex_unlock(&event_queue_mutex);
	}

//=======================================================
//       FUNCTION:  EventDestroy
//       PURPOSE:   Destroy a event from the event queue. 
//======================================================= 
    WGNflag EventDestroy(NodeId id, Event_type type) {
		WGNEvent *ptr,*prevPtr;

		pthread_mutex_lock(&event_queue_mutex);
		ptr = WGNEveQPtr;					  
		prevPtr = NULL;

		while (ptr!=NULL && ((ptr->id)!=id || (ptr->eveType)!=type)) {
			prevPtr = ptr;
			ptr = ptr->nextEventPtr;
		}

		if (ptr != NULL) {
			//ptr is the head of event queue
			if (prevPtr == NULL)	 {	
				WGNEveQPtr = WGNEveQPtr->nextEventPtr;
				if (WGNEveQPtr != NULL) {
					timeOutTime = WGNEveQPtr->eveTime;
				}
				else {
					timeOutTime.tv_sec = 0;
					timeOutTime.tv_nsec = 0;				
				}
			}
			else {
				prevPtr->nextEventPtr = ptr->nextEventPtr;
			}

			free(ptr);	

			//*************************************FOR TEST ONLY***********************************//
			//PrintEventList();	
			//if (PrintEvent == TRUE) {
			//	EventListFilePrint();
			//}

			pthread_mutex_unlock(&event_queue_mutex);
			return(TRUE);
		}
		//ptr point to the end of the queue but still can not find the matching item.
		else	{
			//*************************************FOR TEST ONLY***********************************//
	        //PrintEventList();
			//if (PrintEvent == TRUE) {
			//	EventListFilePrint();
			//}

			pthread_mutex_unlock(&event_queue_mutex);
			return(FALSE);
	    }
	}

//=======================================================
//       FUNCTION:  EventHandler
//       PURPOSE:   To process the event which is located at the header of 
//                              the event queue
//======================================================= 
    void EventHandler() {
	    int id;
		Event_type evetype;
		void* tmp_object;
		//WGN_802_11_Mac_Frame* tmp_frame;

		id = WGNEveQPtr->id;
		evetype = WGNEveQPtr->eveType;
		tmp_object = WGNEveQPtr->eveObject;
		WGNEveQPtr->eveObject = NULL;		  

		EventDelete();	

		switch( evetype ) { 
			case BFTimeOut: 
				switch(SYS_INFO->mac_info->macType) {
					case CSMA:
                        printf("[EventHandler]:: Error, CAMA HAS NO BF TIMER!"); 
					    exit(1);
					    break;
					case DCF_802_11:
						BFTimeoutHandler(WGNnode(id));
						break;
					case NONE:
					    break;
					default: 
					    printf("[EventHandler]:: Error, Invalid mac type: abort!"); 
					    exit(1); 
	            }    	 
					 break;  
			case DFTimeOut:
				switch(SYS_INFO->mac_info->macType) {
					case CSMA:
                        printf("[EventHandler]:: Error, CAMA HAS NO DF TIMER!"); 
					    exit(1);
					    break;
					case DCF_802_11:
						DFTimeoutHandler(WGNnode(id)); 
						break;
					case NONE:
					    break;
					default: 
					    printf("[EventHandler]:: Error, Invalid mac type: abort!"); 
					    exit(1); 
	            }   
					 break; 
			case NAVTimeOut:
				switch(SYS_INFO->mac_info->macType) {
					case CSMA:
                        CSMAMacNAVTimeoutHandler(WGNnode(id));
					    // change it to DF timeout
					    break;
					case DCF_802_11:
						NAVTimeoutHandler(WGNnode(id)); 
						break;
					case NONE:
					    break;
					default: 
					    printf("[EventHandler]:: Error, Invalid mac type: abort!");  
					    exit(1); 
	            }                     
					 break; 
			case IFTimeOut:
				switch(SYS_INFO->mac_info->macType) {
					case CSMA:
                        CSMAMacIFTimeoutHandler(WGNnode(id)); 
					    break;
					case DCF_802_11:
						IFTimeoutHandler(WGNnode(id)); 
						break;
					case NONE:
						NoMacIFTimeoutHandler(WGNnode(id)); 
					    break;
					default: 
					    printf("[EventHandler]:: Error, Invalid mac type: abort!"); 
					    exit(1); 
	            }   			 
					 break; 
			case TXTimeOut:
				switch(SYS_INFO->mac_info->macType) {
					case CSMA:
                        CSMAMacTXTimeoutHandler(WGNnode(id)); 
					    break;
					case DCF_802_11:
						TXTimeoutHandler(WGNnode(id)); 
						break;
					case NONE: 
						NoMacTXTimeoutHandler(WGNnode(id)); 
					    break;
					default: 
					    printf("[EventHandler]:: Error, Invalid mac type: abort!"); 
					    exit(1); 
	            }   					 
					 break; 
			case RXTimeOut:
				switch(SYS_INFO->mac_info->macType) {
					case CSMA:
                        CSMAMacRXTimeoutHandler(WGNnode(id)); 
					    break;
					case DCF_802_11:
						RXTimeoutHandler(WGNnode(id));
						break;
					case NONE:
						NoMacRXTimeoutHandler(WGNnode(id));
					    break;
					default: 
					    printf("[EventHandler]:: Error, Invalid mac type: abort!"); 
					    exit(1); 
	            }   			          
					 break; 
			case INTTimeOut:
                     INTTimeoutHandler(WGNnode(id), (WGN_802_11_Mac_Frame*)tmp_object);
			         break;
			case START_RX:
			         PhyDownPortRecv(WGNnode(id), (WGN_802_11_Mac_Frame*)tmp_object); 
					 break; 
			default: 
					 printf("[EventHandler]:: Error, Invalid event type: abort!");  
					 exit(1); 
           }
    }

//=======================================================
//       FUNCTION:  EventPrint
//======================================================= 
	void EventPrint(WGNEvent* eve , char* do_what ) {
		switch( eve->eveType ) { 
			case BFTimeOut: 
				     printf("\nBFTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);					 
					 break;  
			case DFTimeOut:
			         printf("\nDFTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);
					 break; 
			case NAVTimeOut:
				     printf("\nNAVTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);
					 break; 
			case IFTimeOut:
				     printf("\nIFTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);		
					 break; 
			case TXTimeOut:
                     printf("\nTXTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);	
			         break; 
			case RXTimeOut:
				     printf("\nRXTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);
					 break;
			case INTTimeOut:
				     printf("\nINTTimeOut Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);
					 break;
			case START_RX:
				     printf("\nSTART_RXTimeout Event at node %d at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what); 
					 break; 
			default:
					 printf("[EventPrint]:: Error, Invalid event type: abort!"); 
					 exit(1); 
           }
	}


//=======================================================
//       FUNCTION:  EventFilePrint
//======================================================= 
	void EventFilePrint(WGNEvent* eve , char* do_what ) {
		FILE* in;
		in = fopen(eve_rep_name, "a+");
		switch( eve->eveType ) { 
			case BFTimeOut: 
				     fprintf(in, "\nBFTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);					 
					 break;  
			case DFTimeOut:
			         fprintf(in, "\nDFTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);
					 break; 
			case NAVTimeOut:
				     fprintf(in, "\nNAVTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);
					 break; 
			case IFTimeOut:
				     fprintf(in, "\nIFTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);		
					 break; 
			case TXTimeOut:
                     fprintf(in, "\nTXTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);	
			         break; 
			case RXTimeOut:
				     fprintf(in, "\nRXTimeout Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);
					 break; 
			case INTTimeOut:
				     fprintf(in, "\nINTTimeOut Event at node %d  at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what);
					 break;
			case START_RX:
				     fprintf(in, "\nSTART_RXTimeout Event at node %d at time %d : %d %s\n",eve->id,eve->eveTime.tv_sec,eve->eveTime.tv_nsec, do_what); 
					 break; 
			default:
					 exit(1); 
           }
		 fclose(in);
	}

//=======================================================
//       FUNCTION:  EventListFilePrint
//======================================================= 
	void EventListFilePrint() {
		FILE* in;  
		WGNEvent *ptr;
        
        in = fopen(eve_rep_name, "a+");
	    fprintf(in, "\n=============================================================\n");
	    fprintf(in, "CURRENT EVENT LIST\n");
	    fprintf(in, "=============================================================\n");
		fclose(in);

	    ptr = WGNEveQPtr;
	    if (ptr == NULL) {
		    fprintf(in, "No Event Entry!");
	    }	
        while (ptr!=NULL) {
	        EventFilePrint(ptr,".");
		    ptr = ptr->nextEventPtr;	
	    }	

		in = fopen(eve_rep_name, "a+");
	    fprintf(in, "\n=============================================================\n");
	    fclose(in);
	}

//=======================================================
//       FUNCTION:  PrintEventList
//=======================================================
    void PrintEventList() {
		WGNEvent *ptr;
	    printf("\n=============================================================\n");
	    printf("CURRENT EVENT LIST\n");
	    printf("=============================================================\n");
	    ptr = WGNEveQPtr;
	    if (ptr == NULL) {
		    printf("No Event Entry!");
	    }	
        while (ptr!=NULL) {
	        EventPrint(ptr,".");
		    ptr = ptr->nextEventPtr;	
	    }	
	    printf("\n=============================================================\n");
	}

//=======================================================
//       FUNCTION:  PrintCurTime
//======================================================= 
	void PrintCurTime () {
	    printf("\n=============================================================\n");
	    printf("Current time %d : %d.\n",SYSTEM_TIME.tv_sec,SYSTEM_TIME.tv_nsec);
	    printf("=============================================================\n");
	}

//=======================================================
//       FUNCTION:  PrintEarliestEveTime
//======================================================= 
	void PrintEarliestEveTime() {
	    printf("\n=============================================================\n");
	    printf("Earliest Event Time %d : %d.\n",timeOutTime.tv_sec,timeOutTime.tv_nsec);
	    printf("=============================================================\n");
	}

//=======================================================
//       FUNCTION:  PrintMacAddr
//======================================================= 
	void PrintMacAddr (char* type, unsigned char *mac_addr) {
		int j;
	    printf("\n=============================================================\n");
		     printf("%s :", type);
	    	 for(j=0; j<MAC_ADDR_LEN; j++) {
				   printf("%02x.",mac_addr[j]);
			 }
	    printf("\n=============================================================\n");
	}

//=======================================================
//       FUNCTION:  PrintIPAddr
//======================================================= 
	void PrintIPAddr (char* type, unsigned char *ip_addr) {
		int j;
	    printf("\n=============================================================\n");
		     printf("%s :", type);
	    	 for(j=0; j<4; j++) {
				   printf("%d.",ip_addr[j]);
			 }
	    printf("\n=============================================================\n");
	}

//=======================================================
//       FUNCTION:  PrintProt
//======================================================= 
	void PrintProt (unsigned char *prot) {
	    printf("\n=============================================================\n");
	    if (prot[0]==0x08 && prot[1]==0x06)
	        printf("Packet Type : ARP.\n");
	    if (prot[0]==0x08 && prot[1]==0x00)
	        printf("Packet Type : IP.\n");
	    if (prot[0]==0x08 && prot[1]==0x35)
	        printf("Packet Type : RARP.\n");
	    printf("=============================================================\n");
	}

//=======================================================
//       FUNCTION:  PrintSystemInfo
//======================================================= 
	void PrintSystemInfo (char *info) {
	    printf("\n=============================================================\n");
	    printf("%s\n", info);
	    printf("=============================================================\n");
	}

//=======================================================
//       FUNCTION:  PrintSystemInfo
//======================================================= 
	void PrintDebugInfo (char *info) {
	    printf("\n=============================================================\n");
		fflush(stdout);
		printf("DEBUG BREAK POINT\n"); 
		fflush(stdout);
		printf("=============================================================\n"); 
		fflush(stdout);
	    printf("%s\n", info); 
		fflush(stdout);
	    printf("=============================================================\n\n");
		fflush(stdout);
	}

//=======================================================
//       FUNCTION:  PrintLine
//======================================================= 
	void PrintLine () {
	    printf("=============================================================\n");
	}

//=======================================================
//       FUNCTION:  EventQueueClean
//       PURPOSE:   Delete all events in the event queue. 
//======================================================= 
	void FinalizeEvent() {
		WGNEvent	*ptr;
        WGNEvent	*tmp_ptr;

		pthread_mutex_lock(&event_queue_mutex);	
		ptr = WGNEveQPtr;
        WGNEveQPtr = NULL;
		while (ptr!=NULL) {
			tmp_ptr = ptr;
			ptr = ptr->nextEventPtr;
			if ((tmp_ptr->eveType == INTTimeOut)||(tmp_ptr->eveType == START_RX)) {
				Dot11FrameFree((WGN_802_11_Mac_Frame*)tmp_ptr->eveObject);
			}
            free(tmp_ptr);
		}
	    timeOutTime.tv_sec = 0;
	    timeOutTime.tv_nsec = 0;
		pthread_mutex_unlock(&event_queue_mutex);
    }

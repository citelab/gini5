/*
 * NAME: llc.c 
 * FUNCTION: Collection of functions implements the fading module. It provides
 *                    functions to emulate the Rayleigh fading of the wireless channel. 
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 * NOTE:   Two functions are ported from the previous version of GINI written
 *              by Weiling Xu.
 */

//=======================================================
//       File Name :  llc.c
//=======================================================
   #include "llc.h"

//=======================================================
//       FUNCTION:   IniNodeLlc
//======================================================= 
   void IniNodeLlc(NodeType type) {
	   int id;
	   int j;
	   int ret;
	   
	   if (prog_verbosity_level()==1){
		   printf("[IniNodeLlc]:: Initializing basic functional logical link control layer ... ");
	   }

	   if (type == NORMAL) {
	       for (id=1; id<=TotNodeNo; id++) {
				  WGNnode(id)->nodeLlc = (NodeLlc *)malloc(sizeof(NodeLlc));
				  //initialize LToMArray
				  for (j=0; j<LLC_TO_MAC_BUF_SIZE; j++) {
					     WGNnode(id)->nodeLlc->LToMArray[j]=NULL;
		          }
				  WGNnode(id)->nodeLlc->ltom_buf_Wcount = 0;
				  WGNnode(id)->nodeLlc->ltom_buf_Rcount = 0;
		    
				  ret = pthread_mutex_init(&(WGNnode(id)->nodeLlc->ltom_array_mutex), NULL);
				  if (ret!=0) printf("[IniNodeLlc]:: fail to init mutex, error %d\n",ret);
				  ret = pthread_cond_init(&(WGNnode(id)->nodeLlc->ltom_nonempty), NULL);
				  if (ret!=0) printf("[IniNodeLlc]:: fail to init cond, error %d\n",ret);
				  ret = pthread_cond_init(&(WGNnode(id)->nodeLlc->ltom_nonfull), NULL);
				  if (ret!=0) printf("[IniNodeLlc]:: fail to init cond nonfull, error %d\n",ret);

		          for (j=0; j<LLC_TO_UML_BUF_SIZE; j++) {
			             WGNnode(id)->nodeLlc->LToUArray[j]=NULL;
		          }
		          WGNnode(id)->nodeLlc->ltou_buf_Wcount = 0;
	              WGNnode(id)->nodeLlc->ltou_buf_Rcount = 0;
		    
				  ret = pthread_mutex_init(&(WGNnode(id)->nodeLlc->ltou_array_mutex), NULL);
		          if (ret!=0) printf("[IniNodeLlc]:: fail to init mutex, error %d\n",ret);
		          ret = pthread_cond_init(&(WGNnode(id)->nodeLlc->ltou_nonempty), NULL);
		          if (ret!=0) printf("[IniNodeLlc]:: fail to init cond, error %d\n",ret);
		          ret = pthread_cond_init(&(WGNnode(id)->nodeLlc->ltou_nonfull), NULL);
		          if (ret!=0) printf("[IniNodeLlc]:: fail to init cond nonfull, error %d\n",ret);
		   }//end of for

		   //establish the connection from llc to uml.
			printf("Calling LlcProcess... \n");
		   LlcProcess();

       }//end of if
	   if (prog_verbosity_level()==1){
		   printf("[ OK ]\n");
	   }
   }

//=======================================================
//       FUNCTION:   FinalizeNodeLlc
//======================================================= 
   void FinalizeNodeLlc(NodeType type) {
	   int id,i;
	   printf("Finalizing logic link control layer parameters ... ");	   
	   if (type == NORMAL) {
	       for (id=1; id<=TotNodeNo; id++) {
			      //cancel uml->llc connection.
				  conn_close(WGNnode(id)->nodeLlc->inf);
                  //cancel llc->uml connection.
				  pthread_cancel(WGNnode(id)->nodeLlc->buf_thread_id);			  
				  for (i=0; i<LLC_TO_MAC_BUF_SIZE; i++) {
					     if (WGNnode(id)->nodeLlc->LToMArray[i] != NULL) {
                             free(WGNnode(id)->nodeLlc->LToMArray[i]);
							 WGNnode(id)->nodeLlc->LToMArray[i] = NULL;
					     }
				  } 				  							  
				  for (i=0; i<LLC_TO_UML_BUF_SIZE; i++) {
					     if (WGNnode(id)->nodeLlc->LToUArray[i] != NULL) {
                             free(WGNnode(id)->nodeLlc->LToUArray[i]);
							 WGNnode(id)->nodeLlc->LToUArray[i] = NULL;
					     }
				  } 					  
		          free(WGNnode(id)->nodeLlc);
		   }
	   }
	   printf("[ OK ]\n");
   }


//=======================================================
//       FUNCTION:   LlcProcess
//======================================================= 
  void LlcProcess() {
	  int ret;
	  int i;
	  //pthread_t thread_id;
	  char *pchSocket; 
      
	  pchSocket = (char *)malloc(sizeof(char)*100);

	  for (i=0; i<TotNodeNo; i++) {
			// llc to uml connection
			ret = pthread_create(&(WGNnode(i+1)->nodeLlc->buf_thread_id), NULL, (void *)LlcUpPortSend, WGNnode(i+1));
			if (ret != 0) {
				printf("[LlcProcess]:: The connection from LLC to UML is failed.\n");
			}		
		    //initialize the node interface
	        WGNnode(i+1)->nodeLlc->inf = (struct interface *)malloc(sizeof(struct interface));
			//initialize the uml to llc connection		  
			SocketNameGen(i+1, pchSocket);
			conn_open(WGNnode(i+1), pchSocket);
	  }
  }

//=======================================================
//       FUNCTION:   LlcUpPortRecv	 (thread, get pkt from UML)
//======================================================= 
    void LlcUpPortRecv(void* psConn) {
	   struct interface* psConnection = (struct interface*) psConn;	       
	   unsigned char* input_frame;
	   WGN_802_3_Mac_Frame* frame;
	   WGNflag fullArray;
	   MobileNode *node;
	   int byte_no;
	   
	   fullArray=FALSE;
	   node = WGNnode(psConnection->node_id);	   
	   input_frame = (unsigned char*)malloc(sizeof(char)*RCVBUFSIZE);

	   while(1){		   
		   byte_no = vpl_recvfrom(psConnection->iDescriptor, input_frame, RCVBUFSIZE); 
		   frame = WGN_802_3_FrameDup(input_frame, byte_no);
		   if (frame == NULL) {
			   verbose(4, "[LlcUpPortRecv]:: Node %d received a NULL packet from the UML.", psConnection->node_id);
		   }
		   else {
		       verbose(4, "[LlcUpPortRecv]:: Node %d receives a packet from the UML.", psConnection->node_id);
		   }
		   pthread_mutex_lock(&(node->nodeLlc->ltom_array_mutex));
	       if (node->nodeLlc->LToMArray[(node->nodeLlc->ltom_buf_Wcount)]==NULL){
	   	       node->nodeLlc->LToMArray[(node->nodeLlc->ltom_buf_Wcount)] = frame;
			   frame = NULL;
		       //update index
		       node->nodeLlc->ltom_buf_Wcount = (node->nodeLlc->ltom_buf_Wcount + 1)%LLC_TO_MAC_BUF_SIZE;
	       }
	       else 		 
	          fullArray=TRUE;
		   node->nodeLlc->ltombufempty = FALSE;
		   pthread_mutex_unlock(&(node->nodeLlc->ltom_array_mutex));	    //unlock this module's buffer array  
		    
		   if (node->nodeMac->HasPkt == FALSE) {
			   LlcDownPortSend (node);
		   }
	       if(fullArray==TRUE){
              verbose(4, "[LlcUpPortRecv]:: NODE %d: LLC to MAC buffer is full, packet thrown.", node->Id);
	          Dot3FrameFree(frame);
              node->nodeStats->LToMBufDrop += 1;
			  fullArray=FALSE;
	       }		 
	    }
    }

//=======================================================
//       FUNCTION:   LlcDownPortSend
//=======================================================
    WGNflag LlcDownPortSend(MobileNode *node) {   
	    WGN_802_11_Mac_Frame *frame;
		WGN_802_3_Mac_Frame *tmp_frame;
     	
		verbose(4, "[LlcDownPortSend]:: NODE %d: LLC layer sends a packet to MAC layer.", node->Id);

		pthread_mutex_lock(&(node->nodeLlc->ltom_array_mutex));	                       
		if (node->nodeLlc->LToMArray[(node->nodeLlc->ltom_buf_Rcount)]==NULL){
			pthread_mutex_unlock(&(node->nodeLlc->ltom_array_mutex));
			return (FALSE);
		}

		tmp_frame = node->nodeLlc->LToMArray[node->nodeLlc->ltom_buf_Rcount];    
		node->nodeLlc->LToMArray[node->nodeLlc->ltom_buf_Rcount] = NULL;		
		node->nodeLlc->ltom_buf_Rcount = (node->nodeLlc->ltom_buf_Rcount+1)%LLC_TO_MAC_BUF_SIZE;	
		if (node->nodeLlc->LToMArray[(node->nodeLlc->ltom_buf_Rcount)]==NULL)
		    node->nodeLlc->ltombufempty = TRUE;
		pthread_mutex_unlock(&(node->nodeLlc->ltom_array_mutex));	    

		// Convert the 802.3 frame to 802.11 frame
		frame = WGN_802_3_To_11_Frame_Converter (node, tmp_frame);				
		tmp_frame = NULL;
        // Pass the frame to MAC layer.
		MacUpPortRecv (node, frame);
		return (TRUE);
	}

//=======================================================
//       FUNCTION:   LlcUpPortSend  (all nodes share the same MacToLlc buffer, thread)
//======================================================= 
    void  LlcUpPortSend(MobileNode *node) {   
	    WGN_802_11_Mac_Frame *frame;
        unsigned char* tmp_frame;
	    int frame_len;
	    int body_len;

	    while(1) {   
		    pthread_mutex_lock(&(node->nodeLlc->ltou_array_mutex));	
		    while (node->nodeLlc->LToUArray[node->nodeLlc->ltou_buf_Rcount]==NULL){
			          pthread_cond_wait(&(node->nodeLlc->ltou_nonempty), &(node->nodeLlc->ltou_array_mutex));
		    }

			frame = node->nodeLlc->LToUArray[node->nodeLlc->ltou_buf_Rcount];    
			node->nodeLlc->LToUArray[node->nodeLlc->ltou_buf_Rcount] = NULL;		
			node->nodeLlc->ltou_buf_Rcount = (node->nodeLlc->ltou_buf_Rcount+1)%LLC_TO_UML_BUF_SIZE;	
		    pthread_mutex_unlock(&(node->nodeLlc->ltou_array_mutex));  

			verbose(4, "[LlcUpPortSend]:: NODE %d: LLC layer sends a packet to the UML.", node->Id);
            
			// Convert the 802.11 frame to 802.3 one.
			body_len = Get_Payload_Length (frame->frame_body);
	        frame_len = body_len + DOT_3_HDR_LEN;
            tmp_frame = WGN_802_11_To_3_Frame_Converter(node, frame, body_len, frame_len); 
			// Send the 802.3 frame to the UMLs. 
	        vpl_sendto(node->nodeLlc->inf->iDescriptor, (void *)tmp_frame, frame_len, &(node->nodeLlc->inf->sVPLdata));	
			//  Free memory space.
			Dot11FrameFree(frame);
			free(tmp_frame);
			tmp_frame = NULL;
	    }
	}

//=======================================================
//       FUNCTION:   LlcDownPortRecv  (all nodes share the same MacToLlc buffer)
//                            The input should be dot_11 frame cause I need the dst id.
//======================================================= 
    void LlcDownPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame) {
	   WGNflag fullArray;

	   verbose(4, "[LlcDownPortRecv]:: NODE %d: LLC layer receives a packet from MAC layer.", node->Id);
    	   
	   fullArray=FALSE;
	   // Pass the frame to the LToUArray buffer
	   pthread_mutex_lock(&(node->nodeLlc->ltou_array_mutex));	
	   // If still empty space for the new incoming packet
	   if (node->nodeLlc->LToUArray[node->nodeLlc->ltou_buf_Wcount]==NULL) {
	   	   node->nodeLlc->LToUArray[node->nodeLlc->ltou_buf_Wcount] = frame;
		   //update index
		   pthread_cond_signal(&(node->nodeLlc->ltou_nonempty));  
		   node->nodeLlc->ltou_buf_Wcount = (node->nodeLlc->ltou_buf_Wcount+1)%LLC_TO_UML_BUF_SIZE;
	   }
	   else 		 
	       fullArray=TRUE;
	   pthread_mutex_unlock(&(node->nodeLlc->ltou_array_mutex));

	   if(fullArray==TRUE) {
          verbose(4, "[LlcDownPortRecv]:: NODE %d: LLC to UML buffer is full, packet thrown.", node->Id); 
	      Dot11FrameFree(frame);
		  node->nodeStats->LToUBufDrop += 1;
	   }
	   return;
    }

//=======================================================
//       FUNCTION:   WGN_802_3_FrameDup
//======================================================= 
    WGN_802_3_Mac_Frame* WGN_802_3_FrameDup(unsigned char* input_frame, int byte_no) {
	    WGN_802_3_Mac_Frame* frame;
		int data_len;
		
		data_len = byte_no - DOT_3_HDR_LEN;
		frame = (WGN_802_3_Mac_Frame*)malloc(sizeof(WGN_802_3_Mac_Frame));
		frame->payload_len = data_len;
		frame->data = (unsigned char*)malloc(sizeof(unsigned char)*data_len);		
		memcpy(&(frame->header), input_frame, DOT_3_HDR_LEN);
		memcpy(frame->data, &(input_frame[DOT_3_HDR_LEN]), data_len);
		
		return(frame);
    }

//=======================================================
//       FUNCTION:   WGN_802_3_To_11_Frame_Converter 
//       PURPOSE:    Convert the Mac_802_3_DATA_Frame to 
//                               Mac_802_11_DATA_Frame
//======================================================= 
  WGN_802_11_Mac_Frame* WGN_802_3_To_11_Frame_Converter(MobileNode *node, WGN_802_3_Mac_Frame *dot_3_frame) {	
		 WGN_802_11_Mac_Pseudo_Header *hdr;
		 WGN_802_11_Mac_Frame* dot_11_frame;
		 int payload_len;
		 unsigned char *sa;
		 unsigned char *da;
		 unsigned char *BSSID;

		 BSSID = node->nodeMac->BSSID;
		 dot_11_frame = (WGN_802_11_Mac_Frame*)malloc(sizeof(WGN_802_11_Mac_Frame));
		 //construct the pseudo hdr 
		 dot_11_frame->pseudo_header = (WGN_802_11_Mac_Pseudo_Header *)malloc(sizeof(WGN_802_11_Mac_Pseudo_Header));
		 hdr = dot_11_frame->pseudo_header;
         Set_WGN_802_11_Mac_Pseudo_Frame_Control(&(hdr->fc), MAC_DATA_FRAME);
		 Set_WGN_802_11_Mac_Pseudo_Sequence_Control (node, &(hdr->sc));

		 sa = Dot_3_GetSa(dot_3_frame);
		 da = Dot_3_GetDa(dot_3_frame);
		 memcpy(hdr->SA, sa, MAC_ADDR_LEN);
		 memcpy(hdr->DA, da, MAC_ADDR_LEN);
		 memcpy(hdr->BSSID, BSSID, MAC_ADDR_LEN);
		 memset(hdr->TA, 0, MAC_ADDR_LEN);
		 memset(hdr->RA, 0, MAC_ADDR_LEN);
		 if (CheckIfIsBroadCastPkt(dot_11_frame) == TRUE) 
			  hdr->duration = 0;
		 else
		      hdr->duration = DATA_DURATION();
		 hdr->fcs = 0;	 
		 //Get the node id from the address group
		 hdr->srcid = GetID(hdr->SA);
	     hdr->dstid = GetID(hdr->DA);
		 //in single-hop mode, srcid==txid && dstid==rxid
	     hdr->txid = hdr->srcid;
	     hdr->rxid = hdr->dstid;
		 
		 hdr->colErrorSign = FALSE;
		 hdr->fadErrorSign = FALSE;
		 hdr->noiseErrorSign = FALSE;
		 payload_len = Get_Payload_Length(dot_3_frame);
		 hdr->mac_size = payload_len + MAC_DATA_HDR_LEN;
		 hdr->phy_size = payload_len + PHY_DATA_HDR_LEN;
		 
		 //construct the real frame body
         dot_11_frame->frame_body = dot_3_frame;
		 return(dot_11_frame);
  } 

//=======================================================
//       FUNCTION:   WGN_802_11_To_3_Frame_Converter 
//       PURPOSE:    Convert the Mac_802_11_DATA_Frame to 
//                               Mac_802_3_DATA_Frame
//======================================================= 
  unsigned char* WGN_802_11_To_3_Frame_Converter(MobileNode *node, WGN_802_11_Mac_Frame *dot_11_frame, int body_len, int frame_len) {	
	  unsigned char* tmp_frame;
	 
	  tmp_frame = (unsigned char*)malloc(sizeof(char)*frame_len);
	  memcpy(tmp_frame, &(dot_11_frame->frame_body->header), DOT_3_HDR_LEN);
	  memcpy(&(tmp_frame[DOT_3_HDR_LEN]), dot_11_frame->frame_body->data, body_len);
      return(tmp_frame);
  }

//=======================================================
//       FUNCTION:   conn_open
//       PURPOSE:    Setup an individual connection between UML and WGINI
//======================================================= 
void conn_open(MobileNode *node,char* pchSocket){
	struct vpl_data *psUMLConn;
	struct interface *psRet;
	struct timeval sWaitTime;
	struct {
		char zero;
		int pid;
		int usecs;
	} name;
	int ret;
	
	// Set up UML connection parameters
	psUMLConn = (struct vpl_data *) malloc(sizeof(struct vpl_data));
	bzero(psUMLConn,sizeof(struct vpl_data));
	psUMLConn->sock_type = "unix";
	psUMLConn->ctl_sock = pchSocket;
	psUMLConn->ctl_addr = new_addr(psUMLConn->ctl_sock, strlen(psUMLConn->ctl_sock) + 1);
	psUMLConn->data_addr = NULL;
	psUMLConn->fd = -1;
	psUMLConn->control = -1;
	name.zero = 0;
	name.pid = getpid();
	gettimeofday(&sWaitTime, NULL);
	name.usecs = sWaitTime.tv_usec;
	psUMLConn->local_addr = new_addr(&name, sizeof(name));
	// Connect to the UML
	if ((psUMLConn->fd = vpl_connect(psUMLConn)) < 0) {
		 free (psUMLConn);
		 printf("[LlcProcess]:: The connection from UML to LLC is failed.\n");
		 return;
	}
	// Fill the interface data structure
	psRet = (struct interface*) malloc(sizeof(struct interface));
	bzero(psRet,sizeof(struct interface));
	psRet->node_id = node->Id;
	psRet->iDescriptor = psUMLConn->fd;
	memcpy(&psRet->sVPLdata, psUMLConn, sizeof(struct vpl_data));
	free(psUMLConn);
	// Setup a thread for the new connection
	memcpy(node->nodeLlc->inf, psRet, sizeof(struct interface));
	ret=pthread_create(&(node->nodeLlc->inf->threadID), NULL, (void *)LlcUpPortRecv, (void*)(node->nodeLlc->inf));
}

//=======================================================
//       FUNCTION:   conn_close
//       PURPOSE:    Close an individual connection
//======================================================= 
void conn_close(struct interface* psInt){
    if (psInt!=NULL) {
		// Cancel the corresponding thread
		pthread_cancel(psInt->threadID);   
		// Close the corresponding data socket
		close(psInt->iDescriptor);	
		// Close the corresponding control socket
		close(psInt->sVPLdata.control);
		// Free the memory space assigned for the interface
		free(psInt);
	}
	else 
		printf("[conn_close]:: Try to close a null interface! \n");
	return;
}

//=======================================================
//       FUNCTION:  SocketNameGen
//=======================================================
void SocketNameGen(int id, char* sktname) {    
	char index[10];

	if (wgnconfig.vs_directory == NULL) { 
		sprintf(index,"%d",id);
    strcpy(sktname,getenv("GINI_HOME"));
		strcat(sktname,"/data/uml_virtual_switch/");
		strcat(sktname,index);
		strcat(sktname,"/uml");
		strcat(sktname, index);
		strcat(sktname,".ctl");
	} else {
		sprintf(index,"%d",id);
		strcpy(sktname,wgnconfig.vs_directory);
		strcat(sktname,"/VS_");
		strcat(sktname,index);
		strcat(sktname,"/gw_socket.ctl");	
	}
}

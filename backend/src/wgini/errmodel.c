/*
 * NAME: erromodel.c 
 * FUNCTION: Collection of functions implements the error module. This file
 *                    provides the functions to calculate the bit error probability ba-
 *                    sed on different modulation methods.
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */


//=======================================================
//       File Name :  errmodel.c
//=======================================================  
#include "errmodel.h"

//The relationship Q(x) = 0.5*erfc(x/sqrt(2));

//=======================================================
//       FUNCTION:  GetNCDDBPSKBitErrProb
//		 Non-Coherent Demodulation DBPSK: 	1/2*exp(-Eb/N0)
//======================================================= 
  double GetNCDDBPSKBitErrProb(double snr) {
	 double pb;	 
     pb = 0.5*exp(-snr);
	 return (pb);
  }

//=======================================================
//       FUNCTION:  GetCDDBPSKBitErrProb
//		 Coherent Demodulation DBPSK: 	2*Q(sqrt(Eb/N0))
//======================================================= 
  double GetCDDBPSKBitErrProb(double snr) {
	 double pb;	 
     pb = erfc(sqrt(snr/2));
	 return (pb);
  }

//=======================================================
//       FUNCTION:  GetDQPSKBitErrProb
//       DQPSK:    Q(sqrt(Eb/N0))
//======================================================= 
  double GetDQPSKBitErrProb(double snr) {
	 double pb;
     pb = 0.5*erfc(sqrt(snr/2));
	 return (pb);
  }

//=======================================================
//       FUNCTION:  GetBPSKBitErrProb
//       BPSK:    Q(sqrt(2*Eb/N0))
//======================================================= 
  double GetBPSKBitErrProb(double snr) {
	 double pb;
     pb = 0.5*erfc(sqrt(snr));
	 return (pb);
  }

//=======================================================
//       FUNCTION:  GetFSKBitErrProb
//		 Non-Coherent Demodulation FSK: 	1/2*exp(-Eb/(2*N0))
//======================================================= 
  double GetFSKBitErrProb(double snr) {
	 double pb;	 
     pb = 0.5*exp(-snr/2);
	 return (pb);
  }

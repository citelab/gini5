//=======================================================
//       File Name :  MathLab.h
//======================================================= 
  #include <math.h>
  #include <stdio.h>
  #include <stdio.h>     
  #include <sys/socket.h> 
  #include <arpa/inet.h> 
  #include <stdlib.h>    
  #include <string.h>     
  #include <unistd.h>     
 
  #include "gwcenter.h"

  double NormalDist(double mean,double dev); 
  double UnitUniform(void);
  double Absolute(double x); 
  double Max(double x, double y);
  double WToDB(double x);
  double DBToW(double x);
  unsigned int SecToUsec(double time); 
  unsigned int SecToNsec(double time);
  unsigned int UsecToNsec(double time); 


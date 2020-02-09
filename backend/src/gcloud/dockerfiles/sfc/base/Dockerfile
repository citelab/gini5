FROM alpine:latest

LABEL maintainer="trung.vuongthien@mail.mcgill.ca"

RUN apk add --update --no-cache \
        curl \
        iptables \
	iptables-doc \
        ebtables \
        tcpdump \
	man  \
	man-pages \
	mdocml-apropos  \
	nmap \
	iproute2 \
	nftables \ 
	iperf

RUN apk add --update --no-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
	hping3 \
	hping3-doc \
	ettercap \
	ettercap-doc 

CMD ["/bin/sh"]


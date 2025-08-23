NYC_AIRPORTS = ["JFK","LGA","EWR","HPN","ISP","SWF"]
ORIGIN_METRO = {a:"NYC" for a in NYC_AIRPORTS}

CARIBBEAN_AIRPORTS = [
  "SJU","STT","STX","SDQ","PUJ","POP","STI","MBJ","KIN","AUA","CUR","BON",
  "BGI","ANU","SKB","EIS","DOM","GND","SXM","PTP","FDF","NAS","GGT","ELH","FPO",
  "GCM","PLS"
]
DEST_REGION = {code:"caribbean" for code in CARIBBEAN_AIRPORTS}
DEST_COUNTRY = {
  "SJU":"PR","ANU":"AG","AUA":"AW","BON":"BQ","CUR":"CW","MBJ":"JM","KIN":"JM",
  "BGI":"BB","NAS":"BS","PLS":"TC","GCM":"KY","SXM":"SX","PUJ":"DO","SDQ":"DO",
  "STT":"VI","STX":"VI","GND":"GD","PTP":"GP","FDF":"MQ"
}
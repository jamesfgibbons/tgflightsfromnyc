# NYC airports and Caribbean mapping used by SERP Radio.
NYC_AIRPORTS = ["JFK","LGA","EWR","HPN","ISP","SWF"]
ORIGIN_METRO = {a:"NYC" for a in NYC_AIRPORTS}

# Caribbean airports (extend as needed)
CARIBBEAN_AIRPORTS = [
  # Greater Antilles
  "SJU","STT","STX","SDQ","PUJ","POP","STI","MBJ","KIN","HAV",
  # Lesser Antilles & Bahamas
  "AUA","CUR","BON","BGI","ANU","SKB","EIS","DOM","GND","SXM","PTP","FDF",
  "NAS","GGT","ELH","FPO","GCM","PLS"
]
DEST_REGION = {code: "caribbean" for code in CARIBBEAN_AIRPORTS}

DEST_COUNTRY = {
  "SJU":"PR","AUA":"AW","CUR":"CW","BGI":"BB","NAS":"BS","MBJ":"JM","PLS":"TC",
  "GCM":"KY","SXM":"SX","PUJ":"DO","SDQ":"DO","STT":"VI","ANU":"AG","HAV":"CU",
  "STX":"VI","POP":"DO","STI":"DO","KIN":"JM","GGT":"BS","ELH":"BS","FPO":"BS",
  "BON":"BQ","EIS":"VG","DOM":"DM","GND":"GD","PTP":"GP","FDF":"MQ","SKB":"KN"
}

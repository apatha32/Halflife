# 0001 — SMART attributes kept in silver

Silver keeps nine raw SMART attributes: 5 (reallocated sectors), 187 (reported
uncorrectable), 188 (command timeout), 197 (current pending sectors), 198
(offline uncorrectable), 9 (power-on hours), 12 (power cycles), 194
(temperature) and 199 (UDMA CRC errors). The first five are the attributes
Backblaze itself found most predictive of failure, and 9, 12, 194 and 199 add
age, stress and cabling context. On the 1% sample of 2024-2025 bronze, all nine
are under 2% null for Seagate, Toshiba, WDC and HGST (95%+ of drive-days),
except 187 and 188, which only Seagate reports (100% null for Toshiba and HGST,
~99% for WDC); we keep them because Seagate is the largest maker in the fleet
and LightGBM handles the nulls natively. We dropped attributes that are mostly
null or vendor-specific in meaning (189, 190, 240-242, which are 78-100% null
outside one maker) and normalized values, whose scale differs by vendor.
Counters 5, 9, 12, 187, 188, 198 and 199 should only grow, so silver rebases
them when they drop; 194 and 197 are gauges and are left as reported.

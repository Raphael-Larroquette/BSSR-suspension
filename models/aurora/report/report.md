# Suspension characteristic report

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\models\aurora\front.yaml`
- geometry SHA-256: `2360b2b22835a7fd...`
- format version: 3
- reported side: **left**

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 65 | True | 4.18e-06 | - |
| `02_roll` | roll | 65 | True | 3.65e-06 | - |
| `03_single_wheel_bump` | single_wheel | 65 | True | 4.01e-06 | - |
| `04_steer_design` | steer | 65 | True | 4.35e-06 | - |
| `05_steer_bump` | steer | 65 | True | 4.28e-06 | Held at +40.0 mm wheel travel, not design height. |
| `06_steer_droop` | steer | 65 | True | 4.62e-06 | Held at -40.0 mm wheel travel, not design height. |
| `07_bump_at_steer` | heave_at_steer | 65 | True | 4.08e-06 | Rack held at +20.00 mm - this is a STEERED sweep. |
| `08_damper_stroke` | damper_stroke | 65 | True | 2.14e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |

## 01_bump_parallel  (heave)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0000 | -1.3311 | 0.1213 | 1.4524 |
| Caster | deg | 10.0000 | 9.9969 | 10.0469 | 0.0500 |
| Kingpin inclination | deg | 10.0000 | 9.8769 | 11.3310 | 1.4542 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0069 | 0.0166 | 0.0235 |
| ISO steer angle | deg | -0.0000 | -0.0166 | 0.0069 | 0.0235 |
| Scrub radius (ISO unsigned) | mm | 54.7086 | 54.6909 | 54.8595 | 0.1687 |
| Scrub radius (signed lateral) | mm | -23.8609 | -23.9661 | -23.8519 | 0.1142 |
| Steering-axis offset at ground | mm | -23.8609 | -23.9661 | -23.8519 | 0.1142 |
| Mechanical trail | mm | 49.2309 | 49.2156 | 49.3477 | 0.1321 |
| Half track | mm | 431.2630 | 419.7472 | 431.3512 | 11.6040 |
| Wheel travel | mm | -0.0000 | -63.5000 | 63.5000 | 127.0000 |
| Damper length | mm | 242.8113 | 209.6621 | 274.7803 | 65.1182 |
| Motion ratio (damper/wheel) | mm/mm | 0.5113 | 0.4984 | 0.5324 | 0.0340 |
| Motion ratio squared | - | 0.2615 | 0.2484 | 0.2835 | 0.0350 |
| Front-view IC, y | mm | -5930.6063 | -156225.5218 | 157025.6131 | 313251.1349 |
| Front-view IC, z | mm | 185.0001 | -25357.7228 | 23813.3103 | 49171.0332 |
| Front-view swing-arm length | mm | 6364.5790 | -158632.2369 | 158458.0578 | 317090.2947 |
| Side-view IC, x | mm | nan | -15359909.9339 | 15274171.0123 | 30634080.9462 |
| Side-view IC, z | mm | nan | 423.6196 | 630.5541 | 206.9345 |
| Side-view swing-arm length | mm | nan | -15359909.9336 | 15274171.0120 | 30634080.9455 |
| Side-view swing-arm angle | deg | nan | -0.0654 | 0.0701 | 0.1354 |
| Camber, road-relative | deg | -0.0000 | -1.3311 | 0.1213 | 1.4524 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 862.5260 | 862.5260 | 862.5260 | 0.0000 |
| Track change | mm | 0.0000 | -23.0316 | 0.1764 | 23.2080 |
| Track change rate | mm/mm | 0.0577 | -0.5469 | 0.6721 | 1.2190 |
| Roll-centre height | mm | 11.8884 | -52.6506 | 76.5638 | 129.2145 |
| Roll-centre lateral position | mm | -0.0000 | -0.0001 | 0.0000 | 0.0002 |
| Roll-centre migration vs travel | mm/mm | -1.0397 | -1.0437 | -0.9001 | 0.1436 |
| Body roll | deg | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | -0.0000 | -63.5000 | 63.5000 | 127.0000 |
| Ride-height change | mm | 0.0000 | -63.5753 | 63.4986 | 127.0739 |
| Rack displacement | mm | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Steering ratio | deg/mm | -0.6832 | -0.7555 | -0.6171 | 0.1384 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0089 | -0.0367 | 0.0188 | 0.0556 |
| Bump steer rate | deg/mm | -0.0004 | -0.0004 | 0.0010 | 0.0015 |
| ISO steer gain in bump | deg/mm | 0.0004 | -0.0010 | 0.0004 | 0.0015 |
| Caster gain | deg/mm | 0.0003 | -0.0007 | 0.0014 | 0.0021 |
| KPI gain | deg/mm | 0.0090 | -0.0190 | 0.0366 | 0.0557 |
| Half-track change rate | mm/mm | 0.0289 | -0.2734 | 0.3360 | 0.6095 |
| Wheel-centre recession rate | mm/mm | -0.0002 | -0.0004 | 0.0008 | 0.0012 |
| Damper rate vs wheel | mm/mm | -0.5113 | -0.5324 | -0.4984 | 0.0340 |
| Toe per rack | deg/mm | 0.6832 | 0.6171 | 0.7555 | 0.1384 |
| Steer per rack | deg/mm | -0.6832 | -0.7555 | -0.6171 | 0.1384 |
| Camber per rack | deg/mm | -0.1200 | -0.1344 | -0.1071 | 0.0273 |

## 02_roll  (roll)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0000 | -0.3275 | 0.1209 | 0.4484 |
| Caster | deg | 10.0000 | 9.9969 | 10.0107 | 0.0138 |
| Kingpin inclination | deg | 10.0000 | 9.8773 | 10.3287 | 0.4514 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0065 | 0.0105 | 0.0169 |
| ISO steer angle | deg | -0.0000 | -0.0105 | 0.0065 | 0.0169 |
| Scrub radius (ISO unsigned) | mm | 54.7086 | 54.4371 | 55.0351 | 0.5979 |
| Scrub radius (signed lateral) | mm | -23.8609 | -24.1367 | -23.6750 | 0.4617 |
| Steering-axis offset at ground | mm | -23.8609 | -24.1367 | -23.6750 | 0.4617 |
| Mechanical trail | mm | 49.2309 | 49.0193 | 49.4599 | 0.4405 |
| Half track | mm | 431.2630 | 429.0572 | 431.3512 | 2.2940 |
| Wheel travel | mm | -0.0000 | -25.0000 | 25.0000 | 50.0000 |
| Damper length | mm | 242.8113 | 229.9249 | 255.5027 | 25.5778 |
| Motion ratio (damper/wheel) | mm/mm | 0.5113 | 0.5043 | 0.5197 | 0.0154 |
| Motion ratio squared | - | 0.2615 | 0.2543 | 0.2701 | 0.0158 |
| Front-view IC, y | mm | -5930.6063 | -87020.2499 | -2847.7095 | 84172.5405 |
| Front-view IC, z | mm | 185.0001 | -267.3898 | 12946.8730 | 13214.2628 |
| Front-view swing-arm length | mm | 6364.5790 | 3291.1713 | 88406.2721 | 85115.1008 |
| Side-view IC, x | mm | nan | -38950174.0923 | 38864360.6590 | 77814534.7513 |
| Side-view IC, z | mm | nan | 487.1425 | 563.9190 | 76.7765 |
| Side-view swing-arm length | mm | nan | -38950174.0921 | 38864360.6589 | 77814534.7510 |
| Side-view swing-arm angle | deg | nan | -0.0248 | 0.0253 | 0.0501 |
| Camber, road-relative | deg | -0.0000 | -3.6605 | 3.4539 | 7.1144 |
| Camber recovery | deg/deg | -0.0673 | -0.1290 | -0.0054 | 0.1237 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 862.5260 | 862.5260 | 862.5260 | 0.0000 |
| Track change | mm | 0.0000 | -1.5056 | 0.0000 | 1.5056 |
| Track change rate | mm/mm | 0.0577 | -0.1783 | 0.2960 | 0.4742 |
| Roll-centre height | mm | 11.8884 | -91.8693 | 11.8884 | 103.7577 |
| Roll-centre lateral position | mm | 0.0001 | -875.1146 | 875.1144 | 1750.2290 |
| Roll-centre migration vs roll | mm/deg | 0.0000 | -60.0785 | 60.0780 | 120.1564 |
| Roll-centre lateral migration vs roll | mm/deg | -268.0858 | -268.0858 | -252.2991 | 15.7866 |
| Body roll | deg | -0.0000 | -3.3330 | 3.3330 | 6.6659 |
| Heave | mm | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Ride-height change | mm | -0.0000 | -0.0000 | 0.0384 | 0.0384 |
| Rack displacement | mm | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Steering ratio | deg/mm | -0.6832 | -0.7060 | -0.6609 | 0.0451 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0089 | -0.0175 | -0.0006 | 0.0169 |
| Bump steer rate | deg/mm | -0.0004 | -0.0004 | -0.0001 | 0.0003 |
| ISO steer gain in bump | deg/mm | 0.0004 | 0.0001 | 0.0004 | 0.0003 |
| Caster gain | deg/mm | 0.0003 | -0.0000 | 0.0006 | 0.0006 |
| KPI gain | deg/mm | 0.0090 | 0.0007 | 0.0175 | 0.0168 |
| Half-track change rate | mm/mm | 0.0289 | -0.0891 | 0.1480 | 0.2371 |
| Wheel-centre recession rate | mm/mm | -0.0002 | -0.0004 | 0.0002 | 0.0005 |
| Damper rate vs wheel | mm/mm | -0.5113 | -0.5197 | -0.5043 | 0.0154 |
| Toe per rack | deg/mm | 0.6832 | 0.6609 | 0.7060 | 0.0451 |
| Steer per rack | deg/mm | -0.6832 | -0.7060 | -0.6609 | 0.0451 |
| Camber per rack | deg/mm | -0.1200 | -0.1244 | -0.1157 | 0.0088 |

## 03_single_wheel_bump  (single_wheel)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0000 | -1.3311 | 0.1213 | 1.4524 |
| Caster | deg | 10.0000 | 9.9969 | 10.0469 | 0.0500 |
| Kingpin inclination | deg | 10.0000 | 9.8769 | 11.3310 | 1.4542 |
| Toe (positive = toe-in) | deg | 0.0000 | -0.0069 | 0.0166 | 0.0235 |
| ISO steer angle | deg | -0.0000 | -0.0166 | 0.0069 | 0.0235 |
| Scrub radius (ISO unsigned) | mm | 54.7086 | 54.4550 | 55.1912 | 0.7362 |
| Scrub radius (signed lateral) | mm | -23.8609 | -24.2664 | -23.6794 | 0.5869 |
| Steering-axis offset at ground | mm | -23.8609 | -24.2664 | -23.6794 | 0.5869 |
| Mechanical trail | mm | 49.2309 | 49.0370 | 49.5703 | 0.5333 |
| Half track | mm | 431.2630 | 419.7472 | 431.3512 | 11.6040 |
| Wheel travel | mm | 0.0000 | -63.5000 | 63.5000 | 127.0000 |
| Damper length | mm | 242.8113 | 209.6621 | 274.7803 | 65.1182 |
| Motion ratio (damper/wheel) | mm/mm | 0.5113 | 0.4984 | 0.5324 | 0.0340 |
| Motion ratio squared | - | 0.2615 | 0.2484 | 0.2835 | 0.0350 |
| Front-view IC, y | mm | -5930.6063 | -156225.5230 | 157025.6101 | 313251.1331 |
| Front-view IC, z | mm | 185.0000 | -25357.7232 | 23813.3108 | 49171.0340 |
| Front-view swing-arm length | mm | 6364.5790 | -158632.2339 | 158458.0591 | 317090.2930 |
| Side-view IC, x | mm | nan | -15359910.8154 | 15274179.9551 | 30634090.7705 |
| Side-view IC, z | mm | nan | 423.6196 | 630.5541 | 206.9345 |
| Side-view swing-arm length | mm | nan | -15359910.8151 | 15274179.9547 | 30634090.7698 |
| Side-view swing-arm angle | deg | nan | -0.0654 | 0.0701 | 0.1354 |
| Camber, road-relative | deg | -0.0000 | -5.6120 | 4.0885 | 9.7005 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 862.5260 | 862.5260 | 862.5260 | 0.0000 |
| Track change | mm | 0.0000 | -9.1501 | 0.1169 | 9.2670 |
| Track change rate | mm/mm | 0.0577 | -0.5469 | 0.6721 | 1.2190 |
| Roll-centre height | mm | 11.8884 | -158.4803 | 69.8699 | 228.3502 |
| Roll-centre lateral position | mm | 0.0000 | -5836.6351 | 1986.3800 | 7823.0152 |
| Roll-centre migration vs travel | mm/mm | -0.5336 | -40.0215 | 50.2099 | 90.2313 |
| Body roll | deg | 0.0000 | -4.2718 | 4.2808 | 8.5526 |
| Heave | mm | -0.0000 | -31.7500 | 31.7500 | 63.5000 |
| Ride-height change | mm | 0.0000 | -31.9883 | 32.0878 | 64.0761 |
| Rack displacement | mm | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Steering ratio | deg/mm | -0.6832 | -0.7555 | -0.6171 | 0.1384 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0089 | -0.0367 | 0.0188 | 0.0556 |
| Bump steer rate | deg/mm | -0.0004 | -0.0004 | 0.0010 | 0.0015 |
| ISO steer gain in bump | deg/mm | 0.0004 | -0.0010 | 0.0004 | 0.0015 |
| Caster gain | deg/mm | 0.0003 | -0.0007 | 0.0014 | 0.0021 |
| KPI gain | deg/mm | 0.0090 | -0.0190 | 0.0366 | 0.0557 |
| Half-track change rate | mm/mm | 0.0289 | -0.2734 | 0.3360 | 0.6095 |
| Wheel-centre recession rate | mm/mm | -0.0002 | -0.0004 | 0.0008 | 0.0012 |
| Damper rate vs wheel | mm/mm | -0.5113 | -0.5324 | -0.4984 | 0.0340 |
| Toe per rack | deg/mm | 0.6832 | 0.6171 | 0.7555 | 0.1384 |
| Steer per rack | deg/mm | -0.6832 | -0.7555 | -0.6171 | 0.1384 |
| Camber per rack | deg/mm | -0.1200 | -0.1344 | -0.1071 | 0.0273 |

## 04_steer_design  (steer)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -3.4602 | 6.1973 | 9.6575 |
| Caster | deg | 10.0000 | 9.9996 | 10.0007 | 0.0011 |
| Kingpin inclination | deg | 10.0000 | 9.9876 | 10.0232 | 0.0356 |
| Toe (positive = toe-in) | deg | -0.0000 | -26.3992 | 23.6165 | 50.0157 |
| ISO steer angle | deg | 0.0000 | -23.6165 | 26.3992 | 50.0157 |
| Scrub radius (ISO unsigned) | mm | 54.7086 | 34.4545 | 70.4473 | 35.9928 |
| Scrub radius (signed lateral) | mm | -23.8609 | -24.1726 | -23.5757 | 0.5969 |
| Steering-axis offset at ground | mm | -23.8609 | -24.1726 | -23.5757 | 0.5969 |
| Mechanical trail | mm | 49.2309 | 25.1256 | 66.1702 | 41.0446 |
| Half track | mm | 431.2630 | 404.3032 | 443.2212 | 38.9180 |
| Wheel travel | mm | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Damper length | mm | 242.8113 | 241.5493 | 243.5314 | 1.9820 |
| Motion ratio (damper/wheel) | mm/mm | 0.5113 | 0.5107 | 0.5118 | 0.0011 |
| Motion ratio squared | - | 0.2615 | 0.2608 | 0.2619 | 0.0011 |
| Front-view IC, y | mm | -5930.6063 | -6268.3878 | -5413.8808 | 854.5070 |
| Front-view IC, z | mm | 185.0000 | 104.2071 | 238.1189 | 133.9118 |
| Front-view swing-arm length | mm | 6364.5790 | 5819.1062 | 6715.8414 | 896.7352 |
| Side-view IC, x | mm | nan | -516924661.4177 | 525115414.2124 | 1042040075.6301 |
| Side-view IC, z | mm | nan | 523.0621 | 528.8529 | 5.7908 |
| Side-view swing-arm length | mm | nan | -516924661.0948 | 525115413.8737 | 1042040074.9685 |
| Side-view swing-arm angle | deg | nan | -0.0024 | 0.0014 | 0.0038 |
| Camber, road-relative | deg | 0.0000 | -3.4602 | 6.1973 | 9.6575 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 862.5260 | 862.5260 | 862.5260 | 0.0000 |
| Track change | mm | 0.0000 | -15.0012 | 0.0000 | 15.0012 |
| Track change rate | mm/mm | 0.0577 | 0.0553 | 0.2096 | 0.1544 |
| Roll-centre height | mm | 11.8884 | 10.3680 | 11.8884 | 1.5204 |
| Roll-centre lateral position | mm | -0.0000 | -143.6519 | 143.6519 | 287.3038 |
| Body roll | deg | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Ride-height change | mm | 0.0000 | -0.8897 | 0.0000 | 0.8897 |
| Rack displacement | mm | -0.0000 | -35.0000 | 35.0000 | 70.0000 |
| Ackermann error (inner - outer) | deg | 0.0000 | 0.0000 | 2.7826 | 2.7826 |
| Ackermann | % | nan | 48.5978 | 67.5964 | 18.9986 |
| Steering ratio | deg/mm | -0.6832 | -0.9074 | -0.6716 | 0.2357 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0089 | -0.0196 | -0.0040 | 0.0156 |
| Bump steer rate | deg/mm | -0.0004 | -0.0369 | 0.0313 | 0.0681 |
| ISO steer gain in bump | deg/mm | 0.0004 | -0.0313 | 0.0369 | 0.0681 |
| Caster gain | deg/mm | 0.0003 | 0.0003 | 0.0003 | 0.0000 |
| KPI gain | deg/mm | 0.0090 | 0.0086 | 0.0098 | 0.0012 |
| Half-track change rate | mm/mm | 0.0289 | 0.0276 | 0.1048 | 0.0772 |
| Wheel-centre recession rate | mm/mm | -0.0002 | -0.0150 | 0.0121 | 0.0270 |
| Damper rate vs wheel | mm/mm | -0.5113 | -0.5118 | -0.5107 | 0.0011 |
| Toe per rack | deg/mm | 0.6832 | 0.6716 | 0.9074 | 0.2357 |
| Steer per rack | deg/mm | -0.6832 | -0.9074 | -0.6716 | 0.2357 |
| Camber per rack | deg/mm | -0.1200 | -0.2883 | -0.0842 | 0.2041 |

## 05_steer_bump  (steer)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.6339 | -3.8801 | 5.1251 | 9.0052 |
| Caster | deg | 10.0213 | 10.0202 | 10.0234 | 0.0031 |
| Kingpin inclination | deg | 10.6351 | 10.6043 | 10.6920 | 0.0877 |
| Toe (positive = toe-in) | deg | -0.0065 | -25.0840 | 22.0585 | 47.1425 |
| ISO steer angle | deg | 0.0065 | -22.0585 | 25.0840 | 47.1425 |
| Scrub radius (ISO unsigned) | mm | 54.7842 | 35.0159 | 71.4962 | 36.4803 |
| Scrub radius (signed lateral) | mm | -23.9095 | -24.2474 | -23.6254 | 0.6220 |
| Steering-axis offset at ground | mm | -23.9095 | -24.2474 | -23.6254 | 0.6220 |
| Mechanical trail | mm | 49.2915 | 25.8449 | 67.2590 | 41.4142 |
| Half track | mm | 428.6393 | 401.9634 | 440.2238 | 38.2603 |
| Wheel travel | mm | 40.0000 | 40.0000 | 40.0000 | 0.0000 |
| Damper length | mm | 222.0896 | 220.8498 | 222.7847 | 1.9349 |
| Motion ratio (damper/wheel) | mm/mm | 0.5250 | 0.5243 | 0.5258 | 0.0016 |
| Motion ratio squared | - | 0.2756 | 0.2749 | 0.2765 | 0.0017 |
| Front-view IC, y | mm | -2005.6485 | -2067.4732 | -1900.0707 | 167.4025 |
| Front-view IC, z | mm | -350.8443 | -357.7218 | -346.3477 | 11.3741 |
| Front-view swing-arm length | mm | 2465.3566 | 2336.1756 | 2537.2609 | 201.0853 |
| Side-view IC, x | mm | -786118.5590 | -812007.9851 | -742148.3576 | 69859.6275 |
| Side-view IC, z | mm | 588.2752 | 585.3548 | 591.2381 | 5.8833 |
| Side-view swing-arm length | mm | -786118.5623 | -812024.1206 | -742147.2751 | 69876.8455 |
| Side-view swing-arm angle | deg | -0.0400 | -0.0425 | -0.0385 | 0.0040 |
| Camber, road-relative | deg | -0.6339 | -3.8801 | 5.1251 | 9.0052 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 862.5260 | 862.5260 | 862.5260 | 0.0000 |
| Track change | mm | -5.2473 | -20.3387 | -5.2473 | 15.0914 |
| Track change rate | mm/mm | -0.3208 | -0.3269 | -0.1864 | 0.1405 |
| Roll-centre height | mm | -29.3841 | -29.3841 | -28.5693 | 0.8148 |
| Roll-centre lateral position | mm | 0.0000 | -4.0435 | 4.0435 | 8.0869 |
| Body roll | deg | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | 40.0000 | 40.0000 | 40.0000 | 0.0000 |
| Ride-height change | mm | -40.0171 | -40.7416 | -40.0171 | 0.7245 |
| Rack displacement | mm | -0.0000 | -35.0000 | 35.0000 | 70.0000 |
| Ackermann error (inner - outer) | deg | 0.0000 | 0.0000 | 3.0255 | 3.0255 |
| Ackermann | % | 295.1147 | 67.4391 | 459.7205 | 392.2814 |
| Steering ratio | deg/mm | -0.6460 | -0.8600 | -0.6251 | 0.2350 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0236 | -0.0359 | -0.0175 | 0.0184 |
| Bump steer rate | deg/mm | 0.0001 | -0.0437 | 0.0377 | 0.0814 |
| ISO steer gain in bump | deg/mm | -0.0001 | -0.0377 | 0.0437 | 0.0814 |
| Caster gain | deg/mm | 0.0008 | 0.0008 | 0.0009 | 0.0001 |
| KPI gain | deg/mm | 0.0236 | 0.0230 | 0.0246 | 0.0015 |
| Half-track change rate | mm/mm | -0.1604 | -0.1635 | -0.0932 | 0.0703 |
| Wheel-centre recession rate | mm/mm | 0.0004 | -0.0178 | 0.0149 | 0.0327 |
| Damper rate vs wheel | mm/mm | -0.5250 | -0.5258 | -0.5243 | 0.0016 |
| Toe per rack | deg/mm | 0.6460 | 0.6251 | 0.8600 | 0.2350 |
| Steer per rack | deg/mm | -0.6460 | -0.8600 | -0.6251 | 0.2350 |
| Camber per rack | deg/mm | -0.1127 | -0.2631 | -0.0786 | 0.1845 |

## 06_steer_droop  (steer)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0866 | -3.5901 | 6.7941 | 10.3842 |
| Caster | deg | 9.9989 | 9.9983 | 9.9992 | 0.0009 |
| Kingpin inclination | deg | 9.9107 | 9.8983 | 9.9191 | 0.0207 |
| Toe (positive = toe-in) | deg | 0.0156 | -27.8537 | 25.2202 | 53.0739 |
| ISO steer angle | deg | -0.0156 | -25.2202 | 27.8537 | 53.0739 |
| Scrub radius (ISO unsigned) | mm | 54.6947 | 33.2162 | 70.6270 | 37.4108 |
| Scrub radius (signed lateral) | mm | -23.8544 | -24.1674 | -23.5585 | 0.6089 |
| Steering-axis offset at ground | mm | -23.8544 | -24.1674 | -23.5585 | 0.6089 |
| Mechanical trail | mm | 49.2186 | 23.4161 | 66.3635 | 42.9474 |
| Half track | mm | 426.2925 | 398.4934 | 438.1359 | 39.6425 |
| Wheel travel | mm | -40.0000 | -40.0000 | -40.0000 | 0.0000 |
| Damper length | mm | 263.0420 | 261.7316 | 263.7796 | 2.0480 |
| Motion ratio (damper/wheel) | mm/mm | 0.5011 | 0.4990 | 0.5016 | 0.0026 |
| Motion ratio squared | - | 0.2511 | 0.2490 | 0.2516 | 0.0026 |
| Front-view IC, y | mm | 11200.2774 | 10004.3936 | 14131.8499 | 4127.4563 |
| Front-view IC, z | mm | -2422.1414 | -2892.8816 | -2228.1446 | 664.7370 |
| Front-view swing-arm length | mm | -11034.0390 | -14026.7169 | -9813.2647 | 4213.4522 |
| Side-view IC, x | mm | 695993.5040 | 668294.8214 | 750846.3688 | 82551.5474 |
| Side-view IC, z | mm | 463.5732 | 461.8928 | 468.5017 | 6.6089 |
| Side-view swing-arm length | mm | 695993.4906 | 668277.1398 | 750844.3351 | 82567.1952 |
| Side-view swing-arm angle | deg | 0.0415 | 0.0387 | 0.0431 | 0.0043 |
| Camber, road-relative | deg | 0.0866 | -3.5901 | 6.7941 | 10.3842 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 862.5260 | 862.5260 | 862.5260 | 0.0000 |
| Track change | mm | -9.9410 | -25.8960 | -9.9410 | 15.9550 |
| Track change rate | mm/mm | 0.4417 | 0.4384 | 0.6625 | 0.2241 |
| Roll-centre height | mm | 53.5264 | 51.4069 | 53.5264 | 2.1195 |
| Roll-centre lateral position | mm | -0.0000 | -37.3731 | 37.3731 | 74.7462 |
| Body roll | deg | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | -40.0000 | -40.0000 | -40.0000 | 0.0000 |
| Ride-height change | mm | 39.9997 | 38.9817 | 39.9997 | 1.0179 |
| Rack displacement | mm | -0.0000 | -35.0000 | 35.0000 | 70.0000 |
| Ackermann error (inner - outer) | deg | 0.0000 | -0.0297 | 2.6335 | 2.6632 |
| Ackermann | % | 157.2798 | -679.5316 | 157.2798 | 836.8114 |
| Steering ratio | deg/mm | -0.7218 | -0.9699 | -0.7150 | 0.2548 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | 0.0054 | -0.0114 | 0.0117 | 0.0231 |
| Bump steer rate | deg/mm | -0.0002 | -0.0468 | 0.0465 | 0.0932 |
| ISO steer gain in bump | deg/mm | 0.0002 | -0.0465 | 0.0468 | 0.0932 |
| Caster gain | deg/mm | -0.0002 | -0.0003 | -0.0002 | 0.0001 |
| KPI gain | deg/mm | -0.0053 | -0.0060 | -0.0042 | 0.0018 |
| Half-track change rate | mm/mm | 0.2208 | 0.2192 | 0.3312 | 0.1121 |
| Wheel-centre recession rate | mm/mm | -0.0004 | -0.0190 | 0.0176 | 0.0366 |
| Damper rate vs wheel | mm/mm | -0.5011 | -0.5016 | -0.4990 | 0.0026 |
| Toe per rack | deg/mm | 0.7218 | 0.7150 | 0.9699 | 0.2548 |
| Steer per rack | deg/mm | -0.7218 | -0.9699 | -0.7150 | 0.2548 |
| Camber per rack | deg/mm | -0.1276 | -0.3222 | -0.0896 | 0.2326 |

## 07_bump_at_steer  (heave_at_steer)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -2.1218 | -3.2241 | -2.0686 | 1.1555 |
| Caster | deg | 9.9998 | 9.9969 | 10.0458 | 0.0489 |
| Kingpin inclination | deg | 9.9919 | 9.8767 | 11.3012 | 1.4246 |
| Toe (positive = toe-in) | deg | 13.4949 | 12.0581 | 15.0623 | 3.0042 |
| ISO steer angle | deg | -13.4949 | -15.0623 | -12.0581 | 3.0042 |
| Scrub radius (ISO unsigned) | mm | 43.2905 | 41.7248 | 43.5648 | 1.8400 |
| Scrub radius (signed lateral) | mm | -23.6827 | -23.7845 | -23.6683 | 0.1162 |
| Steering-axis offset at ground | mm | -23.6827 | -23.7845 | -23.6683 | 0.1162 |
| Mechanical trail | mm | 36.2381 | 34.3566 | 36.4992 | 2.1426 |
| Half track | mm | 440.3293 | 429.1161 | 440.3787 | 11.2626 |
| Wheel travel | mm | -0.0000 | -63.5000 | 63.5000 | 127.0000 |
| Damper length | mm | 243.2800 | 210.0983 | 275.2793 | 65.1810 |
| Motion ratio (damper/wheel) | mm/mm | 0.5117 | 0.4993 | 0.5334 | 0.0341 |
| Motion ratio squared | - | 0.2618 | 0.2493 | 0.2845 | 0.0352 |
| Front-view IC, y | mm | -6146.4804 | -3117911.6290 | 79785.1946 | 3197696.8236 |
| Front-view IC, z | mm | 218.9260 | -13229.1759 | 488763.4397 | 501992.6156 |
| Front-view swing-arm length | mm | 6590.4642 | -80437.9508 | 3156425.3182 | 3236863.2690 |
| Side-view IC, x | mm | 33102324.7261 | -28452309.8919 | 33102324.7261 | 61554634.6180 |
| Side-view IC, z | mm | 523.8689 | 422.2320 | 628.5771 | 206.3451 |
| Side-view swing-arm length | mm | 33102316.4530 | -28452318.1551 | 33102316.4530 | 61554634.6081 |
| Side-view swing-arm angle | deg | 0.0009 | -0.0643 | 0.0713 | 0.1356 |
| Camber, road-relative | deg | -2.1218 | -3.2241 | -2.0686 | 1.1555 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 862.5260 | 862.5260 | 862.5260 | 0.0000 |
| Track change | mm | -4.8995 | -28.8097 | -4.7111 | 24.0986 |
| Track change rate | mm/mm | 0.0794 | -0.5577 | 0.7095 | 1.2671 |
| Roll-centre height | mm | 11.3983 | -52.2738 | 75.3907 | 127.6646 |
| Roll-centre lateral position | mm | 82.6216 | -211.0568 | 7438.8867 | 7649.9435 |
| Roll-centre migration vs travel | mm/mm | -1.0940 | -9.9928 | 8.2006 | 18.1934 |
| Body roll | deg | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | -0.0000 | -63.5000 | 63.5000 | 127.0000 |
| Ride-height change | mm | -0.2571 | -63.7365 | 63.1834 | 126.9199 |
| Rack displacement | mm | 20.0000 | 20.0000 | 20.0000 | 0.0000 |
| Steering ratio | deg/mm | -0.6718 | -0.7567 | -0.5926 | 0.1641 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0059 | -0.0317 | 0.0251 | 0.0568 |
| Bump steer rate | deg/mm | -0.0195 | -0.0377 | -0.0195 | 0.0182 |
| ISO steer gain in bump | deg/mm | 0.0195 | 0.0195 | 0.0377 | 0.0182 |
| Caster gain | deg/mm | 0.0003 | -0.0007 | 0.0014 | 0.0021 |
| KPI gain | deg/mm | 0.0087 | -0.0199 | 0.0362 | 0.0560 |
| Half-track change rate | mm/mm | 0.0397 | -0.2788 | 0.3547 | 0.6336 |
| Wheel-centre recession rate | mm/mm | -0.0084 | -0.0165 | -0.0084 | 0.0082 |
| Damper rate vs wheel | mm/mm | -0.5117 | -0.5334 | -0.4993 | 0.0341 |
| Toe per rack | deg/mm | 0.6718 | 0.5926 | 0.7567 | 0.1641 |
| Steer per rack | deg/mm | -0.6718 | -0.7567 | -0.5926 | 0.1641 |
| Camber per rack | deg/mm | -0.0950 | -0.1059 | -0.0845 | 0.0213 |

## 08_damper_stroke  (damper_stroke)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -1.1253 | -1.1253 | 0.1213 | 1.2466 |
| Caster | deg | 10.0392 | 9.9969 | 10.0392 | 0.0423 |
| Kingpin inclination | deg | 11.1257 | 9.8768 | 11.1257 | 1.2489 |
| Toe (positive = toe-in) | deg | -0.0016 | -0.0069 | 0.0166 | 0.0235 |
| ISO steer angle | deg | 0.0016 | -0.0166 | 0.0069 | 0.0235 |
| Scrub radius (ISO unsigned) | mm | 54.8378 | 54.6909 | 54.8378 | 0.1469 |
| Scrub radius (signed lateral) | mm | -23.9490 | -23.9490 | -23.8519 | 0.0971 |
| Steering-axis offset at ground | mm | -23.9490 | -23.9490 | -23.8519 | 0.0971 |
| Mechanical trail | mm | 49.3318 | 49.2156 | 49.3318 | 0.1162 |
| Half track | mm | 425.0795 | 421.0366 | 431.3503 | 10.3137 |
| Wheel travel | mm | 57.5759 | -59.5504 | 57.5759 | 117.1263 |
| Damper length | mm | 212.8113 | 212.8113 | 272.8113 | 60.0000 |
| Motion ratio (damper/wheel) | mm/mm | 0.5304 | 0.4987 | 0.5304 | 0.0317 |
| Motion ratio squared | - | 0.2814 | 0.2487 | 0.2814 | 0.0327 |
| Front-view IC, y | mm | -1329.4347 | -166758.5823 | 167324.9529 | 334083.5352 |
| Front-view IC, z | mm | -371.9024 | -26974.7627 | 25467.0362 | 52441.7989 |
| Front-view swing-arm length | mm | 1806.1608 | -169057.6403 | 169120.0374 | 338177.6777 |
| Side-view IC, x | mm | -548346.3126 | -16630277.3678 | 16525783.2291 | 33156060.5969 |
| Side-view IC, z | mm | 619.2028 | 430.7430 | 619.2028 | 188.4597 |
| Side-view swing-arm length | mm | -548346.3255 | -16630277.3675 | 16525783.2288 | 33156060.5963 |
| Side-view swing-arm angle | deg | -0.0588 | -0.0588 | 0.0649 | 0.1236 |
| Camber, road-relative | deg | -1.1253 | -1.1253 | 0.1213 | 1.2466 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 862.5260 | 862.5260 | 862.5260 | 0.0000 |
| Track change | mm | -12.3671 | -20.4528 | 0.1747 | 20.6275 |
| Roll-centre height | mm | -46.9667 | -46.9667 | 72.9638 | 119.9305 |
| Roll-centre lateral position | mm | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Body roll | deg | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | 57.5759 | -59.5504 | 57.5759 | 117.1263 |
| Ride-height change | mm | -57.6297 | -57.6297 | 59.5498 | 117.1795 |
| Rack displacement | mm | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Steering ratio | deg/mm | -0.6254 | -0.7487 | -0.6254 | 0.1233 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Toe per rack | deg/mm | 0.6254 | 0.6254 | 0.7487 | 0.1233 |
| Steer per rack | deg/mm | -0.6254 | -0.7487 | -0.6254 | 0.1233 |
| Camber per rack | deg/mm | -0.1103 | -0.1320 | -0.1103 | 0.0217 |

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/03_single_wheel_bump.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/07_bump_at_steer.png`
- `plots/08_damper_stroke.png`

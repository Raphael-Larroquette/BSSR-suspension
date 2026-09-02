# Suspension characteristic report

## Provenance

- geometry: `C:\Users\rapha\Documents\BSSR\Suspension_App\BSSR-suspension\models\aurora\front.yaml`
- geometry SHA-256: `4141bf717bba475c...`
- format version: 3
- reported side: **left**

## Sweeps

| file | kind | steps | converged | max residual | notes |
| --- | --- | --- | --- | --- | --- |
| `01_bump_parallel` | heave | 22 | True | 2.02e-06 | - |
| `02_roll` | roll | 65 | True | 4.13e-06 | - |
| `03_single_wheel_bump` | single_wheel | 22 | True | 1.27e-06 | - |
| `04_steer_design` | steer | 65 | True | 2.69e-06 | - |
| `05_steer_bump` | steer | 65 | True | 4.08e-06 | Held at +50.0 mm wheel travel, not design height. |
| `06_steer_droop` | steer | 65 | True | 4.90e-06 | Held at -55.0 mm wheel travel, not design height. |
| `07_bump_at_steer` | heave_at_steer | 65 | True | 2.91e-06 | Rack held at +20.00 mm - this is a STEERED sweep. |
| `08_damper_stroke` | damper_stroke | 65 | True | 3.25e-06 | Driven by damper length, so the wrt_hub_z analytic derivatives are absent. Gradients here are finite-differenced by this parser. |

## 01_bump_parallel  (heave)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -0.8833 | 0.1210 | 1.0043 |
| Caster | deg | 10.0000 | 9.9963 | 10.0279 | 0.0316 |
| Kingpin inclination | deg | 10.0000 | 9.8771 | 10.8844 | 1.0072 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0073 | 0.0173 | 0.0247 |
| ISO steer angle | deg | 0.0000 | -0.0173 | 0.0073 | 0.0247 |
| Scrub radius (ISO unsigned) | mm | 49.2564 | 49.2410 | 49.2665 | 0.0256 |
| Scrub radius (signed lateral) | mm | -1.5819 | -1.5866 | -1.5810 | 0.0056 |
| Steering-axis offset at ground | mm | -1.5819 | -1.5866 | -1.5810 | 0.0056 |
| Mechanical trail | mm | 49.2309 | 49.2156 | 49.2410 | 0.0254 |
| Half track | mm | 453.5420 | 444.6960 | 453.6272 | 8.9312 |
| Wheel travel | mm | 0.0000 | -55.0000 | 50.0000 | 105.0000 |
| Damper length | mm | 242.8113 | 217.0122 | 270.5443 | 53.5321 |
| Motion ratio (damper/wheel) | mm/mm | 0.5094 | 0.5015 | 0.5223 | 0.0208 |
| Motion ratio squared | - | 0.2595 | 0.2515 | 0.2728 | 0.0213 |
| Front-view IC, y | mm | -5930.6063 | -83588.9565 | 49231.5400 | 132820.4965 |
| Front-view IC, z | mm | 185.0000 | -8441.5587 | 12425.8124 | 20867.3711 |
| Front-view swing-arm length | mm | 6386.8485 | -49500.7907 | 84957.7067 | 134458.4974 |
| Camber, road-relative | deg | 0.0000 | -0.8833 | 0.1210 | 1.0043 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 907.0840 | 907.0840 | 907.0840 | 0.0000 |
| Track change | mm | 0.0000 | -17.6920 | 0.1703 | 17.8623 |
| Track change rate | mm/mm | 0.0575 | -0.4096 | 0.5927 | 1.0022 |
| Roll-centre height | mm | 12.4925 | -42.5341 | 75.9925 | 118.5266 |
| Roll-centre lateral position | mm | -0.0000 | -0.0000 | 0.0000 | 0.0001 |
| Roll-centre migration vs travel | mm/mm | -1.1334 | -1.1662 | -1.0573 | 0.1089 |
| Body roll | deg | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | 0.0000 | -55.0000 | 50.0000 | 105.0000 |
| Ride-height change | mm | -0.0000 | -50.0332 | 54.9999 | 105.0331 |
| Rack displacement | mm | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Steering ratio | deg/mm | -0.6833 | -0.7415 | -0.6352 | 0.1062 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0089 | -0.0280 | 0.0131 | 0.0411 |
| Bump steer rate | deg/mm | -0.0004 | -0.0004 | 0.0003 | 0.0007 |
| ISO steer gain in bump | deg/mm | 0.0004 | -0.0003 | 0.0004 | 0.0007 |
| Caster gain | deg/mm | 0.0003 | -0.0004 | 0.0009 | 0.0013 |
| KPI gain | deg/mm | 0.0090 | -0.0132 | 0.0279 | 0.0411 |
| Half-track change rate | mm/mm | 0.0288 | -0.2048 | 0.2963 | 0.5011 |
| Wheel-centre recession rate | mm/mm | -0.0003 | -0.0004 | 0.0002 | 0.0006 |
| Damper rate vs wheel | mm/mm | -0.5094 | -0.5223 | -0.5015 | 0.0208 |
| Toe per rack | deg/mm | 0.6833 | 0.6352 | 0.7415 | 0.1062 |
| Steer per rack | deg/mm | -0.6833 | -0.7415 | -0.6352 | 0.1062 |
| Camber per rack | deg/mm | -0.1196 | -0.1321 | -0.1094 | 0.0227 |

## 02_roll  (roll)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -0.3252 | 0.1210 | 0.4462 |
| Caster | deg | 10.0000 | 9.9963 | 10.0100 | 0.0137 |
| Kingpin inclination | deg | 10.0000 | 9.8771 | 10.3264 | 0.4492 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0066 | 0.0105 | 0.0171 |
| ISO steer angle | deg | 0.0000 | -0.0105 | 0.0066 | 0.0171 |
| Scrub radius (ISO unsigned) | mm | 49.2564 | 49.2465 | 49.2597 | 0.0133 |
| Scrub radius (signed lateral) | mm | -1.5819 | -1.5988 | -1.5703 | 0.0285 |
| Steering-axis offset at ground | mm | -1.5819 | -1.5988 | -1.5703 | 0.0285 |
| Mechanical trail | mm | 49.2309 | 49.2214 | 49.2338 | 0.0124 |
| Half track | mm | 453.5420 | 451.3421 | 453.6301 | 2.2881 |
| Wheel travel | mm | -0.0000 | -25.0000 | 25.0000 | 50.0000 |
| Damper length | mm | 242.8113 | 229.9942 | 255.4757 | 25.4815 |
| Motion ratio (damper/wheel) | mm/mm | 0.5094 | 0.5041 | 0.5160 | 0.0120 |
| Motion ratio squared | - | 0.2595 | 0.2541 | 0.2663 | 0.0122 |
| Front-view IC, y | mm | -5930.6063 | -83588.9717 | -2857.8880 | 80731.0837 |
| Front-view IC, z | mm | 185.0000 | -266.6989 | 12425.8153 | 12692.5142 |
| Front-view swing-arm length | mm | 6386.8485 | 3323.4516 | 84957.7222 | 81634.2706 |
| Camber, road-relative | deg | 0.0000 | -3.4940 | 3.2898 | 6.7838 |
| Camber recovery | deg/deg | -0.0705 | -0.1344 | -0.0059 | 0.1286 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 907.0840 | 907.0840 | 907.0840 | 0.0000 |
| Track change | mm | 0.0000 | -1.5613 | 0.0000 | 1.5613 |
| Track change rate | mm/mm | 0.0575 | -0.1761 | 0.2956 | 0.4717 |
| Roll-centre height | mm | 12.4925 | -98.1499 | 12.4925 | 110.6423 |
| Roll-centre lateral position | mm | 0.0000 | -940.3398 | 940.3396 | 1880.6793 |
| Roll-centre migration vs roll | mm/deg | 0.0000 | -66.2302 | 66.2298 | 132.4599 |
| Roll-centre lateral migration vs roll | mm/deg | -308.4378 | -308.4378 | -274.9713 | 33.4665 |
| Body roll | deg | -0.0000 | -3.1688 | 3.1688 | 6.3376 |
| Heave | mm | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Ride-height change | mm | -0.0000 | -0.0000 | 0.0366 | 0.0366 |
| Rack displacement | mm | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Steering ratio | deg/mm | -0.6833 | -0.7060 | -0.6610 | 0.0449 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0089 | -0.0173 | -0.0006 | 0.0167 |
| Bump steer rate | deg/mm | -0.0004 | -0.0004 | -0.0001 | 0.0003 |
| ISO steer gain in bump | deg/mm | 0.0004 | 0.0001 | 0.0004 | 0.0003 |
| Caster gain | deg/mm | 0.0003 | 0.0000 | 0.0005 | 0.0005 |
| KPI gain | deg/mm | 0.0090 | 0.0007 | 0.0173 | 0.0166 |
| Half-track change rate | mm/mm | 0.0288 | -0.0881 | 0.1478 | 0.2359 |
| Wheel-centre recession rate | mm/mm | -0.0003 | -0.0004 | -0.0001 | 0.0003 |
| Damper rate vs wheel | mm/mm | -0.5094 | -0.5160 | -0.5041 | 0.0120 |
| Toe per rack | deg/mm | 0.6833 | 0.6610 | 0.7060 | 0.0449 |
| Steer per rack | deg/mm | -0.6833 | -0.7060 | -0.6610 | 0.0449 |
| Camber per rack | deg/mm | -0.1196 | -0.1244 | -0.1149 | 0.0095 |

## 03_single_wheel_bump  (single_wheel)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0000 | -0.8833 | 0.1210 | 1.0043 |
| Caster | deg | 10.0000 | 9.9963 | 10.0279 | 0.0316 |
| Kingpin inclination | deg | 10.0000 | 9.8771 | 10.8844 | 1.0072 |
| Toe (positive = toe-in) | deg | -0.0000 | -0.0074 | 0.0173 | 0.0247 |
| ISO steer angle | deg | 0.0000 | -0.0173 | 0.0074 | 0.0247 |
| Scrub radius (ISO unsigned) | mm | 49.2564 | 49.2490 | 49.2565 | 0.0076 |
| Scrub radius (signed lateral) | mm | -1.5819 | -1.6019 | -1.5722 | 0.0297 |
| Steering-axis offset at ground | mm | -1.5819 | -1.6019 | -1.5722 | 0.0297 |
| Mechanical trail | mm | 49.2309 | 49.2239 | 49.2312 | 0.0073 |
| Half track | mm | 453.5420 | 444.6960 | 453.6272 | 8.9312 |
| Wheel travel | mm | -0.0000 | -55.0000 | 50.0000 | 105.0000 |
| Damper length | mm | 242.8113 | 217.0122 | 270.5443 | 53.5321 |
| Motion ratio (damper/wheel) | mm/mm | 0.5094 | 0.5015 | 0.5223 | 0.0208 |
| Motion ratio squared | - | 0.2595 | 0.2515 | 0.2728 | 0.0213 |
| Front-view IC, y | mm | -5930.6063 | -83588.9622 | 49231.5313 | 132820.4935 |
| Front-view IC, z | mm | 185.0000 | -8441.5578 | 12425.8135 | 20867.3713 |
| Front-view swing-arm length | mm | 6386.8485 | -49500.7820 | 84957.7125 | 134458.4945 |
| Camber, road-relative | deg | -0.0000 | -4.0689 | 3.4566 | 7.5254 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 907.0840 | 907.0840 | 907.0840 | 0.0000 |
| Track change | mm | 0.0000 | -7.1637 | 0.1083 | 7.2721 |
| Track change rate | mm/mm | 0.0575 | -0.4096 | 0.5927 | 1.0022 |
| Roll-centre height | mm | 12.4925 | -16.6522 | 52.9884 | 69.6406 |
| Roll-centre lateral position | mm | 0.0000 | -1001.9615 | 1392.2011 | 2394.1627 |
| Roll-centre migration vs travel | mm/mm | -0.6763 | -2.9145 | 4.7551 | 7.6696 |
| Body roll | deg | -0.0000 | -3.5048 | 3.1856 | 6.6904 |
| Heave | mm | -0.0000 | -27.5000 | 25.0000 | 52.5000 |
| Ride-height change | mm | 0.0000 | -25.1011 | 27.7176 | 52.8187 |
| Rack displacement | mm | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Steering ratio | deg/mm | -0.6833 | -0.7415 | -0.6352 | 0.1062 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0089 | -0.0280 | 0.0131 | 0.0411 |
| Bump steer rate | deg/mm | -0.0004 | -0.0004 | 0.0003 | 0.0007 |
| ISO steer gain in bump | deg/mm | 0.0004 | -0.0003 | 0.0004 | 0.0007 |
| Caster gain | deg/mm | 0.0003 | -0.0004 | 0.0009 | 0.0013 |
| KPI gain | deg/mm | 0.0090 | -0.0132 | 0.0279 | 0.0411 |
| Half-track change rate | mm/mm | 0.0288 | -0.2048 | 0.2963 | 0.5011 |
| Wheel-centre recession rate | mm/mm | -0.0003 | -0.0004 | 0.0002 | 0.0006 |
| Damper rate vs wheel | mm/mm | -0.5094 | -0.5223 | -0.5015 | 0.0208 |
| Toe per rack | deg/mm | 0.6833 | 0.6352 | 0.7415 | 0.1062 |
| Steer per rack | deg/mm | -0.6833 | -0.7415 | -0.6352 | 0.1062 |
| Camber per rack | deg/mm | -0.1196 | -0.1321 | -0.1094 | 0.0227 |

## 04_steer_design  (steer)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | 0.0000 | -3.4556 | 6.1546 | 9.6101 |
| Caster | deg | 10.0000 | 9.9993 | 10.0014 | 0.0020 |
| Kingpin inclination | deg | 10.0000 | 9.9773 | 10.0449 | 0.0675 |
| Toe (positive = toe-in) | deg | -0.0000 | -26.3323 | 23.6619 | 49.9943 |
| ISO steer angle | deg | 0.0000 | -23.6619 | 26.3323 | 49.9943 |
| Scrub radius (ISO unsigned) | mm | 49.2564 | 25.0096 | 66.7509 | 41.7413 |
| Scrub radius (signed lateral) | mm | -1.5819 | -2.1736 | -1.0395 | 1.1340 |
| Steering-axis offset at ground | mm | -1.5819 | -2.1736 | -1.0395 | 1.1340 |
| Mechanical trail | mm | 49.2309 | 24.9880 | 66.7155 | 41.7275 |
| Half track | mm | 453.5420 | 424.2482 | 463.6023 | 39.3541 |
| Wheel travel | mm | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Damper length | mm | 242.8113 | 240.4547 | 244.1604 | 3.7057 |
| Motion ratio (damper/wheel) | mm/mm | 0.5094 | 0.5080 | 0.5104 | 0.0025 |
| Motion ratio squared | - | 0.2595 | 0.2580 | 0.2605 | 0.0025 |
| Front-view IC, y | mm | -5930.6063 | -6593.9080 | -5028.9445 | 1564.9635 |
| Front-view IC, z | mm | 185.0000 | 44.3626 | 289.6107 | 245.2480 |
| Front-view swing-arm length | mm | 6386.8485 | 5453.3683 | 7063.4235 | 1610.0552 |
| Camber, road-relative | deg | 0.0000 | -3.4556 | 6.1546 | 9.6101 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 907.0840 | 907.0840 | 907.0840 | 0.0000 |
| Track change | mm | 0.0000 | -19.2709 | 0.0000 | 19.2709 |
| Track change rate | mm/mm | 0.0575 | 0.0568 | 0.1930 | 0.1362 |
| Roll-centre height | mm | 12.4925 | 6.4137 | 12.4925 | 6.0788 |
| Roll-centre lateral position | mm | -0.0000 | -300.7483 | 300.7482 | 601.4966 |
| Body roll | deg | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Ride-height change | mm | 0.0000 | -0.8797 | 0.0000 | 0.8797 |
| Rack displacement | mm | -0.0000 | -35.0000 | 35.0000 | 70.0000 |
| Ackermann error (inner - outer) | deg | 0.0000 | 0.0000 | 2.6704 | 2.6704 |
| Ackermann | % | nan | 43.7065 | 60.9359 | 17.2294 |
| Steering ratio | deg/mm | -0.6833 | -0.9022 | -0.6729 | 0.2293 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0089 | -0.0201 | -0.0036 | 0.0165 |
| Bump steer rate | deg/mm | -0.0004 | -0.0369 | 0.0309 | 0.0678 |
| ISO steer gain in bump | deg/mm | 0.0004 | -0.0309 | 0.0369 | 0.0678 |
| Caster gain | deg/mm | 0.0003 | 0.0002 | 0.0003 | 0.0001 |
| KPI gain | deg/mm | 0.0090 | 0.0082 | 0.0104 | 0.0022 |
| Half-track change rate | mm/mm | 0.0288 | 0.0284 | 0.0965 | 0.0681 |
| Wheel-centre recession rate | mm/mm | -0.0003 | -0.0281 | 0.0224 | 0.0505 |
| Damper rate vs wheel | mm/mm | -0.5094 | -0.5104 | -0.5080 | 0.0025 |
| Toe per rack | deg/mm | 0.6833 | 0.6729 | 0.9022 | 0.2293 |
| Steer per rack | deg/mm | -0.6833 | -0.9022 | -0.6729 | 0.2293 |
| Camber per rack | deg/mm | -0.1196 | -0.2853 | -0.0843 | 0.2010 |

## 05_steer_bump  (steer)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.8833 | -4.0426 | 4.6637 | 8.7063 |
| Caster | deg | 10.0279 | 10.0257 | 10.0321 | 0.0064 |
| Kingpin inclination | deg | 10.8844 | 10.8176 | 11.0112 | 0.1936 |
| Toe (positive = toe-in) | deg | -0.0058 | -24.6130 | 21.6674 | 46.2804 |
| ISO steer angle | deg | 0.0058 | -21.6674 | 24.6130 | 46.2804 |
| Scrub radius (ISO unsigned) | mm | 49.2664 | 25.8281 | 68.2125 | 42.3843 |
| Scrub radius (signed lateral) | mm | -1.5866 | -2.2367 | -1.0549 | 1.1817 |
| Steering-axis offset at ground | mm | -1.5866 | -2.2367 | -1.0549 | 1.1817 |
| Mechanical trail | mm | 49.2409 | 25.8066 | 68.1758 | 42.3692 |
| Half track | mm | 449.1394 | 420.0721 | 459.1889 | 39.1168 |
| Wheel travel | mm | 50.0000 | 50.0000 | 50.0000 | 0.0000 |
| Damper length | mm | 217.0122 | 214.7307 | 218.2880 | 3.5573 |
| Motion ratio (damper/wheel) | mm/mm | 0.5223 | 0.5200 | 0.5245 | 0.0046 |
| Motion ratio squared | - | 0.2728 | 0.2704 | 0.2751 | 0.0048 |
| Front-view IC, y | mm | -1606.5498 | -1699.3816 | -1451.1457 | 248.2358 |
| Front-view IC, z | mm | -371.1390 | -373.3642 | -368.1961 | 5.1681 |
| Front-view swing-arm length | mm | 2098.2504 | 1918.5276 | 2198.6885 | 280.1609 |
| Camber, road-relative | deg | -0.8833 | -4.0426 | 4.6637 | 8.7063 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 907.0840 | 907.0840 | 907.0840 | 0.0000 |
| Track change | mm | -8.8053 | -27.8230 | -8.8053 | 19.0177 |
| Track change rate | mm/mm | -0.4096 | -0.4148 | -0.2775 | 0.1373 |
| Roll-centre height | mm | -42.5341 | -42.5341 | -41.7851 | 0.7490 |
| Roll-centre lateral position | mm | -0.0000 | -14.1692 | 14.1692 | 28.3385 |
| Body roll | deg | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | 50.0000 | 50.0000 | 50.0000 | 0.0000 |
| Ride-height change | mm | -50.0332 | -50.6862 | -50.0332 | 0.6530 |
| Rack displacement | mm | 0.0000 | -35.0000 | 35.0000 | 70.0000 |
| Ackermann error (inner - outer) | deg | -0.0000 | -0.0000 | 2.9456 | 2.9456 |
| Ackermann | % | -1050.4055 | -1050.4055 | 408.3087 | 1458.7142 |
| Steering ratio | deg/mm | -0.6352 | -0.8402 | -0.6126 | 0.2276 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0280 | -0.0430 | -0.0207 | 0.0222 |
| Bump steer rate | deg/mm | 0.0002 | -0.0475 | 0.0432 | 0.0907 |
| ISO steer gain in bump | deg/mm | -0.0002 | -0.0432 | 0.0475 | 0.0907 |
| Caster gain | deg/mm | 0.0009 | 0.0009 | 0.0010 | 0.0001 |
| KPI gain | deg/mm | 0.0279 | 0.0269 | 0.0301 | 0.0032 |
| Half-track change rate | mm/mm | -0.2048 | -0.2074 | -0.1387 | 0.0686 |
| Wheel-centre recession rate | mm/mm | 0.0002 | -0.0370 | 0.0316 | 0.0687 |
| Damper rate vs wheel | mm/mm | -0.5223 | -0.5245 | -0.5200 | 0.0046 |
| Toe per rack | deg/mm | 0.6352 | 0.6126 | 0.8402 | 0.2276 |
| Steer per rack | deg/mm | -0.6352 | -0.8402 | -0.6126 | 0.2276 |
| Camber per rack | deg/mm | -0.1094 | -0.2511 | -0.0767 | 0.1744 |

## 06_steer_droop  (steer)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -0.0483 | -3.8593 | 6.9309 | 10.7902 |
| Caster | deg | 10.0014 | 9.9996 | 10.0026 | 0.0030 |
| Kingpin inclination | deg | 10.0453 | 9.9864 | 10.0848 | 0.0984 |
| Toe (positive = toe-in) | deg | 0.0166 | -28.5230 | 26.0821 | 54.6051 |
| ISO steer angle | deg | -0.0166 | -26.0821 | 28.5230 | 54.6051 |
| Scrub radius (ISO unsigned) | mm | 49.2418 | 21.9952 | 67.4224 | 45.4272 |
| Scrub radius (signed lateral) | mm | -1.5817 | -2.1990 | -0.9964 | 1.2026 |
| Steering-axis offset at ground | mm | -1.5817 | -2.1990 | -0.9964 | 1.2026 |
| Mechanical trail | mm | 49.2164 | 21.9727 | 67.3866 | 45.4139 |
| Half track | mm | 444.6960 | 414.1858 | 453.9974 | 39.8117 |
| Wheel travel | mm | -55.0000 | -55.0000 | -55.0000 | 0.0000 |
| Damper length | mm | 270.5443 | 268.0111 | 271.9530 | 3.9418 |
| Motion ratio (damper/wheel) | mm/mm | 0.5015 | 0.4948 | 0.5031 | 0.0083 |
| Motion ratio squared | - | 0.2515 | 0.2448 | 0.2531 | 0.0083 |
| Front-view IC, y | mm | 4796.2989 | 4266.4963 | 6057.4992 | 1791.0029 |
| Front-view IC, z | mm | -1344.3848 | -1570.7331 | -1244.2178 | 326.5152 |
| Front-view swing-arm length | mm | -4538.4091 | -5843.5519 | -3994.0049 | 1849.5470 |
| Camber, road-relative | deg | -0.0483 | -3.8593 | 6.9309 | 10.7902 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 907.0840 | 907.0840 | 907.0840 | 0.0000 |
| Track change | mm | -17.6920 | -39.3115 | -17.6920 | 21.6195 |
| Track change rate | mm/mm | 0.5927 | 0.5903 | 0.8486 | 0.2584 |
| Roll-centre height | mm | 75.9925 | 70.6451 | 75.9925 | 5.3474 |
| Roll-centre lateral position | mm | -0.0000 | -50.0687 | 50.0687 | 100.1375 |
| Body roll | deg | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | -55.0000 | -55.0000 | -55.0000 | 0.0000 |
| Ride-height change | mm | 54.9999 | 53.9306 | 54.9999 | 1.0693 |
| Rack displacement | mm | 0.0000 | -35.0000 | 35.0000 | 70.0000 |
| Ackermann error (inner - outer) | deg | 0.0000 | -0.0320 | 2.4409 | 2.4729 |
| Ackermann | % | 95.7654 | -658.7092 | 95.7654 | 754.4746 |
| Steering ratio | deg/mm | -0.7415 | -0.9975 | -0.7374 | 0.2601 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | 0.0131 | -0.0107 | 0.0223 | 0.0330 |
| Bump steer rate | deg/mm | 0.0003 | -0.0606 | 0.0609 | 0.1215 |
| ISO steer gain in bump | deg/mm | -0.0003 | -0.0609 | 0.0606 | 0.1215 |
| Caster gain | deg/mm | -0.0004 | -0.0005 | -0.0003 | 0.0002 |
| KPI gain | deg/mm | -0.0132 | -0.0150 | -0.0101 | 0.0050 |
| Half-track change rate | mm/mm | 0.2963 | 0.2951 | 0.4243 | 0.1292 |
| Wheel-centre recession rate | mm/mm | 0.0002 | -0.0448 | 0.0440 | 0.0888 |
| Damper rate vs wheel | mm/mm | -0.5015 | -0.5031 | -0.4948 | 0.0083 |
| Toe per rack | deg/mm | 0.7415 | 0.7374 | 0.9975 | 0.2601 |
| Steer per rack | deg/mm | -0.7415 | -0.9975 | -0.7374 | 0.2601 |
| Camber per rack | deg/mm | -0.1321 | -0.3394 | -0.0929 | 0.2466 |

## 07_bump_at_steer  (heave_at_steer)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -2.1194 | -2.8230 | -2.0686 | 0.7544 |
| Caster | deg | 9.9997 | 9.9963 | 10.0265 | 0.0302 |
| Kingpin inclination | deg | 9.9884 | 9.8766 | 10.8422 | 0.9656 |
| Toe (positive = toe-in) | deg | 13.5027 | 12.4590 | 14.8279 | 2.3689 |
| ISO steer angle | deg | -13.5027 | -14.8279 | -12.4590 | 2.3689 |
| Scrub radius (ISO unsigned) | mm | 36.1512 | 34.6357 | 36.3587 | 1.7231 |
| Scrub radius (signed lateral) | mm | -1.2468 | -1.2546 | -1.2147 | 0.0399 |
| Steering-axis offset at ground | mm | -1.2468 | -1.2546 | -1.2147 | 0.0399 |
| Mechanical trail | mm | 36.1297 | 34.6144 | 36.3371 | 1.7227 |
| Half track | mm | 461.9695 | 452.7472 | 462.0372 | 9.2900 |
| Wheel travel | mm | 0.4022 | -55.8800 | 50.0630 | 105.9430 |
| Damper length | mm | 243.4840 | 217.8106 | 271.9173 | 54.1067 |
| Motion ratio (damper/wheel) | mm/mm | 0.5102 | 0.5028 | 0.5237 | 0.0209 |
| Motion ratio squared | - | 0.2603 | 0.2528 | 0.2743 | 0.0214 |
| Front-view IC, y | mm | -6244.8033 | -234719.0079 | 155869.3045 | 390588.3123 |
| Front-view IC, z | mm | 234.4722 | -25213.0725 | 36189.0350 | 61402.1076 |
| Front-view swing-arm length | mm | 6710.8743 | -157437.4080 | 237950.7155 | 395388.1235 |
| Camber, road-relative | deg | -2.1194 | -2.8230 | -2.0686 | 0.7544 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 907.0840 | 907.0840 | 907.0840 | 0.0000 |
| Track change | mm | -6.1894 | -25.2104 | -6.0121 | 19.1983 |
| Track change rate | mm/mm | 0.0849 | -0.4011 | 0.6527 | 1.0538 |
| Roll-centre height | mm | 10.1549 | -42.3507 | 75.2486 | 117.5993 |
| Roll-centre lateral position | mm | 168.2962 | -749.4333 | 1621.5698 | 2371.0031 |
| Roll-centre migration vs travel | mm/mm | -1.4007 | -4.9034 | 4.1247 | 9.0281 |
| Body roll | deg | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | 0.4022 | -55.8800 | 50.0630 | 105.9430 |
| Ride-height change | mm | -0.6568 | -50.2812 | 55.5701 | 105.8513 |
| Rack displacement | mm | 20.0000 | 20.0000 | 20.0000 | 0.0000 |
| Steering ratio | deg/mm | -0.6729 | -0.7450 | -0.6157 | 0.1293 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber gain | deg/mm | -0.0058 | -0.0236 | 0.0196 | 0.0432 |
| Bump steer rate | deg/mm | -0.0195 | -0.0330 | -0.0194 | 0.0135 |
| ISO steer gain in bump | deg/mm | 0.0195 | 0.0194 | 0.0330 | 0.0135 |
| Caster gain | deg/mm | 0.0003 | -0.0005 | 0.0009 | 0.0014 |
| KPI gain | deg/mm | 0.0086 | -0.0150 | 0.0273 | 0.0422 |
| Half-track change rate | mm/mm | 0.0424 | -0.2005 | 0.3264 | 0.5269 |
| Wheel-centre recession rate | mm/mm | -0.0158 | -0.0263 | -0.0158 | 0.0106 |
| Damper rate vs wheel | mm/mm | -0.5102 | -0.5237 | -0.5028 | 0.0209 |
| Toe per rack | deg/mm | 0.6729 | 0.6157 | 0.7450 | 0.1293 |
| Steer per rack | deg/mm | -0.6729 | -0.7450 | -0.6157 | 0.1293 |
| Camber per rack | deg/mm | -0.0949 | -0.1049 | -0.0868 | 0.0181 |

## 08_damper_stroke  (damper_stroke)

### Corner characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Camber | deg | -1.1253 | -1.1253 | 0.1214 | 1.2467 |
| Caster | deg | 10.0360 | 9.9963 | 10.0360 | 0.0397 |
| Kingpin inclination | deg | 11.1259 | 9.8767 | 11.1259 | 1.2493 |
| Toe (positive = toe-in) | deg | -0.0036 | -0.0073 | 0.0173 | 0.0247 |
| ISO steer angle | deg | 0.0036 | -0.0173 | 0.0073 | 0.0247 |
| Scrub radius (ISO unsigned) | mm | 49.2655 | 49.2409 | 49.2665 | 0.0256 |
| Scrub radius (signed lateral) | mm | -1.5879 | -1.5879 | -1.5810 | 0.0068 |
| Steering-axis offset at ground | mm | -1.5879 | -1.5879 | -1.5810 | 0.0068 |
| Mechanical trail | mm | 49.2399 | 49.2155 | 49.2410 | 0.0255 |
| Half track | mm | 447.3441 | 443.3050 | 453.6293 | 10.3242 |
| Wheel travel | mm | 58.0307 | -59.5200 | 58.0307 | 117.5508 |
| Damper length | mm | 212.8113 | 212.8113 | 272.8113 | 60.0000 |
| Motion ratio (damper/wheel) | mm/mm | 0.5237 | 0.5014 | 0.5237 | 0.0223 |
| Motion ratio squared | - | 0.2743 | 0.2514 | 0.2743 | 0.0228 |
| Front-view IC, y | mm | -1329.7105 | -163053.8487 | 171537.1851 | 334591.0338 |
| Front-view IC, z | mm | -372.4224 | -27676.5720 | 24921.3464 | 52597.9185 |
| Front-view swing-arm length | mm | 1828.2935 | -173305.8849 | 165397.4101 | 338703.2950 |
| Camber, road-relative | deg | -1.1253 | -1.1253 | 0.1214 | 1.2467 |

### Axle characteristics

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Track | mm | 907.0840 | 907.0840 | 907.0840 | 0.0000 |
| Track change | mm | -12.3958 | -20.4739 | 0.1745 | 20.6485 |
| Roll-centre height | mm | -50.8122 | -50.8122 | 81.0707 | 131.8829 |
| Roll-centre lateral position | mm | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Body roll | deg | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Heave | mm | 58.0307 | -59.5200 | 58.0307 | 117.5508 |
| Ride-height change | mm | -58.0846 | -58.0846 | 59.5195 | 117.6041 |
| Rack displacement | mm | -0.0000 | -0.0000 | 0.0000 | 0.0000 |
| Steering ratio | deg/mm | -0.6253 | -0.7487 | -0.6253 | 0.1234 |

### Gradients (analytic unless noted)

| characteristic | unit | at design | min | max | range |
| --- | --- | --- | --- | --- | --- |
| Toe per rack | deg/mm | 0.6253 | 0.6253 | 0.7487 | 0.1234 |
| Steer per rack | deg/mm | -0.6253 | -0.7487 | -0.6253 | 0.1234 |
| Camber per rack | deg/mm | -0.1102 | -0.1320 | -0.1102 | 0.0217 |

## Bearing misalignment

Required angle is the worst value anywhere in this sweep set, not per sweep. Install offset is the angle between the housing and bore directions at the neutral pose: non-zero means the bearing is fitted deliberately off centre and starts already eating part of its cone. The best-available column is what the joint would need if its bore axis were chosen to minimise the worst case.

| joint | part | required (deg) | at | install offset (deg) | best available (deg) | clocking (deg) |
| --- | --- | --- | --- | --- | --- | --- |
| LCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | 0.00 | 0.00 | - |
| UCA Front Bush | bushing | 0.00 | `01_bump_parallel` step 0 | 0.00 | 0.00 | - |
| LBJ | spherical | 20.00 | `08_damper_stroke` step 64 | 0.00 | 19.38 | - |
| UBJ | spherical | 31.37 | `06_steer_droop` step 0 | 0.00 | 25.94 | - |
| Outer Tie Rod End | rod_end | 29.86 | `04_steer_design` step 64 | 8.37 | 26.13 | - |
| Inner Tie Rod End | rod_end | 15.14 | `06_steer_droop` step 0 | 9.14 | 3.25 | - |
| Damper Lower Mount | spherical | 0.00 | `08_damper_stroke` step 32 | 0.00 | 0.00 | - |
| Damper Upper Mount | spherical | 0.00 | `08_damper_stroke` step 11 | 0.00 | 0.00 | - |

### Members whose spin is undetermined

These housings ride a two-point member, whose roll about its own axis no kinematic model can determine. The lower bound assumes the member turns freely to the best position at every instant; the locked value assumes it never turns, so one clocking chosen at assembly serves the whole sweep. Size the bearing against the locked value unless you know the member runs free.

| joint | free-spin lower bound (deg) | locked (deg) | locked clocking (deg) |
| --- | --- | --- | --- |
| Outer Tie Rod End | 29.86 | 30.68 | 91.5 |
| Inner Tie Rod End | 15.14 | 15.46 | 267.6 |
| Damper Lower Mount | 0.00 | 0.00 | 270.0 |
| Damper Upper Mount | 0.00 | 0.00 | 270.0 |

### How each joint was resolved

- **LCA Front Bush** -- LCA Front Bush: housing on 'Chassis' (fixed to chassis), bore on 'Lower Wishbone' (fitted from >=3 points), housing centred
- **UCA Front Bush** -- UCA Front Bush: housing on 'Chassis' (fixed to chassis), bore on 'Upper Wishbone' (fitted from >=3 points), housing centred
- **LBJ** -- LBJ: housing on 'Lower Wishbone' (fitted from >=3 points), bore on 'Upright' (fitted from >=3 points), housing centred
- **UBJ** -- UBJ: housing on 'Upper Wishbone' (fitted from >=3 points), bore on 'Upright' (fitted from >=3 points), housing centred
- **Outer Tie Rod End** -- Outer Tie Rod End: housing on 'Track Rod' (2-point link, transport (spin undetermined)), bore on 'Upright' (fitted from >=3 points), housing indeterminate
- **Inner Tie Rod End** -- Inner Tie Rod End: housing on 'Track Rod' (2-point link, transport (spin undetermined)), bore on 'Chassis' (fixed to chassis), housing indeterminate
- **Damper Lower Mount** -- Damper Lower Mount: housing on 'Spring/Damper' (2-point link, transport (spin undetermined)), bore on 'Lower Wishbone' (fitted from >=3 points), housing indeterminate
- **Damper Upper Mount** -- Damper Upper Mount: housing on 'Spring/Damper' (2-point link, transport (spin undetermined)), bore on 'Chassis' (fixed to chassis), housing indeterminate

## Plots

- `plots/01_bump_parallel.png`
- `plots/02_roll.png`
- `plots/03_single_wheel_bump.png`
- `plots/04_steer_design.png`
- `plots/05_steer_bump.png`
- `plots/06_steer_droop.png`
- `plots/07_bump_at_steer.png`
- `plots/08_damper_stroke.png`

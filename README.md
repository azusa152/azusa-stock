# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| api/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| api/dependencies.py                                   |       12 |        0 |    100% |           |
| api/rate\_limit.py                                    |        3 |        0 |    100% |           |
| api/routes/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| api/routes/forex\_routes.py                           |        6 |        0 |    100% |           |
| api/routes/fx\_watch\_routes.py                       |       50 |        0 |    100% |           |
| api/routes/guru\_routes.py                            |      117 |        3 |     97% |194, 492-493 |
| api/routes/holding\_routes.py                         |       93 |       10 |     89% |173-183, 211-214, 269 |
| api/routes/persona\_routes.py                         |       35 |        0 |    100% |           |
| api/routes/preferences\_routes.py                     |       16 |        0 |    100% |           |
| api/routes/scan\_routes.py                            |       82 |        1 |     99% |       186 |
| api/routes/snapshot\_routes.py                        |       80 |        8 |     90% |37-38, 41-42, 56-57, 74, 116 |
| api/routes/stock\_routes.py                           |      155 |       44 |     72% |127-130, 143, 149-160, 168, 182, 246-247, 256-259, 279, 295, 301, 326-331, 343-345, 359-370, 382-384, 395-397, 410-412 |
| api/routes/telegram\_routes.py                        |       19 |        0 |    100% |           |
| api/routes/thesis\_routes.py                          |       19 |        0 |    100% |           |
| api/schemas/\_\_init\_\_.py                           |        7 |        0 |    100% |           |
| api/schemas/common.py                                 |        7 |        0 |    100% |           |
| api/schemas/fx\_watch.py                              |       21 |        0 |    100% |           |
| api/schemas/guru.py                                   |      108 |        0 |    100% |           |
| api/schemas/notification.py                           |       36 |        0 |    100% |           |
| api/schemas/portfolio.py                              |      103 |        0 |    100% |           |
| api/schemas/scan.py                                   |       87 |        0 |    100% |           |
| api/schemas/stock.py                                  |       58 |        1 |     98% |        77 |
| application/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| application/formatters.py                             |      113 |        8 |     93% |82-83, 122, 272, 274, 301-303 |
| application/guru/\_\_init\_\_.py                      |        2 |        0 |    100% |           |
| application/guru/guru\_service.py                     |       47 |        2 |     96% |  103, 105 |
| application/guru/resonance\_service.py                |       53 |        0 |    100% |           |
| application/messaging/\_\_init\_\_.py                 |        3 |        0 |    100% |           |
| application/messaging/notification\_service.py        |      253 |       19 |     92% |52-56, 61-66, 122, 209-210, 266-267, 385, 464-465 |
| application/messaging/telegram\_settings\_service.py  |       54 |        1 |     98% |        85 |
| application/messaging/webhook\_service.py             |      130 |       14 |     89% |80, 141-149, 194-195, 206-207, 297-298 |
| application/portfolio/\_\_init\_\_.py                 |        5 |        0 |    100% |           |
| application/portfolio/fx\_watch\_service.py           |      115 |        2 |     98% |  151, 379 |
| application/portfolio/holding\_service.py             |       82 |        0 |    100% |           |
| application/portfolio/rebalance\_service.py           |      424 |       35 |     92% |128, 194-195, 203-204, 211-217, 261, 438, 563, 855, 917, 947, 951-966, 992, 1000-1001, 1082-1085, 1138, 1145, 1168-1171 |
| application/portfolio/snapshot\_service.py            |      103 |        7 |     93% |163-164, 168, 171-175, 179 |
| application/portfolio/stress\_test\_service.py        |       39 |        0 |    100% |           |
| application/scan/\_\_init\_\_.py                      |        2 |        0 |    100% |           |
| application/scan/prewarm\_service.py                  |      148 |       21 |     86% |49, 73-76, 150-151, 317-333, 361-362, 387-388, 399-400 |
| application/scan/scan\_service.py                     |      311 |       69 |     78% |81, 122-125, 188, 221, 230, 240, 260, 271, 291, 316, 373-375, 425, 485-508, 513, 538, 544-547, 550, 591, 603-605, 620-621, 667-672, 705-717, 750-755, 760-768 |
| application/services.py                               |        6 |        0 |    100% |           |
| application/settings/\_\_init\_\_.py                  |        2 |        0 |    100% |           |
| application/settings/persona\_service.py              |       53 |        0 |    100% |           |
| application/settings/preferences\_service.py          |       40 |        2 |     95% |    60, 87 |
| application/stock/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| application/stock/filing\_service.py                  |      193 |       11 |     94% |170-177, 217-221, 298, 302, 375, 400-402 |
| application/stock/stock\_service.py                   |      338 |       50 |     85% |308, 315-316, 342-346, 387-389, 500, 505, 588, 606-607, 614-615, 619-621, 628-632, 642-647, 702-703, 708-709, 713-714, 765-772, 813-827 |
| domain/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| domain/analysis/\_\_init\_\_.py                       |        3 |        0 |    100% |           |
| domain/analysis/analysis.py                           |      264 |        0 |    100% |           |
| domain/analysis/fx\_analysis.py                       |      123 |        1 |     99% |        43 |
| domain/analysis/smart\_money.py                       |       27 |        1 |     96% |        35 |
| domain/constants.py                                   |        1 |        0 |    100% |           |
| domain/core/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| domain/core/constants.py                              |      261 |        0 |    100% |           |
| domain/core/entities.py                               |      163 |        4 |     98% |189-190, 202-203 |
| domain/core/enums.py                                  |       60 |        0 |    100% |           |
| domain/core/formatters.py                             |       38 |        0 |    100% |           |
| domain/core/protocols.py                              |        3 |        0 |    100% |           |
| domain/entities.py                                    |        1 |        0 |    100% |           |
| domain/enums.py                                       |        1 |        0 |    100% |           |
| domain/formatters.py                                  |        1 |        0 |    100% |           |
| domain/fx\_analysis.py                                |        1 |        0 |    100% |           |
| domain/portfolio/\_\_init\_\_.py                      |        3 |        0 |    100% |           |
| domain/portfolio/rebalance.py                         |       41 |        0 |    100% |           |
| domain/portfolio/stress\_test.py                      |       40 |        0 |    100% |           |
| domain/portfolio/withdrawal.py                        |      154 |       10 |     94% |81, 95, 113, 117, 123, 127, 157, 236, 250, 280 |
| domain/protocols.py                                   |        1 |        0 |    100% |           |
| domain/rebalance.py                                   |        1 |        0 |    100% |           |
| domain/smart\_money.py                                |        1 |        0 |    100% |           |
| domain/stress\_test.py                                |        1 |        0 |    100% |           |
| domain/withdrawal.py                                  |        1 |        0 |    100% |           |
| infrastructure/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| infrastructure/crypto.py                              |        1 |        0 |    100% |           |
| infrastructure/database.py                            |      118 |       39 |     67% |103-104, 113-117, 143-144, 155-165, 172-173, 177-178, 199-200, 224-246, 271-272 |
| infrastructure/external/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| infrastructure/external/crypto.py                     |       38 |        3 |     92% |     80-82 |
| infrastructure/external/notification.py               |       96 |       20 |     79% |149-150, 164-166, 171-177, 189-208 |
| infrastructure/external/sec\_edgar.py                 |      188 |       38 |     80% |78-83, 104-105, 119, 125-129, 135-139, 212-214, 277-279, 315-316, 393-395, 419, 429-431, 439, 442, 448-449 |
| infrastructure/finmind\_adapter.py                    |        1 |        1 |      0% |         6 |
| infrastructure/jquants\_adapter.py                    |        1 |        0 |    100% |           |
| infrastructure/market\_data/\_\_init\_\_.py           |        1 |        0 |    100% |           |
| infrastructure/market\_data/finmind\_adapter.py       |       55 |        2 |     96% |     55-56 |
| infrastructure/market\_data/jquants\_adapter.py       |       37 |        9 |     76% | 20, 26-34 |
| infrastructure/market\_data/market\_data.py           |     1045 |      489 |     53% |190, 320-321, 378, 403-411, 438, 449-451, 459-461, 482-486, 494-502, 524-526, 541-542, 579, 610-632, 650-652, 667, 759-760, 778-790, 844-845, 850-857, 865, 886-900, 938-939, 965, 981, 1020, 1038-1040, 1104-1116, 1129-1182, 1196-1227, 1232, 1248-1292, 1302-1320, 1383-1416, 1424-1427, 1441-1460, 1474-1511, 1520-1530, 1538-1575, 1584-1594, 1599-1606, 1620-1654, 1688-1700, 1747, 1754, 1759, 1766, 1769-1771, 1803-1817, 1831-1875, 1889-1921, 1932-1938, 1943-1947, 2062, 2074, 2090-2115, 2217-2243, 2269-2277, 2289, 2340, 2422-2424, 2436, 2484-2485, 2501-2592 |
| infrastructure/market\_data/market\_data\_resolver.py |       73 |       23 |     68% |19-25, 43-44, 47-48, 54-55, 58-59, 62, 65, 68, 71, 121, 124, 127, 132 |
| infrastructure/market\_data\_resolver.py              |        1 |        1 |      0% |         6 |
| infrastructure/notification.py                        |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py            |        1 |        0 |    100% |           |
| infrastructure/persistence/repositories.py            |      450 |       53 |     88% |61-69, 93-101, 111, 127-140, 145-159, 171, 184-186, 331-334, 339-343, 360, 365-366, 455, 586, 1259-1262, 1281-1284, 1319-1322 |
| infrastructure/repositories.py                        |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                          |        1 |        0 |    100% |           |
| **TOTAL**                                             | **6931** | **1002** | **86%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/azusa152/Folio/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/azusa152/Folio/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fazusa152%2FFolio%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.
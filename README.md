# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| api/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| api/dependencies.py                                   |       12 |        0 |    100% |           |
| api/rate\_limit.py                                    |        3 |        0 |    100% |           |
| api/routes/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| api/routes/backtest\_routes.py                        |       40 |        1 |     98% |        62 |
| api/routes/forex\_routes.py                           |        6 |        0 |    100% |           |
| api/routes/fx\_watch\_routes.py                       |       50 |        0 |    100% |           |
| api/routes/guru\_routes.py                            |      117 |        3 |     97% |194, 492-493 |
| api/routes/holding\_routes.py                         |       93 |       10 |     89% |173-183, 211-214, 269 |
| api/routes/networth\_routes.py                        |       46 |        3 |     93% |50, 160-161 |
| api/routes/persona\_routes.py                         |       35 |        0 |    100% |           |
| api/routes/preferences\_routes.py                     |       16 |        0 |    100% |           |
| api/routes/scan\_routes.py                            |       82 |        1 |     99% |       150 |
| api/routes/snapshot\_routes.py                        |       80 |        8 |     90% |37-38, 41-42, 56-57, 74, 116 |
| api/routes/stock\_routes.py                           |      155 |       44 |     72% |127-130, 143, 149-160, 168, 182, 246-247, 256-259, 279, 295, 301, 326-331, 343-345, 359-370, 382-384, 395-397, 410-412 |
| api/routes/telegram\_routes.py                        |       19 |        0 |    100% |           |
| api/routes/thesis\_routes.py                          |       19 |        0 |    100% |           |
| api/schemas/\_\_init\_\_.py                           |        9 |        0 |    100% |           |
| api/schemas/backtest.py                               |        8 |        0 |    100% |           |
| api/schemas/common.py                                 |        7 |        0 |    100% |           |
| api/schemas/fx\_watch.py                              |       21 |        0 |    100% |           |
| api/schemas/guru.py                                   |      108 |        0 |    100% |           |
| api/schemas/networth.py                               |       65 |        9 |     86% |39, 59-61, 67-74 |
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
| application/portfolio/\_\_init\_\_.py                 |       10 |        0 |    100% |           |
| application/portfolio/fx\_watch\_service.py           |      115 |        2 |     98% |  151, 379 |
| application/portfolio/holding\_service.py             |       83 |        0 |    100% |           |
| application/portfolio/net\_worth\_service.py          |      215 |       37 |     83% |49-54, 139, 141, 143, 145, 147, 149, 151, 155, 208, 211-212, 231, 330, 373-384, 404, 429-438, 471-472, 487-488 |
| application/portfolio/rebalance\_service.py           |      424 |       35 |     92% |128, 194-195, 203-204, 211-217, 261, 438, 563, 855, 917, 947, 951-966, 992, 1000-1001, 1082-1085, 1138, 1145, 1168-1171 |
| application/portfolio/snapshot\_service.py            |      103 |        7 |     93% |163-164, 168, 171-175, 179 |
| application/portfolio/stress\_test\_service.py        |       39 |        0 |    100% |           |
| application/scan/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| application/scan/backfill\_service.py                 |       77 |        8 |     90% |68-71, 82-84, 151-153 |
| application/scan/backtest\_service.py                 |       80 |        2 |     98% |   45, 149 |
| application/scan/prewarm\_service.py                  |      154 |       21 |     86% |50, 74-77, 151-152, 319-335, 370-371, 396-397, 408-409 |
| application/scan/scan\_service.py                     |      313 |       75 |     76% |79-82, 123-126, 189, 228, 237, 247, 267, 278, 288, 298, 321, 323, 325, 380-382, 432, 492-515, 520, 548, 554-557, 560, 601, 613-615, 630-631, 677-682, 715-727, 760-765, 770-778 |
| application/services.py                               |        8 |        0 |    100% |           |
| application/settings/\_\_init\_\_.py                  |        2 |        0 |    100% |           |
| application/settings/persona\_service.py              |       53 |        0 |    100% |           |
| application/settings/preferences\_service.py          |       40 |        2 |     95% |    60, 87 |
| application/stock/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| application/stock/filing\_service.py                  |      193 |       11 |     94% |170-177, 217-221, 298, 302, 375, 400-402 |
| application/stock/stock\_service.py                   |      339 |       50 |     85% |308, 315-316, 342-346, 387-389, 500, 505, 588, 606-607, 614-615, 619-621, 628-632, 642-647, 702-703, 708-709, 713-714, 769-776, 817-831 |
| domain/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| domain/analysis/\_\_init\_\_.py                       |        4 |        0 |    100% |           |
| domain/analysis/analysis.py                           |      264 |        0 |    100% |           |
| domain/analysis/backtest.py                           |      115 |        9 |     92% |91, 101, 122, 126, 136-137, 236, 242, 272 |
| domain/analysis/fx\_analysis.py                       |      123 |        1 |     99% |        43 |
| domain/analysis/smart\_money.py                       |       27 |        1 |     96% |        35 |
| domain/constants.py                                   |        1 |        0 |    100% |           |
| domain/core/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| domain/core/constants.py                              |      277 |        0 |    100% |           |
| domain/core/entities.py                               |      189 |        4 |     98% |189-190, 202-203 |
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
| infrastructure/database.py                            |      131 |       41 |     69% |109-110, 119-123, 149-150, 161-171, 178-179, 183-184, 205-206, 224-225, 249-271, 297-298 |
| infrastructure/external/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| infrastructure/external/crypto.py                     |       38 |        3 |     92% |     80-82 |
| infrastructure/external/notification.py               |       96 |       20 |     79% |149-150, 164-166, 171-177, 189-208 |
| infrastructure/external/sec\_edgar.py                 |      188 |       38 |     80% |78-83, 104-105, 119, 125-129, 135-139, 212-214, 277-279, 315-316, 393-395, 419, 429-431, 439, 442, 448-449 |
| infrastructure/finmind\_adapter.py                    |        1 |        1 |      0% |         6 |
| infrastructure/jquants\_adapter.py                    |        1 |        0 |    100% |           |
| infrastructure/market\_data/\_\_init\_\_.py           |        1 |        0 |    100% |           |
| infrastructure/market\_data/finmind\_adapter.py       |       55 |        2 |     96% |     55-56 |
| infrastructure/market\_data/jquants\_adapter.py       |       37 |        9 |     76% | 20, 26-34 |
| infrastructure/market\_data/market\_data.py           |     1070 |      475 |     56% |191, 321-322, 379, 404-412, 439, 450-452, 460-462, 472, 483-487, 500, 525-527, 542-543, 580, 611-633, 651-653, 668, 732, 749, 752-758, 764-766, 809-810, 828-840, 894-895, 900-907, 915, 936-950, 988-989, 1015, 1031, 1070, 1088-1090, 1154-1166, 1179-1232, 1246-1277, 1282, 1298-1342, 1352-1370, 1436, 1450-1466, 1475, 1496-1510, 1524-1561, 1570-1580, 1588-1625, 1634-1644, 1649-1656, 1670-1704, 1738-1750, 1797, 1804, 1809, 1816, 1819-1821, 1853-1867, 1881-1925, 1939-1971, 1982-1988, 1993-1997, 2112, 2124, 2140-2165, 2267-2293, 2319-2327, 2339, 2390, 2472-2474, 2486, 2534-2535, 2551-2642 |
| infrastructure/market\_data/market\_data\_resolver.py |       73 |       23 |     68% |19-25, 43-44, 47-48, 54-55, 58-59, 62, 65, 68, 71, 121, 124, 127, 132 |
| infrastructure/market\_data\_resolver.py              |        1 |        1 |      0% |         6 |
| infrastructure/notification.py                        |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py            |        1 |        0 |    100% |           |
| infrastructure/persistence/repositories.py            |      454 |       53 |     88% |61-69, 93-101, 111, 127-140, 145-159, 171, 184-186, 354-357, 362-366, 383, 388-389, 478, 609, 1282-1285, 1304-1307, 1342-1345 |
| infrastructure/repositories.py                        |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                          |        1 |        0 |    100% |           |
| **TOTAL**                                             | **7683** | **1065** | **86%** |           |


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
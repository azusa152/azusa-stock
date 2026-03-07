# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| api/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| api/dependencies.py                                   |       12 |        0 |    100% |           |
| api/rate\_limit.py                                    |        3 |        0 |    100% |           |
| api/routes/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| api/routes/backtest\_routes.py                        |       40 |        1 |     98% |        62 |
| api/routes/crypto\_routes.py                          |       18 |        0 |    100% |           |
| api/routes/forex\_routes.py                           |        6 |        0 |    100% |           |
| api/routes/fx\_watch\_routes.py                       |       50 |        0 |    100% |           |
| api/routes/guru\_routes.py                            |      149 |        4 |     97% |211, 336, 572-573 |
| api/routes/holding\_routes.py                         |       93 |       10 |     89% |173-183, 211-214, 269 |
| api/routes/networth\_routes.py                        |       46 |        3 |     93% |50, 160-161 |
| api/routes/persona\_routes.py                         |       35 |        0 |    100% |           |
| api/routes/preferences\_routes.py                     |       16 |        0 |    100% |           |
| api/routes/scan\_routes.py                            |       82 |        2 |     98% |  150, 186 |
| api/routes/snapshot\_routes.py                        |       80 |        8 |     90% |37-38, 41-42, 56-57, 74, 116 |
| api/routes/stock\_routes.py                           |      159 |       44 |     72% |135-138, 151, 157-168, 176, 190, 254-255, 264-267, 287, 303, 309, 334-339, 351-353, 367-378, 390-392, 403-405, 418-420 |
| api/routes/telegram\_routes.py                        |       19 |        0 |    100% |           |
| api/routes/thesis\_routes.py                          |       19 |        0 |    100% |           |
| api/schemas/\_\_init\_\_.py                           |       11 |        0 |    100% |           |
| api/schemas/backtest.py                               |        8 |        0 |    100% |           |
| api/schemas/common.py                                 |        7 |        0 |    100% |           |
| api/schemas/crypto.py                                 |        6 |        0 |    100% |           |
| api/schemas/fx\_watch.py                              |       21 |        0 |    100% |           |
| api/schemas/guru.py                                   |      108 |        0 |    100% |           |
| api/schemas/guru\_analytics.py                        |       24 |        0 |    100% |           |
| api/schemas/networth.py                               |       65 |        9 |     86% |39, 59-61, 67-74 |
| api/schemas/notification.py                           |       36 |        0 |    100% |           |
| api/schemas/portfolio.py                              |      108 |        0 |    100% |           |
| api/schemas/scan.py                                   |       87 |        0 |    100% |           |
| api/schemas/stock.py                                  |       59 |        1 |     98% |        78 |
| application/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| application/formatters.py                             |      113 |        8 |     93% |82-83, 122, 272, 274, 301-303 |
| application/guru/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| application/guru/backtest\_service.py                 |      109 |       16 |     85% |62, 72, 89, 92-97, 148, 200, 212-214, 235-236, 239, 244, 259-260 |
| application/guru/guru\_service.py                     |       47 |        2 |     96% |  103, 105 |
| application/guru/heatmap\_service.py                  |       83 |       17 |     80% |40, 55-56, 62-63, 66-67, 72-77, 98, 133, 141, 149 |
| application/guru/resonance\_service.py                |       95 |       12 |     87% |39, 71, 77-78, 81-82, 87-92 |
| application/messaging/\_\_init\_\_.py                 |        3 |        0 |    100% |           |
| application/messaging/notification\_service.py        |      253 |       19 |     92% |52-56, 61-66, 122, 209-210, 266-267, 385, 464-465 |
| application/messaging/telegram\_settings\_service.py  |       54 |        1 |     98% |        85 |
| application/messaging/webhook\_service.py             |      130 |       14 |     89% |80, 141-149, 194-195, 206-207, 297-298 |
| application/portfolio/\_\_init\_\_.py                 |       11 |        0 |    100% |           |
| application/portfolio/crypto\_service.py              |       26 |        8 |     69% |15, 36, 49-53, 57 |
| application/portfolio/fx\_watch\_service.py           |      115 |        2 |     98% |  151, 379 |
| application/portfolio/holding\_service.py             |      105 |        1 |     99% |        56 |
| application/portfolio/net\_worth\_service.py          |      215 |       37 |     83% |49-54, 139, 141, 143, 145, 147, 149, 151, 155, 208, 211-212, 231, 330, 373-384, 404, 429-438, 471-472, 487-488 |
| application/portfolio/rebalance\_service.py           |      455 |       60 |     87% |121-149, 160, 226-227, 235-236, 243-249, 293, 332-333, 492, 617, 773, 928, 990, 1020, 1024-1039, 1065, 1073-1074, 1151-1158, 1164-1167, 1220, 1227, 1250-1253 |
| application/portfolio/snapshot\_service.py            |      110 |        7 |     94% |174-175, 179, 182-186, 190 |
| application/portfolio/stress\_test\_service.py        |       39 |        0 |    100% |           |
| application/scan/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| application/scan/backfill\_service.py                 |       77 |        8 |     90% |68-71, 82-84, 151-153 |
| application/scan/backtest\_service.py                 |       80 |        2 |     98% |   45, 149 |
| application/scan/prewarm\_service.py                  |      164 |       20 |     88% |53, 77-80, 146, 158-159, 336-352, 387-388, 413-414 |
| application/scan/scan\_service.py                     |      317 |       73 |     77% |81-84, 127-130, 208, 247, 256, 266, 286, 297, 307, 317, 340, 342, 344, 399-401, 451, 511-534, 539, 567, 575-576, 579, 620, 632-634, 649-650, 696-701, 734-746, 779-784, 789-797 |
| application/services.py                               |        8 |        0 |    100% |           |
| application/settings/\_\_init\_\_.py                  |        2 |        0 |    100% |           |
| application/settings/persona\_service.py              |       53 |        0 |    100% |           |
| application/settings/preferences\_service.py          |       40 |        2 |     95% |    60, 87 |
| application/stock/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| application/stock/filing\_service.py                  |      193 |        9 |     95% |170-177, 217-221, 298, 302, 375 |
| application/stock/stock\_service.py                   |      344 |       54 |     84% |311, 318-319, 345-349, 390-392, 503, 508, 591, 609-610, 617-618, 622-624, 631-635, 645-650, 701-714, 727-728, 733-734, 738-739, 795-802, 843-857 |
| domain/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| domain/analysis/\_\_init\_\_.py                       |        5 |        0 |    100% |           |
| domain/analysis/analysis.py                           |      264 |        0 |    100% |           |
| domain/analysis/backtest.py                           |      115 |        9 |     92% |91, 101, 122, 126, 136-137, 236, 242, 272 |
| domain/analysis/fx\_analysis.py                       |      123 |        1 |     99% |        43 |
| domain/analysis/guru\_backtest.py                     |      136 |       12 |     91% |54, 75, 78, 111, 116, 130, 146, 151, 158, 171, 201, 240 |
| domain/analysis/smart\_money.py                       |       27 |        1 |     96% |        35 |
| domain/constants.py                                   |        1 |        0 |    100% |           |
| domain/core/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| domain/core/constants.py                              |      291 |        0 |    100% |           |
| domain/core/entities.py                               |      191 |        4 |     98% |195-196, 208-209 |
| domain/core/enums.py                                  |       61 |        0 |    100% |           |
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
| infrastructure/database.py                            |      131 |       41 |     69% |113-114, 123-127, 153-154, 165-175, 182-183, 187-188, 209-210, 228-229, 253-275, 301-302 |
| infrastructure/external/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| infrastructure/external/crypto.py                     |       38 |        3 |     92% |     80-82 |
| infrastructure/external/notification.py               |       96 |       20 |     79% |149-150, 164-166, 171-177, 189-208 |
| infrastructure/external/sec\_edgar.py                 |      188 |       38 |     80% |78-83, 104-105, 119, 125-129, 135-139, 212-214, 277-279, 315-316, 393-395, 419, 429-431, 439, 442, 448-449 |
| infrastructure/finmind\_adapter.py                    |        1 |        1 |      0% |         6 |
| infrastructure/jquants\_adapter.py                    |        1 |        0 |    100% |           |
| infrastructure/market\_data/\_\_init\_\_.py           |        2 |        0 |    100% |           |
| infrastructure/market\_data/crypto\_adapter.py        |      211 |      101 |     52% |84-89, 96, 102, 111-112, 123-127, 141-157, 165-166, 173-174, 185-188, 192-194, 200, 202, 211, 222-225, 235, 239, 241, 247, 251-252, 266, 270, 273, 285-293, 299-302, 306-323, 328-330, 335-372, 376-378 |
| infrastructure/market\_data/finmind\_adapter.py       |       55 |        2 |     96% |     55-56 |
| infrastructure/market\_data/jquants\_adapter.py       |       37 |        9 |     76% | 20, 26-34 |
| infrastructure/market\_data/market\_data.py           |     1070 |      474 |     56% |191, 321-322, 379, 404-412, 439, 450-452, 460-462, 483-487, 500, 525-527, 542-543, 580, 611-633, 651-653, 668, 732, 749, 752-758, 764-766, 809-810, 828-840, 894-895, 900-907, 915, 936-950, 988-989, 1015, 1031, 1070, 1088-1090, 1154-1166, 1179-1232, 1246-1277, 1282, 1298-1342, 1352-1370, 1436, 1450-1466, 1475, 1496-1510, 1524-1561, 1570-1580, 1588-1625, 1634-1644, 1649-1656, 1670-1704, 1738-1750, 1797, 1804, 1809, 1816, 1819-1821, 1853-1867, 1881-1925, 1939-1971, 1982-1988, 1993-1997, 2112, 2124, 2140-2165, 2267-2293, 2319-2327, 2339, 2390, 2472-2474, 2486, 2534-2535, 2551-2642 |
| infrastructure/market\_data/market\_data\_resolver.py |       73 |       23 |     68% |19-25, 43-44, 47-48, 54-55, 58-59, 62, 65, 68, 71, 121, 124, 127, 132 |
| infrastructure/market\_data\_resolver.py              |        1 |        1 |      0% |         6 |
| infrastructure/notification.py                        |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py            |        1 |        0 |    100% |           |
| infrastructure/persistence/repositories.py            |      454 |       53 |     88% |61-69, 93-101, 111, 127-140, 145-159, 171, 184-186, 354-357, 362-366, 383, 388-389, 478, 609, 1283-1286, 1305-1308, 1343-1346 |
| infrastructure/repositories.py                        |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                          |        1 |        0 |    100% |           |
| **TOTAL**                                             | **8483** | **1257** | **85%** |           |


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
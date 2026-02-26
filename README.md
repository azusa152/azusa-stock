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
| api/routes/scan\_routes.py                            |       82 |        2 |     98% |  150, 186 |
| api/routes/snapshot\_routes.py                        |       80 |        8 |     90% |37-38, 41-42, 56-57, 74, 116 |
| api/routes/stock\_routes.py                           |      151 |       44 |     71% |126-129, 142, 148-159, 167, 181, 245-246, 255-258, 278, 294, 300, 310-315, 327-329, 343-354, 366-368, 379-381, 394-396 |
| api/routes/telegram\_routes.py                        |       19 |        0 |    100% |           |
| api/routes/thesis\_routes.py                          |       19 |        0 |    100% |           |
| api/schemas/\_\_init\_\_.py                           |        7 |        0 |    100% |           |
| api/schemas/common.py                                 |        7 |        0 |    100% |           |
| api/schemas/fx\_watch.py                              |       21 |        0 |    100% |           |
| api/schemas/guru.py                                   |      108 |        0 |    100% |           |
| api/schemas/notification.py                           |       36 |        0 |    100% |           |
| api/schemas/portfolio.py                              |      103 |        0 |    100% |           |
| api/schemas/scan.py                                   |       87 |        0 |    100% |           |
| api/schemas/stock.py                                  |       45 |        1 |     98% |        77 |
| application/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| application/formatters.py                             |      113 |        8 |     93% |82-83, 122, 272, 274, 301-303 |
| application/guru/\_\_init\_\_.py                      |        2 |        0 |    100% |           |
| application/guru/guru\_service.py                     |       47 |        2 |     96% |  103, 105 |
| application/guru/resonance\_service.py                |       53 |        0 |    100% |           |
| application/messaging/\_\_init\_\_.py                 |        3 |        0 |    100% |           |
| application/messaging/notification\_service.py        |      262 |       19 |     93% |52-56, 61-66, 122, 209-210, 264-265, 383, 461-462 |
| application/messaging/telegram\_settings\_service.py  |       54 |        1 |     98% |        82 |
| application/messaging/webhook\_service.py             |      130 |       14 |     89% |80, 141-149, 194-195, 206-207, 297-298 |
| application/portfolio/\_\_init\_\_.py                 |        5 |        0 |    100% |           |
| application/portfolio/fx\_watch\_service.py           |      115 |        2 |     98% |  151, 379 |
| application/portfolio/holding\_service.py             |       82 |        0 |    100% |           |
| application/portfolio/rebalance\_service.py           |      398 |       28 |     93% |121-124, 188-189, 209, 381, 506, 798, 860, 890, 894-909, 935, 943-944, 1025-1028, 1081, 1088, 1111-1114 |
| application/portfolio/snapshot\_service.py            |      103 |        7 |     93% |162-163, 167, 170-174, 178 |
| application/portfolio/stress\_test\_service.py        |       39 |        0 |    100% |           |
| application/scan/\_\_init\_\_.py                      |        2 |        0 |    100% |           |
| application/scan/prewarm\_service.py                  |      138 |       19 |     86% |48, 72-75, 130-131, 273-289, 317-318, 343-344 |
| application/scan/scan\_service.py                     |      307 |       69 |     78% |78, 109-112, 175, 208, 217, 227, 247, 258, 278, 303, 360-362, 412, 472-495, 500, 525, 531-534, 537, 581, 593-595, 610-611, 657-662, 695-707, 740-745, 750-758 |
| application/services.py                               |        6 |        0 |    100% |           |
| application/settings/\_\_init\_\_.py                  |        2 |        0 |    100% |           |
| application/settings/persona\_service.py              |       53 |        0 |    100% |           |
| application/settings/preferences\_service.py          |       40 |        2 |     95% |    56, 83 |
| application/stock/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| application/stock/filing\_service.py                  |      193 |       11 |     94% |170-177, 217-221, 298, 302, 375, 400-402 |
| application/stock/stock\_service.py                   |      326 |       48 |     85% |305, 312-313, 339-343, 384-386, 497, 502, 585, 603-604, 611-612, 616-618, 625-629, 639-644, 695-696, 700-701, 744-751, 787-801 |
| domain/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| domain/analysis/\_\_init\_\_.py                       |        3 |        0 |    100% |           |
| domain/analysis/analysis.py                           |      242 |        0 |    100% |           |
| domain/analysis/fx\_analysis.py                       |      123 |        1 |     99% |        43 |
| domain/analysis/smart\_money.py                       |       27 |        1 |     96% |        35 |
| domain/constants.py                                   |        1 |        0 |    100% |           |
| domain/core/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| domain/core/constants.py                              |      251 |        0 |    100% |           |
| domain/core/entities.py                               |      163 |        4 |     98% |189-190, 202-203 |
| domain/core/enums.py                                  |       60 |        0 |    100% |           |
| domain/core/formatters.py                             |       36 |        0 |    100% |           |
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
| infrastructure/external/sec\_edgar.py                 |      188 |       38 |     80% |77-82, 103-104, 118, 124-128, 134-138, 211-213, 276-278, 314-315, 392-394, 418, 428-430, 438, 441, 447-448 |
| infrastructure/finmind\_adapter.py                    |        1 |        1 |      0% |         6 |
| infrastructure/jquants\_adapter.py                    |        1 |        0 |    100% |           |
| infrastructure/market\_data/\_\_init\_\_.py           |        1 |        0 |    100% |           |
| infrastructure/market\_data/finmind\_adapter.py       |       55 |        2 |     96% |     55-56 |
| infrastructure/market\_data/jquants\_adapter.py       |       37 |        9 |     76% | 19, 25-33 |
| infrastructure/market\_data/market\_data.py           |      966 |      490 |     49% |177, 296-297, 352, 377-385, 412, 421-424, 430-433, 447-451, 459-467, 482-488, 503-504, 541, 572-594, 612-614, 629, 719-720, 738-750, 782-783, 788-795, 803, 824-838, 876-877, 903, 919, 958, 976-978, 995, 1013-1025, 1038-1091, 1105-1136, 1141, 1157-1201, 1211-1229, 1243-1276, 1284-1287, 1301-1320, 1334-1371, 1380-1390, 1398-1435, 1444-1454, 1459-1466, 1480-1514, 1548-1560, 1607, 1614, 1619, 1626, 1629-1631, 1663-1677, 1691-1735, 1749-1781, 1792-1798, 1803-1807, 1822-1909, 1922, 1934, 1950-1975, 2120, 2216, 2264-2265, 2281-2372 |
| infrastructure/market\_data/market\_data\_resolver.py |       73 |       23 |     68% |18-24, 42-43, 46-47, 53-54, 57-58, 61, 64, 67, 70, 120, 123, 126, 131 |
| infrastructure/market\_data\_resolver.py              |        1 |        1 |      0% |         6 |
| infrastructure/notification.py                        |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py            |        1 |        0 |    100% |           |
| infrastructure/persistence/repositories.py            |      450 |       53 |     88% |59-67, 91-99, 109, 125-138, 143-157, 169, 182-184, 329-332, 337-341, 358, 363-364, 453, 584, 1257-1260, 1279-1282, 1317-1320 |
| infrastructure/repositories.py                        |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                          |        1 |        0 |    100% |           |
| **TOTAL**                                             | **6758** |  **993** | **85%** |           |


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
# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| api/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| api/dependencies.py                                   |       12 |        0 |    100% |           |
| api/rate\_limit.py                                    |        3 |        0 |    100% |           |
| api/routes/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| api/routes/forex\_routes.py                           |        6 |        0 |    100% |           |
| api/routes/fx\_watch\_routes.py                       |       43 |        0 |    100% |           |
| api/routes/guru\_routes.py                            |      115 |        3 |     97% |191, 475-476 |
| api/routes/holding\_routes.py                         |       82 |       16 |     80% |161-168, 184-199, 254, 266-267 |
| api/routes/persona\_routes.py                         |       30 |        9 |     70% |39, 58-61, 89-90, 107-108 |
| api/routes/preferences\_routes.py                     |       16 |        0 |    100% |           |
| api/routes/scan\_routes.py                            |       74 |        2 |     97% |  126, 162 |
| api/routes/snapshot\_routes.py                        |       54 |       12 |     78% |29-30, 42-48, 84, 151-153 |
| api/routes/stock\_routes.py                           |      144 |       43 |     70% |121, 134, 140-151, 159, 173, 235-236, 245-248, 268, 282, 288, 298-303, 315-317, 331-342, 354-356, 367-369, 382-384 |
| api/routes/telegram\_routes.py                        |       19 |        0 |    100% |           |
| api/routes/thesis\_routes.py                          |       19 |        0 |    100% |           |
| api/schemas/\_\_init\_\_.py                           |        7 |        0 |    100% |           |
| api/schemas/common.py                                 |        7 |        0 |    100% |           |
| api/schemas/fx\_watch.py                              |       21 |        0 |    100% |           |
| api/schemas/guru.py                                   |      108 |        0 |    100% |           |
| api/schemas/notification.py                           |       34 |        0 |    100% |           |
| api/schemas/portfolio.py                              |      103 |        0 |    100% |           |
| api/schemas/scan.py                                   |       76 |        0 |    100% |           |
| api/schemas/stock.py                                  |       44 |        1 |     98% |        77 |
| application/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| application/formatters.py                             |      101 |        3 |     97% |82-83, 122 |
| application/guru/\_\_init\_\_.py                      |        2 |        0 |    100% |           |
| application/guru/guru\_service.py                     |       47 |        2 |     96% |  103, 105 |
| application/guru/resonance\_service.py                |       53 |        0 |    100% |           |
| application/messaging/\_\_init\_\_.py                 |        3 |        0 |    100% |           |
| application/messaging/notification\_service.py        |      253 |       18 |     93% |51-55, 60-65, 202-203, 257-258, 371, 449-450 |
| application/messaging/telegram\_settings\_service.py  |       54 |        1 |     98% |        82 |
| application/messaging/webhook\_service.py             |      130 |       14 |     89% |80, 141-149, 194-195, 206-207, 297-298 |
| application/portfolio/\_\_init\_\_.py                 |        5 |        0 |    100% |           |
| application/portfolio/fx\_watch\_service.py           |      112 |        1 |     99% |       149 |
| application/portfolio/holding\_service.py             |       82 |        0 |    100% |           |
| application/portfolio/rebalance\_service.py           |      359 |       38 |     89% |101-104, 179, 337, 438, 727, 785, 810-837, 845-858, 934-937, 990, 997, 1020-1023 |
| application/portfolio/snapshot\_service.py            |       45 |        0 |    100% |           |
| application/portfolio/stress\_test\_service.py        |       39 |        0 |    100% |           |
| application/scan/\_\_init\_\_.py                      |        2 |        0 |    100% |           |
| application/scan/prewarm\_service.py                  |      137 |       19 |     86% |47, 77-80, 127-128, 256-272, 300-301, 326-327 |
| application/scan/scan\_service.py                     |      263 |       55 |     79% |77, 108-111, 174, 207, 216, 226, 246, 257, 277, 302, 359-361, 404, 443-447, 452, 477, 483-486, 489, 533, 545-547, 562-563, 588-600, 633-638, 643-651 |
| application/services.py                               |        6 |        0 |    100% |           |
| application/settings/\_\_init\_\_.py                  |        2 |        0 |    100% |           |
| application/settings/persona\_service.py              |       53 |        0 |    100% |           |
| application/settings/preferences\_service.py          |       36 |        1 |     97% |        75 |
| application/stock/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| application/stock/filing\_service.py                  |      191 |       11 |     94% |162-169, 209-213, 290, 294, 365, 387-389 |
| application/stock/stock\_service.py                   |      273 |       30 |     89% |297, 304-305, 331-335, 376-378, 489, 494, 607-608, 612-613, 652-659, 695-709 |
| domain/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| domain/analysis/\_\_init\_\_.py                       |        3 |        0 |    100% |           |
| domain/analysis/analysis.py                           |      159 |        6 |     96% |58, 84, 97, 102, 179, 432 |
| domain/analysis/fx\_analysis.py                       |      123 |        1 |     99% |        41 |
| domain/analysis/smart\_money.py                       |       27 |        1 |     96% |        35 |
| domain/constants.py                                   |        1 |        0 |    100% |           |
| domain/core/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| domain/core/constants.py                              |      212 |        0 |    100% |           |
| domain/core/entities.py                               |      146 |        2 |     99% |   182-183 |
| domain/core/enums.py                                  |       58 |        0 |    100% |           |
| domain/core/formatters.py                             |       36 |        0 |    100% |           |
| domain/core/protocols.py                              |        3 |        0 |    100% |           |
| domain/entities.py                                    |        1 |        0 |    100% |           |
| domain/enums.py                                       |        1 |        0 |    100% |           |
| domain/formatters.py                                  |        1 |        0 |    100% |           |
| domain/fx\_analysis.py                                |        1 |        0 |    100% |           |
| domain/portfolio/\_\_init\_\_.py                      |        3 |        0 |    100% |           |
| domain/portfolio/rebalance.py                         |       41 |        0 |    100% |           |
| domain/portfolio/stress\_test.py                      |       40 |        0 |    100% |           |
| domain/portfolio/withdrawal.py                        |      153 |       10 |     93% |72, 86, 103, 107, 113, 117, 146, 225, 239, 263 |
| domain/protocols.py                                   |        1 |        0 |    100% |           |
| domain/rebalance.py                                   |        1 |        0 |    100% |           |
| domain/smart\_money.py                                |        1 |        0 |    100% |           |
| domain/stress\_test.py                                |        1 |        0 |    100% |           |
| domain/withdrawal.py                                  |        1 |        0 |    100% |           |
| infrastructure/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| infrastructure/crypto.py                              |        1 |        0 |    100% |           |
| infrastructure/database.py                            |       99 |       25 |     75% |95-96, 105-109, 135-136, 147-157, 164-165, 169-170, 190-191, 222-223 |
| infrastructure/external/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| infrastructure/external/crypto.py                     |       38 |        3 |     92% |     80-82 |
| infrastructure/external/notification.py               |       47 |       30 |     36% |40-60, 65-67, 72-78, 90-109 |
| infrastructure/external/sec\_edgar.py                 |      188 |       38 |     80% |77-82, 103-104, 118, 124-128, 134-138, 211-213, 276-278, 314-315, 392-394, 418, 428-430, 438, 441, 447-448 |
| infrastructure/finmind\_adapter.py                    |        1 |        1 |      0% |         6 |
| infrastructure/jquants\_adapter.py                    |        1 |        0 |    100% |           |
| infrastructure/market\_data/\_\_init\_\_.py           |        1 |        0 |    100% |           |
| infrastructure/market\_data/finmind\_adapter.py       |       57 |        2 |     96% |     52-53 |
| infrastructure/market\_data/jquants\_adapter.py       |       37 |        9 |     76% | 19, 25-33 |
| infrastructure/market\_data/market\_data.py           |      902 |      448 |     50% |166, 285-286, 341, 366-374, 405-408, 414-417, 431-435, 441-444, 459-465, 480-482, 517, 547-569, 587-589, 604, 688-689, 702-714, 746-747, 752-759, 767, 811-812, 838, 854, 893, 911-913, 930, 948-960, 973-1026, 1040-1071, 1076, 1092-1136, 1146-1164, 1178-1211, 1219-1222, 1234-1237, 1251-1288, 1297-1307, 1315-1352, 1361-1371, 1376-1383, 1397-1431, 1444-1455, 1465-1477, 1524, 1531, 1536, 1543, 1546-1548, 1580-1594, 1608-1652, 1666-1698, 1706-1714, 1725, 1737, 1752-1782, 1809, 1813, 1932, 2014-2016, 2028, 2069-2160 |
| infrastructure/market\_data/market\_data\_resolver.py |       73 |       23 |     68% |18-24, 42-43, 46-47, 53-54, 57-58, 61, 64, 67, 70, 120, 123, 126, 131 |
| infrastructure/market\_data\_resolver.py              |        1 |        1 |      0% |         6 |
| infrastructure/notification.py                        |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py            |        1 |        0 |    100% |           |
| infrastructure/persistence/repositories.py            |      402 |       34 |     92% |58-66, 90-98, 104, 252-255, 260-264, 281, 286-287, 468, 1120-1123, 1142-1145, 1180-1183 |
| infrastructure/repositories.py                        |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                          |        1 |        0 |    100% |           |
| **TOTAL**                                             | **6133** |  **913** | **85%** |           |


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
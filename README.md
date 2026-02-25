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
| api/routes/guru\_routes.py                            |      107 |        3 |     97% |176, 419-420 |
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
| api/schemas/guru.py                                   |       72 |        0 |    100% |           |
| api/schemas/notification.py                           |       34 |        0 |    100% |           |
| api/schemas/portfolio.py                              |      103 |        0 |    100% |           |
| api/schemas/scan.py                                   |       76 |        0 |    100% |           |
| api/schemas/stock.py                                  |       44 |        1 |     98% |        77 |
| application/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| application/formatters.py                             |      101 |        3 |     97% |82-83, 122 |
| application/guru/\_\_init\_\_.py                      |        2 |        0 |    100% |           |
| application/guru/guru\_service.py                     |       39 |        0 |    100% |           |
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
| application/stock/filing\_service.py                  |      153 |        8 |     95% |161-168, 208-212, 286, 302 |
| application/stock/stock\_service.py                   |      273 |       30 |     89% |297, 304-305, 331-335, 376-378, 489, 494, 607-608, 612-613, 652-659, 695-709 |
| domain/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| domain/analysis/\_\_init\_\_.py                       |        3 |        0 |    100% |           |
| domain/analysis/analysis.py                           |      159 |        6 |     96% |58, 84, 97, 102, 179, 432 |
| domain/analysis/fx\_analysis.py                       |      123 |        1 |     99% |        41 |
| domain/analysis/smart\_money.py                       |       27 |        1 |     96% |        35 |
| domain/constants.py                                   |        1 |        0 |    100% |           |
| domain/core/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| domain/core/constants.py                              |      210 |        0 |    100% |           |
| domain/core/entities.py                               |      144 |        2 |     99% |   182-183 |
| domain/core/enums.py                                  |       47 |        0 |    100% |           |
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
| infrastructure/database.py                            |       99 |       25 |     75% |92-93, 102-106, 132-133, 144-154, 161-162, 166-167, 187-188, 219-220 |
| infrastructure/external/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| infrastructure/external/crypto.py                     |       38 |        3 |     92% |     80-82 |
| infrastructure/external/notification.py               |       47 |       30 |     36% |40-60, 65-67, 72-78, 90-109 |
| infrastructure/external/sec\_edgar.py                 |      188 |       38 |     80% |77-82, 103-104, 118, 124-128, 134-138, 211-213, 276-278, 314-315, 392-394, 418, 428-430, 438, 441, 447-448 |
| infrastructure/finmind\_adapter.py                    |        1 |        1 |      0% |         6 |
| infrastructure/jquants\_adapter.py                    |        1 |        0 |    100% |           |
| infrastructure/market\_data/\_\_init\_\_.py           |        1 |        0 |    100% |           |
| infrastructure/market\_data/finmind\_adapter.py       |       57 |        2 |     96% |     52-53 |
| infrastructure/market\_data/jquants\_adapter.py       |       37 |        9 |     76% | 19, 25-33 |
| infrastructure/market\_data/market\_data.py           |      846 |      393 |     54% |164, 283-284, 339, 364-372, 403-406, 412-415, 429-433, 439-442, 457-463, 478-480, 515, 545-567, 585-587, 602, 686-687, 700-712, 744-745, 750-757, 765, 809-810, 836, 852, 891, 909-911, 928, 946-958, 971-1024, 1038-1069, 1074, 1090-1134, 1144-1162, 1176-1209, 1217-1220, 1232-1235, 1249-1286, 1295-1305, 1313-1350, 1359-1369, 1374-1381, 1395-1429, 1442-1453, 1463-1475, 1522, 1529, 1534, 1541, 1544-1546, 1578-1592, 1606-1650, 1664-1696, 1704-1712, 1723, 1735, 1750-1780, 1807, 1811, 1930, 2012-2014, 2026 |
| infrastructure/market\_data/market\_data\_resolver.py |       73 |       23 |     68% |18-24, 42-43, 46-47, 53-54, 57-58, 61, 64, 67, 70, 120, 123, 126, 131 |
| infrastructure/market\_data\_resolver.py              |        1 |        1 |      0% |         6 |
| infrastructure/notification.py                        |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py            |        1 |        0 |    100% |           |
| infrastructure/persistence/repositories.py            |      289 |       34 |     88% |58-66, 90-98, 104, 252-255, 260-264, 281, 286-287, 468, 811-814, 833-836, 871-874 |
| infrastructure/repositories.py                        |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                          |        1 |        0 |    100% |           |
| **TOTAL**                                             | **5859** |  **853** | **85%** |           |


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